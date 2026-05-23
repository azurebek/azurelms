from messenger.models import Message


class ConversationSummarizer:
    """Build a compact, deterministic summary from older chat messages."""

    def __init__(self, *, max_chars: int = 1600, max_message_chars: int = 180):
        self.max_chars = max_chars
        self.max_message_chars = max_message_chars

    def build(self, *, existing_summary: str = "", messages: list[Message]) -> str:
        lines = []
        if existing_summary.strip():
            lines.extend(self._clean_existing(existing_summary))

        for message in messages:
            text = self._compact_text(message.text)
            if not text:
                continue
            speaker = "O'quvchi" if message.sender_id else "Azure AI"
            lines.append(f"- {speaker}: {text}")

        return self._trim_lines(lines)

    def _clean_existing(self, existing_summary: str) -> list[str]:
        return [
            line.strip()
            for line in existing_summary.splitlines()
            if line.strip() and line.strip() != "Oldingi suhbat qisqa mazmuni:"
        ]

    def _compact_text(self, text: str) -> str:
        compact = " ".join((text or "").split())
        if len(compact) <= self.max_message_chars:
            return compact
        return f"{compact[: self.max_message_chars - 3].rstrip()}..."

    def _trim_lines(self, lines: list[str]) -> str:
        if not lines:
            return ""

        kept = []
        total = len("Oldingi suhbat qisqa mazmuni:\n")
        for line in reversed(lines):
            next_total = total + len(line) + 1
            if kept and next_total > self.max_chars:
                break
            kept.append(line)
            total = next_total

        kept.reverse()
        return "Oldingi suhbat qisqa mazmuni:\n" + "\n".join(kept)
