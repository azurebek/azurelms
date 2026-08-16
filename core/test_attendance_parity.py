"""A3 — davomat web va Telegram'da bir xil natija berishi kerak.

Backlog A3 outcome: "web/bot/Mini App bir xil state ko'rsatadi", acceptance esa
"adapter parity contract". Loyiha qoidasi ham aniq: bir qoida ikki surface'da
kerak bo'lsa, nusxa yozilmaydi — domain service chiqariladi.

Telegram `/yopish` yo'li `cohorts.attendance_service.upsert_attendance_and_xp()`
ni chaqiradi: u XP beradi, holat o'zgarganda XP farqini to'g'rilaydi va
kunlik faollik seriyasini yozadi. O'qituvchining web sahifasi esa
`Attendance.objects.create()` bilan o'zi yozardi — ya'ni bir xil amal qaysi
yuzada bajarilganiga qarab boshqacha natija berardi:

* web orqali "keldi" belgilangan o'quvchi **XP olmasdi**;
* seriyasi (streak) **yozilmasdi**;
* "keldi" → "kelmadi" ga o'zgartirilsa **XP qaytarib olinmasdi**;
* yozuv `date` siz yaratilib, `(enrollment, lesson, date)` kalitidan chiqib
  ketardi — bot yozgan qatorning yonida ikkinchi qator paydo bo'lishi mumkin.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.attendance_service import upsert_attendance_and_xp
from cohorts.models import Attendance, Cohort, Enrollment
from courses.models import Course, Lesson, Module

User = get_user_model()

LESSON_XP = 40


class AttendanceParityTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="att-teacher",
            email="att-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="att-student",
            email="att-student@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="Attendance Course",
            description="A3 parity",
            instructor=self.teacher,
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="M1", order=1)
        self.lesson = Lesson.objects.create(
            module=self.module,
            title="Dars 1",
            content="<p>matn</p>",
            order=1,
            xp_reward=LESSON_XP,
        )
        self.cohort = Cohort.objects.create(
            name="Attendance Cohort",
            course=self.course,
            start_date="2026-01-01",
            is_active=True,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
        )
        self.client.force_login(self.teacher)

    def _post_attendance(self, status):
        return self.client.post(
            reverse("teacher_attendance"),
            {
                "cohort": self.cohort.id,
                "lesson": self.lesson.id,
                f"att_{self.enrollment.id}": status,
            },
        )

    def _student_xp(self):
        self.student.refresh_from_db()
        return self.student.total_xp

    # --- web yuzasi canonical servis bilan bir xil ishlashi kerak ---

    def test_marking_present_on_the_web_awards_xp(self):
        self._post_attendance(Attendance.STATUS_PRESENT)

        self.assertEqual(self._student_xp(), LESSON_XP)
        record = Attendance.objects.get(enrollment=self.enrollment, lesson=self.lesson)
        self.assertEqual(record.xp_awarded, LESSON_XP)

    def test_partial_attendance_awards_the_reduced_share(self):
        self._post_attendance(Attendance.STATUS_PARTIAL)

        self.assertEqual(self._student_xp(), round(LESSON_XP * 0.3))

    def test_changing_present_to_absent_takes_the_xp_back(self):
        self._post_attendance(Attendance.STATUS_PRESENT)
        self._post_attendance(Attendance.STATUS_ABSENT)

        self.assertEqual(self._student_xp(), 0)
        record = Attendance.objects.get(enrollment=self.enrollment, lesson=self.lesson)
        self.assertEqual(record.xp_awarded, 0)

    def test_resubmitting_the_same_status_does_not_double_award(self):
        self._post_attendance(Attendance.STATUS_PRESENT)
        self._post_attendance(Attendance.STATUS_PRESENT)

        self.assertEqual(self._student_xp(), LESSON_XP)
        self.assertEqual(
            Attendance.objects.filter(enrollment=self.enrollment, lesson=self.lesson).count(),
            1,
        )

    def test_marking_present_on_the_web_records_daily_activity(self):
        """Jonli darsga qatnashish — malakali kunlik faollik (bot yo'li shunday qiladi)."""
        self._post_attendance(Attendance.STATUS_PRESENT)

        from users.models import LearnerStreak

        streak = LearnerStreak.objects.filter(user=self.student).first()
        self.assertIsNotNone(streak, "Web yo'li kunlik faollikni yozmadi")
        self.assertEqual(streak.last_activity_date, timezone.localdate())

    # --- ikkala yuza bir xil natija berishi ---

    def test_the_web_and_the_bot_service_agree(self):
        """Asl da'vo: bir xil kirish, bir xil chiqish."""
        self._post_attendance(Attendance.STATUS_PRESENT)
        web_record = Attendance.objects.get(enrollment=self.enrollment, lesson=self.lesson)
        web_xp = self._student_xp()

        other_student = User.objects.create_user(
            username="bot-student", email="bot-student@example.com", password="x"
        )
        other_enrollment = Enrollment.objects.create(
            student=other_student,
            cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
        )
        upsert_attendance_and_xp(
            enrollment=other_enrollment,
            lesson=self.lesson,
            date=timezone.localdate(),
            status=Attendance.STATUS_PRESENT,
            marked_by=self.teacher,
        )
        other_student.refresh_from_db()
        bot_record = Attendance.objects.get(enrollment=other_enrollment, lesson=self.lesson)

        self.assertEqual(web_record.xp_awarded, bot_record.xp_awarded)
        self.assertEqual(web_xp, other_student.total_xp)
        self.assertEqual(web_record.date, bot_record.date)
