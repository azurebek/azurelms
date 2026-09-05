"""«Davom etish» qayerda to'xtagan bo'lsangiz, o'sha yerdan davom etadi.

UX auditning 6-topilmasi. Tugmada «Davom etish» yozilgan edi, ammo u
`course_detail` ga eltardi: 20 ta darsni tugatgan o'quvchi kurs tavsifiga
tushib, mundarijadan o'zi qayerda qolganini qidirishi kerak edi.

Ikkita alohida nuqson:

1. **Havola noto'g'ri joyga ketardi.** Veb'dagi uchta «Davom etish» tugmasi
   `course_detail` ga bog'langan edi. Telegram Mini App esa allaqachon
   `course_study` ga borardi — yana adapter farqi, xususiyat yetishmasligi
   emas.
2. **`course_study` ning o'zi davom ettirmasdi.** Docstring'ida «current
   lesson (or the first lesson)» deb yozilgan, kod esa faqat
   `first_accessible_lesson` ni ishlatardi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from courses.models import CohortLessonRelease, Course, Lesson, LessonProgress, Module
from courses.resume_service import resume_lesson

User = get_user_model()


class ResumeFixture:
    def setUp(self):
        super().setUp()
        today = timezone.localdate()
        teacher = User.objects.create_user(
            username="davom-teacher", email="t@example.test", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="davom-student", email="s@example.test", password="x"
        )
        self.course = Course.objects.create(
            title="Kurs", description="d", level="beginner", instructor=teacher
        )
        module = Module.objects.create(course=self.course, title="M", order=1)
        self.lessons = [
            Lesson.objects.create(module=module, title=f"Dars {i}", order=i)
            for i in range(1, 6)
        ]
        self.cohort = Cohort.objects.create(
            name="G", course=self.course, start_date=today
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=today + datetime.timedelta(days=30),
        )

    def touch(self, lesson, *, completed, minutes_ago):
        """`last_accessed_at` — `auto_now`, shuning uchun keyin yoziladi."""
        progress = LessonProgress.objects.create(
            enrollment=self.enrollment, lesson=lesson, is_completed=completed,
        )
        LessonProgress.objects.filter(pk=progress.pk).update(
            last_accessed_at=timezone.now() - datetime.timedelta(minutes=minutes_ago)
        )
        return progress

    def resume(self):
        lesson, _ = resume_lesson(self.student, self.course, self.enrollment)
        return lesson


class WhereYouStoppedTests(ResumeFixture, TestCase):
    def test_the_half_finished_lesson_wins(self):
        """Odam aynan shu yerda to'xtagan."""
        self.touch(self.lessons[0], completed=True, minutes_ago=30)
        self.touch(self.lessons[2], completed=False, minutes_ago=5)

        self.assertEqual(self.resume(), self.lessons[2])

    def test_the_most_recent_half_finished_one_wins(self):
        self.touch(self.lessons[1], completed=False, minutes_ago=60)
        self.touch(self.lessons[3], completed=False, minutes_ago=2)

        self.assertEqual(self.resume(), self.lessons[3])

    def test_when_everything_touched_is_done_the_next_one_is_offered(self):
        for lesson in self.lessons[:3]:
            self.touch(lesson, completed=True, minutes_ago=10)

        self.assertEqual(self.resume(), self.lessons[3])

    def test_when_the_whole_course_is_done_the_last_one_opens_again(self):
        """Kurs sahifasiga otib yuborilmaydi — odam darsni ko'rmoqchi."""
        for index, lesson in enumerate(self.lessons):
            self.touch(lesson, completed=True, minutes_ago=50 - index)

        self.assertEqual(self.resume(), self.lessons[-1])

    def test_a_fresh_learner_starts_at_the_first_lesson(self):
        self.assertEqual(self.resume(), self.lessons[0])


class ALockedLessonIsNeverResumedTests(ResumeFixture, TestCase):
    """Qulf davom etishdan kuchliroq."""

    def test_a_lesson_the_teacher_has_not_opened_is_skipped(self):
        # Tomchilab berish: faqat birinchi ikkitasi ochiq.
        for index, lesson in enumerate(self.lessons):
            CohortLessonRelease.objects.create(
                cohort=self.cohort, lesson=lesson, is_released=index < 2,
            )
        self.touch(self.lessons[0], completed=True, minutes_ago=10)

        self.assertEqual(self.resume(), self.lessons[1])

    def test_progress_on_a_since_locked_lesson_is_ignored(self):
        """Dars keyin yopilgan bo'lsa, unga qaytarilmaydi."""
        for index, lesson in enumerate(self.lessons):
            CohortLessonRelease.objects.create(
                cohort=self.cohort, lesson=lesson, is_released=index == 0,
            )
        self.touch(self.lessons[3], completed=False, minutes_ago=1)

        self.assertEqual(self.resume(), self.lessons[0])

    def test_nothing_open_means_nothing_to_resume(self):
        for lesson in self.lessons:
            CohortLessonRelease.objects.create(
                cohort=self.cohort, lesson=lesson, is_released=False,
            )

        self.assertIsNone(self.resume())


class TheButtonActuallyGoesThereTests(ResumeFixture, TestCase):
    def study_url(self):
        return reverse("course_study", kwargs={"course_id": self.course.id})

    def test_the_study_url_redirects_to_the_resumed_lesson(self):
        self.touch(self.lessons[0], completed=True, minutes_ago=20)
        self.touch(self.lessons[2], completed=False, minutes_ago=1)
        self.client.force_login(self.student)

        response = self.client.get(self.study_url())

        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/lesson/{self.lessons[2].id}/", response["Location"])

    def test_it_says_so_when_no_lesson_is_open_yet(self):
        for lesson in self.lessons:
            CohortLessonRelease.objects.create(
                cohort=self.cohort, lesson=lesson, is_released=False,
            )
        self.client.force_login(self.student)

        response = self.client.get(self.study_url(), follow=True)

        self.assertContains(response, "ochiq dars mavjud emas")

    def test_the_dashboard_button_points_at_the_lesson_not_the_course_page(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, f'href="{self.study_url()}?cohort={self.cohort.id}"')

    def test_the_my_courses_button_points_at_the_lesson_not_the_course_page(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("my_courses"))

        self.assertContains(response, f'href="{self.study_url()}?cohort={self.cohort.id}"')

    def test_the_web_now_does_what_the_mini_app_already_did(self):
        """Parity: Mini App allaqachon `course_study` ga borardi."""
        from pathlib import Path

        from django.conf import settings

        base = Path(settings.BASE_DIR)
        mini_app = (base / "templates/bot/miniapp_home.html").read_text(encoding="utf-8")
        dashboard = (base / "templates/users/dashboard.html").read_text(encoding="utf-8")

        self.assertIn("course_study", mini_app)
        self.assertIn("course_study", dashboard)
