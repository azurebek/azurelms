"""`pip-audit` hisobotini ma'lum zaifliklar reyestri bilan solishtiradi (A1a CI gate).

    pip-audit -r requirements.txt --no-deps -f json > audit.json
    python manage.py audit_dependencies --report audit.json

Mantiq `core/dependency_audit.py` da — buyruq yupqa qobiq.
"""

from django.core.management.base import BaseCommand, CommandError

from core.dependency_audit import (
    DependencyAuditError,
    baseline_path,
    compare,
    load_json,
    review_overdue,
)


class Command(BaseCommand):
    help = "pip-audit hisobotini `security/dependency-audit-baseline.json` bilan solishtiradi"

    def add_arguments(self, parser):
        parser.add_argument("--report", required=True, help="`pip-audit -f json` chiqishi")
        parser.add_argument("--baseline", default="", help="Reyestr yo'li (default: repo ichidagi)")

    def handle(self, *args, **options):
        try:
            report = load_json(options["report"])
            baseline = load_json(options["baseline"] or baseline_path())
            result = compare(report, baseline)
            overdue = review_overdue(baseline)
        except DependencyAuditError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            f"Joriy holat: {result['total_current']} advisory / "
            f"{result['packages_affected']} paket (reyestrda kutilgan)."
        )

        for key, ids in result["stale"].items():
            self.stdout.write(
                self.style.WARNING(f"Reyestrda ortiqcha yozuv — {key}: {', '.join(ids)}")
            )

        problems = []
        if result["unlisted"]:
            for key, ids in result["unlisted"].items():
                self.stderr.write(f"YANGI zaiflik — {key}: {', '.join(ids)}")
            problems.append(
                f"{sum(len(ids) for ids in result['unlisted'].values())} ta yangi advisory "
                "reyestrda yo'q. Paketni ko'taring yoki sababini reyestrga yozing."
            )
        if overdue:
            problems.append(
                f"Reyestr muddati o'tdi ({overdue.isoformat()}): zaifliklar qayta ko'rilishi "
                "va `review_by` yangilanishi kerak."
            )

        if problems:
            raise CommandError(" ".join(problems))

        self.stdout.write(self.style.SUCCESS("Yangi zaiflik yo'q."))
