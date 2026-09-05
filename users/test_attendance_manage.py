"""The date-based attendance URL renders and retains canonical XP behavior."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cohorts.models import Attendance, Cohort, Enrollment
from courses.models import Course, Lesson, Module


class AttendanceManageTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create_user(
            username="date-teacher", email="date-teacher@example.test", is_staff=True,
        )
        self.student = User.objects.create_user(
            username="date-student", email="date-student@example.test",
        )
        course = Course.objects.create(title="Turk tili", instructor=self.teacher, level="beginner")
        module = Module.objects.create(course=course, title="Birinchi modul", order=1)
        self.lesson = Lesson.objects.create(module=module, title="Dars", order=1, xp_reward=40)
        self.cohort = Cohort.objects.create(course=course, name="Guruh", start_date="2026-01-01")
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
        )
        self.url = reverse("attendance_manage") + (
            f"?cohort_id={self.cohort.pk}&lesson_id={self.lesson.pk}&date=2026-09-01"
        )
        self.client.force_login(self.teacher)

    def test_get_renders_existing_historical_status_and_date(self):
        Attendance.objects.create(enrollment=self.enrollment, lesson=self.lesson,
                                  date=date(2026, 9, 1), status=Attendance.STATUS_PARTIAL)
        response = self.client.get(self.url)
        self.assertContains(response, 'value="2026-09-01"')
        self.assertContains(response, 'value="partial" selected')
        self.assertContains(response, f'name="status_{self.enrollment.pk}"')

    def test_save_keeps_selected_date_and_is_idempotent_with_xp_reversal(self):
        for status in (Attendance.STATUS_PRESENT, Attendance.STATUS_PRESENT, Attendance.STATUS_ABSENT):
            response = self.client.post(self.url, {f"status_{self.enrollment.pk}": status})
            self.assertRedirects(response, self.url)
            self.student.refresh_from_db()
            self.assertEqual(self.student.total_xp, 0 if status == Attendance.STATUS_ABSENT else 40)
        self.assertEqual(Attendance.objects.get().date, date(2026, 9, 1))

    def test_students_denied_and_other_teachers_cannot_read_or_write_roster(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        other = get_user_model().objects.create_user(
            username="other-teacher", email="other-teacher@example.test", is_staff=True,
        )
        self.client.force_login(other)
        self.assertNotContains(self.client.get(self.url), f'name="status_{self.enrollment.pk}"')
        self.client.post(self.url, {f"status_{self.enrollment.pk}": Attendance.STATUS_PRESENT})
        self.assertFalse(Attendance.objects.exists())

    def test_empty_cohort_is_a_page_not_a_server_error(self):
        self.enrollment.delete()
        self.assertContains(self.client.get(self.url), "faol o'quvchi yo'q")
