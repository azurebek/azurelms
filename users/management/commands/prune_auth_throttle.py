"""Muddati o'tgan auth cheklov hisoblagichlarini o'chiradi (PUB1.0c).

    python manage.py prune_auth_throttle

Har yozuvdan keyin servis o'zi kichik bo'lak tozalaydi, ya'ni jadval odatda bu
buyruqsiz ham o'smaydi. Buyruq Control Center "jadval katta" ogohlantirishidan
keyin yoki cron'dan to'liq tozalash uchun. Qayta yugurish xavfsiz: faqat oynasi
tugagan qatorlar o'chadi, faol blok saqlanadi.
"""

from django.core.management.base import BaseCommand

from users.auth_abuse import prune_expired


class Command(BaseCommand):
    help = "Muddati o'tgan auth cheklov hisoblagichlarini o'chiradi"

    def handle(self, *args, **options):
        deleted = prune_expired()
        self.stdout.write(f"O'chirildi: {deleted} ta muddati o'tgan hisoblagich.")
