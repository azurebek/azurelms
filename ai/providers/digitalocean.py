import logging
import os
import time

import requests
from django.conf import settings

from ai.agent.types import ProviderResponse


logger = logging.getLogger(__name__)


def _normalize_usage(usage) -> dict | None:
    """OpenAI-uslub usage blokini {prompt,completion,total}_tokens ga keltiradi."""
    if not isinstance(usage, dict):
        return None
    prompt = int(usage.get("prompt_tokens") or 0)
    completion = int(usage.get("completion_tokens") or 0)
    total = int(usage.get("total_tokens") or (prompt + completion))
    if not (prompt or completion or total):
        return None
    return {"prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": total}


# mistral-3-14B ataylab OLIB TASHLANGAN: o'zbekcha tarjimada kirill axlat/gibberish
# chiqaradi (jonli sinovda tasdiqlangan), shuning uchun foydalanuvchiga yuzli zanjirda emas.
DEFAULT_MODEL_FALLBACKS = [
    "router:general",
    "deepseek-4-flash",
    "gemma-4-31B-it",
    "llama3.3-70b-instruct",
]


class DigitalOceanProvider:
    supports_web_search = False
    # llama-4-maverick natively multimodal — rasm data-URL'lari bilan vision ishlaydi
    supports_vision = True

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
        images: list[str] | None = None,
    ) -> ProviderResponse:
        if not self.api_key:
            raise RuntimeError("DIGITALOCEAN_INFERENCE_API_KEY mavjud emas.")
        if enable_web_search:
            logger.warning("DigitalOcean provider uchun web search hali ulanmagan.")

        # Vision: OpenAI-compatible content array (matn + image_url data-URL'lar)
        if images:
            content = [{"type": "text", "text": prompt}] + [
                {"type": "image_url", "image_url": {"url": image_url}} for image_url in images
            ]
        else:
            content = prompt

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
                            "messages": [{"role": "user", "content": content}],
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
                        return ProviderResponse(
                            text=text,
                            model_name=model_name,
                            usage=_normalize_usage(payload.get("usage")),
                        )
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
