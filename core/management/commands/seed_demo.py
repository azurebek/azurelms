"""QA va demo uchun ma'lumot to'plami (A5 / R4).

    python manage.py seed_demo
    python manage.py seed_demo --wipe

Mantiq `core/demo_seed.py` da — buyruq yupqa qobiq va lokal gate.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.demo_seed import seed_demo_data, wipe_demo_data


class Command(BaseCommand):
    help = "Mobil QA va demo uchun kurs/guruh/o'quvchi yaratadi (faqat lokal)"

    def add_arguments(self, parser):
        parser.add_argument("--wipe", action="store_true", help="Demo ma'lumotni o'chiradi")

    def handle(self, *args, **options):
        # Fail-closed: demo kurslar va soxta to'lovlar haqiqiy bazaga tushmasin.
        if not settings.IS_LOCAL:
            raise CommandError(
                "Bu buyruq faqat lokal muhitda ishlaydi (APP_ENV=local). "
                f"Joriy muhit: {settings.APP_ENV}."
            )

        if options["wipe"]:
            wipe_demo_data()
            self.stdout.write(self.style.SUCCESS("Demo ma'lumot o'chirildi."))
            return

        result = seed_demo_data()
        self.stdout.write(self.style.SUCCESS("Demo ma'lumot tayyor."))
        self.stdout.write(f"  Kurs   : {result['course'].title}")
        self.stdout.write(f"  Guruh  : {result['cohort'].name}")
        self.stdout.write("  Kirish : demo-student / demo12345")
        self.stdout.write("  O'chirish uchun: manage.py seed_demo --wipe")
