"""Model provider integrations."""

from django.conf import settings

from .digitalocean import DigitalOceanProvider
from .gemini import GeminiProvider


def get_chat_provider():
    provider_name = getattr(settings, "AI_CHAT_PROVIDER", "gemini")
    if provider_name == "digitalocean":
        return DigitalOceanProvider()
    return GeminiProvider()


def get_search_provider():
    """Web-qidiruvni qo'llab-quvvatlaydigan maxsus provayder yoki None.

    Asosiy provayder (maverick/DO) jonli qidira olmaydi. Bu funksiya FAQAT
    web-qidiruv kerak bo'lganda ishlatiladigan Gemini "mutaxassis"ini beradi
    — oddiy chat unga umuman tegmaydi, shu bois Gemini bepul kvotasi tejaladi.
    GEMINI_API_KEY yo'q bo'lsa None (jonli qidiruv o'chadi, chat ishlayveradi).
    """
    provider = GeminiProvider()
    if getattr(provider, "supports_web_search", False) and getattr(provider, "api_key", None):
        return provider
    return None
