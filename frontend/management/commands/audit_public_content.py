"""Public rich text va URL'lar bo'yicha read-only audit (PUB1.0a).

    python manage.py audit_public_content
    python manage.py audit_public_content --format=json

Faqat qator ID'si va topilma turi chiqadi; kontent, payload va URL hech qachon
chiqmaydi. Buyruq hech narsa yozmaydi — mantiq `frontend.public_content_audit`da.
"""

import json

from django.core.management.base import BaseCommand

from frontend.public_content_audit import audit_public_content


class Command(BaseCommand):
    help = "Public rich text va havolalarni PUBLIC_EDITORIAL_V1 bo'yicha read-only tekshiradi"

    def add_arguments(self, parser):
        parser.add_argument("--format", choices=("text", "json"), default="text")

    def handle(self, *args, **options):
        report = audit_public_content()
        if options["format"] == "json":
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
            return

        self.stdout.write(f"Profil: {report['profile']}")
        for row in report["rich_text"]:
            line = f"{row['field']}: {row['rows']} qator, {row['flagged']} tasida topilma"
            for kind, ids in row["findings"].items():
                line += f"\n    {kind}: {', '.join(str(pk) for pk in ids)}"
            self.stdout.write(line)
        for row in report["urls"]:
            rejected = ", ".join(str(pk) for pk in row["rejected"]) or "yo'q"
            self.stdout.write(
                f"{row['field']} [{row['policy']}]: {row['rows']} ta to'ldirilgan, rad etilgan ID: {rejected}"
            )
