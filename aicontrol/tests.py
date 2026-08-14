"""AI token-limit boshqaruvi testlari: limit hal qilish, rolling oyna, enforcement, reset/bonus."""
import datetime
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import (
    AISettings,
    AIPlanPolicy,
    AISupplyEvent,
    AISupplyState,
    AIUserAllowance,
    AIUsageResetEvent,
)
from aicontrol.service import apply_reset_event, get_quota_status, resolve_limits
from cohorts.models import Cohort, Enrollment
from courses.models import Course
from messenger.models import AIResponseRun, ChatRoom, Message
from messenger.signals import suppress_ai_signal
from subscriptions.models import Plan

User = get_user_model()


def _room(user):
    room = ChatRoom.objects.create(room_type="ai", name="t")
    room.participants.add(user)
    return room


def _add_usage(user, room, tokens, *, minutes_ago=1):
    run = AIResponseRun.objects.create(
        room=room, student=user, status=AIResponseRun.STATUS_SUCCEEDED, total_tokens=tokens
    )
    when = timezone.now() - datetime.timedelta(minutes=minutes_ago)
    AIResponseRun.objects.filter(pk=run.pk).update(created_at=when)
    return run


class LimitResolutionTests(TestCase):
    def setUp(self):
        AISettings.objects.all().delete()
        self.settings = AISettings.load()
        self.settings.default_5h_token_limit = 50_000
        self.settings.default_weekly_token_limit = 500_000
        self.settings.save()
        self.user = User.objects.create_user(username="lr", email="lr@t.uz", password="x")

    def test_global_default_when_no_plan_or_override(self):
        self.assertEqual(resolve_limits(self.user), (50_000, 500_000))

    def test_plan_policy_overrides_global(self):
        course = Course.objects.create(title="c", description="d")
        plan = Plan.objects.create(name="Pro", price=100000, description="d")
        cohort = Cohort.objects.create(name="g", course=course, start_date=datetime.date.today())
        Enrollment.objects.create(student=self.user, cohort=cohort, status="active", plan=plan)
        AIPlanPolicy.objects.create(plan=plan, token_limit_5h=200_000, token_limit_weekly=2_000_000)
        self.assertEqual(resolve_limits(self.user), (200_000, 2_000_000))

    def test_user_override_beats_everything(self):
        allowance = AIUserAllowance.objects.create(user=self.user, override_5h_token_limit=9_999)
        self.assertEqual(resolve_limits(self.user, allowance=allowance), (9_999, 500_000))


class QuotaStatusTests(TestCase):
    def setUp(self):
        AISettings.objects.all().delete()
        s = AISettings.load()
        s.default_5h_token_limit = 10_000
        s.default_weekly_token_limit = 40_000
        s.save()
        self.user = User.objects.create_user(username="qs", email="qs@t.uz", password="x")
        self.room = _room(self.user)

    def test_allowed_when_under_limit(self):
        _add_usage(self.user, self.room, 3_000)
        status = get_quota_status(self.user)
        self.assertTrue(status.allowed)
        self.assertEqual(status.used_5h, 3_000)
        self.assertEqual(status.remaining_5h, 7_000)

    def test_blocked_when_5h_exceeded(self):
        _add_usage(self.user, self.room, 6_000)
        _add_usage(self.user, self.room, 5_000)
        status = get_quota_status(self.user)
        self.assertFalse(status.allowed)
        self.assertEqual(status.reason, "5h")

    def test_old_usage_outside_window_not_counted(self):
        _add_usage(self.user, self.room, 9_000, minutes_ago=6 * 60)  # 6 soat oldin — 5h oynadan tashqarida
        status = get_quota_status(self.user)
        self.assertEqual(status.used_5h, 0)
        self.assertTrue(status.allowed)

    def test_weekly_exceeded_blocks_even_if_5h_ok(self):
        for _ in range(9):
            _add_usage(self.user, self.room, 5_000, minutes_ago=60 * 24)  # 1 kun oldin — 5h dan tashqari
        status = get_quota_status(self.user)
        self.assertEqual(status.reason, "weekly")
        self.assertFalse(status.allowed)

    def test_staff_exempt(self):
        staff = User.objects.create_user(username="st", email="st@t.uz", password="x", is_staff=True)
        room = _room(staff)
        _add_usage(staff, room, 999_999)
        self.assertTrue(get_quota_status(staff).allowed)

    def test_enforcement_disabled_never_blocks(self):
        s = AISettings.load()
        s.enforcement_enabled = False
        s.save()
        _add_usage(self.user, self.room, 999_999)
        self.assertTrue(get_quota_status(self.user).allowed)

    def test_blocked_flag(self):
        AIUserAllowance.objects.create(user=self.user, is_blocked=True)
        status = get_quota_status(self.user)
        self.assertFalse(status.allowed)
        self.assertEqual(status.reason, "blocked")

    def test_bonus_extends_limit(self):
        _add_usage(self.user, self.room, 10_000)
        self.assertFalse(get_quota_status(self.user).allowed)
        AIUserAllowance.objects.filter(user=self.user).update(bonus_5h_tokens=5_000)
        status = get_quota_status(self.user)
        self.assertTrue(status.allowed)
        self.assertEqual(status.limit_5h, 15_000)


class ResetEventTests(TestCase):
    def setUp(self):
        AISettings.objects.all().delete()
        s = AISettings.load()
        s.default_5h_token_limit = 10_000
        s.default_weekly_token_limit = 40_000
        s.save()
        self.course = Course.objects.create(title="c", description="d")
        self.cohort = Cohort.objects.create(name="g", course=self.course, start_date=datetime.date.today())
        self.plan = Plan.objects.create(name="Pro", price=100000, description="d")
        self.user = User.objects.create_user(username="re", email="re@t.uz", password="x", telegram_id=123456789)
        Enrollment.objects.create(student=self.user, cohort=self.cohort, status="active", plan=self.plan)
        self.room = _room(self.user)

    def test_mass_reset_forgives_usage(self):
        _add_usage(self.user, self.room, 10_000)
        self.assertFalse(get_quota_status(self.user).allowed)

        event = AIUsageResetEvent.objects.create(
            scope=AIUsageResetEvent.SCOPE_ALL,
            kind=AIUsageResetEvent.KIND_RESET,
            window=AIUsageResetEvent.WINDOW_BOTH,
            reason="Navro'z",
        )
        count = apply_reset_event(event)
        self.assertGreaterEqual(count, 1)
        self.assertTrue(get_quota_status(self.user).allowed)

        # Notification va TelegramOutbox to'g'ri yaratilganligini tekshiramiz
        from users.models import Notification
        from bot.models import TelegramOutbox
        
        notification = Notification.objects.filter(
            recipient=self.user,
            external_key=f"ai-limit-event-{event.id}-{self.user.id}"
        ).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, "AI limitlari yangilandi")
        self.assertIn("Navro'z", notification.message)
        
        outbox = TelegramOutbox.objects.filter(notification=notification).first()
        self.assertIsNotNone(outbox)

    def test_cohort_scope_targets_only_members(self):
        other = User.objects.create_user(username="re2", email="re2@t.uz", password="x")
        other_room = _room(other)
        _add_usage(self.user, self.room, 10_000)
        _add_usage(other, other_room, 10_000)

        event = AIUsageResetEvent.objects.create(
            scope=AIUsageResetEvent.SCOPE_COHORT, cohort=self.cohort,
            kind=AIUsageResetEvent.KIND_RESET, window=AIUsageResetEvent.WINDOW_BOTH,
        )
        apply_reset_event(event)
        self.assertTrue(get_quota_status(self.user).allowed)   # kohort a'zosi — reset qilindi
        self.assertFalse(get_quota_status(other).allowed)      # kohortda emas — tegilmadi

    def test_plan_scope_bonus(self):
        _add_usage(self.user, self.room, 10_000)
        event = AIUsageResetEvent.objects.create(
            scope=AIUsageResetEvent.SCOPE_PLAN, plan=self.plan,
            kind=AIUsageResetEvent.KIND_BONUS, window=AIUsageResetEvent.WINDOW_5H,
            bonus_tokens=5_000,
            reason="A'lo natija",
        )
        apply_reset_event(event)
        allowance = AIUserAllowance.objects.get(user=self.user)
        self.assertEqual(allowance.bonus_5h_tokens, 5_000)
        self.assertTrue(get_quota_status(self.user).allowed)

        # Bonus notification tekshiruvi
        from users.models import Notification
        from bot.models import TelegramOutbox

        notification = Notification.objects.filter(
            recipient=self.user,
            external_key=f"ai-limit-event-{event.id}-{self.user.id}"
        ).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.title, "AI bonus tokenlari taqdim etildi")
        self.assertIn("A'lo natija", notification.message)
        self.assertIn("5,000", notification.message)

        outbox = TelegramOutbox.objects.filter(notification=notification).first()
        self.assertIsNotNone(outbox)


class EnforcementInTaskTests(TestCase):
    def setUp(self):
        AISettings.objects.all().delete()
        s = AISettings.load()
        s.default_5h_token_limit = 5_000
        s.default_weekly_token_limit = 40_000
        s.save()
        self.user = User.objects.create_user(username="ef", email="ef@t.uz", password="x")
        self.room = _room(self.user)

    def test_over_limit_blocks_engine_and_posts_notice(self):
        from messenger.models import Message

        _add_usage(self.user, self.room, 6_000)  # 5h limitdan oshdi
        with patch("messenger.tasks.AIEngine") as engine_cls:
            from messenger.tasks import generate_ai_response

            generate_ai_response.run(room_id=self.room.id, student_id=self.user.id, user_question="salom")
            engine_cls.return_value.generate_reply.assert_not_called()

        block = Message.objects.filter(room=self.room, is_ai_response=True).latest("created_at")
        self.assertIn("limit", block.text.lower())
        self.assertTrue(AIResponseRun.objects.filter(room=self.room, skill_slug="quota_block").exists())

    def test_under_limit_allows_engine_and_records_tokens(self):
        from ai.agent.types import AIResponse

        _add_usage(self.user, self.room, 1_000)
        fake = AIResponse(
            text="javob", model_name="llama-4-maverick", skill_slug="general_chat",
            metadata={"usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}},
        )
        with patch("messenger.tasks.AIEngine") as engine_cls:
            engine_cls.return_value.generate_reply.return_value = fake
            from messenger.tasks import generate_ai_response

            generate_ai_response.run(room_id=self.room.id, student_id=self.user.id, user_question="salom")
            engine_cls.return_value.generate_reply.assert_called_once()

        run = AIResponseRun.objects.filter(room=self.room).exclude(skill_slug="quota_block").latest("created_at")
        self.assertEqual(run.total_tokens, 30)


class TokenNormalizationTests(TestCase):
    def test_do_usage_normalization(self):
        from ai.providers.digitalocean import _normalize_usage

        self.assertEqual(
            _normalize_usage({"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}),
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
        self.assertEqual(_normalize_usage({"prompt_tokens": 3, "completion_tokens": 4})["total_tokens"], 7)
        self.assertIsNone(_normalize_usage(None))
        self.assertIsNone(_normalize_usage({}))


class UsagePanelTests(TestCase):
    def setUp(self):
        AISettings.objects.all().delete()
        s = AISettings.load()
        s.default_5h_token_limit = 10_000
        s.default_weekly_token_limit = 40_000
        s.save()
        self.user = User.objects.create_user(username="up", email="up@t.uz", password="x")
        self.room = _room(self.user)

    def test_panel_percentages_and_shape(self):
        from aicontrol.service import build_usage_panel

        _add_usage(self.user, self.room, 2_500)  # 25% of 5h
        panel = build_usage_panel(self.user)
        self.assertFalse(panel["unlimited"])
        self.assertEqual(panel["session"]["percent"], 25)
        self.assertEqual(panel["session"]["used"], 2_500)
        self.assertEqual(panel["session"]["limit"], 10_000)

    def test_panel_unlimited_for_staff(self):
        from aicontrol.service import build_usage_panel

        staff = User.objects.create_user(username="ups", email="ups@t.uz", password="x", is_staff=True)
        self.assertTrue(build_usage_panel(staff)["unlimited"])

    def test_settings_page_shows_usage_panel(self):
        _add_usage(self.user, self.room, 3_000)
        self.client.force_login(self.user)
        response = self.client.get(reverse("settings_billing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI foydalanish limiti")
        self.assertContains(response, "Joriy sessiya")


class GlobalSupplyBudgetTests(TestCase):
    class FakeProvider:
        last_attempt_count = 1
        last_error_kind = None

        def __init__(self, *, error=None):
            self.error = error
            self.calls = 0

        def generate(self, **kwargs):
            from ai.agent.types import ProviderResponse

            self.calls += 1
            if self.error:
                self.last_error_kind = "quota"
                raise self.error
            return ProviderResponse(
                text="javob",
                model_name="gemini-2.5-flash-lite",
                usage={"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
            )

    def setUp(self):
        AISettings.objects.all().delete()
        AISupplyState.objects.all().delete()
        AISupplyEvent.objects.all().delete()
        self.policy = AISettings.load()
        self.policy.supply_daily_request_limit = 3
        self.policy.supply_daily_token_limit = 10_000
        self.policy.supply_cooldown_seconds = 60
        self.policy.save()

    def test_success_is_reserved_before_call_and_reconciled_to_actual_usage(self):
        from aicontrol.supply import execute_provider_call, supply_snapshot

        provider = self.FakeProvider()
        response = execute_provider_call(
            provider,
            request_key="chat:one",
            call_type=AISupplyEvent.CALL_CHAT,
            prompt="salom",
            max_requests=2,
        )

        self.assertEqual(response.text, "javob")
        event = AISupplyEvent.objects.get(request_key="chat:one")
        self.assertEqual(event.status, AISupplyEvent.STATUS_SUCCEEDED)
        self.assertEqual(event.reserved_requests, 2)
        self.assertEqual(event.actual_requests, 1)
        self.assertEqual(event.accounted_requests, 1)
        self.assertEqual(event.accounted_tokens, 18)
        self.assertEqual(supply_snapshot()["requests_used"], 1)

    def test_duplicate_key_never_executes_provider_twice(self):
        from aicontrol.supply import SupplyDuplicate, execute_provider_call

        provider = self.FakeProvider()
        kwargs = {
            "request_key": "chat:duplicate",
            "call_type": AISupplyEvent.CALL_CHAT,
            "prompt": "salom",
            "max_requests": 1,
        }
        execute_provider_call(provider, **kwargs)
        with self.assertRaises(SupplyDuplicate):
            execute_provider_call(provider, **kwargs)
        self.assertEqual(provider.calls, 1)

    def test_global_cap_includes_staff_and_denies_before_network(self):
        from aicontrol.supply import SupplyDenied, execute_provider_call

        self.policy.supply_daily_request_limit = 1
        self.policy.save(update_fields=["supply_daily_request_limit", "updated_at"])
        staff = User.objects.create_user(username="supply-staff", is_staff=True)
        first = self.FakeProvider()
        execute_provider_call(
            first,
            request_key="staff:first",
            call_type=AISupplyEvent.CALL_CHAT,
            prompt="bir",
            user=staff,
            max_requests=1,
        )
        second = self.FakeProvider()
        with self.assertRaises(SupplyDenied):
            execute_provider_call(
                second,
                request_key="staff:second",
                call_type=AISupplyEvent.CALL_CHAT,
                prompt="ikki",
                user=staff,
                max_requests=1,
            )
        self.assertEqual(second.calls, 0)
        self.assertEqual(
            AISupplyEvent.objects.get(request_key="staff:second").error_kind,
            "daily_request_limit",
        )

    def test_minute_burst_cap_denies_before_network(self):
        from aicontrol.supply import SupplyDenied, execute_provider_call

        self.policy.supply_minute_request_limit = 1
        self.policy.save(update_fields=["supply_minute_request_limit", "updated_at"])
        execute_provider_call(
            self.FakeProvider(),
            request_key="minute:first",
            call_type=AISupplyEvent.CALL_CHAT,
            prompt="bir",
            max_requests=1,
        )
        second = self.FakeProvider()
        with self.assertRaises(SupplyDenied):
            execute_provider_call(
                second,
                request_key="minute:second",
                call_type=AISupplyEvent.CALL_CHAT,
                prompt="ikki",
                max_requests=1,
            )
        self.assertEqual(second.calls, 0)
        self.assertEqual(
            AISupplyEvent.objects.get(request_key="minute:second").error_kind,
            "minute_request_limit",
        )

    def test_quota_failure_opens_circuit_and_next_call_is_local_rejection(self):
        from aicontrol.supply import SupplyDenied, execute_provider_call

        quota_provider = self.FakeProvider(error=RuntimeError("429 RESOURCE_EXHAUSTED quota"))
        with self.assertRaises(RuntimeError):
            execute_provider_call(
                quota_provider,
                request_key="quota:first",
                call_type=AISupplyEvent.CALL_CHAT,
                prompt="bir",
                max_requests=2,
            )
        state = AISupplyState.load()
        self.assertGreater(state.circuit_open_until, timezone.now())

        next_provider = self.FakeProvider()
        with self.assertRaises(SupplyDenied):
            execute_provider_call(
                next_provider,
                request_key="quota:next",
                call_type=AISupplyEvent.CALL_CHAT,
                prompt="ikki",
                max_requests=1,
            )
        self.assertEqual(next_provider.calls, 0)

    def test_previously_reserved_call_rechecks_circuit_before_network(self):
        from aicontrol.supply import (
            SupplyDenied,
            execute_reserved_provider_call,
            reserve_supply,
        )

        reservation = reserve_supply(
            request_key="reserved:before-circuit",
            call_type=AISupplyEvent.CALL_CHAT,
            reserved_requests=1,
            reserved_tokens=20,
        )
        state = AISupplyState.load()
        state.circuit_open_until = timezone.now() + datetime.timedelta(minutes=5)
        state.circuit_reason = "quota"
        state.save()
        provider = self.FakeProvider()

        with self.assertRaises(SupplyDenied):
            execute_reserved_provider_call(
                reservation,
                provider,
                prompt="remote'ga chiqmasin",
            )

        provider_calls = provider.calls
        self.assertEqual(provider_calls, 0)
        event = AISupplyEvent.objects.get(pk=reservation.event_id)
        self.assertEqual(event.status, AISupplyEvent.STATUS_FAILED)
        self.assertEqual(event.actual_requests, 0)
        self.assertEqual(event.accounted_requests, 0)

    def test_ledger_database_failure_is_fail_closed(self):
        from aicontrol.supply import SupplyUnavailable, reserve_supply

        with patch("aicontrol.supply.AISettings.load", side_effect=DatabaseError("offline")):
            with self.assertRaises(SupplyUnavailable):
                reserve_supply(
                    request_key="db:down",
                    call_type=AISupplyEvent.CALL_CHAT,
                    reserved_requests=1,
                    reserved_tokens=10,
                )


class AIResponseTaskIdempotencyTests(TestCase):
    def setUp(self):
        AISettings.objects.all().delete()
        self.user = User.objects.create_user(username="idem", password="x")
        self.room = _room(self.user)

    def test_same_client_request_runs_engine_once_and_reuses_result(self):
        from ai.agent.types import AIResponse
        from messenger.tasks import generate_ai_response

        fake_response = AIResponse(
            text="bir marta",
            model_name="gemini-2.5-flash-lite",
            skill_slug="general_chat",
            metadata={"usage": {"total_tokens": 12}},
        )
        with patch("messenger.tasks.AIEngine") as engine_cls:
            engine_cls.return_value.generate_reply.return_value = fake_response
            first = generate_ai_response.run(
                room_id=self.room.id,
                student_id=self.user.id,
                user_question="salom",
                client_message_id="client-123",
            )
            second = generate_ai_response.run(
                room_id=self.room.id,
                student_id=self.user.id,
                user_question="salom",
                client_message_id="client-123",
            )

        self.assertEqual(first, second)
        engine_cls.return_value.generate_reply.assert_called_once()
        self.assertEqual(AIResponseRun.objects.filter(room=self.room).count(), 1)
        self.assertEqual(
            AISupplyEvent.objects.filter(call_type=AISupplyEvent.CALL_CHAT).count(),
            1,
        )

    def test_same_client_id_wins_over_distinct_resend_message_rows(self):
        from ai.agent.types import AIResponse
        from messenger.tasks import generate_ai_response

        with suppress_ai_signal():
            first_message = Message.objects.create(
                room=self.room,
                sender=self.user,
                text="salom",
            )
            resent_message = Message.objects.create(
                room=self.room,
                sender=self.user,
                text="salom",
            )
        fake_response = AIResponse(
            text="bir marta",
            model_name="gemini-3.1-flash-lite",
            skill_slug="general_chat",
            metadata={"usage": {"total_tokens": 12}},
        )

        with patch("messenger.tasks.AIEngine") as engine_cls:
            engine_cls.return_value.generate_reply.return_value = fake_response
            first = generate_ai_response.run(
                room_id=self.room.id,
                student_id=self.user.id,
                user_question="salom",
                user_message_id=first_message.id,
                client_message_id="stable-client-123",
            )
            second = generate_ai_response.run(
                room_id=self.room.id,
                student_id=self.user.id,
                user_question="salom",
                user_message_id=resent_message.id,
                client_message_id="stable-client-123",
            )

        self.assertEqual(first, second)
        engine_cls.return_value.generate_reply.assert_called_once()
        run = AIResponseRun.objects.get(room=self.room)
        self.assertEqual(run.user_message_id, first_message.id)
        self.assertEqual(run.idempotency_key, f"chat:{self.room.id}:{self.user.id}:client:stable-client-123")
        self.assertEqual(AISupplyEvent.objects.filter(call_type=AISupplyEvent.CALL_CHAT).count(), 1)

    def test_intentional_retry_with_fresh_server_key_runs_again(self):
        from ai.agent.types import AIResponse
        from messenger.tasks import generate_ai_response

        with suppress_ai_signal():
            user_message = Message.objects.create(
                room=self.room,
                sender=self.user,
                text="salom",
            )
        fake_response = AIResponse(
            text="javob",
            model_name="gemini-3.1-flash-lite",
            skill_slug="general_chat",
            metadata={"usage": {"total_tokens": 12}},
        )

        with patch("messenger.tasks.AIEngine") as engine_cls:
            engine_cls.return_value.generate_reply.return_value = fake_response
            first = generate_ai_response.run(
                room_id=self.room.id,
                student_id=self.user.id,
                user_question="salom",
                user_message_id=user_message.id,
                client_message_id="stable-client-123",
            )
            retried = generate_ai_response.run(
                room_id=self.room.id,
                student_id=self.user.id,
                user_question="salom",
                user_message_id=user_message.id,
                client_message_id=f"retry:{user_message.id}:fresh-server-nonce",
            )

        self.assertNotEqual(first, retried)
        self.assertEqual(engine_cls.return_value.generate_reply.call_count, 2)
        self.assertEqual(AIResponseRun.objects.filter(room=self.room).count(), 2)
        self.assertEqual(AISupplyEvent.objects.filter(call_type=AISupplyEvent.CALL_CHAT).count(), 2)

    def test_engine_constructor_failure_releases_main_reservation_without_network_charge(self):
        from messenger.tasks import generate_ai_response

        with patch("messenger.tasks.AIEngine", side_effect=RuntimeError("constructor down")):
            result = generate_ai_response.run(
                room_id=self.room.id,
                student_id=self.user.id,
                user_question="salom",
                client_message_id="constructor-failure",
            )

        self.assertIsNone(result)
        run = AIResponseRun.objects.get(room=self.room)
        self.assertEqual(run.status, AIResponseRun.STATUS_FAILED)
        event = AISupplyEvent.objects.get(call_type=AISupplyEvent.CALL_CHAT)
        self.assertEqual(event.status, AISupplyEvent.STATUS_FAILED)
        self.assertEqual(event.actual_requests, 0)
        self.assertEqual(event.accounted_requests, 0)
        self.assertEqual(event.accounted_tokens, 0)
        self.assertEqual(event.error_kind, "pre_engine_error")


class AISupplyAdminTests(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/admin/")
        self.request.user = User.objects.create_superuser(
            username="supply-admin",
            email="supply-admin@example.test",
            password="x",
        )

    def test_supply_policy_controls_are_visible_on_ai_settings(self):
        model_admin = admin.site._registry[AISettings]
        fields = {
            field
            for _title, options in model_admin.fieldsets
            for field in options["fields"]
        }

        self.assertTrue(
            {
                "supply_enforcement_enabled",
                "supply_daily_request_limit",
                "supply_minute_request_limit",
                "supply_daily_token_limit",
                "supply_default_reservation_tokens",
                "supply_cooldown_seconds",
                "guest_demo_enabled",
                "heavy_search_enabled",
            }.issubset(fields)
        )

    def test_supply_event_admin_is_read_only_and_hides_raw_error(self):
        model_admin = admin.site._registry[AISupplyEvent]

        self.assertFalse(model_admin.has_add_permission(self.request))
        self.assertFalse(model_admin.has_change_permission(self.request))
        self.assertFalse(model_admin.has_delete_permission(self.request))
        self.assertNotIn("error_message", model_admin.fields)
        self.assertNotIn("metadata", model_admin.fields)

    def test_supply_state_admin_is_read_only_and_hides_raw_circuit_reason(self):
        model_admin = admin.site._registry[AISupplyState]

        self.assertFalse(model_admin.has_add_permission(self.request))
        self.assertFalse(model_admin.has_change_permission(self.request))
        self.assertFalse(model_admin.has_delete_permission(self.request))
        self.assertIn("circuit_status", model_admin.fields)
        self.assertIn("circuit_open_until", model_admin.fields)
        self.assertNotIn("circuit_reason", model_admin.fields)
