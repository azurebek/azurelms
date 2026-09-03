"""Namuna kurs, dars va maqolalar bilan platformani to'ldiradi.

    python manage.py seed_content
    python manage.py seed_content --wipe

Mantiq `core/content_seed.py` da — buyruq yupqa qobiq va lokal gate.
QA uchun demo hisob va imtihon kerak bo'lsa, alohida `seed_demo` bor.

Diqqat: qayta yugurtirish **mavjud yozuvni yangilamaydi** (`get_or_create`),
faqat yetishmayotganini qo'shadi. Bu ataylab shunday — owner tahrirlagan
matn jimgina ustidan yozilmasligi kerak. Modul ichidagi matn o'zgargan
bo'lsa, avval `--wipe`, keyin qayta seed qiling.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.content_seed import (
    SampleContentError, seed_sample_content, wipe_sample_content,
)


class Command(BaseCommand):
    help = "Namuna kurs, dars, test va blog maqolalarini yaratadi (faqat lokal)"

    def add_arguments(self, parser):
        parser.add_argument("--wipe", action="store_true", help="Namuna kontentni o'chiradi")

    def handle(self, *args, **options):
        # Fail-closed: namuna kurslar haqiqiy katalogga tushsa, o'quvchi qaysi
        # kurs rost ekanini ajrata olmaydi.
        if not settings.IS_LOCAL:
            raise CommandError(
                "Bu buyruq faqat lokal muhitda ishlaydi (APP_ENV=local). "
                f"Joriy muhit: {settings.APP_ENV}."
            )

        if options["wipe"]:
            wipe_sample_content()
            self.stdout.write(self.style.SUCCESS("Namuna kontent o'chirildi."))
            return

        try:
            result = seed_sample_content()
        except SampleContentError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(self.style.SUCCESS("Namuna kontent tayyor."))
        for course in result["courses"]:
            self.stdout.write(f"  Kurs   : {course.title}")
        self.stdout.write(f"  Darslar: {result['lesson_count']} ta")
        self.stdout.write(f"  Maqola : {len(result['posts'])} ta")
        self.stdout.write(f"  Muallif: {result['author'].username}")
        self.stdout.write(
            "  Narx qo'yilmadi — kurs narxi va tarif farqi owner qarori."
        )
        self.stdout.write("  O'chirish uchun: manage.py seed_content --wipe")
