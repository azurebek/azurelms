"""Darsni tugatilgan deb belgilashni o'quvchi o'zi qiladi.

Owner xabar qildi: chap ustundagi ro'yxatni bosib chiqqanda kirgan
darslarning hammasi yashil belgi olib ketyapti. Sabab aniq edi — sahifani
**ochishning o'zi** `LessonProgress`ni tugatilgan deb yozardi
(`LessonDetailView.get_context_data`). Natijada foiz «o'rganilgan» emas,
«ochilgan» degani bo'lib qolgandi.

Endi belgini o'quvchi o'zi qo'yadi (Coursera naqshi). Bu xavfsiz, chunki
belgi hech qanday qulfni ochmaydi va XP bermaydi — qulflar
`courses/access_service.py` da, XP esa davomatdan keladi. Shuning uchun bu
yerdagi asosiy tekshiruvlar: ochish belgilamaydi, tugma belgilaydi, yopiq
darsni belgilab bo'lmaydi va seriya faqat bir marta yoziladi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from courses.models import (
    Assignment,
    AssignmentSubmission,
    CohortLessonRelease,
    Course,
    Lesson,
    LessonProgress,
    Module,
)
from courses.progress_service import mark_lesson_completed, unmark_lesson_completed
from users.models import LearnerStreak

User = get_user_model()


class LessonCompletionFixture:
    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        self.teacher = User.objects.create_user(
            username="tugat-teacher", email="t@example.test", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="tugat-student", email="s@example.test", password="x"
        )
        self.course = Course.objects.create(
            title="Kurs", description="d", level="beginner", instructor=self.teacher
        )
        self.module = Module.objects.create(course=self.course, title="M", order=1)
        self.first = Lesson.objects.create(module=self.module, title="Birinchi dars", order=1)
        self.second = Lesson.objects.create(module=self.module, title="Ikkinchi dars", order=2)
        self.cohort = Cohort.objects.create(
            name="G", course=self.course, start_date=self.today
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=self.today + datetime.timedelta(days=30),
        )

    def completion_url(self, lesson):
        return reverse(
            "lesson_completion",
            kwargs={"course_id": self.course.id, "lesson_id": lesson.id},
        )

    def is_completed(self, lesson):
        return LessonProgress.objects.filter(
            enrollment=self.enrollment, lesson=lesson, is_completed=True
        ).exists()


class OpeningALessonIsNotFinishingItTests(LessonCompletionFixture, TestCase):
    def test_opening_the_page_leaves_the_lesson_unmarked(self):
        self.client.force_login(self.student)

        self.client.get(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.first.id})
        )

        self.assertFalse(self.is_completed(self.first))

    def test_the_page_offers_the_button(self):
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.first.id})
        )

        self.assertContains(response, "Bajarildi deb belgilash")

    def test_pressing_the_button_marks_the_lesson(self):
        self.client.force_login(self.student)

        self.client.post(self.completion_url(self.first))

        self.assertTrue(self.is_completed(self.first))

    def test_the_mark_can_be_cleared_after_a_mistake(self):
        self.client.force_login(self.student)
        self.client.post(self.completion_url(self.first))

        self.client.post(self.completion_url(self.first), {"action": "clear"})

        self.assertFalse(self.is_completed(self.first))


class CompletionRespectsTheLocksTests(LessonCompletionFixture, TestCase):
    def test_a_lesson_the_teacher_has_not_released_cannot_be_marked(self):
        CohortLessonRelease.objects.create(
            cohort=self.cohort, lesson=self.first, is_released=True
        )
        self.client.force_login(self.student)

        self.client.post(self.completion_url(self.second))

        self.assertFalse(self.is_completed(self.second))

    def test_a_lesson_behind_an_unapproved_assignment_cannot_be_marked(self):
        Assignment.objects.create(lesson=self.first, title="Vazifa", description="d")
        self.client.force_login(self.student)

        self.client.post(self.completion_url(self.second))

        self.assertFalse(self.is_completed(self.second))

    def test_it_opens_once_the_assignment_is_approved(self):
        assignment = Assignment.objects.create(lesson=self.first, title="Vazifa", description="d")
        AssignmentSubmission.objects.create(
            assignment=assignment, student=self.student,
            status=AssignmentSubmission.STATUS_APPROVED,
        )
        self.client.force_login(self.student)

        self.client.post(self.completion_url(self.second))

        self.assertTrue(self.is_completed(self.second))

    def test_a_stranger_cannot_mark_someone_elses_lesson(self):
        outsider = User.objects.create_user(
            username="chetdagi", email="c@example.test", password="x"
        )
        self.client.force_login(outsider)

        self.client.post(self.completion_url(self.first))

        self.assertFalse(self.is_completed(self.first))

    def test_an_anonymous_visitor_is_refused(self):
        response = self.client.post(self.completion_url(self.first))

        self.assertNotEqual(response.status_code, 200)
        self.assertFalse(self.is_completed(self.first))


class CompletionAndTheDailyStreakTests(LessonCompletionFixture, TestCase):
    def test_the_first_completion_counts_as_daily_activity(self):
        mark_lesson_completed(self.enrollment, self.first)

        streak = LearnerStreak.objects.filter(user=self.student).first()
        self.assertIsNotNone(streak)

    def test_clearing_and_pressing_again_does_not_count_twice(self):
        """Aks holda bitta darsni bosib-bosib seriya to'plash mumkin bo'lardi."""
        mark_lesson_completed(self.enrollment, self.first)
        streak = LearnerStreak.objects.get(user=self.student)
        before = (streak.current_streak, streak.longest_streak, streak.last_activity_date)

        unmark_lesson_completed(self.enrollment, self.first)
        mark_lesson_completed(self.enrollment, self.first)

        streak.refresh_from_db()
        self.assertEqual(
            (streak.current_streak, streak.longest_streak, streak.last_activity_date), before
        )

    def test_the_first_completion_time_survives_a_clear(self):
        mark_lesson_completed(self.enrollment, self.first)
        first_time = LessonProgress.objects.get(
            enrollment=self.enrollment, lesson=self.first
        ).completed_at

        unmark_lesson_completed(self.enrollment, self.first)
        mark_lesson_completed(self.enrollment, self.first)

        self.assertEqual(
            LessonProgress.objects.get(
                enrollment=self.enrollment, lesson=self.first
            ).completed_at,
            first_time,
        )
