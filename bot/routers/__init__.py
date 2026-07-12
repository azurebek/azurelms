"""Bot router'lari — modul boshiga bitta Router, shu yerda yig'iladi.

Tartib muhim: guruh buyruqlari avval, shaxsiy chat (onboarding/workspace) keyin.
"""

import logging

from aiogram import Router
from aiogram.types.error_event import ErrorEvent

from bot.routers.group_ops import router as group_ops_router
from bot.routers.onboarding import router as onboarding_router
from bot.routers.workspace import router as workspace_router

logger = logging.getLogger(__name__)

root_router = Router(name="root")
root_router.include_router(group_ops_router)
root_router.include_router(workspace_router)
# onboarding oxirida — unda catch-all (erkin matn) handler bor
root_router.include_router(onboarding_router)


@root_router.errors()
async def error_boundary(event: ErrorEvent):
    """Handler xatosi userga 'o'lik tugma' bo'lib ko'rinmasin.

    Xato log'ga to'liq yoziladi; callback bo'lsa user qisqa alert oladi.
    """
    logger.exception("Bot handler xatosi: %s", event.exception)
    update = event.update
    try:
        if update.callback_query:
            await update.callback_query.answer(
                "Xatolik yuz berdi — birozdan so'ng qayta urinib ko'ring.",
                show_alert=True,
            )
        elif update.message:
            await update.message.answer("Xatolik yuz berdi — qayta urinib ko'ring.")
    except Exception:
        pass
    return True
