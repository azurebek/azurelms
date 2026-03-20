from django.contrib.auth import get_user_model
from datetime import date
from django.test import TestCase
from django.urls import reverse

from cohorts.models import Attendance, Cohort, Enrollment
from courses.models import Course, Lesson, Module


User = get_user_model()


class BackofficeAccessTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="regular-user",
            email="regular@example.com",
            password="testpass123",
        )
        self.staff = User.objects.create_user(
            username="staff-user",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.teacher = User.objects.create_user(
            username="teacher-user",
            email="teacher@example.com",
            password="testpass123",
            is_staff=True,
        )

        self.course = Course.objects.create(
            title="Backoffice Cohort Course",
            description="Backoffice test",
            instructor=self.teacher,
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="1-modul", order=1)
        self.lesson = Lesson.objects.create(module=self.module, title="1-dars", order=1)
        self.cohort = Cohort.objects.create(
            name="Backoffice Cohort",
            course=self.course,
            start_date="2026-03-01",
            is_active=True,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status="active",
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("backoffice:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_dashboard_denies_non_staff_user(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("backoffice:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard"), response.url)

    def test_staff_can_open_backoffice_pages(self):
        self.client.force_login(self.staff)
        for route_name in (
            "backoffice:dashboard",
            "backoffice:students",
            "backoffice:payments",
            "backoffice:cohorts",
            "backoffice:attendance",
        ):
            response = self.client.get(reverse(route_name))
            self.assertEqual(response.status_code, 200, route_name)

    def test_staff_can_save_attendance_from_backoffice(self):
        self.client.force_login(self.staff)
        target_date = date(2026, 3, 20)
        query = f"?cohort_id={self.cohort.id}&lesson_id={self.lesson.id}&date={target_date.isoformat()}"
        url = reverse("backoffice:attendance") + query

        response = self.client.post(
            url,
            {
                f"status_{self.enrollment.id}": Attendance.STATUS_PRESENT,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("backoffice:attendance"), response.url)

        attendance = Attendance.objects.get(
            enrollment=self.enrollment,
            lesson=self.lesson,
            date=target_date,
        )
        self.assertEqual(attendance.status, Attendance.STATUS_PRESENT)
