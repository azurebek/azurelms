from django.core.management.base import BaseCommand
from django.conf import settings
import asyncio
from bot.aiogram_app import bot, dp

class Command(BaseCommand):
    help = 'Runs the bot using long polling temporarily'

    def handle(self, *args, **options):
        asyncio.run(self.run_bot())

    async def run_bot(self):
        if getattr(settings, "TELEGRAM_MODE", "polling") != "polling":
            self.stdout.write(
                self.style.WARNING(
                    "TELEGRAM_MODE polling emas. Webhook rejimida runbot ishga tushirish tavsiya etilmaydi."
                )
            )
        self.stdout.write(self.style.SUCCESS("Starting bot with long polling..."))
        # First remove any existing webhooks
        await bot.delete_webhook()
        # Then start polling
        await dp.start_polling(bot)
