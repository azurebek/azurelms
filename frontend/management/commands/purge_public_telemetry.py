"""Voronka takror kalitlarini muddati o'tgach o'chirish (PUB1.8a).

    python manage.py purge_public_telemetry

Odatda kerak emas: birinchi hodisa har kuni bir marta o'zi tozalaydi. Kunlik sonlar
(shaxsiy ma'lumotsiz) o'chirilmaydi.
"""

from django.core.management.base import BaseCommand

from frontend.public_telemetry import prune_receipts


class Command(BaseCommand):
    help = "Muddati o'tgan voronka takror kalitlarini o'chiradi"

    def handle(self, *args, **options):
        self.stdout.write(f"O'chirildi: {prune_receipts()}")
