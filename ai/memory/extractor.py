import re

from .policy import MemoryPolicy
from .types import MemoryExtraction


SAVE_MEMORY_PATTERN = re.compile(r"<SAVE_MEMORY>(.*?)</SAVE_MEMORY>", re.DOTALL)


class MemoryExtractor:
    def __init__(self, policy: MemoryPolicy | None = None):
        self.policy = policy or MemoryPolicy()

    def extract(self, raw_reply: str, *, user_question: str = "") -> MemoryExtraction:
        reply = raw_reply or ""
        raw_facts = [match.strip() for match in SAVE_MEMORY_PATTERN.findall(reply)]
        cleaned_reply = SAVE_MEMORY_PATTERN.sub("", reply).strip()

        candidates = []
        for raw_fact in raw_facts:
            candidate = self.policy.build_candidate(raw_fact, user_question=user_question)
            if candidate:
                candidates.append(candidate)

        return MemoryExtraction(reply_text=cleaned_reply, candidates=candidates)

