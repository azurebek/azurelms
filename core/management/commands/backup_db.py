"""Local bazaning izchil zaxirasini oladi (A1a).

    python manage.py backup_db
    python manage.py backup_db --output backups/2026-08-15.sqlite3

Mantiq `core/backup_service.py` da — buyruq yupqa qobiq.
"""

from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.backup_service import BackupError, create_backup


class Command(BaseCommand):
    help = "Bazaning izchil zaxirasini yozadi (SQLite: VACUUM INTO)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="",
            help="Zaxira fayli yo'li. Berilmasa: backups/db-<sana>.sqlite3",
        )

    def handle(self, *args, **options):
        destination = options["output"]
        if not destination:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            destination = Path(settings.BASE_DIR) / "backups" / f"db-{stamp}.sqlite3"

        try:
            written = create_backup(destination)
        except BackupError as exc:
            raise CommandError(str(exc)) from exc

        size_mb = written.stat().st_size / (1024 * 1024)
        self.stdout.write(
            self.style.SUCCESS(f"Zaxira yozildi: {written} ({size_mb:.1f} MB, integrity ok)")
        )
