"""O'quvchi yuklagan fayllarning zaxirasini oladi (A1b).

    python manage.py backup_media
    python manage.py backup_media --output backups/media-2026-09-11.tar.gz

`backup_db` bazani oladi, bu buyruq esa baza faqat **yo'lini** saqlaydigan
fayllarni: to'lov cheki, vazifa fayli, chat biriktirmasi, speaking audiosi.
Ikkisi birgalikda tiklanadigan holatni tashkil qiladi; yolg'iz baza zaxirasi
tiklanganda mavjud bo'lmagan fayllarga ishora qiladigan qatorlarni beradi.

Mantiq `core/media_backup.py` da — buyruq yupqa qobiq.
"""

from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.media_backup import (
    ARCHIVE_SUFFIX,
    MediaBackupError,
    create_media_backup,
    describe_media_archive,
    media_roots,
)


class Command(BaseCommand):
    help = "Public va private media fayllarini bitta tekshirilgan arxivga yozadi"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="",
            help=f"Arxiv yo'li. Berilmasa: backups/media-<sana>{ARCHIVE_SUFFIX}",
        )

    def handle(self, *args, **options):
        destination = options["output"]
        if not destination:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            destination = (
                Path(settings.BASE_DIR) / "backups" / f"media-{stamp}{ARCHIVE_SUFFIX}"
            )

        roots = media_roots()
        for section, root in roots:
            self.stdout.write(f"  {section:8s}: {root}")

        try:
            written = create_media_backup(destination)
        except MediaBackupError as exc:
            raise CommandError(str(exc)) from exc

        counts = describe_media_archive(written)
        size_mb = written.stat().st_size / (1024 * 1024)
        self.stdout.write(
            self.style.SUCCESS(
                f"Media zaxirasi yozildi: {written} ({size_mb:.1f} MB, "
                f"public={counts['public']}, private={counts['private']}, "
                f"jami={counts['total']} fayl)"
            )
        )
