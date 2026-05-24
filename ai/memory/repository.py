import hashlib

from django.utils.dateparse import parse_datetime
from django.utils import timezone

from messenger.models import AIMemoryFact, AIMemoryTrace, AIConversationSummary, AILongTermMemory

from .evaluation import MemoryQualityEvaluator
from .types import MemoryCandidate, SavedMemory


class MemoryRepository:
    DECAY_START_DAYS = 30
    DECAY_STEP_DAYS = 30
    DECAY_AMOUNT = 0.07
    ARCHIVE_CONFIDENCE_BELOW = 0.35
    ARCHIVE_STALE_DAYS = 180

    def __init__(self, *, evaluator: MemoryQualityEvaluator | None = None):
        self.evaluator = evaluator or MemoryQualityEvaluator()

    def get_legacy_memory_text(self, user) -> str:
        memory, _ = AILongTermMemory.objects.get_or_create(user=user)
        return memory.learned_facts or ""

    def save_candidate(self, *, user, candidate: MemoryCandidate, source_room=None, source_message=None) -> SavedMemory:
        quality_eval = self.evaluator.evaluate_candidate(candidate)
        fingerprint = self.fingerprint(candidate.category, candidate.value)
        now = timezone.now()
        candidate_metadata = {
            **(candidate.metadata or {}),
            "last_seen_at": now.isoformat(),
        }
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
                "metadata": candidate_metadata,
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
            fact.metadata = {**(fact.metadata or {}), **candidate_metadata}
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
        self.maintain_user_memory(user=user)
        return AIMemoryFact.objects.filter(
            user=user,
            status=AIMemoryFact.STATUS_ACTIVE,
        )

    def mark_used(self, fact_ids: list[int]) -> None:
        if not fact_ids:
            return
        AIMemoryFact.objects.filter(id__in=fact_ids).update(last_used_at=timezone.now())

    def archive_one(self, *, user, fact_id: int) -> bool:
        fact = AIMemoryFact.objects.filter(
            user=user,
            id=fact_id,
            status=AIMemoryFact.STATUS_ACTIVE,
        ).first()
        if not fact:
            return False
        fact.status = AIMemoryFact.STATUS_ARCHIVED
        fact.save(update_fields=["status", "updated_at"])
        self.create_trace(
            user=user,
            fact=fact,
            event_type=AIMemoryTrace.EVENT_ARCHIVED,
            reason="User archived this memory fact from memory settings.",
            metadata={"action": "user_archive"},
        )
        return True

    def reject_one(self, *, user, fact_id: int) -> bool:
        fact = AIMemoryFact.objects.filter(
            user=user,
            id=fact_id,
            status=AIMemoryFact.STATUS_ACTIVE,
        ).first()
        if not fact:
            return False
        fact.status = AIMemoryFact.STATUS_REJECTED
        fact.confidence = 0.0
        fact.metadata = {
            **(fact.metadata or {}),
            "rejected_by_user_at": timezone.now().isoformat(),
        }
        fact.save(update_fields=["status", "confidence", "metadata", "updated_at"])
        self.create_trace(
            user=user,
            fact=fact,
            event_type=AIMemoryTrace.EVENT_ARCHIVED,
            reason="User marked this memory fact as incorrect.",
            metadata={"action": "user_reject"},
        )
        return True

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

    def maintain_user_memory(self, *, user, now=None) -> dict:
        """Decay stale memory confidence and archive very old or weak facts.

        This intentionally runs on normal memory reads. It is conservative:
        only active facts older than DECAY_START_DAYS since last update are
        touched, and automatic archival needs either very old staleness or a
        confidence score that has decayed below the threshold.
        """
        now = now or timezone.now()
        decayed = 0
        archived = 0
        for fact in (
            AIMemoryFact.objects.filter(user=user, status=AIMemoryFact.STATUS_ACTIVE)
            .select_related("source_message")
        ):
            anchor = self._staleness_anchor(fact)
            stale_days = max(0, (now - anchor).days)
            if stale_days < self.DECAY_START_DAYS:
                continue

            decay_steps = max(1, stale_days // self.DECAY_STEP_DAYS)
            current_confidence = max(0.0, min(float(fact.confidence or 0.0), 1.0))
            next_confidence = max(0.0, round(current_confidence - (decay_steps * self.DECAY_AMOUNT), 3))
            should_archive = (
                stale_days >= self.ARCHIVE_STALE_DAYS
                or next_confidence < self.ARCHIVE_CONFIDENCE_BELOW
            )

            metadata = {
                **(fact.metadata or {}),
                "last_confidence_decay": {
                    "at": now.isoformat(),
                    "stale_days": stale_days,
                    "from": current_confidence,
                    "to": next_confidence,
                },
            }
            fact.confidence = next_confidence
            fact.metadata = metadata
            update_fields = ["confidence", "metadata", "updated_at"]
            reason = "Decayed memory confidence because the fact has not been used recently."
            event_metadata = {
                "action": "confidence_decay",
                "stale_days": stale_days,
                "previous_confidence": current_confidence,
                "new_confidence": next_confidence,
            }
            if should_archive:
                fact.status = AIMemoryFact.STATUS_ARCHIVED
                update_fields.append("status")
                archived += 1
                reason = "Automatically archived stale or low-confidence memory fact."
                event_metadata["action"] = "auto_archive_stale"
            else:
                decayed += 1
            fact.save(update_fields=update_fields)
            self.create_trace(
                user=user,
                fact=fact,
                event_type=AIMemoryTrace.EVENT_ARCHIVED if should_archive else AIMemoryTrace.EVENT_SKIPPED,
                reason=reason,
                score=next_confidence,
                metadata=event_metadata,
            )

        return {"decayed": decayed, "archived": archived}

    def _staleness_anchor(self, fact):
        """Return the last meaningful use/update time, ignoring maintenance writes."""
        metadata = fact.metadata or {}
        last_seen_at = metadata.get("last_seen_at")
        parsed = parse_datetime(last_seen_at) if last_seen_at else None
        if parsed and timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        if fact.last_used_at:
            return fact.last_used_at
        if parsed:
            return parsed
        if fact.source_message_id and fact.source_message:
            return fact.source_message.created_at
        return fact.created_at

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
