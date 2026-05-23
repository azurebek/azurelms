import hashlib

from django.utils import timezone

from messenger.models import AIMemoryFact, AIMemoryTrace, AIConversationSummary, AILongTermMemory

from .evaluation import MemoryQualityEvaluator
from .types import MemoryCandidate, SavedMemory


class MemoryRepository:
    def __init__(self, *, evaluator: MemoryQualityEvaluator | None = None):
        self.evaluator = evaluator or MemoryQualityEvaluator()

    def get_legacy_memory_text(self, user) -> str:
        memory, _ = AILongTermMemory.objects.get_or_create(user=user)
        return memory.learned_facts or ""

    def save_candidate(self, *, user, candidate: MemoryCandidate, source_room=None, source_message=None) -> SavedMemory:
        quality_eval = self.evaluator.evaluate_candidate(candidate)
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
        self.archive_conflicting_facts(
            user=user,
            category=candidate.category,
            key=candidate.key,
            keep_id=fact.id,
        )
        self.create_trace(
            user=user,
            fact=fact,
            room=source_room,
            event_type=AIMemoryTrace.EVENT_SAVED,
            reason="Model emitted SAVE_MEMORY tag and memory policy accepted it.",
            metadata={
                "created": created,
                "category": candidate.category,
                "key": candidate.key,
                "confidence": candidate.confidence,
                "quality_eval": quality_eval,
                "candidate_metadata": candidate.metadata,
            },
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

    def archive_conflicting_facts(self, *, user, category: str, key: str, keep_id: int | None = None) -> int:
        if not key:
            return 0

        conflicts = AIMemoryFact.objects.filter(
            user=user,
            category=category,
            key=key,
            status=AIMemoryFact.STATUS_ACTIVE,
        )
        if keep_id:
            conflicts = conflicts.exclude(id=keep_id)
        conflict_ids = list(conflicts.values_list("id", flat=True))
        updated = conflicts.update(status=AIMemoryFact.STATUS_ARCHIVED, updated_at=timezone.now())
        for fact in AIMemoryFact.objects.filter(id__in=conflict_ids):
            self.create_trace(
                user=user,
                fact=fact,
                event_type=AIMemoryTrace.EVENT_ARCHIVED,
                reason="Archived because a newer memory with the same category/key replaced it.",
                metadata={"category": category, "key": key, "replacement_id": keep_id},
            )
        return updated

    def create_trace(
        self,
        *,
        user,
        event_type: str,
        reason: str = "",
        fact=None,
        room=None,
        score: float | None = None,
        metadata: dict | None = None,
    ):
        return AIMemoryTrace.objects.create(
            user=user,
            fact=fact,
            room=room,
            event_type=event_type,
            reason=reason,
            score=score,
            metadata=metadata or {},
        )

    def get_conversation_summary(self, *, room):
        summary, _created = AIConversationSummary.objects.get_or_create(room=room)
        return summary

    def save_conversation_summary(
        self,
        *,
        room,
        summary_text: str,
        covered_message=None,
        covered_message_count: int = 0,
    ):
        summary, _created = AIConversationSummary.objects.update_or_create(
            room=room,
            defaults={
                "summary_text": summary_text,
                "covered_message": covered_message,
                "covered_message_count": max(covered_message_count, 0),
            },
        )
        return summary

    def fingerprint(self, category: str, value: str) -> str:
        normalized = " ".join((value or "").lower().split())
        payload = f"{category}:{normalized}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
