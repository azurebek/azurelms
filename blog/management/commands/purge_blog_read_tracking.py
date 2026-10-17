"""PUB1.0g'gacha yig'ilgan anonim blog kuzatuvini tozalaydi.

    python manage.py purge_blog_read_tracking           # faqat hisobot
    python manage.py purge_blog_read_tracking --apply   # tozalash

Anonim o'qish/olqish qatorlari o'chadi, kirgan foydalanuvchilarnikida IP xeshi
va user-agent bo'shatiladi. Jami ko'rish va olqish sonlari o'zgarmaydi. Qayta
yugurish xavfsiz.
"""

from django.core.management.base import BaseCommand

from blog.tracking_cleanup import legacy_tracking, purge_legacy_tracking


class Command(BaseCommand):
    help = "PUB1.0g'gacha yig'ilgan anonim blog kuzatuvini ko'rsatadi yoki tozalaydi"

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Haqiqatan tozalash (aks holda faqat hisobot)")

    def handle(self, *args, **options):
        state = purge_legacy_tracking() if options["apply"] else legacy_tracking()
        verb = "Tozalandi" if options["apply"] else "Topildi (o'zgartirilmadi)"
        self.stdout.write(
            f"{verb}: anonim o'qish {state.anonymous_reads}, IP/UA bor o'qish {state.reader_fingerprints}, "
            f"anonim olqish {state.anonymous_claps}."
        )
        if not options["apply"] and state.total:
            self.stdout.write("Tozalash uchun: python manage.py purge_blog_read_tracking --apply")
