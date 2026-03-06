from aiogram import Bot, Dispatcher
from django.conf import settings

# Initialize bot and dispatcher
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# We will import and register routers here later
from .handlers import router
dp.include_router(router)
