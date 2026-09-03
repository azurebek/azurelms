"""Oltin oqim uchdan-uchgacha: bitta o'quvchining haftasi (A3 acceptance).

`03-mahsulot-backlog.md` A3 dan qolgan band: *"test cohortda end-to-end"* va
*"adapter parity contract"*. Mavjud testlar oqimning bo'laklarini alohida
qamraydi (davomat parity, sessiya atomikligi, dars release, grade→learner,
checkout parity), ammo **bitta o'quvchini boshidan oxirigacha olib
o'tadigan** yo'l yo'q edi.

Farqi bor. Bo'lak testlar har servis o'z ishini qilishini isbotlaydi;
bu yerdagi test qadamlar **bir-biriga ulanishini** va har qadamda web bilan
Telegram bir xil haqiqatni ko'rsatishini isbotlaydi. Aynan shu ulanishlarda
nuqson topilgan edi — baholangan vazifa learnerga yetib bormasdi, davomat
ikki xil hisoblanardi, yopiq darsga yozib bo'lardi.

Yurib chiqiladigan yo'l:

    release → o'qish → vazifa → review → keyingi dars ochiladi → quiz → XP

Har qadamdan keyin ikkala adapter so'roq qilinadi. "Servis to'g'ri qaror
qildi" va "adapter o'sha qarorni ko'rsatdi" bir xil narsa emas.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bot.models import TelegramOutbox
from bot.services import (
    answer_quiz_question, start_quiz, student_course_map, student_open_lesson,
    submit_assignment_answer,
)
from cohorts.models import Cohort, Enrollment
from courses.access_service import build_lesson_access_bundle
from courses.models import (
    Assignment, AssignmentSubmission, Choice, Course, Lesson, LessonProgress,
    Module, Question, Quiz,
)
from courses.release_service import set_lesson_release
from courses.submission_service import review_assignment_submission

User = get_user_model()


class GoldenFlowEndToEndTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="flow-teacher", email="flow-teacher@example.test",
            password="x", is_staff=True,
        )
        self.student = User.objects.create_user(
            username="flow-student", email="flow-student@example.test",
            password="x", telegram_id=770001,
        )
        self.course = Course.objects.create(
            title="Oltin oqim kursi", description="d", level="beginner",
            instructor=self.teacher,
        )
        module = Module.objects.create(course=self.course, title="M1", order=1)
        self.lesson_one = Lesson.objects.create(
            module=module, title="Dars 1", content="<p>birinchi</p>",
            order=1, xp_reward=10,
        )
        self.lesson_two = Lesson.objects.create(
            module=module, title="Dars 2", content="<p>ikkinchi</p>",
            order=2, xp_reward=10,
        )
        self.assignment = Assignment.objects.create(
            lesson=self.lesson_one, title="Vazifa 1", description="d", max_xp=30
        )
        self.quiz = Quiz.objects.create(
            lesson=self.lesson_two, title="Quiz 2", xp_reward=20
        )
        self.question = Question.objects.create(
            quiz=self.quiz, text="2+2?", points=5
        )
        self.right = Choice.objects.create(
            question=self.question, text="4", is_correct=True
        )
        Choice.objects.create(question=self.question, text="5", is_correct=False)

        self.cohort = Cohort.objects.create(
            name="Oltin guruh", course=self.course,
            start_date=timezone.now().date(),
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
        )

    # ------------------------------------------------------------ yordamchi

    def _web_lock_state(self, lesson):
        bundle = build_lesson_access_bundle(self.course, self.student, self.enrollment)
        return bundle["lesson_access_map"][lesson.id]

    def _bot_lock_state(self, lesson):
        data = student_course_map(self.student, self.course.id)
        for lessons in data["modules"].values():
            for item in lessons:
                if item["id"] == lesson.id:
                    return item
        self.fail(f"Bot xaritasida dars topilmadi: {lesson.title}")

    def _assert_both_surfaces_agree(self, lesson, *, expected_open):
        """Parity shartnomasi: web nima desa, bot ham shuni deydi."""
        web = self._web_lock_state(lesson)
        bot = self._bot_lock_state(lesson)
        self.assertEqual(web["is_accessible"], expected_open, f"web: {lesson.title}")
        self.assertEqual(bot["locked"], not expected_open, f"bot: {lesson.title}")
        if not expected_open:
            # Sabab ham ko'chishi kerak — "yopiq" o'zi o'quvchiga nima
            # qilishini aytmaydi.
            self.assertTrue(bot["lock_reason"], "bot sababsiz qulf ko'rsatdi")
            self.assertEqual(bot["lock_reason"], web["lock_reason"])

    # ------------------------------------------------------------ oltin oqim

    def test_a_learner_walks_the_whole_week(self):
        # --- 1. O'qituvchi birinchi darsni ochadi -------------------------
        # Bitta release qatori butun kursni drip rejimiga o'tkazadi, ya'ni
        # 2-dars shu qadamning o'zidayoq yopiladi.
        set_lesson_release(
            cohort=self.cohort, lesson=self.lesson_one, released=True,
            actor=self.teacher, note="Hafta boshlandi",
        )

        self._assert_both_surfaces_agree(self.lesson_one, expected_open=True)
        self._assert_both_surfaces_agree(self.lesson_two, expected_open=False)

        # --- 2. O'quvchi darsni botda ochadi ------------------------------
        opened = student_open_lesson(self.student, self.lesson_one.id)
        self.assertTrue(opened.ok, opened.message)
        self.assertTrue(
            LessonProgress.objects.filter(
                enrollment=self.enrollment, lesson=self.lesson_one, is_completed=True
            ).exists(),
            "dars ochilgani progress sifatida yozilmadi",
        )

        # --- 3. Vazifani botda topshiradi ---------------------------------
        submitted = submit_assignment_answer(
            self.student, self.assignment.id, text="Mening javobim"
        )
        self.assertTrue(submitted.ok, submitted.message)

        submission = AssignmentSubmission.objects.get(
            assignment=self.assignment, student=self.student
        )
        self.assertEqual(submission.status, AssignmentSubmission.STATUS_PENDING)

        # Web ham xuddi shu topshiriqni ko'radi — bot alohida holat yaratmadi.
        self.client.force_login(self.teacher)
        queue = self.client.get(reverse("teacher_grading"))
        self.assertEqual(queue.status_code, 200)
        self.assertContains(queue, self.assignment.title)

        # --- 4. Tekshiruvgacha 2-dars yopiq qoladi ------------------------
        self._assert_both_surfaces_agree(self.lesson_two, expected_open=False)

        # --- 5. O'qituvchi tasdiqlaydi ------------------------------------
        xp_before = User.objects.get(pk=self.student.pk).total_xp
        review_assignment_submission(
            submission=submission, approved=True, reviewer=self.teacher,
            feedback="Yaxshi", awarded_xp=25,
        )

        submission.refresh_from_db()
        self.assertEqual(submission.status, AssignmentSubmission.STATUS_APPROVED)
        self.assertEqual(
            User.objects.get(pk=self.student.pk).total_xp, xp_before + 25,
            "o'qituvchi bergan XP o'quvchiga yetib bormadi",
        )
        self.assertTrue(
            TelegramOutbox.objects.filter(telegram_id=self.student.telegram_id).exists(),
            "hukm o'zgardi, ammo o'quvchiga xabar navbatga tushmadi",
        )

        # --- 6. Vazifa tasdiqlandi, lekin drip hali ochmagan ---------------
        # Ikki qulf mustaqil: ketma-ketlik ochildi, release hali yo'q.
        self._assert_both_surfaces_agree(self.lesson_two, expected_open=False)
        self.assertIn("ochilmagan", self._web_lock_state(self.lesson_two)["lock_reason"])

        # --- 7. O'qituvchi ikkinchi darsni ochadi --------------------------
        set_lesson_release(
            cohort=self.cohort, lesson=self.lesson_two, released=True,
            actor=self.teacher, note="Keyingi mavzu",
        )
        self._assert_both_surfaces_agree(self.lesson_two, expected_open=True)

        # --- 8. Quizni botda yechadi --------------------------------------
        started = start_quiz(self.student, self.quiz.id)
        self.assertTrue(started.ok, started.message)

        xp_before_quiz = User.objects.get(pk=self.student.pk).total_xp
        finished = answer_quiz_question(
            self.student, self.quiz.id, self.question.id, self.right.id
        )
        self.assertTrue(finished.ok, finished.message)
        self.assertTrue(finished.finished)
        self.assertEqual(finished.score, 100.0)
        self.assertEqual(
            User.objects.get(pk=self.student.pk).total_xp,
            xp_before_quiz + finished.xp_earned,
        )

    # -------------------------------------------------- teskari yo'nalishlar

    def test_closing_a_lesson_again_closes_it_on_both_surfaces(self):
        """Release qaytarib olinsa, ikkala yuza ham darhol yopilishi kerak."""
        set_lesson_release(
            cohort=self.cohort, lesson=self.lesson_one, released=True,
            actor=self.teacher,
        )
        self._assert_both_surfaces_agree(self.lesson_one, expected_open=True)

        set_lesson_release(
            cohort=self.cohort, lesson=self.lesson_one, released=False,
            actor=self.teacher, note="Xato ochildi",
        )

        self._assert_both_surfaces_agree(self.lesson_one, expected_open=False)
        self.assertFalse(student_open_lesson(self.student, self.lesson_one.id).ok)

    def test_an_expired_enrollment_closes_the_whole_course_on_both_surfaces(self):
        set_lesson_release(
            cohort=self.cohort, lesson=self.lesson_one, released=True,
            actor=self.teacher,
        )
        self.enrollment.status = Enrollment.STATUS_EXPIRED
        self.enrollment.save(update_fields=["status"])
        self.enrollment = None

        bundle = build_lesson_access_bundle(self.course, self.student, None)
        self.assertFalse(bundle["lesson_access_map"][self.lesson_one.id]["is_accessible"])
        self.assertTrue(self._bot_lock_state(self.lesson_one)["locked"])
        self.assertFalse(
            submit_assignment_answer(self.student, self.assignment.id, text="x").ok
        )
