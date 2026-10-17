"""Route registri hisoboti: har nomli route public, ops yoki private (PUB1.1a).

    python manage.py audit_public_routes

Faqat o'qiydi va so'rov yubormaydi. Joriy xulq (anonim/kirgan/faolsiz status,
method) `frontend/public_route_snapshot.json`da — test fixture'ida o'lchanadi.
"""

from collections import Counter

from django.core.management.base import BaseCommand

from frontend.public_policy import OPS, OPS_ROUTES, PUBLIC, classify, registry_errors, route_inventory, surface_by_name


class Command(BaseCommand):
    help = "Public route registri va URL inventarini solishtiradi"

    def handle(self, *args, **options):
        inventory = route_inventory()
        counts = Counter(classify(name) or "tasniflanmagan" for name, _pattern, _converters in inventory)
        self.stdout.write(
            f"Route'lar: {len(inventory)} — public {counts[PUBLIC]}, ops {counts[OPS]}, "
            f"private {counts['private']}, tasniflanmagan {counts['tasniflanmagan']}."
        )
        surfaces = surface_by_name()
        self.stdout.write("\nPublic yuzalar:")
        for name, pattern, _converters in inventory:
            policy = surfaces.get(name)
            if policy is None:
                continue
            methods = ",".join(sorted(policy.methods))
            self.stdout.write(
                f"  {name:28s} /{pattern:45s} {methods:14s} {policy.audience:10s} {policy.index_policy:11s} "
                f"{policy.cache_class.value}"
            )
        self.stdout.write("\nOps (mahsulot sahifasi emas):")
        for name, reason in OPS_ROUTES.items():
            self.stdout.write(f"  {name:28s} {reason}")
        errors = registry_errors()
        if errors:
            self.stdout.write(self.style.ERROR(f"\nXatolar ({len(errors)}):"))
            for error in errors:
                self.stdout.write(f"  - {error}")
        else:
            self.stdout.write(self.style.SUCCESS("\nRegistry va URL inventari mos."))
