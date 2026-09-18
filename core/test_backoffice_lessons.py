"""Dars muharriri scope'i — o'qituvchi faqat o'z kursining darsiga tegadi.

Qoida `core/access.py::teacher_course_queryset` da: superuser hammasini
ko'radi, qolgan har kim faqat o'zi instructor bo'lgan kursni. Bu yuzada
ilgari scope umuman yo'q edi, shuning uchun testlar ikkala yo'lni ham
tekshiradi: **o'qish** (sahifani ochish) va **yozish** (saqlash, shu jumladan
darsni begona modulga ko'chirish).
"""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from courses.models import Course, Lesson, Module


@override_settings(GEMINI_API_KEY=None)
class BackofficeLessonEditorScopeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_superuser(
            username="lesson_owner",
            email="owner@example.test",
            password="pass-12345",
        )
        self.teacher = User.objects.create_user(
            username="lesson_teacher",
            email="teacher@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.other_teacher = User.objects.create_user(
            username="lesson_other",
            email="other@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="lesson_student",
            email="student@example.test",
            password="pass-12345",
        )

        self.course = Course.objects.create(
            title="Turk tili A1",
            description="O'z kursim",
            instructor=self.teacher,
            level="beginner",
            duration=20,
        )
        self.module = Module.objects.create(course=self.course, title="Birinchi modul", order=1)
        self.lesson = Lesson.objects.create(module=self.module, title="Mening darsim", order=1)

        self.foreign_course = Course.objects.create(
            title="Turk tili B2",
            description="Begona kurs",
            instructor=self.other_teacher,
            level="intermediate",
            duration=30,
        )
        self.foreign_module = Module.objects.create(
            course=self.foreign_course, title="Begona modul", order=1
        )
        self.foreign_lesson = Lesson.objects.create(
            module=self.foreign_module, title="Begona dars", order=1
        )

    def _edit_url(self, lesson):
        return reverse("backoffice_lesson_edit", kwargs={"lesson_id": lesson.pk})

    def _payload(self, **overrides):
        data = {
            "title": "Mening darsim",
            "module": self.module.pk,
            "video_url": "",
            "content": "",
            "order": 1,
            "xp_reward": 10,
        }
        data.update(overrides)
        return data

    def test_teacher_opens_their_own_lesson(self):
        self.client.force_login(self.teacher)
        response = self.client.get(self._edit_url(self.lesson))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mening darsim")

    def test_foreign_lesson_is_not_found_for_a_teacher(self):
        self.client.force_login(self.teacher)
        response = self.client.get(self._edit_url(self.foreign_lesson))

        self.assertEqual(response.status_code, 404)

    def test_foreign_lesson_cannot_be_saved(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            self._edit_url(self.foreign_lesson),
            self._payload(title="O'zlashtirildi", module=self.foreign_module.pk),
        )

        self.assertEqual(response.status_code, 404)
        self.foreign_lesson.refresh_from_db()
        self.assertEqual(self.foreign_lesson.title, "Begona dars")

    def test_module_choices_stay_inside_the_teachers_courses(self):
        self.client.force_login(self.teacher)
        response = self.client.get(self._edit_url(self.lesson))

        module_ids = set(
            response.context["form"].fields["module"].queryset.values_list("pk", flat=True)
        )
        self.assertEqual(module_ids, {self.module.pk})
        self.assertNotContains(response, "Begona modul")

    def test_a_lesson_cannot_be_moved_into_a_foreign_course(self):
        """Scope faqat ochishda emas, saqlashda ham — aks holda ko'chirib bo'lardi."""
        self.client.force_login(self.teacher)
        response = self.client.post(
            self._edit_url(self.lesson), self._payload(module=self.foreign_module.pk)
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "module",
            ["Select a valid choice. That choice is not one of the available choices."],
        )
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.module_id, self.module.pk)

    def test_own_lesson_still_saves(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            self._edit_url(self.lesson), self._payload(title="Yangilangan dars", xp_reward=25)
        )

        self.assertRedirects(response, self._edit_url(self.lesson))
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, "Yangilangan dars")
        self.assertEqual(self.lesson.xp_reward, 25)

    def test_the_index_route_opens_a_lesson_from_the_teachers_own_courses(self):
        """Manzilda ID bo'lmasa ham birinchi dars scope ichidan tanlanadi."""
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("backoffice_lessons"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["lesson"].pk, self.lesson.pk)

    def test_a_teacher_without_courses_gets_an_empty_editor(self):
        User = get_user_model()
        lonely = User.objects.create_user(
            username="lesson_lonely",
            email="lonely@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.client.force_login(lonely)
        response = self.client.get(reverse("backoffice_lessons"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["lesson"])
        self.assertEqual(list(response.context["courses"]), [])

    def test_owner_still_sees_every_lesson(self):
        self.client.force_login(self.owner)
        response = self.client.get(self._edit_url(self.foreign_lesson))

        self.assertEqual(response.status_code, 200)
        module_ids = set(
            response.context["form"].fields["module"].queryset.values_list("pk", flat=True)
        )
        self.assertEqual(module_ids, {self.module.pk, self.foreign_module.pk})

    def test_a_student_cannot_open_the_editor(self):
        self.client.force_login(self.student)
        response = self.client.get(self._edit_url(self.lesson))

        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(response.status_code, 302)
