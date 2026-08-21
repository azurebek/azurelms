"""Zaxiradan bazani tiklaydi (A1a) yoki restore drill qiladi (A2).

    python manage.py restore_db --input backups/db-....sqlite3 --yes
    python manage.py restore_db --input backups/db-....sqlite3 --into /tmp/drill.sqlite3

Birinchi shakl joriy bazani **ustidan yozadi**, shuning uchun `--yes` majburiy.
Ikkinchisi — drill: alohida faylga tiklaydi, joriy bazaga tegmaydi va tiklangan
nusxaning sxemasini ko'rsatadi. Hech qachon tiklanmagan zaxira — umid, zaxira emas.

Mantiq `core/backup_service.py` da.
"""

from django.core.management.base import BaseCommand, CommandError

from core.backup_service import BackupError, describe_sqlite, restore_backup


class Command(BaseCommand):
    help = "Zaxiradan bazani tiklaydi (joriy bazani ustidan yozadi)"

    def add_arguments(self, parser):
        parser.add_argument("--input", required=True, help="Zaxira fayli yo'li")
        parser.add_argument(
            "--into",
            default="",
            help="Drill: alohida faylga tiklaydi, joriy bazaga tegmaydi",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Joriy bazani ustidan yozishga rozilik (`--into` siz majburiy)",
        )

    def handle(self, *args, **options):
        drill_target = options["into"]

        # `--yes` joriy bazani yo'qotishga rozilik. Drill hech narsa
        # yo'qotmaydi, shuning uchun undan tasdiq talab qilinmaydi — aks
        # holda xavfsiz amal xavflisi bilan bir xil qiyinlikda bo'lardi.
        if not drill_target and not options["yes"]:
            raise CommandError(
                "Bu amal joriy bazani ustidan yozadi. Rozi bo'lsangiz `--yes` qo'shing, "
                "yoki xavfsiz tekshirish uchun `--into <yo'l>` bilan drill qiling."
            )

        try:
            target = restore_backup(options["input"], into=drill_target or None)
        except BackupError as exc:
            raise CommandError(str(exc)) from exc

        if not drill_target:
            self.stdout.write(self.style.SUCCESS(f"Baza tiklandi: {target}"))
            return

        report = describe_sqlite(target)
        self.stdout.write(self.style.SUCCESS(f"Drill bajarildi: {target}"))
        self.stdout.write(f"  butunlik      : {report['integrity']}")
        self.stdout.write(f"  jadvallar     : {report['tables']}")
        self.stdout.write(f"  migratsiyalar : {report['migrations']}")
        if report["latest_migration"]:
            self.stdout.write(f"  oxirgisi      : {report['latest_migration']}")
        self.stdout.write(
            "  Joriy baza o'zgarmadi. Sxema kod kutayotganiga mos kelishini tekshiring."
        )
