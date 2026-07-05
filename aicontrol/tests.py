"""AI token-limit boshqaruvi testlari: limit hal qilish, rolling oyna, enforcement, reset/bonus."""
import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from aicontrol.models import AISettings, AIPlanPolicy, AIUserAllowance, AIUsageResetEvent
from aicontrol.service import apply_reset_event, get_quota_status, resolve_limits
from cohorts.models import Cohort, Enrollment
from courses.models import Course
from messenger.models import AIResponseRun, ChatRoom
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
        self.user = User.objects.create_user(username="re", email="re@t.uz", password="x")
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
        )
        apply_reset_event(event)
        allowance = AIUserAllowance.objects.get(user=self.user)
        self.assertEqual(allowance.bonus_5h_tokens, 5_000)
        self.assertTrue(get_quota_status(self.user).allowed)


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
