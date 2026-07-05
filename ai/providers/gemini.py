import logging
import os
import time

from django.conf import settings
from google import genai
from google.genai import types as genai_types

from ai.agent.types import ProviderResponse


logger = logging.getLogger(__name__)


DEFAULT_MODEL_FALLBACKS = [
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.1-pro-preview",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-pro-latest",
]


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

    def generate(
        self,
        *,
        prompt: str,
        selected_model: str | None = None,
        enable_web_search: bool = False,
    ) -> ProviderResponse:
        client = genai.Client(api_key=self.api_key)
        candidates = self._model_candidates(selected_model)
        config = self._build_config(enable_web_search=enable_web_search)
        last_error = None

        for model_name in candidates:
            for attempt in range(2):
                try:
                    kwargs = {"model": model_name, "contents": prompt}
                    if config is not None:
                        kwargs["config"] = config
                    response = client.models.generate_content(**kwargs)
                    text = (response.text or "").strip()
                    if text:
                        web_search = self._extract_web_search_metadata(response) if enable_web_search else None
                        return ProviderResponse(
                            text=text,
                            model_name=model_name,
                            web_search=web_search,
                            usage=self._extract_usage(response),
                        )
                    raise RuntimeError(f"Bo'sh javob qaytdi (model={model_name})")
                except Exception as exc:
                    last_error = exc
                    if self._is_rate_limited(exc) and attempt == 0:
                        self.sleep(1.5)
                        continue
                    if enable_web_search and self._is_unsupported_tool(exc):
                        # Model bu modelda google_search'ni qo'llab-quvvatlamasa, tools'siz qayta urinamiz.
                        logger.warning(
                            "Model %s google_search tool'ni qabul qilmadi, web_search'siz qayta urinaman.",
                            model_name,
                        )
                        config = None
                        enable_web_search = False
                        continue
                    break

        raise RuntimeError(f"Barcha modellar muvaffaqiyatsiz tugadi. Last error: {last_error}")

    def _build_config(self, *, enable_web_search: bool):
        if not enable_web_search:
            return None
        try:
            return genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
            )
        except Exception:
            logger.exception("Google Search tool konfiguratsiyasi yaratib bo'lmadi")
            return None

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
        raw_models = os.getenv(
            "GEMINI_MODEL_FALLBACKS",
            ",".join(DEFAULT_MODEL_FALLBACKS),
        )
        configured_models = [model.strip() for model in raw_models.split(",") if model.strip()]
        selected = selected_model or DEFAULT_MODEL_FALLBACKS[0]
        candidates = [selected] + [model for model in configured_models if model != selected]
        return candidates or [DEFAULT_MODEL_FALLBACKS[0]]

    def _is_rate_limited(self, error) -> bool:
        error_text = str(error).lower()
        return (
            "429" in error_text
            or "quota" in error_text
            or "rate" in error_text
            or "resource_exhausted" in error_text
            or "too many requests" in error_text
        )
