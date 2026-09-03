"""Yopiq darsga yozib bo'lmaydi — UI emas, servis qaror qiladi (A3).

Qulf ilgari faqat **ko'rsatishda** ishlardi: dars ro'yxatida ikonka, dars
sahifasiga kirishda redirect. Yozuv yo'llari esa faqat kurs obunasini
tekshirardi, ya'ni:

* web'da submit URL'iga to'g'ridan-to'g'ri POST yopiq darsga vazifa
  topshirardi va quizni baholab XP berardi;
* botda `start_*` qulfni tekshirardi, lekin `BotPendingAction` bazada
  saqlanadi — qulf o'zgargandan keyin ham topshirish davom etardi.

Bu yerdagi testlar ikkala qulf turini (drip release va ketma-ketlik) va
ikkala adapterni qamraydi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bot.services import submit_assignment_answer
from cohorts.models import Cohort, Enrollment
from courses.models import (
    Assignment, AssignmentSubmission, Choice, CohortLessonRelease, Course,
    Lesson, Module, Question, Quiz, QuizAttempt,
)
from courses.submission_service import grade_quiz, submit_assignment

User = get_user_model()


class LockedLessonWriteGateTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="gate-teacher", email="gate-teacher@example.test",
            password="x", is_staff=True,
        )
        self.student = User.objects.create_user(
            username="gate-student", email="gate-student@example.test", password="x",
        )
        self.course = Course.objects.create(
            title="Gate kursi", description="d", level="beginner",
            instructor=self.teacher,
        )
        module = Module.objects.create(course=self.course, title="M1", order=1)
        self.lesson_one = Lesson.objects.create(
            module=module, title="Dars 1", content="<p>a</p>", order=1, xp_reward=10
        )
        self.lesson_two = Lesson.objects.create(
            module=module, title="Dars 2", content="<p>b</p>", order=2, xp_reward=10
        )
        self.assignment_one = Assignment.objects.create(
            lesson=self.lesson_one, title="V1", description="d", max_xp=20
        )
        self.assignment_two = Assignment.objects.create(
            lesson=self.lesson_two, title="V2", description="d", max_xp=20
        )
        self.quiz_two = Quiz.objects.create(
            lesson=self.lesson_two, title="Q2", xp_reward=15
        )
        question = Question.objects.create(quiz=self.quiz_two, text="2+2?", points=5)
        self.right = Choice.objects.create(question=question, text="4", is_correct=True)
        Choice.objects.create(question=question, text="5", is_correct=False)
        self.question = question

        self.cohort = Cohort.objects.create(
            name="Gate guruhi", course=self.course, start_date=timezone.now().date()
        )
        Enrollment.objects.create(
            student=self.student, cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
        )

    def _lock_by_drip(self):
        """Faqat 1-darsni ochamiz — bitta qator butun kursni drip'ga o'tkazadi."""
        CohortLessonRelease.objects.create(
            cohort=self.cohort, lesson=self.lesson_one, is_released=True
        )

    # ---------------------------------------------------------------- servis

    def test_service_refuses_an_assignment_for_a_drip_locked_lesson(self):
        self._lock_by_drip()

        result = submit_assignment(
            user=self.student, assignment=self.assignment_two, answer_text="javob"
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "locked")
        self.assertFalse(
            AssignmentSubmission.objects.filter(
                assignment=self.assignment_two, student=self.student
            ).exists()
        )

    def test_service_refuses_an_assignment_when_the_previous_one_is_unapproved(self):
        """Ikkinchi qulf: oldingi dars vazifasi tasdiqlanmagan."""
        AssignmentSubmission.objects.create(
            assignment=self.assignment_one, student=self.student,
            answer_text="x", status=AssignmentSubmission.STATUS_PENDING,
        )

        result = submit_assignment(
            user=self.student, assignment=self.assignment_two, answer_text="javob"
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "locked")

    def test_service_still_accepts_an_open_lesson(self):
        """Gate qulflanmagan darsni to'sib qo'ymasligi kerak."""
        self._lock_by_drip()

        result = submit_assignment(
            user=self.student, assignment=self.assignment_one, answer_text="javob"
        )

        self.assertTrue(result.ok, result.message)

    def test_service_refuses_to_grade_a_quiz_in_a_locked_lesson(self):
        self._lock_by_drip()

        result = grade_quiz(
            user=self.student, quiz=self.quiz_two,
            answers={str(self.question.id): self.right.id},
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "locked")
        self.assertFalse(QuizAttempt.objects.filter(student=self.student).exists())

    # ------------------------------------------------------------------- web

    def test_a_direct_post_cannot_submit_into_a_locked_lesson(self):
        """UI formani ko'rsatmaydi — bu himoya emas edi."""
        self._lock_by_drip()
        self.client.force_login(self.student)

        response = self.client.post(
            reverse(
                "assignment_submit",
                kwargs={
                    "course_id": self.course.id,
                    "lesson_id": self.lesson_two.id,
                    "assignment_id": self.assignment_two.id,
                },
            ),
            {"answer_text": "chetlab o'tish"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            AssignmentSubmission.objects.filter(
                assignment=self.assignment_two, student=self.student
            ).exists()
        )

    def test_a_direct_post_cannot_grade_a_quiz_in_a_locked_lesson(self):
        self._lock_by_drip()
        self.client.force_login(self.student)

        response = self.client.post(
            reverse(
                "api_quiz_submit",
                kwargs={
                    "course_id": self.course.id,
                    "lesson_id": self.lesson_two.id,
                    "quiz_id": self.quiz_two.id,
                },
            ),
            data='{"answers": {"%s": %s}}' % (self.question.id, self.right.id),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(QuizAttempt.objects.filter(student=self.student).exists())

    # ------------------------------------------------------------------- bot

    def test_the_bot_cannot_submit_into_a_locked_lesson_either(self):
        """`start_*` qulfni tekshiradi, ammo pending action bazada qoladi."""
        self._lock_by_drip()

        result = submit_assignment_answer(
            self.student, self.assignment_two.id, text="chetlab o'tish"
        )

        self.assertFalse(result.ok)
        self.assertFalse(
            AssignmentSubmission.objects.filter(
                assignment=self.assignment_two, student=self.student
            ).exists()
        )
