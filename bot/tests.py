import base64
import datetime

from django.contrib.auth import get_user_model
from django.core.signing import Signer
from django.test import TestCase
from django.utils import timezone

from bot.models import TelegramLessonCheckIn, TelegramLessonSession
from bot.services import (
    bind_chat_to_cohort,
    close_lesson_session,
    link_user_from_start_token,
    register_checkin,
    start_lesson_session,
)
from cohorts.models import Attendance, Cohort, Enrollment
from courses.models import Course, Lesson, Module
from users.models import Notification


User = get_user_model()


class TelegramBotFlowTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="tg-teacher",
            email="tg-teacher@example.com",
            password="testpass123",
            is_staff=True,
            telegram_id=1001,
        )
        self.student_present = User.objects.create_user(
            username="tg-present",
            email="tg-present@example.com",
            password="testpass123",
            telegram_id=2001,
        )
        self.student_partial = User.objects.create_user(
            username="tg-partial",
            email="tg-partial@example.com",
            password="testpass123",
            telegram_id=2002,
        )
        self.student_absent = User.objects.create_user(
            username="tg-absent",
            email="tg-absent@example.com",
            password="testpass123",
            telegram_id=2003,
        )
        self.unlinked_user = User.objects.create_user(
            username="tg-unlinked",
            email="tg-unlinked@example.com",
            password="testpass123",
        )

        self.course = Course.objects.create(
            title="Telegram Attendance Course",
            description="Course for telegram attendance tests",
            instructor=self.teacher,
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="Modul 1", order=1)
        self.lesson_1 = Lesson.objects.create(module=self.module, title="Dars 1", order=1, xp_reward=10)
        self.lesson_2 = Lesson.objects.create(module=self.module, title="Dars 2", order=2, xp_reward=10)
        self.cohort = Cohort.objects.create(
            name="Telegram Cohort",
            course=self.course,
            start_date="2026-03-26",
            is_active=True,
        )
        self.present_enrollment = Enrollment.objects.create(
            student=self.student_present,
            cohort=self.cohort,
            status="active",
        )
        self.partial_enrollment = Enrollment.objects.create(
            student=self.student_partial,
            cohort=self.cohort,
            status="active",
        )
        self.absent_enrollment = Enrollment.objects.create(
            student=self.student_absent,
            cohort=self.cohort,
            status="active",
        )

    def _make_start_token(self, user):
        raw_token = Signer().sign(str(user.id))
        return base64.urlsafe_b64encode(raw_token.encode()).decode().rstrip("=")

    def test_start_token_link_saves_telegram_fields_and_notification(self):
        token = self._make_start_token(self.unlinked_user)

        result = link_user_from_start_token(token, 999001, "local_test_user")

        self.assertTrue(result.ok)
        self.unlinked_user.refresh_from_db()
        self.assertEqual(self.unlinked_user.telegram_id, 999001)
        self.assertEqual(self.unlinked_user.telegram_username, "local_test_user")
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.unlinked_user,
                title="Telegram hisobi ulandi",
            ).exists()
        )

    def test_link_cohort_binds_group_chat_metadata(self):
        result = bind_chat_to_cohort(
            cohort_id=self.cohort.id,
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
        )

        self.assertTrue(result.ok)
        self.cohort.refresh_from_db()
        self.assertEqual(self.cohort.telegram_chat_id, -1001234567890)
        self.assertEqual(self.cohort.telegram_chat_title, "A1 Evening Group")

    def test_start_session_and_checkin_flow(self):
        bind_chat_to_cohort(
            cohort_id=self.cohort.id,
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
        )

        start_result = start_lesson_session(
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
            lesson_ref="1",
        )
        checkin_result = register_checkin(
            session_id=start_result.session.id,
            telegram_user_id=self.student_present.telegram_id,
            telegram_username="student_present",
        )

        self.assertTrue(start_result.ok)
        self.assertEqual(start_result.lesson_index, 1)
        self.assertEqual(start_result.session.lesson, self.lesson_1)
        self.assertTrue(checkin_result.ok)
        self.assertEqual(checkin_result.code, "checked_in")
        self.assertEqual(
            TelegramLessonCheckIn.objects.filter(session=start_result.session).count(),
            1,
        )

        duplicate_result = register_checkin(
            session_id=start_result.session.id,
            telegram_user_id=self.student_present.telegram_id,
            telegram_username="student_present",
        )
        self.assertTrue(duplicate_result.ok)
        self.assertEqual(duplicate_result.code, "already_checked_in")

    def test_close_session_writes_present_partial_and_absent_attendance(self):
        bind_chat_to_cohort(
            cohort_id=self.cohort.id,
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
        )
        start_result = start_lesson_session(
            chat_id=-1001234567890,
            chat_title="A1 Evening Group",
            actor_telegram_id=self.teacher.telegram_id,
            lesson_ref="1",
        )
        session = start_result.session
        session.started_at = timezone.now() - datetime.timedelta(minutes=30)
        session.save(update_fields=["started_at"])

        register_checkin(
            session_id=session.id,
            telegram_user_id=self.student_present.telegram_id,
            telegram_username="student_present",
        )
        present_checkin = TelegramLessonCheckIn.objects.get(session=session, enrollment=self.present_enrollment)
        present_checkin.checked_in_at = session.started_at + datetime.timedelta(minutes=5)
        present_checkin.save(update_fields=["checked_in_at"])

        register_checkin(
            session_id=session.id,
            telegram_user_id=self.student_partial.telegram_id,
            telegram_username="student_partial",
        )

        close_result = close_lesson_session(
            chat_id=-1001234567890,
            actor_telegram_id=self.teacher.telegram_id,
        )

        self.assertTrue(close_result.ok)
        session.refresh_from_db()
        self.assertEqual(session.status, TelegramLessonSession.STATUS_CLOSED)

        present_record = Attendance.objects.get(
            enrollment=self.present_enrollment,
            lesson=self.lesson_1,
            date=timezone.localdate(),
        )
        partial_record = Attendance.objects.get(
            enrollment=self.partial_enrollment,
            lesson=self.lesson_1,
            date=timezone.localdate(),
        )
        absent_record = Attendance.objects.get(
            enrollment=self.absent_enrollment,
            lesson=self.lesson_1,
            date=timezone.localdate(),
        )

        self.assertEqual(present_record.status, Attendance.STATUS_PRESENT)
        self.assertEqual(partial_record.status, Attendance.STATUS_PARTIAL)
        self.assertEqual(absent_record.status, Attendance.STATUS_ABSENT)
        self.assertEqual(close_result.summary[Attendance.STATUS_PRESENT], 1)
        self.assertEqual(close_result.summary[Attendance.STATUS_PARTIAL], 1)
        self.assertEqual(close_result.summary[Attendance.STATUS_ABSENT], 1)
