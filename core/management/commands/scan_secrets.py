"""Repozitoriyda qolib ketgan sirlarni qidiradi (A1a CI gate).

    python manage.py scan_secrets

Mantiq `core/secret_scan.py` da — buyruq yupqa qobiq.
"""

from django.core.management.base import BaseCommand, CommandError

from core.secret_scan import scan_repository


class Command(BaseCommand):
    help = "Kuzatuvdagi fayllardan sir (API kalit, token, parolli DSN) qidiradi"

    def handle(self, *args, **options):
        findings = scan_repository()
        if not findings:
            self.stdout.write(self.style.SUCCESS("Sir topilmadi: kuzatuvdagi fayllar toza."))
            return

        for item in findings:
            location = f"{item['file']}:{item['line']}" if item["line"] else item["file"]
            self.stderr.write(f"{location}  [{item['rule']}] {item['label']} ({item['preview']})")
        raise CommandError(f"{len(findings)} ta ehtimoliy sir topildi.")
