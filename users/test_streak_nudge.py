import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from users.models import LearnerStreak, Notification
from users.streak_messages import (
    AT_RISK_BY_TIME,
    STATE_ABSENT,
    STATE_AT_RISK,
    STATE_BROKEN,
    pick_message,
    time_bucket,
)
from users.streak_nudge import classify, send_streak_nudges


User = get_user_model()


class TimeBucketTests(TestCase):
    def _at(self, hour):
        return datetime.datetime(2026, 3, 10, hour, 0)

    def test_buckets(self):
        self.assertEqual(time_bucket(self._at(7)), "morning")
        self.assertEqual(time_bucket(self._at(13)), "midday")
        self.assertEqual(time_bucket(self._at(19)), "evening")
        self.assertEqual(time_bucket(self._at(23)), "night")
        self.assertEqual(time_bucket(self._at(2)), "night")

    def test_pick_message_matches_time_and_state(self):
        now = self._at(20)  # evening
        msg = pick_message(STATE_AT_RISK, now)
        self.assertIn(msg, AT_RISK_BY_TIME["evening"])


class ClassifyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="c", email="c@example.test", password="x"
        )
        self.today = datetime.date(2026, 3, 20)

    def _streak(self, **kw):
        defaults = dict(user=self.user, current_streak=5, last_activity_date=self.today)
        defaults.update(kw)
        return LearnerStreak.objects.create(**defaults)

    def test_active_today_is_not_nudged(self):
        streak = self._streak(last_activity_date=self.today)
        self.assertIsNone(classify(streak, self.today))

    def test_at_risk_when_active_yesterday(self):
        streak = self._streak(last_activity_date=self.today - datetime.timedelta(days=1))
        self.assertEqual(classify(streak, self.today), STATE_AT_RISK)

    def test_broken_recently(self):
        streak = self._streak(last_activity_date=self.today - datetime.timedelta(days=2))
        self.assertEqual(classify(streak, self.today), STATE_BROKEN)

    def test_absent_after_broken_window(self):
        streak = self._streak(last_activity_date=self.today - datetime.timedelta(days=7))
        self.assertEqual(classify(streak, self.today), STATE_ABSENT)

    def test_long_gone_is_not_nudged(self):
        streak = self._streak(last_activity_date=self.today - datetime.timedelta(days=40))
        self.assertIsNone(classify(streak, self.today))

    def test_never_built_a_streak_is_not_nudged_when_broken(self):
        streak = self._streak(
            current_streak=0, last_activity_date=self.today - datetime.timedelta(days=5)
        )
        self.assertIsNone(classify(streak, self.today))


class SendNudgeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="n", email="n@example.test", password="x"
        )

    def _make_streak(self, days_ago, current=5):
        return LearnerStreak.objects.create(
            user=self.user,
            current_streak=current,
            last_activity_date=timezone.localdate() - datetime.timedelta(days=days_ago),
        )

    def test_at_risk_user_gets_one_notification(self):
        self._make_streak(days_ago=1)
        sent = send_streak_nudges()
        self.assertEqual(sent, 1)
        notif = Notification.objects.get(recipient=self.user)
        self.assertEqual(notif.category, Notification.CATEGORY_STREAK)
        self.assertTrue(notif.external_key.startswith("streak-nudge-"))

    def test_idempotent_same_day(self):
        self._make_streak(days_ago=1)
        send_streak_nudges()
        send_streak_nudges()  # ikkinchi run
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 1)

    def test_active_today_gets_no_nudge(self):
        self._make_streak(days_ago=0)
        self.assertEqual(send_streak_nudges(), 0)
        self.assertFalse(Notification.objects.filter(recipient=self.user).exists())

    def test_inactive_user_is_skipped(self):
        self._make_streak(days_ago=1)
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertEqual(send_streak_nudges(), 0)


class NudgeReplacedByActivityTests(TestCase):
    """Event-bound: nudge yuborilgach o'quvchi harakat qilsa, O'SHA
    bildirishnoma tabrikka aylanadi — yangisi qo'shilmaydi."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="r", email="r@example.test", password="x"
        )

    def test_activity_today_turns_nudge_into_congrats(self):
        from users.streak import record_activity

        # Kecha faol edi, bugun hali yo'q → at_risk nudge
        LearnerStreak.objects.create(
            user=self.user,
            current_streak=3,
            last_activity_date=timezone.localdate() - datetime.timedelta(days=1),
        )
        send_streak_nudges()
        nudge = Notification.objects.get(recipient=self.user)
        self.assertEqual(nudge.title, "🔥 Seriyangiz kutmoqda")
        self.assertFalse(nudge.is_read)

        # Endi bugun malakali harakat — on_commit callback ishlaydi
        with self.captureOnCommitCallbacks(execute=True):
            record_activity(self.user)

        # Bitta bildirishnoma qoladi, lekin endi tabrik
        notifs = Notification.objects.filter(recipient=self.user)
        self.assertEqual(notifs.count(), 1)
        self.assertEqual(notifs.first().title, "🔥 Seriya saqlandi")

    def test_activity_without_prior_nudge_creates_congrats(self):
        from users.streak import record_activity

        with self.captureOnCommitCallbacks(execute=True):
            record_activity(self.user)

        notif = Notification.objects.get(recipient=self.user)
        self.assertEqual(notif.category, Notification.CATEGORY_STREAK)
        self.assertEqual(notif.title, "🔥 Seriya saqlandi")


class NudgeBubblesToTopTests(TestCase):
    """Holat o'zgarganda seriya bildirishnomasi ro'yxat tepasiga chiqadi."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="b", email="b@example.test", password="x"
        )

    def test_streak_notification_resurfaces_on_state_change(self):
        from users.streak import record_activity

        # at_risk nudge
        LearnerStreak.objects.create(
            user=self.user,
            current_streak=3,
            last_activity_date=timezone.localdate() - datetime.timedelta(days=1),
        )
        send_streak_nudges()

        # Keyin yangiroq, aloqasiz bildirishnoma keladi
        Notification.objects.create(
            recipient=self.user, message="Boshqa xabar", external_key=None
        )
        # Ayrim OS/database kombinatsiyalarida ketma-ket yozuvlar bir xil
        # timestamp tick'iga tushadi. Eng yangi PK deterministic tie-breaker.
        tied_at = timezone.now()
        Notification.objects.filter(recipient=self.user).update(created_at=tied_at)
        top_before = Notification.objects.filter(recipient=self.user).first()
        self.assertEqual(top_before.message, "Boshqa xabar")  # streak pastda

        # Malakali harakat → streak bildirishnomasi yangilanadi va tepaga chiqadi
        with self.captureOnCommitCallbacks(execute=True):
            record_activity(self.user)

        top_after = Notification.objects.filter(recipient=self.user).first()
        self.assertEqual(top_after.category, Notification.CATEGORY_STREAK)
        self.assertEqual(top_after.title, "🔥 Seriya saqlandi")
