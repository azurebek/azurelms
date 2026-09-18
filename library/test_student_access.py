"""O'quvchi tomoni: nima ko'rinadi va fayl qachon ochiladi.

Asosiy shart: kutubxonaning o'zi o'quvchi uchun mavjud emas. U faqat **darsga
ochiq biriktirilgan** materialni ko'radi, faylni esa ruxsat tekshiradigan
view beradi — ro'yxatda ko'rinmasligi himoya emas, shuning uchun har ikkalasi
alohida tekshiriladi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from courses.models import CohortLessonRelease, Course, Lesson, Module

from . import services
from .models import LibraryResource, MaterialAudience
from .test_resources import pdf_upload


@override_settings(GEMINI_API_KEY=None)
class StudentMaterialAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create_user(
            username="mat_teacher",
            email="teacher@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="mat_student", email="student@example.test", password="pass-12345"
        )
        self.outsider = User.objects.create_user(
            username="mat_outsider", email="outsider@example.test", password="pass-12345"
        )
        self.course = Course.objects.create(
            title="Turk tili A1",
            description="Test",
            instructor=self.teacher,
            level="beginner",
            duration=20,
        )
        module = Module.objects.create(course=self.course, title="Modul", order=1)
        self.lesson = Lesson.objects.create(module=module, title="1-dars", order=1)
        self.cohort = Cohort.objects.create(
            name="A1 tonggi",
            course=self.course,
            start_date=datetime.date(2026, 9, 1),
        )
        Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE
        )

        self.resource = LibraryResource(title="Dars varaqasi")
        services.apply_upload(self.resource, pdf_upload(), actor=self.teacher)
        self.resource.save()
        self.material, _ = services.attach_to_lesson(
            self.lesson, self.resource, actor=self.teacher
        )

    def _file_url(self, material=None):
        return reverse("library:material_file", args=[(material or self.material).pk])

    def test_enrolled_student_can_open_an_open_material(self):
        self.client.force_login(self.student)
        response = self.client.get(self._file_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_view_only_material_opens_in_the_browser(self):
        self.material.is_downloadable = False
        self.material.save(update_fields=["is_downloadable"])

        self.client.force_login(self.student)
        response = self.client.get(self._file_url())

        self.assertEqual(response.status_code, 200)
        self.assertIn("inline", response["Content-Disposition"])

    def test_hidden_attachment_is_not_reachable(self):
        self.material.is_visible = False
        self.material.save(update_fields=["is_visible"])

        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self._file_url()).status_code, 404)

    def test_teacher_only_attachment_is_not_reachable_for_students(self):
        self.material.audience = MaterialAudience.TEACHER
        self.material.save(update_fields=["audience"])

        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self._file_url()).status_code, 404)

        # O'qituvchining o'zi ko'radi — bu uning kursi.
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(self._file_url()).status_code, 200)

    def test_scheduled_material_stays_closed_until_its_time(self):
        self.material.available_from = timezone.now() + datetime.timedelta(days=1)
        self.material.save(update_fields=["available_from"])

        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self._file_url()).status_code, 404)

        self.material.available_from = timezone.now() - datetime.timedelta(minutes=1)
        self.material.save(update_fields=["available_from"])
        self.assertEqual(self.client.get(self._file_url()).status_code, 200)

    def test_a_user_without_enrollment_gets_nothing(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self._file_url()).status_code, 404)

    def test_anonymous_visitor_is_redirected_to_login(self):
        response = self.client.get(self._file_url())
        self.assertEqual(response.status_code, 302)

    def test_a_locked_lesson_also_locks_its_materials(self):
        """Drip yopiq dars — biriktirma ochiq bo'lsa ham fayl berilmaydi."""
        CohortLessonRelease.objects.create(
            cohort=self.cohort, lesson=self.lesson, is_released=False
        )

        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self._file_url()).status_code, 404)

    def test_expired_enrollment_loses_access(self):
        Enrollment.objects.filter(student=self.student).update(
            status=Enrollment.STATUS_EXPIRED
        )
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self._file_url()).status_code, 404)


@override_settings(GEMINI_API_KEY=None)
class LessonPageMaterialTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.teacher = User.objects.create_user(
            username="page_teacher",
            email="pteacher@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="page_student", email="pstudent@example.test", password="pass-12345"
        )
        self.course = Course.objects.create(
            title="Turk tili A1",
            description="Test",
            instructor=self.teacher,
            level="beginner",
            duration=20,
        )
        module = Module.objects.create(course=self.course, title="Modul", order=1)
        self.lesson = Lesson.objects.create(module=module, title="1-dars", order=1)
        cohort = Cohort.objects.create(
            name="A1 tonggi", course=self.course, start_date=datetime.date(2026, 9, 1)
        )
        Enrollment.objects.create(
            student=self.student, cohort=cohort, status=Enrollment.STATUS_ACTIVE
        )

        self.open_resource = LibraryResource(title="Ochiq varaqa")
        services.apply_upload(self.open_resource, pdf_upload(), actor=self.teacher)
        self.open_resource.save()
        self.secret_resource = LibraryResource(title="Javoblar kaliti", is_teacher_only=True)
        services.apply_upload(self.secret_resource, pdf_upload("kalit.pdf"), actor=self.teacher)
        self.secret_resource.save()

        services.attach_to_lesson(self.lesson, self.open_resource, actor=self.teacher)
        services.attach_to_lesson(self.lesson, self.secret_resource, actor=self.teacher)

    def test_lesson_page_shows_only_student_visible_materials(self):
        self.client.force_login(self.student)
        response = self.client.get(
            reverse("lesson_detail", args=[self.course.pk, self.lesson.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ochiq varaqa")
        self.assertNotContains(response, "Javoblar kaliti")
        self.assertEqual(
            [m.resource_id for m in response.context["lesson_materials"]],
            [self.open_resource.pk],
        )
        self.assertContains(response, "Materiallar")
