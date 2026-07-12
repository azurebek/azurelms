import asyncio
import os
import sys

import django

# Setup Django Environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from bot.aiogram_app import get_bot, get_dispatcher  # noqa: E402
from bot.outbox import outbox_worker  # noqa: E402


async def main():
    bot = get_bot()
    dp = get_dispatcher()

    print("Deleting any existing webhook...")
    await bot.delete_webhook(drop_pending_updates=True)

    print("Starting outbox worker (platforma bildirishnomalari -> DM)...")
    outbox_task = asyncio.create_task(outbox_worker(bot))

    print("Starting Telegram Bot Polling (Long-Polling Mode)...")
    try:
        await dp.start_polling(bot)
    finally:
        outbox_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
