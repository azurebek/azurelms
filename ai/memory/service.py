import re

from messenger.models import AILongTermMemory, Message


SAVE_MEMORY_PATTERN = re.compile(r"<SAVE_MEMORY>(.*?)</SAVE_MEMORY>", re.DOTALL)


class MemoryService:
    def get_recent_dialogue(self, room, limit: int = 10) -> str:
        recent_messages = Message.objects.filter(room=room).order_by("-created_at")[:limit]
        return "\n".join(
            f"{message.sender.username if message.sender else 'Azure AI'}: {message.text}"
            for message in reversed(recent_messages)
        )

    def get_long_term_memory(self, student) -> AILongTermMemory:
        memory, _ = AILongTermMemory.objects.get_or_create(user=student)
        return memory

    def sanitize_user_question(self, question: str | None) -> str:
        return (question or "").replace("<SAVE_MEMORY>", "").replace("</SAVE_MEMORY>", "")

    def extract_memory_directive(self, raw_reply: str) -> tuple[str, str | None]:
        match = SAVE_MEMORY_PATTERN.search(raw_reply or "")
        if not match:
            return raw_reply, None
        fact = match.group(1).strip()
        reply_without_tag = SAVE_MEMORY_PATTERN.sub("", raw_reply, count=1).strip()
        return reply_without_tag, fact or None

    def append_fact(self, memory: AILongTermMemory, fact: str | None) -> None:
        if not fact:
            return
        normalized_fact = " ".join(fact.split())
        existing_lines = {line.strip() for line in (memory.learned_facts or "").splitlines()}
        bullet = f"- {normalized_fact}"
        if bullet in existing_lines:
            return
        memory.learned_facts = f"{memory.learned_facts}\n{bullet}" if memory.learned_facts else bullet
        memory.save(update_fields=["learned_facts", "updated_at"])
