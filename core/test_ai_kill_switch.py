"""A2 — AI kill switch: bitta tugma bilan barcha remote chaqiruvni to'xtatish.

Nega kerak edi: `AISettings` da `supply_enforcement_enabled` bor, ammo u
**budjetni** o'chiradi — ya'ni teskari ta'sir qiladi. Umumiy "AI ni hoziroq
to'xtat" tugmasi yo'q edi, va uni Django admin orqali qilish ham mumkin emas,
chunki admin default o'chiq (`ENABLE_LEGACY_ADMIN=False`).

Kill switch ataylab budjetdan **mustaqil**: enforcement o'chirilgan bo'lsa ham
u ishlaydi, chunki bu shoshilinch to'xtatish tugmasi, sozlama emas.

Muhim chegara: to'xtatish faqat **remote AI** ga tegishli. Kurs, dars, to'lov,
davomat va odam bilan yozishuv oqimlari ishlashda davom etadi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from aicontrol.models import AISettings, AISupplyEvent
from aicontrol.supply import SupplyDenied, execute_provider_call, reserve_supply

User = get_user_model()


class FakeProvider:
    """Chaqirilgan-chaqirilmaganini sanaydi; tarmoqqa chiqmaydi."""

    last_attempt_count = 1
    last_error_kind = None

    def __init__(self):
        self.calls = 0

    def generate(self, **kwargs):
        from ai.agent.types import ProviderResponse

        self.calls += 1
        return ProviderResponse(text="javob", model_name="test", usage={"total_tokens": 5})


class KillSwitchEnforcementTests(TestCase):
    def setUp(self):
        AISettings.objects.all().delete()
        AISupplyEvent.objects.all().delete()
        self.policy = AISettings.load()

    def _turn_off(self):
        self.policy.ai_remote_calls_enabled = False
        self.policy.save(update_fields=["ai_remote_calls_enabled", "updated_at"])

    def test_calls_pass_while_the_switch_is_on(self):
        provider = FakeProvider()
        execute_provider_call(
            provider, request_key="ks:on", call_type=AISupplyEvent.CALL_CHAT,
            prompt="salom", max_requests=1,
        )
        self.assertEqual(provider.calls, 1)

    def test_switch_off_blocks_the_call_before_any_network(self):
        self._turn_off()
        provider = FakeProvider()
        with self.assertRaises(SupplyDenied):
            execute_provider_call(
                provider, request_key="ks:off", call_type=AISupplyEvent.CALL_CHAT,
                prompt="salom", max_requests=1,
            )
        self.assertEqual(provider.calls, 0, "kill switch yoqiq bo'lsa ham provider chaqirildi")

    def test_refusal_is_recorded_in_the_ledger_with_its_reason(self):
        self._turn_off()
        with self.assertRaises(SupplyDenied):
            reserve_supply(request_key="ks:ledger", call_type=AISupplyEvent.CALL_CHAT)
        event = AISupplyEvent.objects.get(request_key="ks:ledger")
        self.assertEqual(event.status, AISupplyEvent.STATUS_REJECTED)
        self.assertEqual(event.error_kind, "kill_switch")
        self.assertEqual(event.accounted_requests, 0)

    def test_switch_works_even_when_budget_enforcement_is_disabled(self):
        """Kill switch budjet sozlamasi emas — enforcement o'chiq bo'lsa ham ishlaydi."""
        self.policy.ai_remote_calls_enabled = False
        self.policy.supply_enforcement_enabled = False
        self.policy.save(update_fields=[
            "ai_remote_calls_enabled", "supply_enforcement_enabled", "updated_at",
        ])
        with self.assertRaises(SupplyDenied):
            reserve_supply(request_key="ks:no-enforcement", call_type=AISupplyEvent.CALL_CHAT)

    def test_every_call_type_is_stopped_not_just_chat(self):
        self._turn_off()
        for call_type in (
            AISupplyEvent.CALL_SEARCH,
            AISupplyEvent.CALL_SMART_FORM,
            AISupplyEvent.CALL_BOT_GUEST,
            AISupplyEvent.CALL_RAG_EMBEDDING,
            AISupplyEvent.CALL_REINDEX,
        ):
            with self.subTest(call_type=call_type):
                with self.assertRaises(SupplyDenied):
                    reserve_supply(request_key=f"ks:{call_type}", call_type=call_type)

    def test_turning_the_switch_back_on_restores_calls(self):
        self._turn_off()
        self.policy.ai_remote_calls_enabled = True
        self.policy.save(update_fields=["ai_remote_calls_enabled", "updated_at"])

        provider = FakeProvider()
        execute_provider_call(
            provider, request_key="ks:back-on", call_type=AISupplyEvent.CALL_CHAT,
            prompt="salom", max_requests=1,
        )
        self.assertEqual(provider.calls, 1)


class KillSwitchControlSurfaceTests(TestCase):
    def setUp(self):
        AISettings.objects.all().delete()
        AISettings.load()
        self.owner = User.objects.create_superuser(
            username="ks_owner", email="ks_owner@t.uz", password="pass-12345")
        self.staff = User.objects.create_user(
            username="ks_staff", email="ks_staff@t.uz", password="pass-12345", is_staff=True)
        self.url = reverse("backoffice_ai_kill_switch")

    def test_only_the_owner_can_open_it(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)  # anonim
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url).status_code, 302)  # staff ham emas
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_owner_can_stop_ai_and_the_change_is_audited(self):
        from django.contrib.admin.models import LogEntry

        self.client.force_login(self.owner)
        response = self.client.post(self.url, {
            "change_reason": "Kvota kutilmaganda yonib ketdi",
            "confirm_change": "on",
            # checkbox yuborilmasa -> False, ya'ni o'chirish
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(AISettings.load().ai_remote_calls_enabled)

        entry = LogEntry.objects.latest("action_time")
        self.assertIn("O'CHIRILDI", entry.change_message)
        self.assertIn("Kvota kutilmaganda", entry.change_message)

    def test_reason_is_required(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, {"confirm_change": "on"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AISettings.load().ai_remote_calls_enabled, "sababsiz o'zgardi")

    def test_confirmation_is_required(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url, {"change_reason": "shunchaki"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AISettings.load().ai_remote_calls_enabled, "tasdiqsiz o'zgardi")

    def test_no_op_submit_writes_nothing(self):
        from django.contrib.admin.models import LogEntry

        self.client.force_login(self.owner)
        before = LogEntry.objects.count()
        self.client.post(self.url, {
            "ai_remote_calls_enabled": "on",  # allaqachon yoqiq
            "change_reason": "o'zgarish yo'q",
            "confirm_change": "on",
        })
        self.assertEqual(LogEntry.objects.count(), before)


class KillSwitchHealthTests(TestCase):
    def setUp(self):
        AISettings.objects.all().delete()
        self.policy = AISettings.load()

    def _ai_result(self):
        from core.control_center.registry import CAPABILITY_REGISTRY
        from core.control_center.snapshot import PROBE_FUNCTIONS

        definition = next(d for d in CAPABILITY_REGISTRY if d.slug == "ai_provider")
        return PROBE_FUNCTIONS["ai_provider"](definition)

    def test_control_center_reports_the_switch_state(self):
        self.assertIn(("remote_calls_enabled", "True"), self._ai_result().details)

    def test_stopping_ai_shows_as_amber_not_red(self):
        """Ataylab qilingan to'xtatish nosozlik emas — oltin oqim ishlayveradi."""
        self.policy.ai_remote_calls_enabled = False
        self.policy.save(update_fields=["ai_remote_calls_enabled", "updated_at"])

        result = self._ai_result()
        self.assertEqual(result.status, "amber")
        self.assertIn("kill switch", result.summary.lower())

    def test_control_center_links_to_the_kill_switch(self):
        """Sahifa mavjud bo'lishi yetarli emas — shoshilinch paytda topilishi kerak."""
        owner = User.objects.create_superuser(
            username="ks_link_owner", email="ks_link@t.uz", password="pass-12345")
        self.client.force_login(owner)
        response = self.client.get(reverse("backoffice_control"))
        self.assertContains(response, reverse("backoffice_ai_kill_switch"))
