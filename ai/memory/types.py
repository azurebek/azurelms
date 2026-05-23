from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MemoryCandidate:
    category: str
    key: str
    value: str
    confidence: float = 0.8
    visibility: str = "user_visible"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryExtraction:
    reply_text: str
    candidates: list[MemoryCandidate]


@dataclass(frozen=True)
class SavedMemory:
    fact: Any
    created: bool


@dataclass(frozen=True)
class ConversationContext:
    summary: str = ""
    recent_dialogue: str = ""
    summarized_message_count: int = 0
    recent_message_count: int = 0
