"""Mavjud sertifikatlarga ochiq tekshiruv kodi (PUB1.5d).

    python manage.py backfill_certificate_tokens                  # mashq: nechtasi kodsiz
    python manage.py backfill_certificate_tokens --apply          # kod beradi
    python manage.py backfill_certificate_tokens --apply --limit 500

Qayta yugurish xavfsiz va to'xtagan joyidan davom etadi: faqat kodsiz sertifikatlar
olinadi (pk tartibida). Kodlarning o'zi chiqarilmaydi; `digest` — ishlangan pk'lar
izi, ikki yugurishni solishtirish uchun. Hech narsa o'chirilmaydi.
"""

from django.core.management.base import BaseCommand

from courses.certificate_verifier import backfill_tokens


class Command(BaseCommand):
    help = "Kodsiz sertifikatlarga ochiq tekshiruv kodi (standart: mashq)"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Kodlarni haqiqatan yozish")
        parser.add_argument("--batch-size", type=int, default=200)
        parser.add_argument("--limit", type=int, default=None, help="Shu yugurishda ko'pi bilan nechta")

    def handle(self, *args, **options):
        report = backfill_tokens(apply=options["apply"], batch_size=options["batch_size"], limit=options["limit"])
        mode = "yozish" if options["apply"] else "mashq (hech narsa yozilmadi)"
        self.stdout.write(
            f"Rejim: {mode}. Kodsiz edi: {report.missing_before}; ishlandi: {report.processed}; "
            f"kodsiz qoldi: {report.missing_after}; iz: {report.digest}"
        )
