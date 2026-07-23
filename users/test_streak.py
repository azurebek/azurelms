import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from users.models import LearnerStreak
from users.streak import grant_freeze, record_activity, streak_snapshot


User = get_user_model()
DAY = datetime.timedelta(days=1)


class StreakServiceTests(TestCase):
    """Kun asosidagi seriya mantig'i — barcha o'tish holatlari."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="streaker", email="streaker@example.test", password="x"
        )
        self.d0 = datetime.date(2026, 3, 10)

    def _streak(self):
        return LearnerStreak.objects.get(user=self.user)

    # --- asosiy oqim ----------------------------------------------------

    def test_first_activity_starts_at_one(self):
        event = record_activity(self.user, on_date=self.d0)
        self.assertEqual(event.outcome, "started")
        self.assertEqual(event.current_streak, 1)
        self.assertEqual(self._streak().longest_streak, 1)

    def test_consecutive_days_extend(self):
        record_activity(self.user, on_date=self.d0)
        event = record_activity(self.user, on_date=self.d0 + DAY)
        self.assertEqual(event.outcome, "extended")
        self.assertEqual(event.current_streak, 2)
        event = record_activity(self.user, on_date=self.d0 + 2 * DAY)
        self.assertEqual(event.current_streak, 3)

    def test_multiple_activities_same_day_count_once(self):
        record_activity(self.user, on_date=self.d0)
        again = record_activity(self.user, on_date=self.d0)
        self.assertEqual(again.outcome, "already")
        self.assertEqual(again.current_streak, 1)
        self.assertEqual(self._streak().total_active_days, 1)

    def test_gap_resets_to_one(self):
        record_activity(self.user, on_date=self.d0)
        record_activity(self.user, on_date=self.d0 + DAY)  # streak 2
        event = record_activity(self.user, on_date=self.d0 + 4 * DAY)  # 2 kun tashlab
        self.assertEqual(event.outcome, "reset")
        self.assertEqual(event.current_streak, 1)

    def test_longest_is_preserved_after_reset(self):
        for i in range(5):
            record_activity(self.user, on_date=self.d0 + i * DAY)  # streak 5
        self.assertEqual(self._streak().longest_streak, 5)
        record_activity(self.user, on_date=self.d0 + 10 * DAY)  # reset
        streak = self._streak()
        self.assertEqual(streak.current_streak, 1)
        self.assertEqual(streak.longest_streak, 5)

    def test_new_record_flag(self):
        e1 = record_activity(self.user, on_date=self.d0)
        self.assertFalse(e1.is_new_record)  # 1 kun rekord emas
        e2 = record_activity(self.user, on_date=self.d0 + DAY)
        self.assertTrue(e2.is_new_record)  # 2 > oldingi longest 1

    def test_retroactive_activity_is_ignored(self):
        record_activity(self.user, on_date=self.d0 + 3 * DAY)
        event = record_activity(self.user, on_date=self.d0)  # o'tmish
        self.assertEqual(event.outcome, "ignored")
        self.assertEqual(self._streak().current_streak, 1)

    # --- freeze ---------------------------------------------------------

    def test_freeze_covers_a_single_missed_day(self):
        grant_freeze(self.user, 1)
        record_activity(self.user, on_date=self.d0)  # streak 1
        event = record_activity(self.user, on_date=self.d0 + 2 * DAY)  # 1 kun tashlab
        self.assertEqual(event.outcome, "maintained_with_freeze")
        self.assertEqual(event.current_streak, 2)
        self.assertEqual(event.freezes_used, 1)
        self.assertEqual(self._streak().freezes_available, 0)
        self.assertEqual(self._streak().freezes_used_total, 1)

    def test_freeze_insufficient_for_two_missed_days(self):
        grant_freeze(self.user, 1)
        record_activity(self.user, on_date=self.d0)
        event = record_activity(self.user, on_date=self.d0 + 3 * DAY)  # 2 kun tashlab
        self.assertEqual(event.outcome, "reset")
        self.assertEqual(event.current_streak, 1)
        self.assertEqual(self._streak().freezes_available, 1)  # sarflanmadi

    # --- effective_current (ko'rsatish) --------------------------------

    def test_effective_current_zero_when_broken(self):
        record_activity(self.user, on_date=self.d0)
        streak = self._streak()
        # 3 kun o'tdi, freeze yo'q → jonli qiymat 0
        self.assertEqual(streak.effective_current(today=self.d0 + 3 * DAY), 0)

    def test_effective_current_holds_yesterday(self):
        record_activity(self.user, on_date=self.d0)
        streak = self._streak()
        # kecha faol edi, bugun hali yo'q — hali buzilmagan
        self.assertEqual(streak.effective_current(today=self.d0 + DAY), 1)
        self.assertTrue(streak.at_risk(today=self.d0 + DAY))

    def test_effective_current_holds_within_freeze_window(self):
        grant_freeze(self.user, 1)
        record_activity(self.user, on_date=self.d0)
        streak = self._streak()
        # 2 kun o'tdi (1 kun o'tkazildi), freeze bor → hali ushlanadi
        self.assertEqual(streak.effective_current(today=self.d0 + 2 * DAY), 1)

    def test_streak_days_property_uses_effective_value(self):
        record_activity(self.user, on_date=self.d0)
        self.user.refresh_from_db()
        # property bugungi sanani ishlatadi — o'tmishdagi d0 dan ko'p o'tган,
        # shuning uchun buzilgan holatда 0 qaytaradi.
        self.assertEqual(self.user.streak_days, 0)

    # --- snapshot -------------------------------------------------------

    def test_snapshot_for_user_without_streak(self):
        snap = streak_snapshot(self.user, today=self.d0)
        self.assertEqual(snap["current"], 0)
        self.assertFalse(snap["active_today"])

    def test_snapshot_active_today(self):
        record_activity(self.user, on_date=self.d0)
        snap = streak_snapshot(self.user, today=self.d0)
        self.assertEqual(snap["current"], 1)
        self.assertTrue(snap["active_today"])
        self.assertFalse(snap["at_risk"])


class StreakPropertyEdgeTests(TestCase):
    """streak_days property streak obyekti yo'q userda ham xato bermaydi."""

    def test_property_without_streak_object_returns_zero(self):
        user = User.objects.create_user(
            username="no-streak", email="no-streak@example.test", password="x"
        )
        self.assertEqual(user.streak_days, 0)  # DoesNotExist ushlanadi
