import logging
import os
import time

import requests
from django.conf import settings

from ai.agent.types import ProviderResponse


logger = logging.getLogger(__name__)

DEFAULT_MODEL_FALLBACKS = [
    "router:general",
    "deepseek-4-flash",
    "gemma-4-31B-it",
    "mistral-3-14B",
    "llama3.3-70b-instruct",
]


class DigitalOceanProvider:
    supports_web_search = False

    def __init__(self, *, api_key: str | None = None, session=None, sleep=time.sleep):
        self.api_key = api_key if api_key is not None else settings.DIGITALOCEAN_INFERENCE_API_KEY
        self.base_url = settings.DIGITALOCEAN_INFERENCE_BASE_URL
        self.default_model = settings.DIGITALOCEAN_INFERENCE_MODEL
        self.session = session or requests
        self.sleep = sleep

    def generate(
        self,
        *,
        prompt: str,
        selected_model: str | None = None,
        enable_web_search: bool = False,
    ) -> ProviderResponse:
        if not self.api_key:
            raise RuntimeError("DIGITALOCEAN_INFERENCE_API_KEY mavjud emas.")
        if enable_web_search:
            logger.warning("DigitalOcean provider uchun web search hali ulanmagan.")

        last_error = None
        for model_name in self._model_candidates(selected_model):
            for attempt in range(2):
                try:
                    response = self.session.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model_name,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 1200,
                        },
                        timeout=60,
                    )
                    response.raise_for_status()
                    payload = response.json()
                    text = (
                        (payload.get("choices") or [{}])[0]
                        .get("message", {})
                        .get("content", "")
                        .strip()
                    )
                    if text:
                        return ProviderResponse(text=text, model_name=model_name)
                    raise RuntimeError(f"Bo'sh javob qaytdi (model={model_name})")
                except Exception as exc:
                    last_error = exc
                    if self._is_rate_limited(exc) and attempt == 0:
                        self.sleep(1.5)
                        continue
                    break

        raise RuntimeError(f"Barcha DO modellari muvaffaqiyatsiz tugadi. Last error: {last_error}")

    def _model_candidates(self, selected_model: str | None) -> list[str]:
        raw_models = os.getenv(
            "DIGITALOCEAN_INFERENCE_MODEL_FALLBACKS",
            ",".join(DEFAULT_MODEL_FALLBACKS),
        )
        configured_models = [model.strip() for model in raw_models.split(",") if model.strip()]
        selected = selected_model if selected_model in configured_models else self.default_model
        candidates = [selected] + [model for model in configured_models if model != selected]
        return candidates or [self.default_model]

    def _is_rate_limited(self, error) -> bool:
        error_text = str(error).lower()
        return "429" in error_text or "rate" in error_text or "too many requests" in error_text
