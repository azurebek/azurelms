"""A3 — dars sessiyasini yopish yarim yo'lda qolmasligi kerak.

`close_lesson_session()` bitta amalda butun guruhning davomatini yozadi, keyin
sessiyani yopadi va kelmaganlarga bildirishnoma qo'yadi. Bularning hammasi
bitta tranzaksiyada bo'lishi kerak: sikl o'rtasida uzilish (masalan bazaga
ulanish yo'qolishi) yarim yozilgan davomatni va OPEN qolgan sessiyani
qoldiradi. Har bir yozuv alohida idempotent bo'lgani uchun bu buzilish emas,
ammo o'qituvchi "davomat olindimi?" degan savolga javob topolmaydi — ro'yxatning
yarmi bor, sessiya esa hali ochiq.

Ikkinchi da'vo: yopish ikki marta chaqirilsa (ikkita o'qituvchi bir vaqtda
`/yopish` yuborsa) natija bitta izchil holat bo'lishi kerak.
"""

import datetime
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bot.models import TelegramLessonSession
from bot.services import close_lesson_session, start_lesson_session
from cohorts.models import Attendance, Cohort, Enrollment
from courses.models import Course, Lesson, Module
from users.models import Notification

User = get_user_model()

CHAT_ID = -1009876543210


class CloseLessonSessionAtomicityTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="close-teacher",
            email="close-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.teacher.telegram_id = 770000001
        self.teacher.save(update_fields=["telegram_id"])

        self.course = Course.objects.create(
            title="Close Session Course",
            description="A3 atomicity",
            instructor=self.teacher,
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="M1", order=1)
        self.lesson = Lesson.objects.create(
            module=self.module, title="Dars 1", content="<p>x</p>", order=1, xp_reward=30
        )
        self.cohort = Cohort.objects.create(
            name="Close Cohort",
            course=self.course,
            start_date="2026-01-01",
            is_active=True,
            telegram_chat_id=CHAT_ID,
        )

        self.enrollments = []
        for index in range(3):
            student = User.objects.create_user(
                username=f"close-student-{index}",
                email=f"close-student-{index}@example.com",
                password="testpass123",
            )
            student.telegram_id = 770001000 + index
            student.save(update_fields=["telegram_id"])
            self.enrollments.append(
                Enrollment.objects.create(
                    student=student,
                    cohort=self.cohort,
                    status=Enrollment.STATUS_ACTIVE,
                )
            )

        started = start_lesson_session(
            chat_id=CHAT_ID,
            chat_title="Close Group",
            actor_telegram_id=self.teacher.telegram_id,
            lesson_ref="1",
        )
        self.assertTrue(started.ok, started.message)
        self.session = started.session
        self.session.started_at = timezone.now() - datetime.timedelta(minutes=20)
        self.session.save(update_fields=["started_at"])

    def _close(self):
        return close_lesson_session(chat_id=CHAT_ID, actor_telegram_id=self.teacher.telegram_id)

    # --- yarim yozilgan holat qolmasligi ---

    def test_a_failure_midway_leaves_no_attendance_at_all(self):
        """Uchinchi o'quvchida uzilsa, birinchi ikkitasiniki ham yozilmasligi kerak."""
        from cohorts.attendance_service import upsert_attendance_and_xp as original

        calls = {"n": 0}

        def flaky_upsert(**kwargs):
            calls["n"] += 1
            if calls["n"] == 3:
                raise RuntimeError("baza uzildi")
            return original(**kwargs)

        with mock.patch("bot.services.upsert_attendance_and_xp", side_effect=flaky_upsert):
            with self.assertRaises(RuntimeError):
                self._close()

        self.assertEqual(
            Attendance.objects.filter(lesson=self.lesson).count(),
            0,
            "Yarim yozilgan davomat qoldi",
        )

    def test_a_failure_midway_leaves_the_session_open(self):
        """Sessiya yopilmagan bo'lsa, o'qituvchi qayta urinib ko'ra oladi."""

        def boom(**kwargs):
            raise RuntimeError("baza uzildi")

        with mock.patch("bot.services.upsert_attendance_and_xp", side_effect=boom):
            with self.assertRaises(RuntimeError):
                self._close()

        self.session.refresh_from_db()
        self.assertEqual(self.session.status, TelegramLessonSession.STATUS_OPEN)

    def test_a_failure_midway_sends_no_absence_notification(self):
        """Yopilmagan sessiya uchun "darsni qoldirdingiz" xabari ketmasligi kerak."""

        def boom(**kwargs):
            raise RuntimeError("baza uzildi")

        with mock.patch("bot.services.upsert_attendance_and_xp", side_effect=boom):
            with self.assertRaises(RuntimeError):
                self._close()

        self.assertEqual(Notification.objects.filter(external_key__startswith="tg-absent-").count(), 0)

    def test_retrying_after_a_failure_completes_cleanly(self):
        """Uzilishdan keyin qayta yugurtirish to'liq va bir martalik natija beradi."""

        def boom(**kwargs):
            raise RuntimeError("baza uzildi")

        with mock.patch("bot.services.upsert_attendance_and_xp", side_effect=boom):
            with self.assertRaises(RuntimeError):
                self._close()

        result = self._close()

        self.assertTrue(result.ok, result.message)
        self.assertEqual(Attendance.objects.filter(lesson=self.lesson).count(), len(self.enrollments))
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, TelegramLessonSession.STATUS_CLOSED)

    # --- oddiy yo'l buzilmasligi ---

    def test_a_normal_close_writes_everyone_and_closes(self):
        result = self._close()

        self.assertTrue(result.ok, result.message)
        self.assertEqual(result.summary["total"], len(self.enrollments))
        self.assertEqual(Attendance.objects.filter(lesson=self.lesson).count(), len(self.enrollments))
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, TelegramLessonSession.STATUS_CLOSED)

    def test_closing_twice_is_reported_and_changes_nothing(self):
        first = self._close()
        second = self._close()

        self.assertTrue(first.ok)
        self.assertFalse(second.ok)
        self.assertEqual(second.code, "session_missing")
        self.assertEqual(Attendance.objects.filter(lesson=self.lesson).count(), len(self.enrollments))
