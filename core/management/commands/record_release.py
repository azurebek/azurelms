"""Ishlab turgan release'ni yozadi (A2).

    python manage.py record_release --sha $GITHUB_SHA
    python manage.py record_release --sha abc123 --gate checks=success

Deploy bosqichida chaqiriladi. Mantiq `core/release_service.py` da.
"""

from django.core.management.base import BaseCommand

from core.control_center.snapshot import _release_sha
from core.release_service import record_current_release


class Command(BaseCommand):
    help = "Ishlab turgan commit SHA va migratsiya holatini ReleaseRecord'ga yozadi"

    def add_arguments(self, parser):
        parser.add_argument("--sha", default="", help="Commit SHA (default: muhitdan)")
        parser.add_argument(
            "--gate",
            action="append",
            default=[],
            metavar="NOM=NATIJA",
            help="Gate natijasi, bir necha marta berilishi mumkin",
        )

    def handle(self, *args, **options):
        sha = (options["sha"] or _release_sha()).strip()
        gates = {}
        for pair in options["gate"]:
            name, _, value = pair.partition("=")
            if name:
                gates[name.strip()] = value.strip()

        record = record_current_release(commit_sha=sha, gate_results=gates or None)

        self.stdout.write(f"Release {record.commit_sha[:12]} yozildi.")
        self.stdout.write(f"Qo'llangan migratsiya: {record.migrations_applied}")
        if record.unapplied_migrations:
            self.stdout.write(
                self.style.ERROR(
                    f"QO'LLANMAGAN {len(record.unapplied_migrations)} ta: "
                    + ", ".join(record.unapplied_migrations)
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Kod va baza mos."))
