"""Ochiq sahifalardagi fayli yo'q rasm/videolar (PUB1.7b).

    python manage.py audit_public_media

Faqat o'qiydi: nashr etilgan blog, SIT, faol kurs, bosh sahifa, jamoa, fikrlar va
brend fayllarini saqlovchida (lokal disk yoki S3) tekshiradi va topilmaganlarini
ro'yxat qiladi. Hech narsa o'chirmaydi; tuzatish — tegishli muharrirda yangi fayl
yuklash yoki havolani olib tashlash.
"""

from django.core.management.base import BaseCommand

from frontend.public_media import missing_public_media


class Command(BaseCommand):
    help = "Ochiq sahifalardagi fayli yo'q media havolalari (faqat o'qiydi)"

    def handle(self, *args, **options):
        checked, missing = missing_public_media()
        for item in missing:
            self.stdout.write(f"YO'Q  {item.source} #{item.pk} · {item.field} · {item.name}")
        self.stdout.write(f"Tekshirildi: {checked}; fayli yo'q: {len(missing)}")
