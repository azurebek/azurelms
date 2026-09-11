"""Oldinga qaragan eslatmalar testlari (T2).

Uch qatlam:

1. **Sozlama** — kunlar ro'yxatini o'qish, chegara, jim soatlar oynasi.
2. **Eslatma servisi** — to'lov oynasi sozlamadan olinadimi, o'qituvchi
   navbati scope'ga bo'ysunadimi.
3. **Jim soatlar outbox darajasida** — tunda eslatma DM'i navbatdan
   olinmaydimi. Aynan shu qatlam haqiqiy nosozlikni yopadi: obuna eslatmasi
   kunlik lifecycle ishi bilan **soat 03:05 da** yaratiladi va outbox uni
   o'sha zahoti yuborardi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from courses.models import Assignment, AssignmentSubmission, Course, Lesson, Module
from users.models import Notification, ReminderSettings
from users.reminder_service import pending_review_summary, send_teacher_review_reminders
from users.reminder_settings import (
    ReminderPolicy,
    current_policy,
    parse_days_before,
)

User = get_user_model()


def _aware(year, month, day, hour):
    return timezone.make_aware(datetime.datetime(year, month, day, hour))


# ===================================================== 1) sozlama
class DaysBeforeParsingTests(SimpleTestCase):
    def test_plain_list(self):
        self.assertEqual(parse_days_before("3,1,0"), [3, 1, 0])

    def test_owner_typing_is_forgiven(self):
        """Owner buni admin panelidan yozadi — bo'sh joy va nuqtali vergul."""
        self.assertEqual(parse_days_before(" 3 , 1 ,0 "), [3, 1, 0])
        self.assertEqual(parse_days_before("3;1"), [3, 1])

    def test_broken_input_falls_back_to_the_default(self):
        """Bitta noto'g'ri belgi kunlik eslatma ishini to'xtatib qo'ymasin."""
        self.assertEqual(parse_days_before("salom"), [3, 1, 0])
        self.assertEqual(parse_days_before(""), [3, 1, 0])
        self.assertEqual(parse_days_before(None), [3, 1, 0])

    def test_duplicates_and_out_of_range_are_dropped(self):
        self.assertEqual(parse_days_before("3,3,1,-5,9999"), [3, 1])


class QuietHoursTests(SimpleTestCase):
    def _policy(self, start, end):
        base = ReminderPolicy.defaults()
        return ReminderPolicy(
            payment_days_before=base.payment_days_before,
            teacher_review_after_days=base.teacher_review_after_days,
            quiet_hours_start=start,
            quiet_hours_end=end,
        )

    def test_window_crossing_midnight(self):
        policy = self._policy(22, 8)
        self.assertTrue(policy.is_quiet_at(_aware(2026, 9, 11, 23)))
        self.assertTrue(policy.is_quiet_at(_aware(2026, 9, 11, 3)))
        self.assertTrue(policy.is_quiet_at(_aware(2026, 9, 11, 22)))
        self.assertFalse(policy.is_quiet_at(_aware(2026, 9, 11, 8)))
        self.assertFalse(policy.is_quiet_at(_aware(2026, 9, 11, 12)))

    def test_window_inside_one_day(self):
        policy = self._policy(13, 15)
        self.assertTrue(policy.is_quiet_at(_aware(2026, 9, 11, 14)))
        self.assertFalse(policy.is_quiet_at(_aware(2026, 9, 11, 16)))

    def test_equal_bounds_disable_quiet_hours(self):
        """`22 == 22` ni "butun sutka jim" deb talqin qilish xavfli bo'lardi."""
        policy = self._policy(22, 22)
        self.assertFalse(policy.quiet_hours_enabled)
        self.assertFalse(policy.is_quiet_at(_aware(2026, 9, 11, 23)))


class ReminderSettingsResolutionTests(TestCase):
    def test_no_row_falls_back_to_defaults(self):
        ReminderSettings.objects.all().delete()
        self.assertEqual(current_policy(), ReminderPolicy.defaults())

    def test_out_of_range_is_clamped_on_read(self):
        ReminderSettings.objects.update_or_create(pk=1, defaults={})
        ReminderSettings.objects.filter(pk=1).update(
            teacher_review_after_days=9999, quiet_hours_start=99
        )
        policy = current_policy()
        self.assertEqual(policy.teacher_review_after_days, 60)
        self.assertEqual(policy.quiet_hours_start, 23)


# ===================================================== 2) o'qituvchi navbati
class TeacherReviewReminderTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="t2teacher", email="t2t@azurelms.test", password="pass-12345"
        )
        self.other = User.objects.create_user(
            username="t2other", email="t2o@azurelms.test", password="pass-12345"
        )
        self.student = User.objects.create_user(
            username="t2student", email="t2s@azurelms.test", password="pass-12345"
        )
        self.course = Course.objects.create(title="Turk tili A1", instructor=self.teacher)
        self.other_course = Course.objects.create(title="Boshqa", instructor=self.other)
        ReminderSettings.objects.update_or_create(
            pk=1, defaults={"teacher_review_after_days": 2}
        )

    def _submission(self, course, *, days_old):
        module = Module.objects.create(course=course, title="M1")
        lesson = Lesson.objects.create(module=module, title="L1")
        assignment = Assignment.objects.create(
            lesson=lesson, title="Vazifa", description="matn"
        )
        submission = AssignmentSubmission.objects.create(
            assignment=assignment,
            student=self.student,
            answer_text="javob",
            status=AssignmentSubmission.STATUS_PENDING,
        )
        old = timezone.now() - datetime.timedelta(days=days_old)
        AssignmentSubmission.objects.filter(pk=submission.pk).update(submitted_at=old)
        return submission

    def test_old_pending_submission_produces_one_digest(self):
        self._submission(self.course, days_old=5)
        sent = send_teacher_review_reminders()
        self.assertEqual(sent, 1)
        note = Notification.objects.get(recipient=self.teacher)
        self.assertEqual(note.category, Notification.CATEGORY_REMINDER)
        self.assertIn("1 ta topshiriq", note.message)

    def test_fresh_submission_is_not_reported(self):
        """Bugun topshirilgan ish kechikkan hisoblanmaydi."""
        self._submission(self.course, days_old=0)
        self.assertEqual(send_teacher_review_reminders(), 0)
        self.assertFalse(Notification.objects.exists())

    def test_a_teacher_never_sees_another_teachers_queue(self):
        """Scope canonical funksiyadan — A0b/1 aynan shu nusxalanishda buzilgan edi."""
        self._submission(self.other_course, days_old=5)
        send_teacher_review_reminders()
        self.assertFalse(Notification.objects.filter(recipient=self.teacher).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.other).exists())

    def test_running_twice_the_same_day_sends_one_reminder(self):
        self._submission(self.course, days_old=5)
        send_teacher_review_reminders()
        self.assertEqual(send_teacher_review_reminders(), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.teacher).count(), 1)

    def test_threshold_comes_from_the_settings(self):
        self._submission(self.course, days_old=3)
        ReminderSettings.objects.filter(pk=1).update(teacher_review_after_days=10)
        self.assertEqual(send_teacher_review_reminders(), 0)
        ReminderSettings.objects.filter(pk=1).update(teacher_review_after_days=2)
        self.assertEqual(send_teacher_review_reminders(), 1)

    def test_flag_off_stops_the_reminder(self):
        from core.flags import set_flag

        self._submission(self.course, days_old=5)
        set_flag("reminder_teacher_review", enabled=False, reason="test")
        self.assertEqual(send_teacher_review_reminders(), 0)

    def test_summary_counts_only_pending(self):
        first = self._submission(self.course, days_old=5)
        self._submission(self.course, days_old=5)
        AssignmentSubmission.objects.filter(pk=first.pk).update(
            status=AssignmentSubmission.STATUS_APPROVED
        )
        count, _ = pending_review_summary(self.teacher, older_than_days=2)
        self.assertEqual(count, 1)


class PaymentReminderWindowTests(TestCase):
    """To'lov eslatmasi oynasi sozlamadan olinadimi.

    Ilgari `users/notification_service.py` da `days_left in {3, 1, 0}` bo'lib
    qotib turardi — ya'ni "necha kun oldin eslatamiz" degan mahsulot qarorini
    o'zgartirish uchun deploy kerak bo'lardi.
    """

    def setUp(self):
        from cohorts.models import Cohort, Enrollment
        from subscriptions.models import Plan

        self.today = timezone.localdate()
        self.student = User.objects.create_user(
            username="t2pay", email="t2pay@azurelms.test", password="pass-12345"
        )
        course = Course.objects.create(title="Kurs", instructor=None)
        cohort = Cohort.objects.create(name="G", course=course, start_date=self.today)
        plan = Plan.objects.create(
            code="t2-plan", name="Economic", price=89000, description="d"
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=cohort,
            plan=plan,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=self.today + datetime.timedelta(days=5),
        )

    def _run(self):
        from users.notification_service import ensure_subscription_notifications_for_user

        ensure_subscription_notifications_for_user(self.student)
        return Notification.objects.filter(
            recipient=self.student, category=Notification.CATEGORY_REMINDER
        )

    def test_default_window_does_not_fire_five_days_out(self):
        """Default `3,1,0` — besh kun qolganda eslatma yo'q."""
        ReminderSettings.objects.update_or_create(pk=1, defaults={})
        self.assertEqual(self._run().count(), 0)

    def test_owner_can_widen_the_window(self):
        ReminderSettings.objects.update_or_create(
            pk=1, defaults={"payment_days_before": "5,3,1,0"}
        )
        notes = self._run()
        self.assertEqual(notes.count(), 1)
        self.assertIn("5 kundan so'ng", notes.first().message)

    def test_flag_off_silences_the_reminder(self):
        from core.flags import set_flag

        ReminderSettings.objects.update_or_create(
            pk=1, defaults={"payment_days_before": "5"}
        )
        set_flag("reminder_payment_due", enabled=False, reason="test")
        self.assertEqual(self._run().count(), 0)

    def test_frozen_notice_is_not_a_reminder_and_still_arrives(self):
        """Hodisaga javob beruvchi xabar flagdan qat'i nazar yetib boradi."""
        from cohorts.models import Enrollment
        from core.flags import set_flag

        set_flag("reminder_payment_due", enabled=False, reason="test")
        Enrollment.objects.filter(pk=self.enrollment.pk).update(
            status=Enrollment.STATUS_FROZEN
        )
        self._run()
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student, category=Notification.CATEGORY_SUBSCRIPTION
            ).exists()
        )


# ===================================================== 3) jim soatlar
class QuietHoursOutboxTests(TestCase):
    """Tunda eslatma DM'i navbatdan olinmasligi kerak.

    Haqiqiy holat: obuna eslatmasi kunlik lifecycle ishi bilan soat 03:05 da
    yaratiladi va outbox uni o'sha zahoti yuborardi.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="t2quiet", email="t2q@azurelms.test", password="pass-12345"
        )
        ReminderSettings.objects.update_or_create(
            pk=1, defaults={"quiet_hours_start": 22, "quiet_hours_end": 8}
        )

    def _queue(self, category):
        from bot.models import TelegramOutbox

        note = Notification.objects.create(
            recipient=self.user, title="X", message="y", category=category
        )
        return TelegramOutbox.objects.create(notification=note, telegram_id=4242)

    def test_reminder_is_held_during_quiet_hours(self):
        from bot.outbox import eligible_outbox_ids

        row = self._queue(Notification.CATEGORY_REMINDER)
        night = _aware(2026, 9, 11, 3)
        self.assertNotIn(row.id, eligible_outbox_ids(now=night))

    def test_event_message_is_never_held(self):
        """Chek tasdiqlandi / vazifa baholandi — foydalanuvchi kutmasligi kerak."""
        from bot.outbox import eligible_outbox_ids

        row = self._queue(Notification.CATEGORY_SYSTEM)
        night = _aware(2026, 9, 11, 3)
        self.assertIn(row.id, eligible_outbox_ids(now=night))

    def test_reminder_flows_again_after_quiet_hours(self):
        from bot.outbox import eligible_outbox_ids

        row = self._queue(Notification.CATEGORY_REMINDER)
        morning = _aware(2026, 9, 11, 9)
        self.assertIn(row.id, eligible_outbox_ids(now=morning))

    def test_nothing_is_written_while_holding(self):
        """Qator hech narsa yozilmasdan navbatda qoladi.

        `next_attempt_at` ni surish o'rniga shunday qilingan: owner sozlamani
        o'zgartirsa eskirgan rejalashtirish qolib ketardi.
        """
        from bot.models import TelegramOutbox
        from bot.outbox import eligible_outbox_ids

        row = self._queue(Notification.CATEGORY_REMINDER)
        eligible_outbox_ids(now=_aware(2026, 9, 11, 3))
        row.refresh_from_db()
        self.assertEqual(row.status, TelegramOutbox.STATUS_PENDING)
        self.assertIsNone(row.next_attempt_at)
