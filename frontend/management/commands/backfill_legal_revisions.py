"""Eski `LegalPage` matnidan tasdiqlanmagan qoralama (PUB1.5a).

    python manage.py backfill_legal_revisions          # faqat hisobot
    python manage.py backfill_legal_revisions --apply  # qoralama yaratadi

Qayta yugurish xavfsiz. Hech narsa nashr qilinmaydi va `LegalPage` qatori
tegilmaydi: saytdagi maxfiylik/shartlar sahifasi owner versiyani tasdiqlab
nashr qilmaguncha "hali e'lon qilinmagan" bo'lib qoladi. Umumiy namuna matn
qoralama bo'lishi mumkin, lekin tasdiqlanmaydi.
"""

from django.core.management.base import BaseCommand

from frontend.legal_revisions import backfill_from_legacy

ACTIONS = {
    "created": "qoralama yaratildi",
    "would_create": "qoralama yaratiladi (--apply bilan)",
    "exists": "eski matndan qoralama allaqachon bor",
    "no_legacy": "eski sahifa yo'q",
    "empty": "eski sahifa matni bo'sh",
}


class Command(BaseCommand):
    help = "Eski huquqiy sahifalardan tasdiqlanmagan qoralama (standart: faqat hisobot)"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Qoralamalarni haqiqatan yaratish")

    def handle(self, *args, **options):
        apply = options["apply"]
        self.stdout.write("Rejim: " + ("yozish" if apply else "mashq (hech narsa yozilmaydi)"))
        for row in backfill_from_legacy(apply=apply):
            note = " — umumiy namuna matn, tasdiqlanmaydi" if row.generated else ""
            self.stdout.write(f"  {row.kind}: {ACTIONS[row.action]}{note}")
