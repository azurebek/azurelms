"""Imtihon muharriri scope'i — o'qituvchi faqat o'z kursining imtihoniga tegadi.

`core/test_backoffice_lessons.py` bilan bir xil shakl: qoida
`core/access.py::teacher_course_queryset` da, tekshiruv esa ikki yo'lda —
sahifani **ochish** va **saqlash** (shu jumladan imtihonni begona kursga
ko'chirishga urinish).
"""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from courses.models import Course, Exam, ExamSection


@override_settings(GEMINI_API_KEY=None)
class BackofficeExamEditorScopeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_superuser(
            username="exam_owner",
            email="owner@example.test",
            password="pass-12345",
        )
        self.teacher = User.objects.create_user(
            username="exam_teacher",
            email="teacher@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.other_teacher = User.objects.create_user(
            username="exam_other",
            email="other@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="exam_student",
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
        self.exam = Exam.objects.create(
            course=self.course,
            title="A1 yakuniy",
            exam_type="final",
            weight_percentage=60,
        )
        self.section = ExamSection.objects.create(
            exam=self.exam,
            title="Grammatika",
            section_type="grammar_quiz",
            instructions="Savollarga javob bering.",
            max_score=40,
            time_limit_minutes=30,
            order=1,
        )
        self.earlier_exam = Exam.objects.create(
            course=self.course,
            title="A1 oraliq",
            exam_type="visa",
            weight_percentage=40,
        )

        self.foreign_course = Course.objects.create(
            title="Turk tili B2",
            description="Begona kurs",
            instructor=self.other_teacher,
            level="intermediate",
            duration=30,
        )
        self.foreign_exam = Exam.objects.create(
            course=self.foreign_course,
            title="B2 begona imtihon",
            exam_type="final",
            weight_percentage=50,
        )
        ExamSection.objects.create(
            exam=self.foreign_exam,
            title="Begona bo'lim",
            section_type="reading",
            instructions="Begona shart.",
            max_score=50,
            time_limit_minutes=40,
            order=1,
        )

    def _edit_url(self, exam):
        return reverse("backoffice_exam_edit", kwargs={"exam_id": exam.pk})

    def _payload(self, **overrides):
        data = {
            "title": "A1 yakuniy",
            "course": self.course.pk,
            "exam_type": "final",
            "weight_percentage": 60,
            "passing_score": 60,
            "max_attempts": 2,
            "prerequisite_exam": "",
            "minimum_lesson_completion_percent": 0,
            "minimum_attendance_percent": 0,
            "section-title": "Grammatika",
            "section-section_type": "grammar_quiz",
            "section-instructions": "Savollarga javob bering.",
            "section-reading_text": "",
            "section-media_url": "",
            "section-max_score": 40,
            "section-time_limit_minutes": 30,
            "section-order": 1,
        }
        data.update(overrides)
        return data

    def test_teacher_opens_their_own_exam(self):
        self.client.force_login(self.teacher)
        response = self.client.get(self._edit_url(self.exam))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A1 yakuniy")

    def test_foreign_exam_is_not_found_for_a_teacher(self):
        self.client.force_login(self.teacher)
        response = self.client.get(self._edit_url(self.foreign_exam))

        self.assertEqual(response.status_code, 404)

    def test_foreign_exam_cannot_be_saved(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            self._edit_url(self.foreign_exam),
            self._payload(title="O'zlashtirildi", course=self.foreign_course.pk),
        )

        self.assertEqual(response.status_code, 404)
        self.foreign_exam.refresh_from_db()
        self.assertEqual(self.foreign_exam.title, "B2 begona imtihon")

    def test_course_choices_stay_inside_the_teachers_courses(self):
        self.client.force_login(self.teacher)
        response = self.client.get(self._edit_url(self.exam))

        course_ids = set(
            response.context["exam_form"].fields["course"].queryset.values_list("pk", flat=True)
        )
        self.assertEqual(course_ids, {self.course.pk})
        self.assertNotContains(response, "Turk tili B2")

    def test_prerequisite_choices_do_not_leak_foreign_exams(self):
        self.client.force_login(self.teacher)
        response = self.client.get(self._edit_url(self.exam))

        prerequisite_ids = set(
            response.context["exam_form"]
            .fields["prerequisite_exam"]
            .queryset.values_list("pk", flat=True)
        )
        # O'z kursidagi boshqa imtihon qoladi, begonasi va o'zi chiqib ketadi.
        self.assertEqual(prerequisite_ids, {self.earlier_exam.pk})
        self.assertNotContains(response, "B2 begona imtihon")

    def test_an_exam_cannot_be_moved_into_a_foreign_course(self):
        """Scope faqat ochishda emas, saqlashda ham."""
        self.client.force_login(self.teacher)
        response = self.client.post(
            self._edit_url(self.exam), self._payload(course=self.foreign_course.pk)
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["exam_form"],
            "course",
            ["Select a valid choice. That choice is not one of the available choices."],
        )
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.course_id, self.course.pk)

    def test_own_exam_still_saves(self):
        self.client.force_login(self.teacher)
        response = self.client.post(
            self._edit_url(self.exam),
            self._payload(title="A1 yakuniy (yangilangan)", passing_score=70),
        )

        self.assertRedirects(response, self._edit_url(self.exam))
        self.exam.refresh_from_db()
        self.assertEqual(self.exam.title, "A1 yakuniy (yangilangan)")
        self.assertEqual(self.exam.passing_score, 70)

    def test_the_index_route_opens_an_exam_from_the_teachers_own_courses(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("backoffice_exams"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.context["exam"].pk, {self.exam.pk, self.earlier_exam.pk})
        self.assertEqual(response.context["exam"].course_id, self.course.pk)

    def test_a_teacher_without_courses_gets_an_empty_editor(self):
        User = get_user_model()
        lonely = User.objects.create_user(
            username="exam_lonely",
            email="lonely@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.client.force_login(lonely)
        response = self.client.get(reverse("backoffice_exams"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["exam"])

    def test_owner_still_sees_every_exam(self):
        self.client.force_login(self.owner)
        response = self.client.get(self._edit_url(self.foreign_exam))

        self.assertEqual(response.status_code, 200)
        course_ids = set(
            response.context["exam_form"].fields["course"].queryset.values_list("pk", flat=True)
        )
        self.assertEqual(course_ids, {self.course.pk, self.foreign_course.pk})

    def test_a_student_cannot_open_the_editor(self):
        self.client.force_login(self.student)
        response = self.client.get(self._edit_url(self.exam))

        self.assertNotEqual(response.status_code, 200)
        self.assertEqual(response.status_code, 302)
