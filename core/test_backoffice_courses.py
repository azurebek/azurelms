import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from cohorts.models import Cohort, Enrollment
from courses.models import Course, Lesson, Module


@override_settings(GEMINI_API_KEY=None)
class BackofficeCourseListTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_superuser(
            username="course_owner",
            email="owner@example.test",
            password="pass-12345",
        )
        self.teacher = User.objects.create_user(
            username="teacher_one",
            email="teacher-one@example.test",
            password="pass-12345",
            first_name="Dilnoza",
            is_staff=True,
        )
        self.other_teacher = User.objects.create_user(
            username="teacher_two",
            email="teacher-two@example.test",
            password="pass-12345",
            first_name="Kamola",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="course_student",
            email="student@example.test",
            password="pass-12345",
        )
        self.active_course = Course.objects.create(
            title="Turk tili B1",
            description="Faol kurs",
            instructor=self.teacher,
            level="intermediate",
            duration=40,
            is_active=True,
        )
        module = Module.objects.create(course=self.active_course, title="Birinchi modul", order=1)
        Lesson.objects.create(module=module, title="Birinchi dars", order=1)
        Lesson.objects.create(module=module, title="Ikkinchi dars", order=2)
        cohort = Cohort.objects.create(
            name="B1 tonggi",
            course=self.active_course,
            start_date=datetime.date(2026, 9, 1),
        )
        Enrollment.objects.create(student=self.student, cohort=cohort, status=Enrollment.STATUS_ACTIVE)
        self.draft_course = Course.objects.create(
            title="Turk tili C1",
            description="Qoralama kurs",
            instructor=self.other_teacher,
            level="advanced",
            duration=60,
            is_active=False,
        )

    def test_owner_sees_course_inventory_counts_and_edit_actions(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("backoffice_courses"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backoffice/courses.html")
        self.assertEqual(response.context["course_stats"], {
            "total": 2,
            "active": 1,
            "draft": 1,
            "lessons": 2,
        })
        rows = list(response.context["page_obj"].object_list)
        self.assertEqual({course.pk for course in rows}, {self.active_course.pk, self.draft_course.pk})
        active_row = next(course for course in rows if course.pk == self.active_course.pk)
        self.assertEqual(active_row.annotated_modules_count, 1)
        self.assertEqual(active_row.annotated_lessons_count, 2)
        self.assertEqual(active_row.annotated_cohorts_count, 1)
        self.assertEqual(active_row.annotated_students_count, 1)
        self.assertContains(response, reverse("backoffice_course_create"))
        self.assertContains(
            response,
            reverse("backoffice_course_edit", kwargs={"course_id": self.active_course.pk}),
        )
        self.assertContains(response, "Kurslar")

    def test_status_and_search_filters_narrow_the_list(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse("backoffice_courses"),
            {"status": "draft", "q": "Kamola"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["page_obj"].object_list), [self.draft_course])
        self.assertEqual(response.context["filters"], {"q": "Kamola", "status": "draft"})
        self.assertNotContains(response, self.active_course.title)

    def test_teacher_only_lists_and_edits_courses_in_teacher_scope(self):
        self.client.force_login(self.teacher)

        response = self.client.get(reverse("backoffice_courses"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["course_stats"]["total"], 1)
        self.assertEqual(response.context["counts"]["courses"], 1)
        self.assertContains(response, self.active_course.title)
        self.assertNotContains(response, self.draft_course.title)
        own_edit = self.client.get(
            reverse("backoffice_course_edit", kwargs={"course_id": self.active_course.pk})
        )
        other_edit = self.client.get(
            reverse("backoffice_course_edit", kwargs={"course_id": self.draft_course.pk})
        )
        self.assertEqual(own_edit.status_code, 200)
        self.assertEqual(other_edit.status_code, 404)

    def test_teacher_cannot_transfer_course_outside_teacher_scope(self):
        self.client.force_login(self.teacher)
        url = reverse("backoffice_course_edit", kwargs={"course_id": self.active_course.pk})

        get_response = self.client.get(url)
        self.assertEqual(
            list(get_response.context["form"].fields["instructor"].queryset),
            [self.teacher],
        )

        response = self.client.post(
            url,
            {
                "title": self.active_course.title,
                "description": self.active_course.description,
                "instructor": self.other_teacher.pk,
                "level": self.active_course.level,
                "duration": self.active_course.duration,
                "price": self.active_course.price,
                "cover_mode": self.active_course.cover_mode,
                "gradient_preset": self.active_course.gradient_preset,
                "gradient_cover_title": self.active_course.gradient_cover_title,
                "gradient_cover_label": self.active_course.gradient_cover_label,
                "certificate_min_lesson_completion_percent": 0,
                "certificate_min_attendance_percent": 0,
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("instructor", response.context["form"].errors)
        self.active_course.refresh_from_db()
        self.assertEqual(self.active_course.instructor, self.teacher)

    def test_course_badge_uses_teacher_scope_across_backoffice_pages(self):
        self.client.force_login(self.teacher)

        for url_name in (
            "backoffice_dashboard",
            "backoffice_chats",
            "backoffice_lessons",
            "backoffice_exams",
            "backoffice_users",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["counts"]["courses"], 1)

    def test_student_cannot_open_course_inventory(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("backoffice_courses"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response["Location"])

    def test_course_editor_returns_to_course_inventory(self):
        self.client.force_login(self.owner)

        response = self.client.get(
            reverse("backoffice_course_edit", kwargs={"course_id": self.active_course.pk})
        )

        self.assertContains(response, reverse("backoffice_courses"))
        self.assertContains(response, "Kurslar ro'yxatiga qaytish")
