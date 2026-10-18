"""Katalog qidiruv proyeksiyasini tekshiradi yoki yangilaydi (PUB1.3a).

    python manage.py rebuild_course_search           # faqat hisobot
    python manage.py rebuild_course_search --apply   # eskirganlarini yozish

Odatiy saqlash, `bulk_create` va `update` proyeksiyani o'zi yangilaydi. Bu
buyruq normallashtirish qoidasi o'zgarganda yoki ma'lumot chetlab yuklanganda
(masalan, `loaddata`) kerak. Qayta yugurish xavfsiz.
"""

from django.core.management.base import BaseCommand

from courses.catalog import refresh_search_text
from courses.models import Course


class Command(BaseCommand):
    help = "Kurs katalogi qidiruv proyeksiyasini ko'rsatadi yoki yangilaydi"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Haqiqatan yozish (aks holda faqat hisobot)")

    def handle(self, *args, **options):
        count = refresh_search_text(Course.objects.all(), apply=options["apply"])
        verb = "Yangilandi" if options["apply"] else "Eskirgan (o'zgartirilmadi)"
        self.stdout.write(f"{verb}: {count} ta kurs.")
        if not options["apply"] and count:
            self.stdout.write("Yangilash uchun: python manage.py rebuild_course_search --apply")
