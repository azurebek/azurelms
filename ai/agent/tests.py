"""AIEngine provider routing and project-wide supply guard tests."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import TestCase, override_settings

from ai.agent.engine import AIEngine
from ai.agent.types import AIRequest, ProviderResponse
from ai.providers import get_search_provider
from ai.skills.registry import SkillRegistry


def _conversation_ctx():
    return SimpleNamespace(
        recent_message_count=1,
        summarized_message_count=0,
        summary="",
        recent_dialogue="",
    )


def _rag_ctx():
    return SimpleNamespace(
        lesson_context="",
        rag_context="",
        access_note="",
        chunks=[],
        sources=[],
    )


def _fake_memory():
    memory = MagicMock()
    memory.sanitize_user_question.side_effect = lambda q: q
    memory.build_retrieval_query.side_effect = lambda *, room, question: question
    memory.get_conversation_context.return_value = _conversation_ctx()
    memory.render_relevant_memory.return_value = ""
    memory.extract_from_reply.side_effect = lambda text, **kw: SimpleNamespace(
        reply_text=text, candidates=[]
    )
    memory.save_candidates.return_value = []
    return memory


def _fake_provider(*, supports_web_search=False, supports_vision=False, text="javob", model="m", web=None):
    provider = MagicMock()
    provider.supports_web_search = supports_web_search
    provider.supports_vision = supports_vision
    provider.generate.return_value = ProviderResponse(text=text, model_name=model, web_search=web)
    return provider


def _make_engine(*, primary, search_provider, used_tools):
    rag = MagicMock()
    rag.build.return_value = _rag_ctx()
    prompt_builder = MagicMock()
    prompt_builder.build.return_value = "PROMPT"
    tool_ctx = MagicMock()
    tool_ctx.build.return_value = SimpleNamespace(rendered="", used_tools=used_tools)
    skill_registry = MagicMock()
    skill_registry.select_for_request.return_value = SkillRegistry().get("general_chat")
    return AIEngine(
        memory_service=_fake_memory(),
        rag_service=rag,
        prompt_builder=prompt_builder,
        provider=primary,
        search_provider=search_provider,
        skill_registry=skill_registry,
        tool_context_service=tool_ctx,
    )


def _student():
    return SimpleNamespace(ai_web_search_effort="light", ai_model="llama-4-maverick")


class SearchProviderFactoryTests(TestCase):
    @override_settings(GEMINI_API_KEY="test-key")
    def test_returns_gemini_when_key_present(self):
        provider = get_search_provider()
        self.assertIsNotNone(provider)
        self.assertTrue(getattr(provider, "supports_web_search", False))

    @override_settings(GEMINI_API_KEY=None)
    def test_returns_none_without_key(self):
        self.assertIsNone(get_search_provider())


class EngineProviderRoutingTests(TestCase):
    def test_normal_chat_never_touches_search_provider(self):
        # ENG MUHIM KAFOLAT: oddiy suhbatda Gemini chaqirilmaydi
        primary = _fake_provider(supports_vision=True, text="maverick javob", model="llama-4-maverick")
        search = _fake_provider(supports_web_search=True, text="gemini", model="gemini-2.5-flash")
        engine = _make_engine(primary=primary, search_provider=search, used_tools=[])

        response = engine.generate_reply(
            AIRequest(room=None, student=_student(), user_question="Salom, qalaysan?")
        )

        primary.generate.assert_called_once()
        search.generate.assert_not_called()
        self.assertEqual(response.text, "maverick javob")
        self.assertFalse(response.metadata["search_specialist_used"])

    @override_settings(AI_FREE_TIER_MODE=False, GEMINI_GROUNDING_ENABLED=True)
    def test_web_search_query_routes_to_gemini_specialist_in_admitted_mode(self):
        primary = _fake_provider(supports_vision=True, model="llama-4-maverick")
        search = _fake_provider(
            supports_web_search=True,
            text="grounded javob",
            model="gemini-2.5-flash",
            web={"queries": ["dollar kursi"], "sources": [{"title": "cbu", "uri": "https://cbu.uz"}]},
        )
        engine = _make_engine(primary=primary, search_provider=search, used_tools=["web_search"])

        response = engine.generate_reply(
            AIRequest(room=None, student=_student(), user_question="Bugungi dollar kursi qancha?")
        )

        search.generate.assert_called_once()
        primary.generate.assert_not_called()
        # Gemini'ga DO model nomi uzatilmasligi kerak (o'z defoltini ishlatadi)
        self.assertNotIn("selected_model", search.generate.call_args.kwargs)
        self.assertTrue(search.generate.call_args.kwargs["enable_web_search"])
        self.assertTrue(response.metadata["search_specialist_used"])
        self.assertEqual(response.metadata["web_search_sources"], [{"title": "cbu", "uri": "https://cbu.uz"}])

    @override_settings(AI_FREE_TIER_MODE=True, GEMINI_GROUNDING_ENABLED=True)
    def test_free_tier_web_query_stays_on_primary_without_grounding(self):
        primary = _fake_provider(
            supports_web_search=True,
            text="Jonli ma'lumotni tekshira olmayman.",
            model="gemini-3.1-flash-lite",
        )
        search = _fake_provider(
            supports_web_search=True,
            text="grounded bo'lmasligi kerak",
            model="gemini-3.1-flash-lite",
        )
        engine = _make_engine(primary=primary, search_provider=search, used_tools=["web_search"])

        response = engine.generate_reply(
            AIRequest(room=None, student=_student(), user_question="Bugungi kursni qidirib ber")
        )

        primary.generate.assert_called_once()
        search.generate.assert_not_called()
        self.assertFalse(primary.generate.call_args.kwargs["enable_web_search"])
        self.assertTrue(response.metadata["web_search_requested"])
        self.assertTrue(response.metadata["web_search_blocked_by_free_tier"])
        self.assertFalse(response.metadata["web_search_enabled"])
        self.assertFalse(response.metadata["search_specialist_used"])

    def test_web_query_without_specialist_falls_back_to_primary_honestly(self):
        # Kalit yo'q (search_provider=None) → maverick'da halol javob, crash yo'q
        primary = _fake_provider(supports_vision=True, text="halol javob", model="llama-4-maverick")
        engine = _make_engine(primary=primary, search_provider=None, used_tools=["web_search"])

        response = engine.generate_reply(
            AIRequest(room=None, student=_student(), user_question="Bugungi ob-havo?")
        )

        primary.generate.assert_called_once()
        self.assertFalse(primary.generate.call_args.kwargs["enable_web_search"])
        self.assertFalse(response.metadata["search_specialist_used"])

    @override_settings(AI_FREE_TIER_MODE=False, GEMINI_GROUNDING_ENABLED=True)
    def test_search_specialist_quota_failure_does_not_fan_out_to_primary(self):
        # 429 boshqa provider chainni boshlamasligi kerak: circuit shu yerda ochiladi.
        primary = _fake_provider(text="halol javob (qidiruvsiz)", model="llama-4-maverick")
        search = _fake_provider(supports_web_search=True, model="gemini-2.5-flash")
        search.generate.side_effect = RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")
        engine = _make_engine(primary=primary, search_provider=search, used_tools=["web_search"])

        response = engine.generate_reply(
            AIRequest(room=None, student=_student(), user_question="internetdan qidirib top")
        )

        search.generate.assert_called_once()
        primary.generate.assert_not_called()
        self.assertIsNone(response.model_name)
        self.assertIn("limit", response.text.lower())

    def test_primary_failure_still_returns_fallback_message(self):
        # Asosiy provayder yiqilsa eski xatti-harakat saqlanadi: fallback xabar
        primary = _fake_provider(model="llama-4-maverick")
        primary.generate.side_effect = RuntimeError("DO down")
        engine = _make_engine(primary=primary, search_provider=None, used_tools=[])

        response = engine.generate_reply(
            AIRequest(room=None, student=_student(), user_question="salom")
        )

        self.assertIsNone(response.model_name)
        self.assertTrue(response.text)

    def test_retrieval_uses_context_augmented_query_but_prompt_keeps_original(self):
        # "davom et" kabi qisqa savolda memory/RAG boyitilgan so'rov bilan qidiradi,
        # promptdagi user_question esa asl xabarligicha qoladi.
        primary = _fake_provider(text="javob", model="llama-4-maverick")
        engine = _make_engine(primary=primary, search_provider=None, used_tools=[])
        engine.memory_service.build_retrieval_query.side_effect = (
            lambda *, room, question: f"Turkchada kelasi zamon qanday yasaladi?\n{question}"
        )

        response = engine.generate_reply(
            AIRequest(room=None, student=_student(), user_question="davom et")
        )

        memory_kwargs = engine.memory_service.render_relevant_memory.call_args.kwargs
        rag_kwargs = engine.rag_service.build.call_args.kwargs
        prompt_kwargs = engine.prompt_builder.build.call_args.kwargs
        self.assertIn("kelasi zamon", memory_kwargs["question"])
        self.assertIn("kelasi zamon", rag_kwargs["question"])
        self.assertEqual(prompt_kwargs["user_question"], "davom et")
        self.assertTrue(response.metadata["retrieval_query_augmented"])

    def test_image_plus_web_query_prefers_vision_on_primary(self):
        # Rasm bor → vision ustun: maverick'da qoladi, Gemini chaqirilmaydi
        primary = _fake_provider(supports_vision=True, text="rasm tahlili", model="llama-4-maverick")
        search = _fake_provider(supports_web_search=True, model="gemini-2.5-flash")
        engine = _make_engine(primary=primary, search_provider=search, used_tools=["web_search"])

        request = AIRequest(
            room=None,
            student=_student(),
            user_question="rasmda nima va bugungi narxi qancha?",
            image_data_url="data:image/jpeg;base64,xxx",
            image_name="foto.png",
        )
        response = engine.generate_reply(request)

        primary.generate.assert_called_once()
        search.generate.assert_not_called()
        self.assertEqual(primary.generate.call_args.kwargs["images"], ["data:image/jpeg;base64,xxx"])
        self.assertTrue(response.metadata["vision_used"])
