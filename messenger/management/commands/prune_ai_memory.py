from collections import defaultdict

from django.core.management.base import BaseCommand

from ai.memory.policy import MemoryPolicy
from ai.memory.repository import MemoryRepository
from messenger.models import AIMemoryFact


class Command(BaseCommand):
    help = (
        "AI memory faktlaridan shablon-axlat ('category: X') va near-dubllarni arxivlaydi. "
        "Har (user, category, normalized-value) uchun eng so'nggisini qoldiradi."
    )

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, default=None)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        policy = MemoryPolicy()
        repo = MemoryRepository()
        dry = bool(options.get("dry_run"))

        queryset = AIMemoryFact.objects.filter(
            status=AIMemoryFact.STATUS_ACTIVE
        ).order_by("user_id", "-updated_at")
        if options.get("user_id"):
            queryset = queryset.filter(user_id=options["user_id"])

        noise_ids = []
        dupe_ids = []
        seen = defaultdict(int)  # (user_id, category, normalized) -> ko'rilgan soni

        for fact in queryset:
            if policy.is_template_noise(fact.value or ""):
                noise_ids.append(fact.id)
                continue
            key = (fact.user_id, fact.category, repo._normalize_for_fingerprint(fact.value or ""))
            seen[key] += 1
            if seen[key] > 1:  # eng so'nggisi (-updated_at) allaqachon qoldirildi
                dupe_ids.append(fact.id)

        total = len(noise_ids) + len(dupe_ids)
        self.stdout.write(
            f"Shablon-axlat: {len(noise_ids)} | near-dubl: {len(dupe_ids)} | jami arxivlanadi: {total}"
        )

        if dry:
            self.stdout.write(self.style.WARNING("dry-run — hech narsa o'zgartirilmadi."))
            return
        if not total:
            self.stdout.write(self.style.SUCCESS("Tozalash shart emas — hammasi toza."))
            return

        AIMemoryFact.objects.filter(id__in=noise_ids + dupe_ids).update(
            status=AIMemoryFact.STATUS_ARCHIVED
        )
        self.stdout.write(self.style.SUCCESS(f"{total} ta fakt arxivlandi."))
