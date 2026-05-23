from messenger.models import Message

from .extractor import MemoryExtractor
from .types import MemoryExtraction
from .repository import MemoryRepository
from .retriever import MemoryRetriever


class MemoryService:
    def __init__(
        self,
        *,
        extractor: MemoryExtractor | None = None,
        repository: MemoryRepository | None = None,
        retriever: MemoryRetriever | None = None,
    ):
        self.extractor = extractor or MemoryExtractor()
        self.repository = repository or MemoryRepository()
        self.retriever = retriever or MemoryRetriever(repository=self.repository)

    def is_enabled_for(self, student) -> bool:
        return bool(getattr(student, "ai_memory_enabled", True))

    def get_recent_dialogue(self, room, limit: int = 10) -> str:
        recent_messages = Message.objects.filter(room=room).order_by("-created_at")[:limit]
        return "\n".join(
            f"{message.sender.username if message.sender else 'Azure AI'}: {message.text}"
            for message in reversed(recent_messages)
        )

    def sanitize_user_question(self, question: str | None) -> str:
        return (question or "").replace("<SAVE_MEMORY>", "").replace("</SAVE_MEMORY>", "")

    def render_relevant_memory(self, *, student, question: str, limit: int = 7) -> str:
        if not self.is_enabled_for(student):
            return ""
        return self.retriever.render_for_prompt(user=student, question=question, limit=limit)

    def extract_from_reply(self, raw_reply: str, *, user_question: str = "", student=None):
        if student is not None and not self.is_enabled_for(student):
            cleaned = self.extractor.extract(raw_reply, user_question=user_question).reply_text
            return MemoryExtraction(reply_text=cleaned, candidates=[])
        return self.extractor.extract(raw_reply, user_question=user_question)

    def save_candidates(self, *, student, candidates, source_room=None, source_message=None):
        if not self.is_enabled_for(student):
            return []
        saved = []
        for candidate in candidates:
            saved.append(
                self.repository.save_candidate(
                    user=student,
                    candidate=candidate,
                    source_room=source_room,
                    source_message=source_message,
                )
            )
        return saved
