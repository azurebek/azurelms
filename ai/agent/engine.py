import logging

from ai.agent.types import AIRequest, AIResponse
from ai.memory.service import MemoryService
from ai.prompts.builder import PromptBuilder
from ai.providers.gemini import GeminiProvider, fallback_ai_reply
from ai.rag.context import RAGContextService
from ai.skills.registry import SkillRegistry


logger = logging.getLogger(__name__)


class AIEngine:
    def __init__(
        self,
        *,
        memory_service: MemoryService | None = None,
        rag_service: RAGContextService | None = None,
        prompt_builder: PromptBuilder | None = None,
        provider: GeminiProvider | None = None,
        skill_registry: SkillRegistry | None = None,
    ):
        self.memory_service = memory_service or MemoryService()
        self.rag_service = rag_service or RAGContextService()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.provider = provider or GeminiProvider()
        self.skill_registry = skill_registry or SkillRegistry()

    def generate_reply(self, request: AIRequest) -> AIResponse:
        try:
            skill = self.skill_registry.select_for_request(request)
            safe_question = self.memory_service.sanitize_user_question(request.user_question)
            dialogue = self.memory_service.get_recent_dialogue(request.room)
            long_term_memory = self.memory_service.get_long_term_memory(request.student)
            rag_context = self.rag_service.build(
                user=request.student,
                question=safe_question,
                context_lesson=request.context_lesson,
            )
            prompt = self.prompt_builder.build(
                student=request.student,
                skill=skill,
                long_term_memory=long_term_memory.learned_facts,
                dialogue=dialogue,
                lesson_context=rag_context.lesson_context,
                rag_context=rag_context.rag_context,
                user_question=safe_question,
            )
            provider_response = self.provider.generate(
                prompt=prompt,
                selected_model=getattr(request.student, "ai_model", None),
            )

            reply_without_tag, new_fact = self.memory_service.extract_memory_directive(provider_response.text)
            clean_reply = self._sanitize_reply(reply_without_tag)
            if new_fact:
                self.memory_service.append_fact(long_term_memory, new_fact)

            return AIResponse(
                text=clean_reply,
                model_name=provider_response.model_name,
                skill_slug=skill.slug,
                saved_memory_fact=new_fact,
                metadata={"rag_chunks": len(rag_context.chunks)},
            )
        except Exception as exc:
            logger.exception(
                "AI engine failed for room_id=%s student_id=%s",
                getattr(request.room, "id", None),
                getattr(request.student, "id", None),
            )
            return AIResponse(text=fallback_ai_reply(exc))

    def _sanitize_reply(self, reply: str) -> str:
        return (reply or "").replace("**", "").replace("__", "").replace("`", "").replace("#", "").strip()
