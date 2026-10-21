"""Ochiq sayt reliz tayyorligi darvozasi (PUB1.8b) — faqat o'qiydi.

    python manage.py public_release_gate                 # matn; pilotga tayyor bo'lmasa xato bilan chiqadi
    python manage.py public_release_gate --json
    python manage.py public_release_gate --fail-on never

`--fail-on`: `pilot` (default — majburiy band yashil bo'lmasa, sariq bo'lsa ham), `red`, `amber`
(umumiy holat sariq yoki qizil), `never`.

Owner sahifasi (/backoffice/release/) va Control Center bilan ayni selector
(`frontend/release_readiness.py`). Tasdiq faqat sahifadan, sabab bilan.
"""

import json

from django.core.management.base import BaseCommand, CommandError

from frontend.release_readiness import ORDER, release_readiness


class Command(BaseCommand):
    help = "Ochiq sayt reliz tayyorligi: majburiy va ixtiyoriy bandlar (faqat o'qiydi)"

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--fail-on", choices=("pilot", "red", "amber", "never"), default="pilot")

    def handle(self, *args, **options):
        readiness = release_readiness()
        if options["as_json"]:
            self.stdout.write(json.dumps(readiness.as_dict(), ensure_ascii=False, indent=2))
        else:
            verdict = "PILOTGA TAYYOR" if readiness.ready_for_pilot else "TAYYOR EMAS"
            self.stdout.write(f"Reliz tayyorligi: {verdict} ({readiness.status}, iz {readiness.digest()})")
            for item in readiness.items:
                kind = "majburiy" if item.required else "ixtiyoriy"
                self.stdout.write(f"[{item.status.upper():5}] {item.label} ({kind}): {item.summary}")
                if item.fix and item.status != "green":
                    self.stdout.write(f"        → {item.fix}")
        fail_on = options["fail_on"]
        if fail_on == "pilot":
            failed = not readiness.ready_for_pilot
        else:
            failed = fail_on != "never" and ORDER[readiness.status] >= ORDER[fail_on]
        if failed:
            blockers = ", ".join(item.label for item in readiness.blockers) or "-"
            raise CommandError(f"Reliz darvozasi: {readiness.status}; majburiy to'siqlar: {blockers}")
