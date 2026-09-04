import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from cohorts.models import Cohort, Enrollment
from cohorts.attendance_service import upsert_attendance_and_xp
from courses.models import (
    Assignment,
    Choice,
    Course,
    Lesson,
    Module,
    Question,
    Quiz,
)
from courses.submission_service import grade_quiz, submit_assignment
from courses.progress_service import mark_lesson_completed
from users.models import LearnerStreak


User = get_user_model()


class StreakWiringTests(TestCase):
    """Har malakali harakat canonical `record_activity` ni chaqiradi.

    Seriya mantig'i alohida unit-testlangan; bu yerda faqat ULANISH
    tekshiriladi — har harakatdan keyin seriya haqiqatan oshadimi.
    """

    def setUp(self):
        self.student = User.objects.create_user(
            username="wire-student", email="wire@example.test", password="x"
        )
        self.instructor = User.objects.create_user(
            username="wire-teacher", email="wire-t@example.test", password="x", is_staff=True
        )
        self.course = Course.objects.create(
            title="C", description="d", instructor=self.instructor, level="beginner"
        )
        self.module = Module.objects.create(course=self.course, title="M", order=1)
        self.lesson = Lesson.objects.create(module=self.module, title="L", order=1)
        self.cohort = Cohort.objects.create(
            name="G", course=self.course, start_date=datetime.date(2026, 3, 1)
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE
        )

    def _current(self):
        streak = LearnerStreak.objects.filter(user=self.student).first()
        return streak.current_streak if streak else 0

    def test_lesson_completion_advances_streak(self):
        self.assertEqual(self._current(), 0)
        mark_lesson_completed(self.enrollment, self.lesson)
        self.assertEqual(self._current(), 1)

    def test_assignment_submission_advances_streak(self):
        assignment = Assignment.objects.create(lesson=self.lesson, title="A", description="d")
        result = submit_assignment(user=self.student, assignment=assignment, answer_text="javob")
        self.assertTrue(result.ok)
        self.assertEqual(self._current(), 1)

    def test_quiz_grading_advances_streak(self):
        quiz = Quiz.objects.create(lesson=self.lesson, title="Q", xp_reward=10)
        question = Question.objects.create(quiz=quiz, text="2+2?")
        correct = Choice.objects.create(question=question, text="4", is_correct=True)
        Choice.objects.create(question=question, text="5", is_correct=False)

        result = grade_quiz(user=self.student, quiz=quiz, answers={str(question.id): correct.id})
        self.assertTrue(result.ok)
        self.assertEqual(self._current(), 1)

    def test_present_attendance_advances_streak(self):
        upsert_attendance_and_xp(
            enrollment=self.enrollment,
            lesson=self.lesson,
            date=datetime.date(2026, 3, 5),
            status="present",
            marked_by=self.instructor,
        )
        streak = LearnerStreak.objects.get(user=self.student)
        self.assertEqual(streak.current_streak, 1)
        self.assertEqual(streak.last_activity_date, datetime.date(2026, 3, 5))

    def test_absent_attendance_does_not_advance_streak(self):
        upsert_attendance_and_xp(
            enrollment=self.enrollment,
            lesson=self.lesson,
            date=datetime.date(2026, 3, 5),
            status="absent",
            marked_by=self.instructor,
        )
        self.assertEqual(self._current(), 0)

    def test_two_actions_same_day_count_once(self):
        assignment = Assignment.objects.create(lesson=self.lesson, title="A", description="d")
        submit_assignment(user=self.student, assignment=assignment, answer_text="javob")
        mark_lesson_completed(self.enrollment, self.lesson)
        streak = LearnerStreak.objects.get(user=self.student)
        self.assertEqual(streak.current_streak, 1)
        self.assertEqual(streak.total_active_days, 1)
