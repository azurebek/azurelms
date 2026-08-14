"""Smart Form Engine testlari — registratsiya, to'liq suhbat oqimi, statuslar."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ai.agent.types import AIRequest, ProviderResponse
from ai.skills.registry import SkillRegistry
from ai.smart_form.engine import SmartFormEngine
from ai.smart_form.extractor import LLMExtractor, parse_llm_json
from ai.smart_form.registry import get_form_class
from aicontrol.models import AISupplyEvent
from messenger.models import ChatRoom, Message, SmartFormSession
from users.models import UserOnboarding
from users.smart_forms import UserOnboardingSmartForm

User = get_user_model()


class _FakeProvider:
    def __init__(self, text="{}", error=None):
        self.text = text
        self.error = error
        self.prompts = []

    def generate(self, *, prompt, **kwargs):
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return ProviderResponse(text=self.text, model_name="fake-model")


def _make_room_with_session(user):
    room = ChatRoom.objects.create(room_type="ai", name="Azure AI Onboarding")
    room.participants.add(user)
    session = SmartFormSession.objects.create(chat_room=room, schema_name="user_onboarding")
    return room, session


class SmartFormRegistryTests(TestCase):
    def test_user_onboarding_form_is_registered_on_app_ready(self):
        # users/apps.py ready() import qiladi — avval bu umuman ishlamasdi
        # (users/forms/ namespace-package users/forms.py soyasida edi)
        self.assertIs(get_form_class("user_onboarding"), UserOnboardingSmartForm)


class SmartFormNormalizationTests(TestCase):
    def test_goal_and_level_are_normalized_to_model_choices(self):
        form = UserOnboardingSmartForm(goal="Sayohat", level="B1")
        self.assertEqual(form.goal, "travel")
        self.assertEqual(form.level, "b1")

    def test_unknown_values_fall_back_safely(self):
        form = UserOnboardingSmartForm(goal="kosmosga uchish", level="super")
        self.assertEqual(form.goal, "other")
        self.assertEqual(form.level, "unknown")

    def test_submit_creates_onboarding_and_returns_dashboard_url(self):
        user = User.objects.create_user(username="sf_u1", email="sf1@t.uz", password="x")
        form = UserOnboardingSmartForm(goal="travel", level="a2")
        result = form.submit(user=user)
        self.assertEqual(result, reverse("dashboard"))
        onboarding = UserOnboarding.objects.get(user=user)
        self.assertEqual(onboarding.goal, "travel")
        self.assertEqual(onboarding.current_level, "a2")


class SmartFormExtractorTests(TestCase):
    def test_parse_llm_json_handles_fences_and_noise(self):
        fenced = '```json\n{"goal": {"extracted_value": "travel"}}\n```'
        self.assertEqual(parse_llm_json(fenced)["goal"]["extracted_value"], "travel")
        noisy = 'Mana javob: {"level": {"extracted_value": "b1"}} — tayyor!'
        self.assertEqual(parse_llm_json(noisy)["level"]["extracted_value"], "b1")
        self.assertEqual(parse_llm_json("json emas"), {})

    def test_extractor_returns_fields_from_provider_json(self):
        provider = _FakeProvider(
            text='{"goal": {"extracted_value": "travel", "needs_confirmation": false},'
            ' "level": {"extracted_value": null, "needs_confirmation": false}}'
        )
        extractor = LLMExtractor(provider=provider)
        result = extractor.extract("Sayohat uchun o'rganaman", UserOnboardingSmartForm, {})
        self.assertEqual(result, {"goal": {"value": "travel", "status": "confirmed"}})
        # confirmed maydonlar qayta so'ralmaydi
        state = {"fields": {"goal": {"value": "travel", "status": "confirmed"},
                            "level": {"value": "b1", "status": "confirmed"}}}
        self.assertEqual(extractor.extract("yana nimadir", UserOnboardingSmartForm, state), {})
        self.assertFalse(AISupplyEvent.objects.exists())

    def test_extractor_survives_provider_failure(self):
        extractor = LLMExtractor(provider=_FakeProvider(error=RuntimeError("DO down")))
        self.assertEqual(extractor.extract("salom", UserOnboardingSmartForm, {}), {})


class SmartFormEngineFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sf_flow", email="sff@t.uz", password="x")
        self.room, self.session = _make_room_with_session(self.user)

    def test_full_conversation_flow_completes_and_submits(self):
        engine = SmartFormEngine(self.session)

        with patch.object(
            LLMExtractor,
            "extract",
            side_effect=[
                {"goal": {"value": "travel", "status": "confirmed"}},
                {"level": {"value": "B1", "status": "confirmed"}},
            ],
        ):
            intent1 = engine.process_user_message("Sayohat uchun o'rganmoqchiman")
            self.session.refresh_from_db()
            self.assertEqual(intent1, "ASK_LEVEL")
            self.assertEqual(self.session.status, SmartFormSession.STATUS_COLLECTING)

            intent2 = engine.process_user_message("Darajam B1 deb o'ylayman")

        self.assertEqual(intent2, f"SUBMIT_SUCCESS|{reverse('dashboard')}")
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, SmartFormSession.STATUS_COMPLETED)
        onboarding = UserOnboarding.objects.get(user=self.user)
        self.assertEqual(onboarding.goal, "travel")
        self.assertEqual(onboarding.current_level, "b1")

    def test_confirmation_intent_when_value_uncertain(self):
        engine = SmartFormEngine(self.session)
        with patch.object(
            LLMExtractor,
            "extract",
            return_value={"goal": {"value": "exam", "status": "needs_confirmation"}},
        ):
            intent = engine.process_user_message("balki imtihon uchundir")
        self.assertEqual(intent, "CONFIRM_GOAL")

    def test_extraction_failure_keeps_asking_not_crashing(self):
        engine = SmartFormEngine(self.session)
        with patch.object(LLMExtractor, "extract", return_value={}):
            intent = engine.process_user_message("shunchaki salom")
        self.assertEqual(intent, "ASK_GOAL")

    def test_runtime_extractor_ledgers_one_stable_smart_form_call(self):
        from aicontrol.supply import fingerprint_request
        from messenger.signals import suppress_ai_signal

        question = "Sayohat uchun o'rganmoqchiman"
        with suppress_ai_signal():
            user_message = Message.objects.create(
                room=self.room,
                sender=self.user,
                text=question,
            )
        provider = _FakeProvider(
            text=(
                '{"goal": {"extracted_value": "travel", '
                '"needs_confirmation": false}}'
            )
        )
        engine = SmartFormEngine(self.session)

        with patch("ai.providers.get_chat_provider", return_value=provider):
            self.assertEqual(engine.process_user_message(question), "ASK_LEVEL")
            # A retry for the same persisted user message must not create a
            # second remote call, even though the session state has changed.
            self.assertEqual(engine.process_user_message(question), "ASK_LEVEL")

        self.assertEqual(len(provider.prompts), 1)
        event = AISupplyEvent.objects.get()
        self.assertEqual(event.call_type, AISupplyEvent.CALL_SMART_FORM)
        self.assertEqual(event.status, AISupplyEvent.STATUS_SUCCEEDED)
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.actual_requests, 1)
        self.assertEqual(
            event.request_key,
            fingerprint_request(
                "smart-form",
                self.session.id,
                f"message:{user_message.id}",
            ),
        )


class SmartFormSkillSelectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sf_skill", email="sfs@t.uz", password="x")
        self.room, self.session = _make_room_with_session(self.user)
        self.registry = SkillRegistry()

    def _request(self):
        return AIRequest(room=self.room, student=self.user, user_question="salom")

    def test_active_session_routes_to_smart_form_skill(self):
        self.assertEqual(self.registry.select_for_request(self._request()).slug, "smart_form")

    def test_completed_session_releases_the_room(self):
        # Avvalgi bug: UPPERCASE status exclude — tugagan session ham xonani band qilardi
        self.session.status = SmartFormSession.STATUS_COMPLETED
        self.session.save(update_fields=["status"])
        self.assertIsNone(SmartFormSession.active_for_room(self.room))
        self.assertNotEqual(self.registry.select_for_request(self._request()).slug, "smart_form")


class StartSmartOnboardingViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sf_view", email="sfv@t.uz", password="pass-12345")
        self.client.force_login(self.user)

    def test_post_creates_room_session_and_welcome_message(self):
        response = self.client.post(reverse("start_smart_onboarding"))
        self.assertEqual(response.status_code, 302)

        session = SmartFormSession.objects.get(schema_name="user_onboarding")
        room = session.chat_room
        self.assertIn(self.user, room.participants.all())
        self.assertEqual(response["Location"], reverse("messenger:ai_room", args=[room.id]))

        welcome = Message.objects.get(room=room)
        self.assertTrue(welcome.is_ai_response)
        self.assertIn("maqsadda", welcome.text)

    def test_second_post_reuses_active_session(self):
        self.client.post(reverse("start_smart_onboarding"))
        self.client.post(reverse("start_smart_onboarding"))
        self.assertEqual(SmartFormSession.objects.filter(schema_name="user_onboarding").count(), 1)
