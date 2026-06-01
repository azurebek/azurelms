"""Model provider integrations."""

from django.conf import settings

from .digitalocean import DigitalOceanProvider
from .gemini import GeminiProvider


def get_chat_provider():
    provider_name = getattr(settings, "AI_CHAT_PROVIDER", "gemini")
    if provider_name == "digitalocean":
        return DigitalOceanProvider()
    return GeminiProvider()
