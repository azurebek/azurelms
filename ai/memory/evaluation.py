from .types import MemoryCandidate


class MemoryQualityEvaluator:
    """Small deterministic eval layer for memory facts before/after saving."""

    def evaluate_candidate(self, candidate: MemoryCandidate) -> dict:
        value = (candidate.value or "").strip()
        score = 0.0
        checks = {}

        checks["has_category"] = bool(candidate.category)
        checks["has_key"] = bool(candidate.key)
        checks["reasonable_length"] = 8 <= len(value) <= 500
        checks["confidence_ok"] = float(candidate.confidence or 0.0) >= 0.5

        score += 0.25 if checks["has_category"] else 0.0
        score += 0.2 if checks["has_key"] else 0.0
        score += 0.3 if checks["reasonable_length"] else 0.0
        score += 0.25 if checks["confidence_ok"] else 0.0

        return {
            "score": round(score, 3),
            "checks": checks,
            "passed": score >= 0.75,
        }
