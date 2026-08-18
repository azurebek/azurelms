import logging
import os
import time

from django.conf import settings
from google import genai
from google.genai import types as genai_types

from ai.agent.types import ProviderResponse


logger = logging.getLogger(__name__)


#: Google yopgan modellar. `models.list` ularni hamon ro'yxatda ko'rsatadi,
#: ya'ni ro'yxat hisobga xos ruxsatni bildirmaydi — faqat haqiqiy
#: `generateContent` chaqiruvi `404 no longer available to new users` beradi.
#: Shuning uchun ro'yxat qo'lda yuritiladi va test uni sozlamalarga qarshi
#: tekshiradi.
RETIRED_MODELS = frozenset({
    # 2026-08-19: jonli 404. Google `gemini-3.5-flash-lite` ga o'tishni so'radi.
    "gemini-2.5-flash-lite",
})

DEFAULT_PRIMARY_MODEL = "gemini-3.1-flash-lite"
DEFAULT_FALLBACK_MODEL = "gemini-3.5-flash-lite"
DEFAULT_FREE_MODEL_ALLOWLIST = (
    DEFAULT_PRIMARY_MODEL,
    DEFAULT_FALLBACK_MODEL,
)
DEFAULT_MAX_OUTPUT_TOKENS = 640
DEFAULT_MAX_PROMPT_CHARS = 12_000
DEFAULT_REQUEST_TIMEOUT_MS = 8_000
DEFAULT_DEADLINE_MS = 20_000


def fallback_ai_reply(error) -> str:
    error_text = str(error).lower()
    if (
        "resource_exhausted" in error_text
        or "prepayment credits are depleted" in error_text
        or "quota" in error_text
        or "billing" in error_text
    ):
        return (
            "AI xizmati hozir limit yoki billing chekloviga tushdi. "
            "Admin API kreditini tekshirgandan keyin yana yozib ko'ring."
        )

    if "not found" in error_text and "models/" in error_text:
        return (
            "AI modeli konfiguratsiyasida muammo bor. "
            "Admin model ro'yxatini yangilagandan keyin yana urinib ko'ring."
        )

    return "Kechirasiz, hozircha ulanishda xatolik yuz berdi. Iltimos, birozdan so'ng qayta urinib ko'ring."


class GeminiProvider:
    # Gemini Google Search grounding orqali jonli web-qidiruvni qo'llab-quvvatlaydi
    supports_web_search = True
    supports_vision = False

    def __init__(self, *, api_key: str | None = None, sleep=time.sleep):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.sleep = sleep
        self.last_attempt_count = 0
        self.last_error_kind = None
        self.last_grounding_requested = False
        self.last_grounding_blocked = False

    def generate(
        self,
        *,
        prompt: str,
        selected_model: str | None = None,
        enable_web_search: bool = False,
    ) -> ProviderResponse:
        self.last_attempt_count = 0
        self.last_error_kind = None
        self.last_grounding_requested = bool(enable_web_search)
        grounding_allowed = (
            not bool(getattr(settings, "AI_FREE_TIER_MODE", True))
            and bool(getattr(settings, "GEMINI_GROUNDING_ENABLED", False))
        )
        self.last_grounding_blocked = self.last_grounding_requested and not grounding_allowed
        # Defense in depth: engine va UI guardlari chetlab o'tilsa ham Free
        # tier'da SDK config'iga google_search tool hech qachon kirmaydi.
        enable_web_search = self.last_grounding_requested and grounding_allowed

        # google-genai `api_key=None` bo'lsa ambient GOOGLE_API_KEY kabi SDK
        # credentiallarini avtomatik qabul qiladi. Project credentiali explicit
        # sozlanmagan paytda bu supply/control-plane gate'larini chetlab o'tib
        # kutilmagan real quota sarfiga olib kelmasligi uchun clientdan oldin
        # fail-closed qilamiz.
        if not str(self.api_key or "").strip():
            self.last_error_kind = "missing_credential"
            raise RuntimeError("GEMINI_API_KEY mavjud emas.")

        request_timeout_ms = self._positive_int_setting(
            "GEMINI_REQUEST_TIMEOUT_MS",
            DEFAULT_REQUEST_TIMEOUT_MS,
        )
        deadline_ms = self._positive_int_setting("GEMINI_DEADLINE_MS", DEFAULT_DEADLINE_MS)
        max_output_tokens = self._positive_int_setting(
            "GEMINI_MAX_OUTPUT_TOKENS",
            DEFAULT_MAX_OUTPUT_TOKENS,
        )
        max_prompt_chars = self._positive_int_setting(
            "GEMINI_MAX_PROMPT_CHARS",
            DEFAULT_MAX_PROMPT_CHARS,
        )
        prompt = self._bounded_prompt(prompt, max_prompt_chars=max_prompt_chars)
        client = genai.Client(
            api_key=self.api_key,
            http_options=self._http_options(min(request_timeout_ms, deadline_ms)),
        )
        candidates = self._model_candidates(selected_model)
        started_at = time.monotonic()
        model_index = 0
        last_error = None

        # Provider darajasida ham, SDK ichida ham jami ikki requestdan oshmaydi.
        # google_search unsupported bo'lsa, ikkinchi request o'sha modelda toolsiz
        # bajariladi va boshqa modelga uchinchi fan-out qilinmaydi.
        while model_index < len(candidates) and self.last_attempt_count < 2:
            model_name = candidates[model_index]
            elapsed_ms = int((time.monotonic() - started_at) * 1000)
            remaining_ms = deadline_ms - elapsed_ms
            if remaining_ms <= 0:
                last_error = TimeoutError("Gemini umumiy deadline tugadi")
                self.last_error_kind = "timeout"
                break

            timeout_ms = min(request_timeout_ms, remaining_ms)
            config = self._build_config(
                enable_web_search=enable_web_search,
                max_output_tokens=max_output_tokens,
                timeout_ms=timeout_ms,
            )
            self.last_attempt_count += 1
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config,
                )
                text = (response.text or "").strip()
                if not text:
                    raise RuntimeError(f"Bo'sh javob qaytdi (model={model_name})")
                web_search = self._extract_web_search_metadata(response) if enable_web_search else None
                return ProviderResponse(
                    text=text,
                    model_name=model_name,
                    web_search=web_search,
                    usage=self._extract_usage(response),
                )
            except Exception as exc:
                last_error = exc
                self.last_error_kind = self._error_kind(exc)
                if self.last_error_kind == "quota":
                    # 429/quota/billing boshqa model ham ayni project supply'ini
                    # sarflashi mumkin; shu logical request shu yerda to'xtaydi.
                    raise RuntimeError(
                        f"Gemini quota/billing cheklovi sabab request to'xtatildi: {exc}"
                    ) from exc
                if enable_web_search and self._is_unsupported_tool(exc):
                    logger.warning(
                        "Model %s google_search tool'ni qabul qilmadi, "
                        "qolgan yagona request web_search'siz bajariladi.",
                        model_name,
                    )
                    enable_web_search = False
                    continue
                model_index += 1

        raise RuntimeError(f"Barcha modellar muvaffaqiyatsiz tugadi. Last error: {last_error}")

    def _build_config(
        self,
        *,
        enable_web_search: bool,
        max_output_tokens: int,
        timeout_ms: int,
    ):
        tools = None
        if enable_web_search:
            try:
                tools = [genai_types.Tool(google_search=genai_types.GoogleSearch())]
            except Exception:
                logger.exception("Google Search tool konfiguratsiyasi yaratib bo'lmadi")
        try:
            return genai_types.GenerateContentConfig(
                max_output_tokens=max_output_tokens,
                tools=tools,
                http_options=self._http_options(timeout_ms),
            )
        except Exception:
            logger.exception("Gemini generate konfiguratsiyasi yaratib bo'lmadi")
            raise

    def _http_options(self, timeout_ms: int):
        return genai_types.HttpOptions(
            timeout=timeout_ms,
            retry_options=genai_types.HttpRetryOptions(attempts=1),
        )

    def _positive_int_setting(self, name: str, default: int) -> int:
        try:
            value = int(getattr(settings, name, default))
        except (TypeError, ValueError):
            return default
        return value if value > 0 else default

    def _bounded_prompt(self, prompt: str, *, max_prompt_chars: int) -> str:
        text = str(prompt or "")
        if len(text) <= max_prompt_chars:
            return text
        # Keep system/rubric instructions from the beginning and the latest user
        # question from the end. The removed middle is usually old dialogue/RAG.
        tail_size = max_prompt_chars // 3
        head_size = max_prompt_chars - tail_size - 32
        return f"{text[:head_size]}\n\n[CONTEXT TRUNCATED]\n\n{text[-tail_size:]}"

    def _extract_usage(self, response):
        """Gemini usage_metadata -> {prompt,completion,total}_tokens."""
        try:
            meta = getattr(response, "usage_metadata", None)
            if not meta:
                return None
            prompt = int(getattr(meta, "prompt_token_count", 0) or 0)
            completion = int(getattr(meta, "candidates_token_count", 0) or 0)
            total = int(getattr(meta, "total_token_count", 0) or (prompt + completion))
            if not (prompt or completion or total):
                return None
            return {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": total}
        except Exception:
            logger.exception("Gemini usage_metadata parse qilinmadi")
            return None

    def _extract_web_search_metadata(self, response):
        try:
            candidate = (response.candidates or [None])[0]
            grounding = getattr(candidate, "grounding_metadata", None)
            if not grounding:
                return None
            queries = list(getattr(grounding, "web_search_queries", None) or [])
            sources = []
            for index, chunk in enumerate(getattr(grounding, "grounding_chunks", None) or [], start=1):
                web = getattr(chunk, "web", None)
                if not web:
                    continue
                sources.append(
                    {
                        "number": index,
                        "title": getattr(web, "title", "") or "",
                        "uri": getattr(web, "uri", "") or "",
                    }
                )
            if not queries and not sources:
                return None
            return {"queries": queries, "sources": sources}
        except Exception:
            logger.exception("Web search grounding metadata parse qilinmadi")
            return None

    def _is_unsupported_tool(self, error) -> bool:
        error_text = str(error).lower()
        return (
            "google_search" in error_text
            and ("not supported" in error_text or "unsupported" in error_text or "invalid" in error_text)
        )

    def _model_candidates(self, selected_model: str | None) -> list[str]:
        allowlist = self._free_model_allowlist()
        configured_primary = str(
            getattr(settings, "GEMINI_PRIMARY_MODEL", DEFAULT_PRIMARY_MODEL) or ""
        ).strip()
        primary = selected_model if selected_model in allowlist else configured_primary
        if primary not in allowlist:
            primary = allowlist[0]

        configured_fallback = str(
            getattr(settings, "GEMINI_FALLBACK_MODEL", DEFAULT_FALLBACK_MODEL) or ""
        ).strip()
        fallback = configured_fallback if configured_fallback in allowlist else None
        if not fallback or fallback == primary:
            fallback = next((model for model in allowlist if model != primary), None)

        return [primary] + ([fallback] if fallback else [])

    def _free_model_allowlist(self) -> list[str]:
        raw_models = getattr(
            settings,
            "GEMINI_FREE_MODEL_ALLOWLIST",
            os.getenv(
                "GEMINI_FREE_MODEL_ALLOWLIST",
                ",".join(DEFAULT_FREE_MODEL_ALLOWLIST),
            ),
        )
        if isinstance(raw_models, str):
            raw_models = raw_models.split(",")
        try:
            models = [str(model).strip() for model in raw_models if str(model).strip()]
        except TypeError:
            models = []
        return list(dict.fromkeys(models)) or list(DEFAULT_FREE_MODEL_ALLOWLIST)

    def _error_kind(self, error) -> str:
        error_text = str(error).lower()
        if (
            "429" in error_text
            or "quota" in error_text
            or "rate limit" in error_text
            or "rate_limit" in error_text
            or "ratelimit" in error_text
            or "resource_exhausted" in error_text
            or "too many requests" in error_text
            or "billing" in error_text
            or "prepayment credits are depleted" in error_text
        ):
            return "quota"
        if isinstance(error, TimeoutError) or "timeout" in error_text or "deadline" in error_text:
            return "timeout"
        if self._is_unsupported_tool(error):
            return "unsupported_tool"
        if "bo'sh javob" in error_text:
            return "empty_response"
        return "provider_error"
