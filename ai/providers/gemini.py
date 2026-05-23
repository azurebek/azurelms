import os
import time

from django.conf import settings
from google import genai

from ai.agent.types import ProviderResponse


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
    def __init__(self, *, api_key: str | None = None, sleep=time.sleep):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.sleep = sleep

    def generate(self, *, prompt: str, selected_model: str | None = None) -> ProviderResponse:
        client = genai.Client(api_key=self.api_key)
        candidates = self._model_candidates(selected_model)
        last_error = None

        for model_name in candidates:
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    text = (response.text or "").strip()
                    if text:
                        return ProviderResponse(text=text, model_name=model_name)
                    raise RuntimeError(f"Bo'sh javob qaytdi (model={model_name})")
                except Exception as exc:
                    last_error = exc
                    if self._is_rate_limited(exc) and attempt == 0:
                        self.sleep(1.5)
                        continue
                    break

        raise RuntimeError(f"Barcha modellar muvaffaqiyatsiz tugadi. Last error: {last_error}")

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
