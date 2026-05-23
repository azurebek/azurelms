import hashlib

from django.utils import timezone

from messenger.models import AIMemoryFact, AILongTermMemory

from .types import MemoryCandidate, SavedMemory


class MemoryRepository:
    def get_legacy_memory_text(self, user) -> str:
        memory, _ = AILongTermMemory.objects.get_or_create(user=user)
        return memory.learned_facts or ""

    def save_candidate(self, *, user, candidate: MemoryCandidate, source_room=None, source_message=None) -> SavedMemory:
        fingerprint = self.fingerprint(candidate.category, candidate.value)
        fact, created = AIMemoryFact.objects.get_or_create(
            user=user,
            fingerprint=fingerprint,
            defaults={
                "category": candidate.category,
                "key": candidate.key,
                "value": candidate.value,
                "confidence": candidate.confidence,
                "status": AIMemoryFact.STATUS_ACTIVE,
                "visibility": candidate.visibility,
                "source_room": source_room,
                "source_message": source_message,
                "metadata": candidate.metadata,
            },
        )
        if not created:
            fact.category = candidate.category
            fact.key = candidate.key or fact.key
            fact.value = candidate.value
            fact.confidence = max(fact.confidence, candidate.confidence)
            fact.status = AIMemoryFact.STATUS_ACTIVE
            fact.visibility = candidate.visibility
            fact.source_room = source_room or fact.source_room
            fact.source_message = source_message or fact.source_message
            fact.metadata = {**(fact.metadata or {}), **candidate.metadata}
            fact.save(
                update_fields=[
                    "category",
                    "key",
                    "value",
                    "confidence",
                    "status",
                    "visibility",
                    "source_room",
                    "source_message",
                    "metadata",
                    "updated_at",
                ]
            )
        return SavedMemory(fact=fact, created=created)

    def active_facts(self, *, user):
        return AIMemoryFact.objects.filter(
            user=user,
            status=AIMemoryFact.STATUS_ACTIVE,
        )

    def mark_used(self, fact_ids: list[int]) -> None:
        if not fact_ids:
            return
        AIMemoryFact.objects.filter(id__in=fact_ids).update(last_used_at=timezone.now())

    def archive_one(self, *, user, fact_id: int) -> bool:
        updated = AIMemoryFact.objects.filter(
            user=user,
            id=fact_id,
            status=AIMemoryFact.STATUS_ACTIVE,
        ).update(status=AIMemoryFact.STATUS_ARCHIVED, updated_at=timezone.now())
        return updated > 0

    def archive_all_for_user(self, *, user, clear_legacy: bool = True) -> int:
        archived_count = AIMemoryFact.objects.filter(
            user=user,
            status=AIMemoryFact.STATUS_ACTIVE,
        ).update(status=AIMemoryFact.STATUS_ARCHIVED, updated_at=timezone.now())
        if clear_legacy:
            AILongTermMemory.objects.filter(user=user).update(learned_facts="")
        return archived_count

    def fingerprint(self, category: str, value: str) -> str:
        normalized = " ".join((value or "").lower().split())
        payload = f"{category}:{normalized}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

