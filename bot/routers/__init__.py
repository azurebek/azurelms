"""Bot router'lari — modul boshiga bitta Router, shu yerda yig'iladi.

Tartib muhim: guruh buyruqlari avval, shaxsiy chat (onboarding/workspace) keyin.
"""

from aiogram import Router

from bot.routers.group_ops import router as group_ops_router
from bot.routers.onboarding import router as onboarding_router

root_router = Router(name="root")
root_router.include_router(group_ops_router)
root_router.include_router(onboarding_router)
