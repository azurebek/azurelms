"""Model provider integrations."""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .digitalocean import DigitalOceanProvider
from .gemini import GeminiProvider


def get_chat_provider():
    provider_name = str(getattr(settings, "AI_CHAT_PROVIDER", "gemini") or "gemini").strip().lower()
    if provider_name == "digitalocean":
        if not bool(getattr(settings, "AI_ALLOW_DIGITALOCEAN", False)):
            raise ImproperlyConfigured(
                "AI_CHAT_PROVIDER=digitalocean is blocked by owner policy. "
                "Set AI_ALLOW_DIGITALOCEAN=True only after explicit production admission."
            )
        return DigitalOceanProvider()
    if provider_name == "gemini":
        return GeminiProvider()
    raise ImproperlyConfigured(
        f"Unknown AI_CHAT_PROVIDER={provider_name!r}; remote AI is fail-closed."
    )


def get_search_provider():
    """Gemini web-qidiruv adapterini qaytaradi; kalit bo'lmasa None."""
    provider = GeminiProvider()
    if getattr(provider, "supports_web_search", False) and getattr(provider, "api_key", None):
        return provider
    return None
