"""Ochiq voronka hisoboti (PUB1.8a) — faqat o'qiydi.

    python manage.py public_funnel_report            # oxirgi 28 kun
    python manage.py public_funnel_report --days 14

Har ko'rsatkich surat/maxraj va ta'rifi bilan chiqadi: ayni bazadan ayni natija.
Ma'lumot `public_telemetry_v1` flagi yoqilgandan keyingina yig'iladi.
"""

from django.core.management.base import BaseCommand

from frontend.public_telemetry import EVENTS, funnel_report


class Command(BaseCommand):
    help = "Ochiq voronka hisoboti: hodisalar soni va o'tish foizlari (faqat o'qiydi)"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=28)

    def handle(self, *args, **options):
        report = funnel_report(days=max(1, min(options["days"], 400)))
        self.stdout.write(f"Davr: {report['start']} — {report['end']}")
        for event in EVENTS:
            self.stdout.write(f"  {event}: {report['totals'][event]}")
        for title, top, bottom, percent, definition in report["rates"]:
            value = f"{percent}%" if percent is not None else "maxraj 0 — hisoblanmaydi"
            self.stdout.write(f"{title}: {top} / {bottom} = {value}")
            self.stdout.write(f"    ta'rif: {definition}")
