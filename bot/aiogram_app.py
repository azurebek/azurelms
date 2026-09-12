"""Aiogram Bot/Dispatcher — LAZY qurilish.

Muhim: Bot(token=...) IMPORT vaqtida qurilmaydi. Aks holda bo'sh/xato token
butun loyihani yiqitadi (URLconf bot.urls'ni yuklaydi → har runserver/check/
migrate shu modulni import qiladi). Bot faqat haqiqatan kerak bo'lganda
(webhook update kelganda yoki polling boshlanganda) quriladi.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from django.conf import settings

logger = logging.getLogger(__name__)

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
        from bot.middleware import IdentityMiddleware, MetricsMiddleware
        from bot.routers import root_router

        _dp = Dispatcher()
        # Tartib muhim: aiogram birinchi ro'yxatdan o'tgan middleware'ni eng
        # tashqi qatlam qiladi. MetricsMiddleware identity'dan OLDIN turadi,
        # ya'ni o'lchov identity'ning 3 DB so'rovini ham qamrab oladi —
        # foydalanuvchi kutgan to'liq vaqt o'lchanadi.
        _dp.update.outer_middleware(MetricsMiddleware())
        _dp.update.outer_middleware(IdentityMiddleware())
        _dp.include_router(root_router)
        _register_metrics_lifecycle(_dp)
    return _dp


def _register_metrics_lifecycle(dp: Dispatcher) -> None:
    """Polling davomida heartbeat yozadigan siklni ulaydi (T4).

    Nega `runbot` yoki `run_bot.py` da emas: ikkita polling kirish nuqtasi
    bor va har biriga qo'lda ulash bittasini unutish yo'li. aiogram ning
    `startup`/`shutdown` hodisalari esa `start_polling` bilan avtomatik
    ishga tushadi va webhook yo'lida (`feed_update`) umuman chaqirilmaydi —
    aynan kerakli xatti-harakat, chunki webhook'da uzoq yashovchi loop yo'q.
    """
    task_holder: dict = {}

    async def _start(**_kwargs):
        from bot.metrics import run_metrics_flusher

        task_holder["task"] = asyncio.create_task(run_metrics_flusher())

    async def _stop(**_kwargs):
        from asgiref.sync import sync_to_async

        from bot.metrics import safe_flush

        task = task_holder.pop("task", None)
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:  # noqa: BLE001 — to'xtatish yo'li jim bo'lishi kerak
                logger.warning("Kuzatuv sikli xato bilan tugadi", exc_info=True)
        # Rejali to'xtatishni halokatdan ajratib yozamiz: aks holda Control
        # Center "bot javob bermayapti" deb ko'rsatardi va owner mavjud
        # bo'lmagan nosozlikni qidirardi.
        await sync_to_async(safe_flush)(stopped=True)

    dp.startup.register(_start)
    dp.shutdown.register(_stop)
