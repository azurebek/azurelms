import logging
import re

from aicontrol.models import AISettings, AISupplyEvent
from aicontrol.supply import (
    execute_provider_call,
    execute_reserved_provider_call,
    normalize_request_key,
    reconcile_supply,
    set_reservation_call_type,
)
from ai.agent.types import AIRequest, AIResponse
from ai.memory.service import MemoryService
from ai.prompts.builder import PromptBuilder
from ai.providers import get_chat_provider, get_search_provider
from ai.providers.gemini import fallback_ai_reply
from ai.rag.context import RAGContextService
from ai.skills.registry import SkillRegistry
from ai.tools.context import ToolContextService


logger = logging.getLogger(__name__)

# search_provider'ni "berilmagan" (default → get_search_provider) va "ataylab None"
# (mutaxassis yo'q) holatlarini farqlash uchun sentinel.
_UNSET = object()


class AIEngine:
    def __init__(
        self,
        *,
        memory_service: MemoryService | None = None,
        rag_service: RAGContextService | None = None,
        prompt_builder: PromptBuilder | None = None,
        provider=None,
        search_provider=_UNSET,
        skill_registry: SkillRegistry | None = None,
        tool_context_service: ToolContextService | None = None,
    ):
        self.memory_service = memory_service or MemoryService()
        self.rag_service = rag_service or RAGContextService()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.provider = provider or get_chat_provider()
        # Web-qidiruv mutaxassisi (Gemini) — faqat qidiruv kerak bo'lganda ishlatiladi.
        # GeminiProvider konstruktori tarmoqqa chiqmaydi (kalitni o'qiydi xolos), shuning
        # uchun har so'rovda yaratish arzon; genai.Client faqat generate()da tuziladi.
        self.search_provider = get_search_provider() if search_provider is _UNSET else search_provider
        self.skill_registry = skill_registry or SkillRegistry()
        self.tool_context_service = tool_context_service or ToolContextService()

    def generate_reply(self, request: AIRequest) -> AIResponse:
        supply_reservation = getattr(request, "supply_reservation", None)
        provider_invoked = False
        try:
            skill = self.skill_registry.select_for_request(request)
            tool_context = self.tool_context_service.build(request=request, skill=skill)
            safe_question = self.memory_service.sanitize_user_question(request.user_question)
            
            if skill.slug == "smart_form" and getattr(request, "room", None):
                from messenger.models import SmartFormSession
                from ai.smart_form.engine import SmartFormEngine

                active_session = SmartFormSession.active_for_room(request.room)
                if active_session:
                    # Forma dvigateli yiqilsa ham chat javob berishda davom etsin
                    try:
                        form_engine = SmartFormEngine(active_session)
                        intent = form_engine.process_user_message(safe_question)
                    except Exception:
                        logger.exception("SmartFormEngine xatosi (session=%s)", active_session.id)
                        intent = "ASK_RETRY"
                    safe_question = f"{safe_question}\n\n[SYSTEM INSTRUCTION - SMART FORM ENGINE INTENT: {intent}]"
            
            conversation_context = self.memory_service.get_conversation_context(
                room=request.room,
                student=request.student,
            )
            # Qisqa/anaforik savol ("davom et", "buni tushuntir") retrieval uchun oldingi
            # user xabarlari bilan boyitiladi — promptdagi user_question o'zgarmaydi.
            retrieval_query = self.memory_service.build_retrieval_query(
                room=request.room,
                question=safe_question,
            )
            relevant_memory = self.memory_service.render_relevant_memory(
                student=request.student,
                question=retrieval_query,
            )
            rag_context = self.rag_service.build(
                user=request.student,
                question=retrieval_query,
                context_lesson=request.context_lesson,
            )
            is_first_message = (
                conversation_context.recent_message_count <= 1
                and conversation_context.summarized_message_count == 0
            )
            prompt = self.prompt_builder.build(
                student=request.student,
                skill=skill,
                long_term_memory=relevant_memory,
                conversation_summary=conversation_context.summary,
                dialogue=conversation_context.recent_dialogue,
                lesson_context=rag_context.lesson_context,
                rag_context=rag_context.rag_context,
                rag_access_note=rag_context.access_note,
                tool_context=tool_context.rendered,
                user_question=safe_question,
                is_first_message=is_first_message,
                document_context=getattr(request, "document_context", "") or "",
                document_name=getattr(request, "document_name", "") or "",
                image_name=getattr(request, "image_name", "") or "",
            )
            effort = getattr(request.student, "ai_web_search_effort", "light") or "light"
            try:
                heavy_search_enabled = AISettings.load().heavy_search_enabled
            except Exception:
                # Policy read failure cannot silently turn every message into a
                # grounded request while free-tier conservation is active.
                heavy_search_enabled = False
            wants_web_search = "web_search" in tool_context.used_tools or (
                heavy_search_enabled and effort == "heavy"
            )
            image_data_url = getattr(request, "image_data_url", "") or ""

            # --- Provayderni qobiliyat bo'yicha tanlash ---
            # Local profilning asosiy provideri Gemini. Grounding faqat explicit
            # web_search tool (yoki owner yoqqan heavy mode) bo'lganda ishlaydi.
            # DigitalOcean esa alohida admissiongacha HOLD.
            active_provider = self.provider
            enable_web_search = False
            used_search_specialist = False
            if wants_web_search and not image_data_url:
                if getattr(self.provider, "supports_web_search", False):
                    enable_web_search = True
                elif self.search_provider is not None:
                    active_provider = self.search_provider
                    enable_web_search = True
                    used_search_specialist = True
                # aks holda: qidiruv backendi yo'q → asosiy provayderda halol javob

            generate_kwargs = {"prompt": prompt, "enable_web_search": enable_web_search}
            # Foydalanuvchi tanlagan model faqat asosiy provayderga tegishli
            # (Gemini mutaxassisi DO model nomini tanimaydi — o'z defoltini ishlatadi).
            if not used_search_specialist:
                generate_kwargs["selected_model"] = getattr(request.student, "ai_model", None)
            if image_data_url and getattr(active_provider, "supports_vision", False):
                generate_kwargs["images"] = [image_data_url]

            search_specialist_failed = False
            try:
                call_type = (
                    AISupplyEvent.CALL_SEARCH
                    if enable_web_search
                    else AISupplyEvent.CALL_CHAT
                )
                if supply_reservation is not None:
                    set_reservation_call_type(supply_reservation, call_type)
                    provider_invoked = True
                    provider_response = execute_reserved_provider_call(
                        supply_reservation,
                        active_provider,
                        **generate_kwargs,
                    )
                else:
                    provider_invoked = True
                    provider_response = execute_provider_call(
                        active_provider,
                        request_key=normalize_request_key(
                            getattr(request, "supply_request_key", "") or None,
                            prefix="engine",
                        ),
                        call_type=call_type,
                        user=request.student,
                        max_requests=2,
                        **generate_kwargs,
                    )
            except Exception:
                # A failed grounded call must not fan out into a second provider
                # chain. Gemini itself is already bounded to at most two physical
                # attempts, and 429/quota opens the project circuit immediately.
                raise

            extraction = self.memory_service.extract_from_reply(
                provider_response.text,
                user_question=safe_question,
                student=request.student,
            )
            clean_reply = self._sanitize_reply(
                extraction.reply_text,
                strip_leading_greeting=not is_first_message,
            )
            saved_memories = self.memory_service.save_candidates(
                student=request.student,
                candidates=extraction.candidates,
                source_room=request.room,
            )

            web_search_meta = provider_response.web_search or {}
            return AIResponse(
                text=clean_reply,
                model_name=provider_response.model_name,
                skill_slug=skill.slug,
                saved_memory_fact=saved_memories[0].fact.value if saved_memories else None,
                metadata={
                    "rag_chunks": len(rag_context.chunks),
                    "rag_sources": rag_context.sources,
                    "rag_access_note": rag_context.access_note,
                    "memory_candidates": len(extraction.candidates),
                    "saved_memories": len(saved_memories),
                    "summarized_messages": conversation_context.summarized_message_count,
                    "recent_dialogue_messages": conversation_context.recent_message_count,
                    "active_skill": skill.slug,
                    "requested_skill": request.requested_skill_slug or "auto",
                    "retrieval_query_augmented": retrieval_query != safe_question,
                    "used_tools": tool_context.used_tools,
                    "document_name": getattr(request, "document_name", "") or "",
                    "image_name": getattr(request, "image_name", "") or "",
                    "vision_used": bool(generate_kwargs.get("images")),
                    "search_specialist_used": used_search_specialist,
                    "search_specialist_failed": search_specialist_failed,
                    "web_search_requested": enable_web_search,
                    # Requested grounding can be retried without the tool when
                    # a model rejects it. Only provider grounding metadata is
                    # evidence that web search actually ran.
                    "web_search_enabled": bool(web_search_meta),
                    "web_search_queries": web_search_meta.get("queries", []),
                    "web_search_sources": web_search_meta.get("sources", []),
                    "usage": provider_response.usage or {},
                },
            )
        except Exception as exc:
            if supply_reservation is not None and not provider_invoked:
                try:
                    reconcile_supply(
                        supply_reservation,
                        succeeded=False,
                        actual_requests=0,
                        error=exc,
                        error_kind="pre_provider_error",
                    )
                except Exception:
                    logger.exception("Unused main AI reservation reconciliation failed")
            logger.exception(
                "AI engine failed for room_id=%s student_id=%s",
                getattr(request.room, "id", None),
                getattr(request.student, "id", None),
            )
            return AIResponse(text=fallback_ai_reply(exc))

    # `(Manba 1)` / `(Manba 1, 2)` / `(Manba 1, Manba 2, Manba 3)` shaklidagi inline citation'larni topadi.
    _INLINE_SOURCE_RE = re.compile(
        r"\s*\((?:Manba|Source)\s*\d+(?:\s*,\s*(?:Manba|Source)?\s*\d+)*\)",
        flags=re.IGNORECASE,
    )
    # Javob oxiridagi "Manbalar:" / "Sources:" ro'yxatini topadi (boshqa muhim matn yo'q deb taxmin qilamiz).
    _TRAILING_SOURCES_RE = re.compile(
        r"\n+\s*(?:Manbalar|Sources)\s*:.*\Z",
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Davomli suhbatda javob boshidagi salom murojaatini (va keyingi bo'sh satrlarni) topadi:
    # "Salom!", "Salom, Aziz!", "Assalomu alaykum, Aziz", "Hi Aziz", "Aziz," va shu kabilar.
    _LEADING_GREETING_RE = re.compile(
        r"^\s*(?:assalomu\s+alaykum|salom|salomlar|hayrli\s+kun|hello|hi|hey)\b[^\n]*\n+",
        flags=re.IGNORECASE,
    )

    def _sanitize_reply(self, reply: str, *, strip_leading_greeting: bool = False) -> str:
        text = (reply or "").replace("**", "").replace("__", "").replace("`", "").replace("#", "")
        text = self._TRAILING_SOURCES_RE.sub("", text)
        text = self._INLINE_SOURCE_RE.sub("", text)
        if strip_leading_greeting:
            text = self._LEADING_GREETING_RE.sub("", text, count=1)
        # Citation'larni olib tashlagandan keyin qolgan ortiqcha bo'sh joylar va satrlarni siqib qo'yamiz.
        text = re.sub(r"[ \t]+([.!?,:;])", r"\1", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
