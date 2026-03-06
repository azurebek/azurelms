import os
import sys
import django
from pathlib import Path
import asyncio

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from asgiref.sync import sync_to_async
from bot.aiogram_app import bot, dp

async def main():
    print("Deleting any existing webhook...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    print("Starting Telegram Bot Polling (Long-Polling Mode)...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
