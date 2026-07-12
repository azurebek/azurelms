"""Aiogram Bot/Dispatcher — LAZY qurilish.

Muhim: Bot(token=...) IMPORT vaqtida qurilmaydi. Aks holda bo'sh/xato token
butun loyihani yiqitadi (URLconf bot.urls'ni yuklaydi → har runserver/check/
migrate shu modulni import qiladi). Bot faqat haqiqatan kerak bo'lganda
(webhook update kelganda yoki polling boshlanganda) quriladi.
"""

from aiogram import Bot, Dispatcher
from django.conf import settings

_bot = None
_dp = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        token = (getattr(settings, "TELEGRAM_BOT_TOKEN", "") or "").strip()
        if not token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN sozlanmagan — bot ishga tushira olmaydi. "
                ".env faylida token bering."
            )
        _bot = Bot(token=token)
    return _bot


def get_dispatcher() -> Dispatcher:
    global _dp
    if _dp is None:
        from bot.middleware import IdentityMiddleware
        from bot.routers import root_router

        _dp = Dispatcher()
        _dp.update.outer_middleware(IdentityMiddleware())
        _dp.include_router(root_router)
    return _dp
