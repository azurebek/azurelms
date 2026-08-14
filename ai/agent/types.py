from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AIRequest:
    room: Any
    student: Any
    user_question: str
    context_lesson: Any | None = None
    requested_skill_slug: str | None = None
    # Xonaga yuklangan PDF'dan ajratilgan matn (bo'lsa) — prompt'ga hujjat bo'limi sifatida kiradi
    document_context: str = ""
    document_name: str = ""
    # Xonaga yuklangan oxirgi rasm (data-URL) — vision-model'ga to'g'ridan yuboriladi
    image_data_url: str = ""
    image_name: str = ""
    # Main remote reply is normally reserved by the Celery task before any
    # best-effort SmartForm/RAG/memory calls. Direct engine users may provide
    # only a request key and let the engine reserve it itself.
    supply_request_key: str = ""
    supply_reservation: Any | None = None


@dataclass(frozen=True)
class AIResponse:
    text: str
    model_name: str | None = None
    skill_slug: str | None = None
    saved_memory_fact: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResponse:
    text: str
    model_name: str
    web_search: dict[str, Any] | None = None
    # {"prompt_tokens", "completion_tokens", "total_tokens"} — provayder qaytarsa
    usage: dict[str, int] | None = None
