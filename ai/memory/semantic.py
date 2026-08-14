import math
import os
import re

from messenger.models import AIMemoryFact
from messenger.rag import DEFAULT_EMBEDDING_MODEL, embed_texts

from .types import ScoredMemoryFact


SEMANTIC_ALIASES = {
    "def": {"function", "funksiya", "funksiyalar", "metod"},
    "function": {"def", "funksiya", "funksiyalar", "metod"},
    "funksiya": {"def", "function", "funksiyalar", "metod"},
    "funksiyalar": {"def", "function", "funksiya", "metod"},
    "grammar": {"grammatika", "zamon", "tense"},
    "grammatika": {"grammar", "zamon", "tense"},
    "essay": {"writing", "insho", "yozish"},
    "writing": {"essay", "insho", "yozish"},
    "speaking": {"gapirish", "nutq", "talaffuz"},
    "listening": {"tinglash", "audio"},
    "qisqa": {"brief", "short", "ixcham"},
    "brief": {"qisqa", "short", "ixcham"},
    "batafsil": {"detailed", "keng", "uzun"},
    "detailed": {"batafsil", "keng", "uzun"},
}

CATEGORY_PRIORS = {
    AIMemoryFact.CATEGORY_PREFERENCE: 0.22,
    AIMemoryFact.CATEGORY_PROFILE: 0.18,
    AIMemoryFact.CATEGORY_SCHEDULE: 0.14,
    AIMemoryFact.CATEGORY_LEARNING_GOAL: 0.08,
    AIMemoryFact.CATEGORY_WEAK_TOPIC: 0.06,
}


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class SemanticMemoryScorer:
    def __init__(self, *, embedding_model: str = DEFAULT_EMBEDDING_MODEL, use_vectors: bool | None = None):
        self.embedding_model = embedding_model
        self.use_vectors = env_bool("AI_MEMORY_USE_VECTOR_RETRIEVAL", True) if use_vectors is None else use_vectors

    def score(self, *, facts: list[AIMemoryFact], question: str) -> list[ScoredMemoryFact]:
        query_terms = self._terms(question)
        expanded_query_terms = self._expand_terms(query_terms)
        vector_scores = self._vector_scores(facts=facts, question=question)

        scored = []
        for fact in facts:
            fact_terms = self._terms(f"{fact.category} {fact.key} {fact.value}")
            expanded_fact_terms = self._expand_terms(fact_terms)

            lexical_overlap = len(query_terms & fact_terms)
            semantic_overlap = len(expanded_query_terms & expanded_fact_terms) - lexical_overlap
            semantic_overlap = max(0, semantic_overlap)
            confidence_bonus = min(float(fact.confidence or 0.0), 1.0) * 0.08
            category_prior = CATEGORY_PRIORS.get(fact.category, 0.0)
            vector_score = vector_scores.get(fact.id)

            score = confidence_bonus
            reasons = []

            if lexical_overlap:
                score += lexical_overlap * 1.0
                reasons.append(f"lexical_overlap:{lexical_overlap}")
            if semantic_overlap:
                score += semantic_overlap * 0.55
                reasons.append(f"semantic_overlap:{semantic_overlap}")
            if vector_score is not None and vector_score > 0:
                score += vector_score * 1.35
                reasons.append(f"semantic_vector:{vector_score:.3f}")
            if category_prior:
                score += category_prior
                reasons.append(f"category_prior:{fact.category}")
            if confidence_bonus:
                reasons.append(f"confidence:{fact.confidence:.2f}")

            scored.append(
                ScoredMemoryFact(
                    fact=fact,
                    score=score,
                    reasons=reasons,
                    lexical_overlap=lexical_overlap,
                    semantic_overlap=semantic_overlap,
                    vector_score=vector_score,
                )
            )

        scored.sort(key=lambda item: (item.score, item.fact.updated_at), reverse=True)
        return scored

    def _vector_scores(self, *, facts: list[AIMemoryFact], question: str) -> dict[int, float]:
        if not self.use_vectors or not (question or "").strip():
            return {}

        embedded_facts = [
            fact
            for fact in facts
            if fact.embedding
            and fact.embedding_model == self.embedding_model
            and fact.embedding_dim == len(fact.embedding)
        ]
        if not embedded_facts:
            return {}

        try:
            memory_user = embedded_facts[0].user
            query_vectors = embed_texts(
                [question],
                embedding_model=self.embedding_model,
                call_type="memory_embedding",
                user=memory_user,
                request_key=f"memory-query:user:{embedded_facts[0].user_id}",
            )
        except Exception:
            return {}
        if not query_vectors:
            return {}

        query_vector = query_vectors[0]
        return {
            fact.id: self._cosine_similarity(query_vector, fact.embedding)
            for fact in embedded_facts
        }

    def _expand_terms(self, terms: set[str]) -> set[str]:
        expanded = set(terms)
        for term in list(terms):
            expanded.update(SEMANTIC_ALIASES.get(term, set()))
        return expanded

    def _terms(self, text: str) -> set[str]:
        return {term for term in re.findall(r"[\w']{2,}", (text or "").lower())}

    def _cosine_similarity(self, a, b) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for av, bv in zip(a, b):
            dot += float(av) * float(bv)
            norm_a += float(av) * float(av)
            norm_b += float(bv) * float(bv)
        if norm_a <= 0 or norm_b <= 0:
            return 0.0
        return max(0.0, dot / (math.sqrt(norm_a) * math.sqrt(norm_b)))
