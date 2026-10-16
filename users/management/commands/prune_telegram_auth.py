"""Saqlash muddati o'tgan Telegram kirish sessiyalarini o'chiradi (PUB1.0d).

    python manage.py prune_telegram_auth

Har init'dan keyin servis o'zi kichik bo'lak tozalaydi, ya'ni jadval odatda
bu buyruqsiz ham o'smaydi. Buyruq cron yoki qo'lda to'liq tozalash uchun.
Qayta yugurish xavfsiz: faqat saqlash muddati tugagan qatorlar o'chadi, faol
oqimga tegilmaydi.
"""

from django.core.management.base import BaseCommand

from users.telegram_auth_service import purge_expired


class Command(BaseCommand):
    help = "Saqlash muddati o'tgan Telegram kirish sessiyalarini o'chiradi"

    def handle(self, *args, **options):
        deleted = purge_expired()
        self.stdout.write(f"O'chirildi: {deleted} ta eski Telegram kirish sessiyasi.")
