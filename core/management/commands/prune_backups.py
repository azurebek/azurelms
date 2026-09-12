"""Muddati o'tgan zaxiralarni o'chiradi (A1b).

    python manage.py prune_backups
    python manage.py prune_backups --dry-run
    python manage.py prune_backups --days 30

Kunlik cron shu buyruqni **konteyner ichida** chaqiradi. Host'dagi `find`
ishlamaydi: `deploy/backups` konteyner foydalanuvchisiga tegishli va faylni
o'chirish uchun papkaga yozish huquqi kerak (PR #111 review).

Saqlash muddati owner sozlamasida — `OperationalSettings.backup_retention_days`.
`--days` faqat bir martalik chetlab o'tish uchun.

Mantiq `core/backup_rotation.py` da — buyruq yupqa qobiq.
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.backup_rotation import apply_rotation, backup_taken_at, plan_rotation
from core.backup_target import describe_write_problem
from core.operational_settings import current_thresholds


class Command(BaseCommand):
    help = "Muddati o'tgan zaxira fayllarini o'chiradi"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Saqlash muddati (default: owner sozlamasidan)",
        )
        parser.add_argument(
            "--directory",
            default="",
            help="Zaxira papkasi (default: BASE_DIR/backups)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Hech narsa o'chirilmaydi, faqat ro'yxat ko'rsatiladi",
        )

    def handle(self, *args, **options):
        directory = Path(options["directory"] or Path(settings.BASE_DIR) / "backups")
        days = options["days"]
        if days is None:
            days = current_thresholds().backup_retention_days
        if days < 1:
            raise CommandError("Saqlash muddati kamida 1 kun bo'lishi kerak.")

        if not options["dry_run"]:
            # O'chirish ham yozish huquqini talab qiladi (papkaga yozish),
            # ya'ni bu yerdagi to'siq `backup_db` dagi bilan bir xil sabab.
            problem = describe_write_problem(directory)
            if problem:
                raise CommandError(problem)

        plan = plan_rotation(directory, retention_days=days)
        self.stdout.write(f"Papka: {directory}  |  saqlash muddati: {days} kun")

        if plan.kept_newest is not None:
            stamp = backup_taken_at(plan.kept_newest).strftime("%Y-%m-%d %H:%M")
            self.stdout.write(f"  Eng yangisi saqlanadi: {plan.kept_newest.name} ({stamp})")

        if not plan.delete:
            self.stdout.write(self.style.SUCCESS("O'chiriladigan zaxira yo'q."))
            return

        for item in plan.delete:
            self.stdout.write(f"  {'(mashq) ' if options['dry_run'] else ''}o'chadi: {item.name}")

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(f"Mashq rejimi — {len(plan.delete)} fayl tegilmadi.")
            )
            return

        removed = apply_rotation(plan)
        if len(removed) != len(plan.delete):
            # Yarim bajarilgan rotatsiya jim qolmasin: disk baribir to'ladi.
            raise CommandError(
                f"{len(plan.delete)} fayldan faqat {len(removed)} tasi o'chdi — "
                "qolganlarining huquqini tekshiring."
            )
        self.stdout.write(
            self.style.SUCCESS(f"{len(removed)} eski zaxira o'chirildi.")
        )
