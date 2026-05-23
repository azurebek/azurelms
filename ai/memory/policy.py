import re

from messenger.models import AIMemoryFact

from .types import MemoryCandidate


DO_NOT_REMEMBER_PATTERNS = (
    "eslab qolma",
    "xotirada saqlama",
    "saqlama",
    "remember qilma",
    "don't remember",
    "do not remember",
    "forget this",
)
SENSITIVE_PATTERNS = (
    "password",
    "parol",
    "api key",
    "apikey",
    "secret",
    "token",
    "private key",
    "card number",
    "karta raqami",
    "passport",
    "pasport",
    "ssn",
)
CATEGORY_ALIASES = {
    "preference": AIMemoryFact.CATEGORY_PREFERENCE,
    "preferences": AIMemoryFact.CATEGORY_PREFERENCE,
    "learning_goal": AIMemoryFact.CATEGORY_LEARNING_GOAL,
    "goal": AIMemoryFact.CATEGORY_LEARNING_GOAL,
    "weak_topic": AIMemoryFact.CATEGORY_WEAK_TOPIC,
    "weakness": AIMemoryFact.CATEGORY_WEAK_TOPIC,
    "schedule": AIMemoryFact.CATEGORY_SCHEDULE,
    "profile": AIMemoryFact.CATEGORY_PROFILE,
    "other": AIMemoryFact.CATEGORY_OTHER,
}


class MemoryPolicy:
    def should_skip_extraction(self, user_question: str) -> bool:
        lowered = (user_question or "").lower()
        return any(pattern in lowered for pattern in DO_NOT_REMEMBER_PATTERNS)

    def build_candidate(self, raw_fact: str, *, user_question: str = "") -> MemoryCandidate | None:
        if self.should_skip_extraction(user_question):
            return None

        category, value = self._split_category(raw_fact)
        normalized_value = self.normalize_value(value)
        if not self.is_safe_to_store(normalized_value):
            return None

        category = category or self.infer_category(normalized_value)
        return MemoryCandidate(
            category=category,
            key=self.make_key(category, normalized_value),
            value=normalized_value,
            confidence=self.infer_confidence(normalized_value),
            visibility=AIMemoryFact.VISIBILITY_USER_VISIBLE,
            metadata={"source": "model_directive"},
        )

    def normalize_value(self, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", (value or "")).strip(" -:;\n\t")
        return cleaned[:500]

    def is_safe_to_store(self, value: str) -> bool:
        lowered = value.lower()
        if len(value) < 8:
            return False
        if len(value) > 500:
            return False
        return not any(pattern in lowered for pattern in SENSITIVE_PATTERNS)

    def infer_category(self, value: str) -> str:
        lowered = value.lower()
        if any(word in lowered for word in ("yoqtir", "afzal", "qisqa", "uzun", "style", "uslub")):
            return AIMemoryFact.CATEGORY_PREFERENCE
        if any(word in lowered for word in ("maqsad", "ielts", "goal", "target", "o'rganmoqchi", "yaxshilamoqchi")):
            return AIMemoryFact.CATEGORY_LEARNING_GOAL
        if any(word in lowered for word in ("qiynal", "qiyin", "tushunmay", "weak", "xato", "adash")):
            return AIMemoryFact.CATEGORY_WEAK_TOPIC
        if any(word in lowered for word in ("ertalab", "kechqurun", "vaqt", "schedule", "dushanba", "yakshanba")):
            return AIMemoryFact.CATEGORY_SCHEDULE
        if any(word in lowered for word in ("beginner", "intermediate", "advanced", "talaba", "student", "daraja")):
            return AIMemoryFact.CATEGORY_PROFILE
        return AIMemoryFact.CATEGORY_OTHER

    def infer_confidence(self, value: str) -> float:
        lowered = value.lower()
        if any(word in lowered for word in ("ehtimol", "balki", "shekilli", "maybe", "probably")):
            return 0.55
        return 0.82

    def make_key(self, category: str, value: str) -> str:
        canonical = self._canonical_key(category, value)
        if canonical:
            return canonical
        words = re.findall(r"[\w']+", value.lower())
        compact = "-".join(words[:8])
        return f"{category}:{compact}"[:120]

    def _canonical_key(self, category: str, value: str) -> str | None:
        lowered = value.lower()
        if category == AIMemoryFact.CATEGORY_PREFERENCE:
            if any(word in lowered for word in ("qisqa", "brief", "batafsil", "detailed", "uzun", "keng")):
                return f"{category}:answer_length"
            if "emoji" in lowered:
                return f"{category}:emoji"
            if any(word in lowered for word in ("o'zbek", "uzbek", "english", "ingliz", "til")):
                return f"{category}:language"
        if category == AIMemoryFact.CATEGORY_SCHEDULE:
            if any(word in lowered for word in ("ertalab", "kechqurun", "dushanba", "seshanba", "chorshanba", "vaqt")):
                return f"{category}:study_time"
        if category == AIMemoryFact.CATEGORY_PROFILE:
            if any(word in lowered for word in ("beginner", "boshlang", "intermediate", "advanced", "daraja")):
                return f"{category}:level"
        return None

    def _split_category(self, raw_fact: str) -> tuple[str | None, str]:
        text = (raw_fact or "").strip()
        if ":" not in text:
            return None, text
        prefix, value = text.split(":", 1)
        category = CATEGORY_ALIASES.get(prefix.strip().lower())
        return category, value if category else text
