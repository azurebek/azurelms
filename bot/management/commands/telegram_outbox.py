"""Outbox yuboruvchi — webhook (prod) rejimida alohida worker sifatida.

Polling rejimida kerak emas (run_bot.py o'zi worker yurgizadi).

    python manage.py telegram_outbox          # bitta sikl (cron uchun)
    python manage.py telegram_outbox --loop   # doimiy worker
"""

import asyncio

from django.core.management.base import BaseCommand

from bot.aiogram_app import get_bot
from bot.outbox import outbox_worker, process_outbox_once


class Command(BaseCommand):
    help = "Telegram outbox'dagi bildirishnomalarni DM qilib yuboradi"

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true", help="Doimiy worker rejimi")

    def handle(self, *args, **options):
        bot = get_bot()
        if options["loop"]:
            asyncio.run(outbox_worker(bot))
            return
        sent = asyncio.run(self._run_once(bot))
        self.stdout.write(self.style.SUCCESS(f"Yuborildi: {sent} ta"))

    @staticmethod
    async def _run_once(bot):
        try:
            return await process_outbox_once(bot)
        finally:
            await bot.session.close()
