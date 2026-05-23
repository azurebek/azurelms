from messenger.models import AIMemoryTrace

from .repository import MemoryRepository
from .semantic import SemanticMemoryScorer


class MemoryRetriever:
    def __init__(
        self,
        repository: MemoryRepository | None = None,
        scorer: SemanticMemoryScorer | None = None,
    ):
        self.repository = repository or MemoryRepository()
        self.scorer = scorer or SemanticMemoryScorer()

    def render_for_prompt(self, *, user, question: str, limit: int = 7) -> str:
        scored_facts = self.retrieve_scored(user=user, question=question, limit=limit)
        legacy_text = self.repository.get_legacy_memory_text(user).strip()
        if scored_facts:
            self.repository.mark_used([item.fact.id for item in scored_facts])
            self._trace_retrieval(user=user, question=question, scored_facts=scored_facts)
            lines = [f"- [{item.fact.category}] {item.fact.value}" for item in scored_facts]
            if legacy_text:
                lines.append(f"Legacy memory:\n{legacy_text}")
            return "\n".join(lines)

        return legacy_text

    def retrieve(self, *, user, question: str, limit: int = 7):
        return [item.fact for item in self.retrieve_scored(user=user, question=question, limit=limit)]

    def retrieve_scored(self, *, user, question: str, limit: int = 7):
        fact_list = list(self.repository.active_facts(user=user).order_by("-updated_at")[:80])
        if not fact_list:
            return []

        scored = self.scorer.score(facts=fact_list, question=question)
        if not (question or "").strip():
            return scored[:limit]
        return [item for item in scored[:limit] if item.score > 0]

    def _trace_retrieval(self, *, user, question: str, scored_facts) -> None:
        top_items = []
        for item in scored_facts:
            top_items.append(
                {
                    "fact_id": item.fact.id,
                    "category": item.fact.category,
                    "key": item.fact.key,
                    "value": item.fact.value,
                    "score": round(item.score, 4),
                    "reasons": item.reasons,
                    "lexical_overlap": item.lexical_overlap,
                    "semantic_overlap": item.semantic_overlap,
                    "vector_score": item.vector_score,
                }
            )

        best = scored_facts[0]
        self.repository.create_trace(
            user=user,
            fact=best.fact,
            event_type=AIMemoryTrace.EVENT_RETRIEVED,
            reason="Selected relevant memories for the prompt using lexical, semantic, category, confidence, and optional vector scores.",
            score=best.score,
            metadata={
                "question": question,
                "selected": top_items,
            },
        )
