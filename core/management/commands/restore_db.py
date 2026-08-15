"""Zaxiradan bazani tiklaydi (A1a).

    python manage.py restore_db --input backups/db-....sqlite3 --yes

Bu buyruq joriy bazani **ustidan yozadi**, shuning uchun `--yes` majburiy.
Mantiq `core/backup_service.py` da.
"""

from django.core.management.base import BaseCommand, CommandError

from core.backup_service import BackupError, restore_backup


class Command(BaseCommand):
    help = "Zaxiradan bazani tiklaydi (joriy bazani ustidan yozadi)"

    def add_arguments(self, parser):
        parser.add_argument("--input", required=True, help="Zaxira fayli yo'li")
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Joriy bazani ustidan yozishga rozilik (majburiy)",
        )

    def handle(self, *args, **options):
        if not options["yes"]:
            raise CommandError(
                "Bu amal joriy bazani ustidan yozadi. Rozi bo'lsangiz `--yes` qo'shing."
            )
        try:
            target = restore_backup(options["input"])
        except BackupError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Baza tiklandi: {target}"))
