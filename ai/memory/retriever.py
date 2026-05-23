import re

from messenger.models import AIMemoryFact

from .repository import MemoryRepository


class MemoryRetriever:
    def __init__(self, repository: MemoryRepository | None = None):
        self.repository = repository or MemoryRepository()

    def render_for_prompt(self, *, user, question: str, limit: int = 7) -> str:
        facts = self.retrieve(user=user, question=question, limit=limit)
        legacy_text = self.repository.get_legacy_memory_text(user).strip()
        if facts:
            self.repository.mark_used([fact.id for fact in facts])
            lines = [f"- [{fact.category}] {fact.value}" for fact in facts]
            if legacy_text:
                lines.append(f"Legacy memory:\n{legacy_text}")
            return "\n".join(lines)

        return legacy_text

    def retrieve(self, *, user, question: str, limit: int = 7):
        fact_list = list(self.repository.active_facts(user=user).order_by("-updated_at")[:80])
        if not fact_list:
            return []

        query_terms = self._terms(question)
        scored = []
        for fact in fact_list:
            score = self._score_fact(fact, query_terms)
            scored.append((score, fact.updated_at, fact))

        scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [fact for score, _updated_at, fact in scored[:limit] if score > 0 or not query_terms]

    def _score_fact(self, fact: AIMemoryFact, query_terms: set[str]) -> float:
        if not query_terms:
            return fact.confidence

        haystack = self._terms(f"{fact.category} {fact.key} {fact.value}")
        overlap = len(query_terms & haystack)
        if overlap:
            return overlap + min(fact.confidence, 1.0) / 10
        if fact.category in {
            AIMemoryFact.CATEGORY_PREFERENCE,
            AIMemoryFact.CATEGORY_PROFILE,
            AIMemoryFact.CATEGORY_SCHEDULE,
        }:
            return 0.2 + min(fact.confidence, 1.0) / 10
        return 0.0

    def _terms(self, text: str) -> set[str]:
        return {term for term in re.findall(r"[\w']{3,}", (text or "").lower())}
