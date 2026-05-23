from messenger.models import Message

from .extractor import MemoryExtractor
from .summarizer import ConversationSummarizer
from .types import ConversationContext, MemoryExtraction
from .repository import MemoryRepository
from .retriever import MemoryRetriever


class MemoryService:
    RECENT_DIALOGUE_LIMIT = 8
    SUMMARY_BATCH_LIMIT = 30

    def __init__(
        self,
        *,
        extractor: MemoryExtractor | None = None,
        repository: MemoryRepository | None = None,
        retriever: MemoryRetriever | None = None,
        summarizer: ConversationSummarizer | None = None,
    ):
        self.extractor = extractor or MemoryExtractor()
        self.repository = repository or MemoryRepository()
        self.retriever = retriever or MemoryRetriever(repository=self.repository)
        self.summarizer = summarizer or ConversationSummarizer()

    def is_enabled_for(self, student) -> bool:
        return bool(getattr(student, "ai_memory_enabled", True))

    def get_recent_dialogue(self, room, limit: int = 10) -> str:
        recent_messages = list(
            Message.objects.filter(room=room).select_related("sender").order_by("-created_at")[:limit]
        )
        return self._render_dialogue(reversed(recent_messages))

    def get_conversation_context(self, *, room, student, recent_limit: int | None = None) -> ConversationContext:
        recent_limit = recent_limit or self.RECENT_DIALOGUE_LIMIT
        messages = list(Message.objects.filter(room=room).select_related("sender").order_by("created_at"))

        if not messages:
            return ConversationContext()

        recent_messages = messages[-recent_limit:]
        recent_dialogue = self._render_dialogue(recent_messages)

        if not self.is_enabled_for(student) or len(messages) <= recent_limit:
            return ConversationContext(
                recent_dialogue=recent_dialogue,
                recent_message_count=len(recent_messages),
            )

        older_messages = messages[:-recent_limit]
        summary = self._build_or_update_summary(room=room, older_messages=older_messages)
        return ConversationContext(
            summary=summary,
            recent_dialogue=recent_dialogue,
            summarized_message_count=len(older_messages),
            recent_message_count=len(recent_messages),
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

    def _build_or_update_summary(self, *, room, older_messages: list[Message]) -> str:
        if not older_messages:
            return ""

        stored_summary = self.repository.get_conversation_summary(room=room)
        existing_summary = stored_summary.summary_text or ""
        messages_to_add = older_messages[-self.SUMMARY_BATCH_LIMIT :]

        if stored_summary.covered_message_id:
            covered_index = next(
                (
                    index
                    for index, message in enumerate(older_messages)
                    if message.id == stored_summary.covered_message_id
                ),
                None,
            )
            if covered_index is not None:
                messages_to_add = older_messages[covered_index + 1 :]
            else:
                existing_summary = ""

        if not messages_to_add and existing_summary:
            return existing_summary

        summary_text = self.summarizer.build(
            existing_summary=existing_summary,
            messages=messages_to_add,
        )
        last_covered = older_messages[-1]
        self.repository.save_conversation_summary(
            room=room,
            summary_text=summary_text,
            covered_message=last_covered,
            covered_message_count=len(older_messages),
        )
        return summary_text

    def _render_dialogue(self, messages) -> str:
        return "\n".join(
            f"{message.sender.username if message.sender else 'Azure AI'}: {message.text}"
            for message in messages
        )
