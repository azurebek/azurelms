"""Read-only command-line adapter for the Control Center snapshot."""

import json

from django.core.management.base import BaseCommand, CommandError

from core.control_center import build_control_center_snapshot
from core.control_center.snapshot import STATUS_ORDER


class Command(BaseCommand):
    help = "Print the canonical AzureLMS operational snapshot without mutating state."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument(
            "--fail-on",
            choices=("red", "amber", "never"),
            default="red",
            help="Return a non-zero exit when the snapshot reaches this status (default: red).",
        )

    def handle(self, *args, **options):
        snapshot = build_control_center_snapshot()
        if options["as_json"]:
            self.stdout.write(json.dumps(snapshot.as_dict(), ensure_ascii=False, indent=2))
        else:
            self.stdout.write(
                f"AzureLMS system audit: {snapshot.overall_status.upper()} "
                f"({snapshot.environment}, release={snapshot.release_sha})"
            )
            for result in snapshot.results:
                self.stdout.write(f"[{result.status.upper():5}] {result.definition.label}: {result.summary}")
            counts = snapshot.counts
            self.stdout.write(
                f"Summary: {counts['green']} green, {counts['amber']} amber, "
                f"{counts['red']} red / {counts['total']} total"
            )

        fail_on = options["fail_on"]
        if fail_on != "never" and STATUS_ORDER[snapshot.overall_status] >= STATUS_ORDER[fail_on]:
            raise CommandError(f"System audit threshold reached: {snapshot.overall_status}")
