import datetime
import json
import base64
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.test.utils import override_settings
from django.utils import timezone
from PIL import Image

from cohorts.models import Cohort, Enrollment
from courses.completion_service import evaluate_course_completion
from courses.models import (
    Assignment,
    AssignmentSubmission,
    Choice,
    CohortLessonRelease,
    Course,
    Exam,
    ExamAttempt,
    ExamSection,
    ExamSectionReview,
    Lesson,
    LessonProgress,
    Module,
    Question,
    Quiz,
    ReadingAcceptedAnswer,
    ReadingItem,
    ReadingOption,
    ReadingPassage,
    ReadingResponse,
    ReadingTask,
)
from users.models import Notification


User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)


class ExamReviewFlowTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='teacher',
            email='teacher@example.com',
            password='testpass123',
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@example.com',
            password='testpass123',
        )
        self.course = Course.objects.create(
            title='Turk tili A1',
            description='Test course',
            instructor=self.instructor,
            level='beginner',
        )
        Module.objects.create(course=self.course, title='1-modul', order=1)
        self.cohort = Cohort.objects.create(
            name='A1 Cohort',
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
        )

        self.visa = Exam.objects.create(
            course=self.course,
            title='Visa',
            exam_type='visa',
            weight_percentage=40,
            passing_score=60,
        )
        self.final = Exam.objects.create(
            course=self.course,
            title='Final',
            exam_type='final',
            weight_percentage=60,
            passing_score=60,
        )
        self.visa_section = ExamSection.objects.create(
            exam=self.visa,
            title='Visa section',
            section_type='reading',
            instructions='Instructions',
            max_score=50,
            time_limit_minutes=30,
            order=1,
        )
        self.final_section = ExamSection.objects.create(
            exam=self.final,
            title='Final section',
            section_type='writing',
            instructions='Instructions',
            max_score=50,
            time_limit_minutes=30,
            order=1,
        )

    def _create_attempt_with_review(self, exam, section, awarded_score):
        attempt = ExamAttempt.objects.create(
            student=self.student,
            exam=exam,
            is_completed=True,
        )
        ExamSectionReview.objects.create(
            attempt=attempt,
            section=section,
            awarded_score=awarded_score,
        )
        return attempt

    def test_certificate_and_notification_created_only_after_review_approval(self):
        visa_attempt = self._create_attempt_with_review(self.visa, self.visa_section, 40)
        final_attempt = self._create_attempt_with_review(self.final, self.final_section, 45)

        certificate, created = visa_attempt.finalize_review(reviewed_by=self.instructor)
        self.assertIsNone(certificate)
        self.assertFalse(created)
        self.assertEqual(self.student.course_certificates.count(), 0)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.completion_state, Enrollment.COMPLETION_STATE_IN_PROGRESS)

        certificate, created = final_attempt.finalize_review(reviewed_by=self.instructor)
        self.assertIsNotNone(certificate)
        self.assertTrue(created)
        self.assertEqual(self.student.course_certificates.count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 1)
        self.enrollment.refresh_from_db()
        self.assertEqual(
            self.enrollment.completion_state,
            Enrollment.COMPLETION_STATE_PROMOTION_READY,
        )
        self.assertIsNotNone(self.enrollment.completed_at)
        self.assertIsNotNone(self.enrollment.promotion_ready_at)

    def test_review_approval_sets_attempt_score_and_marks_reviewed(self):
        attempt = self._create_attempt_with_review(self.visa, self.visa_section, 35)

        attempt.finalize_review(reviewed_by=self.instructor)
        attempt.refresh_from_db()

        self.assertTrue(attempt.is_reviewed)
        self.assertEqual(float(attempt.score), 70.0)
        self.assertTrue(attempt.passed)

    def test_certificate_appendix_view_shows_section_scores(self):
        visa_attempt = self._create_attempt_with_review(self.visa, self.visa_section, 42)
        final_attempt = self._create_attempt_with_review(self.final, self.final_section, 44)
        visa_attempt.finalize_review(reviewed_by=self.instructor)
        certificate, _ = final_attempt.finalize_review(reviewed_by=self.instructor)

        response = self.client.get(
            reverse('certificate_appendix', kwargs={'certificate_id': certificate.certificate_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sertifikat Ilovasi')
        self.assertContains(response, 'Visa section')
        self.assertContains(response, 'Final section')


class QuizXpAwardTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="quiz-student",
            email="quiz-student@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="Quiz XP Course",
            description="Quiz XP test",
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="1-modul", order=1)
        self.lesson = Lesson.objects.create(module=self.module, title="1-dars", order=1)
        self.quiz = Quiz.objects.create(title="XP Quiz", lesson=self.lesson, xp_reward=20)
        self.question_one = Question.objects.create(quiz=self.quiz, text="Savol 1", points=1)
        self.question_two = Question.objects.create(quiz=self.quiz, text="Savol 2", points=1)
        self.choice_one = Choice.objects.create(question=self.question_one, text="To'g'ri 1", is_correct=True)
        self.choice_two = Choice.objects.create(question=self.question_two, text="To'g'ri 2", is_correct=True)
        Choice.objects.create(question=self.question_one, text="Noto'g'ri 1", is_correct=False)
        self.wrong_choice_two = Choice.objects.create(question=self.question_two, text="Noto'g'ri 2", is_correct=False)
        self.cohort = Cohort.objects.create(
            name="Quiz Cohort",
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )
        Enrollment.objects.create(student=self.student, cohort=self.cohort, status="active")
        self.client.force_login(self.student)
        self.url = reverse(
            "api_quiz_submit",
            kwargs={
                "course_id": self.course.id,
                "lesson_id": self.lesson.id,
                "quiz_id": self.quiz.id,
            },
        )

    def submit_answers(self, answers):
        return self.client.post(
            self.url,
            data=json.dumps({"answers": answers}),
            content_type="application/json",
        )

    def test_repeat_submission_only_awards_missing_xp(self):
        first = self.submit_answers(
            {
                str(self.question_one.id): self.choice_one.id,
                str(self.question_two.id): self.wrong_choice_two.id,
            }
        )
        self.student.refresh_from_db()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["xp_earned"], 10)
        self.assertEqual(first.json()["attempt_xp"], 10)
        self.assertEqual(self.student.total_xp, 10)

        second = self.submit_answers(
            {
                str(self.question_one.id): self.choice_one.id,
                str(self.question_two.id): self.choice_two.id,
            }
        )
        self.student.refresh_from_db()
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["xp_earned"], 10)
        self.assertEqual(second.json()["attempt_xp"], 20)
        self.assertEqual(self.student.total_xp, 20)

        third = self.submit_answers(
            {
                str(self.question_one.id): self.choice_one.id,
                str(self.question_two.id): self.choice_two.id,
            }
        )
        self.student.refresh_from_db()
        self.assertEqual(third.status_code, 200)
        self.assertEqual(third.json()["xp_earned"], 0)
        self.assertEqual(third.json()["attempt_xp"], 20)
        self.assertEqual(self.student.total_xp, 20)


class ExamAttemptPolicyTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="attempt-teacher",
            email="attempt-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="attempt-student",
            email="attempt-student@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="Attempt Course",
            description="Attempt policy test",
            instructor=self.instructor,
            level="beginner",
        )
        self.cohort = Cohort.objects.create(
            name="Attempt Cohort",
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )
        Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
        )
        self.exam = Exam.objects.create(
            course=self.course,
            title="Final",
            exam_type="final",
            weight_percentage=100,
            passing_score=60,
            max_attempts=2,
        )
        self.section = ExamSection.objects.create(
            exam=self.exam,
            title="Essay",
            section_type="writing",
            instructions="Write something",
            max_score=50,
            time_limit_minutes=1,
            order=1,
        )
        self.start_url = reverse(
            "api_exam_start",
            kwargs={"course_id": self.course.id, "exam_id": self.exam.id},
        )
        self.client.force_login(self.student)

    def _create_attempt(self, **overrides):
        data = {
            "student": self.student,
            "exam": self.exam,
            "attempt_number": 1,
        }
        data.update(overrides)
        attempt = ExamAttempt.objects.create(**data)
        if attempt.is_completed:
            attempt.ensure_section_reviews()
        return attempt

    def test_failed_review_allows_next_attempt_until_limit(self):
        self._create_attempt(
            is_completed=True,
            is_reviewed=True,
            passed=False,
            score=45,
            completed_time=timezone.now(),
        )

        response = self.client.post(self.start_url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["attempt_number"], 2)
        self.assertEqual(ExamAttempt.objects.filter(student=self.student, exam=self.exam).count(), 2)

    def test_pending_review_blocks_new_attempt(self):
        self._create_attempt(
            is_completed=True,
            is_reviewed=False,
            passed=False,
            completed_time=timezone.now(),
        )

        response = self.client.post(self.start_url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "pending_review")
        self.assertEqual(ExamAttempt.objects.filter(student=self.student, exam=self.exam).count(), 1)

    def test_passed_attempt_blocks_new_attempt(self):
        self._create_attempt(
            is_completed=True,
            is_reviewed=True,
            passed=True,
            score=82,
            completed_time=timezone.now(),
        )

        response = self.client.post(self.start_url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "already_passed")

    def test_attempt_limit_blocks_after_last_failed_attempt(self):
        self._create_attempt(
            attempt_number=1,
            is_completed=True,
            is_reviewed=True,
            passed=False,
            score=30,
            completed_time=timezone.now() - datetime.timedelta(days=1),
        )
        self._create_attempt(
            attempt_number=2,
            is_completed=True,
            is_reviewed=True,
            passed=False,
            score=45,
            completed_time=timezone.now(),
        )

        response = self.client.post(self.start_url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "attempt_limit_reached")

    def test_time_limit_expiry_auto_submits_existing_attempt(self):
        attempt = self._create_attempt(is_completed=False, is_reviewed=False, passed=False)
        attempt.start_time = timezone.now() - datetime.timedelta(minutes=2)
        attempt.save(update_fields=["start_time"])

        response = self.client.post(self.start_url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "pending_review")
        attempt.refresh_from_db()
        self.assertTrue(attempt.is_completed)
        self.assertFalse(attempt.is_reviewed)
        self.assertIsNotNone(attempt.completed_time)


class ReadingSectionEngineTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="reading-teacher",
            email="reading-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="reading-student",
            email="reading-student@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="Reading Course",
            description="Reading engine tests",
            instructor=self.instructor,
            level="beginner",
        )
        self.cohort = Cohort.objects.create(
            name="Reading Cohort",
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )
        Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
        )
        self.exam = Exam.objects.create(
            course=self.course,
            title="Reading Final",
            exam_type="final",
            weight_percentage=100,
            passing_score=60,
            max_attempts=2,
        )
        self.section = ExamSection.objects.create(
            exam=self.exam,
            title="Reading section",
            section_type="reading",
            instructions="Read carefully",
            reading_text="<p>Legacy passage</p>",
            max_score=20,
            time_limit_minutes=20,
            order=1,
        )
        self.passage = ReadingPassage.objects.create(
            section=self.section,
            title="Passage 1",
            body="<p>Yusuf kutubxonaga kirdi.</p>",
            paragraph_labels=["A", "B"],
            order=1,
        )
        self.start_url = reverse(
            "api_exam_start",
            kwargs={"course_id": self.course.id, "exam_id": self.exam.id},
        )
        self.section_state_url = reverse(
            "api_exam_section_state",
            kwargs={
                "course_id": self.course.id,
                "exam_id": self.exam.id,
                "section_id": self.section.id,
            },
        )
        self.save_url = reverse(
            "api_exam_save",
            kwargs={"course_id": self.course.id, "exam_id": self.exam.id},
        )
        self.flag_url = reverse(
            "api_exam_review_flag",
            kwargs={"course_id": self.course.id, "exam_id": self.exam.id},
        )
        self.submit_url = reverse(
            "api_exam_submit",
            kwargs={"course_id": self.course.id, "exam_id": self.exam.id},
        )
        self.client.force_login(self.student)

    def _start_attempt(self):
        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, 200)
        return ExamAttempt.objects.get(id=response.json()["attempt_id"])

    def _create_single_choice_item(self):
        task = ReadingTask.objects.create(
            section=self.section,
            passage=self.passage,
            title="Single choice",
            task_type="single_choice",
            order=1,
        )
        item = ReadingItem.objects.create(
            task=task,
            prompt="<p>Yusuf qayerga kirdi?</p>",
            short_label="01",
            order=1,
            points=2,
        )
        ReadingOption.objects.create(item=item, label="A", text="Kutubxona", order=1, is_correct=True)
        ReadingOption.objects.create(item=item, label="B", text="Park", order=2, is_correct=False)
        return item

    def _create_multiple_choice_item(self):
        task = ReadingTask.objects.create(
            section=self.section,
            passage=self.passage,
            title="Multi choice",
            task_type="multiple_choice",
            max_selections_per_item=2,
            order=2,
        )
        item = ReadingItem.objects.create(
            task=task,
            prompt="<p>Ikki to'g'ri javobni tanlang.</p>",
            short_label="02",
            order=1,
            points=3,
        )
        option_a = ReadingOption.objects.create(item=item, label="A", text="Kutubxona", order=1, is_correct=True)
        option_b = ReadingOption.objects.create(item=item, label="B", text="Yangi kitob", order=2, is_correct=True)
        option_c = ReadingOption.objects.create(item=item, label="C", text="Bozor", order=3, is_correct=False)
        return item, option_a, option_b, option_c

    def _create_matching_item(self):
        task = ReadingTask.objects.create(
            section=self.section,
            passage=self.passage,
            title="Matching headings",
            task_type="matching",
            display_variant="matching_headings",
            order=3,
        )
        option_a = ReadingOption.objects.create(task=task, label="A", option_key="a", text="Kutubxona", order=1)
        option_b = ReadingOption.objects.create(task=task, label="B", option_key="b", text="Ertalabki kelish", order=2)
        item = ReadingItem.objects.create(
            task=task,
            prompt="<p>Paragraph A uchun headingni tanlang.</p>",
            short_label="03",
            order=1,
            points=2,
        )
        ReadingAcceptedAnswer.objects.create(item=item, value="b", order=1)
        return item, option_a, option_b

    def _create_tfng_item(self):
        task = ReadingTask.objects.create(
            section=self.section,
            passage=self.passage,
            title="TFNG",
            task_type="true_false_not_given",
            order=4,
        )
        option_true = ReadingOption.objects.create(task=task, label="True", option_key="true", text="True", order=1)
        option_false = ReadingOption.objects.create(task=task, label="False", option_key="false", text="False", order=2)
        option_ng = ReadingOption.objects.create(task=task, label="NG", option_key="not_given", text="Not Given", order=3)
        item = ReadingItem.objects.create(
            task=task,
            prompt="<p>Yusuf bozorga bordi.</p>",
            short_label="04",
            order=1,
            points=2,
        )
        ReadingAcceptedAnswer.objects.create(item=item, value="not_given", order=1)
        return item, option_true, option_false, option_ng

    def _create_text_input_item(self):
        task = ReadingTask.objects.create(
            section=self.section,
            passage=self.passage,
            title="Sentence completion",
            task_type="text_input",
            display_variant="sentence_completion",
            max_words_per_answer=2,
            order=5,
        )
        item = ReadingItem.objects.create(
            task=task,
            prompt="<p>Yusuf ____ga kirdi.</p>",
            short_label="05",
            order=1,
            points=2,
        )
        ReadingAcceptedAnswer.objects.create(item=item, value="kutubxona", order=1)
        return item

    def _create_structured_gap_fill_item(self):
        task = ReadingTask.objects.create(
            section=self.section,
            passage=self.passage,
            title="Summary completion",
            task_type="structured_gap_fill",
            display_variant="summary_completion",
            max_words_per_answer=2,
            order=6,
        )
        item = ReadingItem.objects.create(
            task=task,
            prompt="<p>Yusuf yangi ____ oldi.</p>",
            short_label="06",
            order=1,
            points=2,
        )
        ReadingAcceptedAnswer.objects.create(item=item, value="kitob", order=1)
        return item

    def test_reading_section_state_returns_passages_tasks_and_question_map(self):
        self._create_single_choice_item()
        self._create_matching_item()
        self._start_attempt()

        response = self.client.get(self.section_state_url)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "success")
        self.assertEqual(len(payload["passages"]), 1)
        self.assertEqual(len(payload["tasks"]), 2)
        self.assertEqual(payload["tasks"][0]["task_type"], "single_choice")
        self.assertEqual(payload["tasks"][1]["task_type"], "matching")
        self.assertEqual(payload["state"]["counts"]["current"], 1)
        self.assertEqual(len(payload["state"]["question_map"]), 2)

    def test_single_choice_answer_auto_grades_and_updates_question_map(self):
        item = self._create_single_choice_item()
        correct_option = item.options.get(is_correct=True)
        self._start_attempt()

        response = self.client.post(
            self.save_url,
            data=json.dumps({"reading_item_id": item.id, "option_id": correct_option.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["saved_response"]["awarded_score"], 2.0)
        self.assertEqual(payload["section_state"]["counts"]["done"], 1)
        reading_response = ReadingResponse.objects.get(item=item)
        self.assertEqual(reading_response.selected_option_id, correct_option.id)
        self.assertTrue(reading_response.is_graded)

    def test_multiple_choice_requires_exact_correct_set(self):
        item, option_a, option_b, option_c = self._create_multiple_choice_item()
        self._start_attempt()

        wrong = self.client.post(
            self.save_url,
            data=json.dumps({"reading_item_id": item.id, "option_ids": [option_a.id, option_c.id]}),
            content_type="application/json",
        )
        self.assertEqual(wrong.status_code, 200)
        self.assertEqual(wrong.json()["saved_response"]["awarded_score"], 0.0)

        correct = self.client.post(
            self.save_url,
            data=json.dumps({"reading_item_id": item.id, "option_ids": [option_a.id, option_b.id]}),
            content_type="application/json",
        )
        self.assertEqual(correct.status_code, 200)
        self.assertEqual(correct.json()["saved_response"]["awarded_score"], 3.0)

    def test_matching_and_tfng_tasks_use_shared_options_and_accepted_answer_keys(self):
        matching_item, _, matching_correct = self._create_matching_item()
        tfng_item, _, _, not_given = self._create_tfng_item()
        self._start_attempt()

        matching_response = self.client.post(
            self.save_url,
            data=json.dumps({"reading_item_id": matching_item.id, "option_id": matching_correct.id}),
            content_type="application/json",
        )
        tfng_response = self.client.post(
            self.save_url,
            data=json.dumps({"reading_item_id": tfng_item.id, "option_id": not_given.id}),
            content_type="application/json",
        )

        self.assertEqual(matching_response.status_code, 200)
        self.assertEqual(tfng_response.status_code, 200)
        self.assertEqual(matching_response.json()["saved_response"]["awarded_score"], 2.0)
        self.assertEqual(tfng_response.json()["saved_response"]["awarded_score"], 2.0)

    def test_text_tasks_enforce_word_limit_and_auto_grade(self):
        text_item = self._create_text_input_item()
        structured_item = self._create_structured_gap_fill_item()
        self._start_attempt()

        too_long = self.client.post(
            self.save_url,
            data=json.dumps({"reading_item_id": text_item.id, "text_answer": "juda uzun javob"}),
            content_type="application/json",
        )
        self.assertEqual(too_long.status_code, 400)
        self.assertContains(too_long, "2 ta so'zdan oshmasligi kerak", status_code=400)

        text_ok = self.client.post(
            self.save_url,
            data=json.dumps({"reading_item_id": text_item.id, "text_answer": "kutubxona"}),
            content_type="application/json",
        )
        structured_ok = self.client.post(
            self.save_url,
            data=json.dumps({"reading_item_id": structured_item.id, "text_answer": "kitob"}),
            content_type="application/json",
        )

        self.assertEqual(text_ok.status_code, 200)
        self.assertEqual(structured_ok.status_code, 200)
        self.assertEqual(text_ok.json()["saved_response"]["awarded_score"], 2.0)
        self.assertEqual(structured_ok.json()["saved_response"]["awarded_score"], 2.0)

    def test_review_flag_endpoint_marks_item_for_follow_up(self):
        item = self._create_single_choice_item()
        self._start_attempt()

        response = self.client.post(
            self.flag_url,
            data=json.dumps({"reading_item_id": item.id, "flagged": True}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_flagged_for_review"])
        reading_response = ReadingResponse.objects.get(item=item)
        self.assertTrue(reading_response.is_flagged_for_review)

    def test_submit_for_review_prefills_section_score_from_reading_responses(self):
        item_one = self._create_single_choice_item()
        item_two = self._create_structured_gap_fill_item()
        self._start_attempt()

        self.client.post(
            self.save_url,
            data=json.dumps(
                {
                    "reading_item_id": item_one.id,
                    "option_id": item_one.options.get(is_correct=True).id,
                }
            ),
            content_type="application/json",
        )
        self.client.post(
            self.save_url,
            data=json.dumps({"reading_item_id": item_two.id, "text_answer": "kitob"}),
            content_type="application/json",
        )

        submit_response = self.client.post(self.submit_url)

        self.assertEqual(submit_response.status_code, 200)
        attempt = ExamAttempt.objects.get(student=self.student, exam=self.exam)
        attempt.refresh_from_db()
        self.assertTrue(attempt.is_completed)
        review = ExamSectionReview.objects.get(attempt=attempt, section=self.section)
        self.assertEqual(float(review.awarded_score), 4.0)


class ExamEntryPolicyTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="policy-teacher",
            email="policy-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="policy-student",
            email="policy-student@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="Policy Course",
            description="Exam policy test",
            instructor=self.instructor,
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="1-modul", order=1)
        self.lesson_1 = Lesson.objects.create(module=self.module, title="1-dars", order=1)
        self.lesson_2 = Lesson.objects.create(module=self.module, title="2-dars", order=2)
        self.assignment = Assignment.objects.create(
            lesson=self.lesson_1,
            title="Policy homework",
            description="<p>Homework</p>",
            max_xp=20,
        )
        self.cohort = Cohort.objects.create(
            name="Policy Cohort",
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
        )
        self.visa = Exam.objects.create(
            course=self.course,
            title="Policy Visa",
            exam_type="visa",
            weight_percentage=40,
            passing_score=60,
        )
        self.final = Exam.objects.create(
            course=self.course,
            title="Policy Final",
            exam_type="final",
            weight_percentage=60,
            passing_score=60,
            prerequisite_exam=self.visa,
            requires_all_assignments_approved=True,
            minimum_lesson_completion_percent=100,
        )
        ExamSection.objects.create(
            exam=self.visa,
            title="Visa section",
            section_type="reading",
            instructions="Read",
            max_score=50,
            order=1,
        )
        ExamSection.objects.create(
            exam=self.final,
            title="Final section",
            section_type="writing",
            instructions="Write",
            max_score=50,
            order=1,
        )
        self.client.force_login(self.student)
        self.start_url = reverse(
            "api_exam_start",
            kwargs={"course_id": self.course.id, "exam_id": self.final.id},
        )

    def test_exam_start_blocks_until_prerequisite_exam_passed(self):
        response = self.client.post(self.start_url)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "prerequisite_exam")

        visa_attempt = ExamAttempt.objects.create(
            student=self.student,
            exam=self.visa,
            is_completed=True,
            is_reviewed=True,
            passed=True,
            score=80,
            completed_time=timezone.now(),
        )
        visa_attempt.ensure_section_reviews()
        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            answer_text="Javob",
            status=AssignmentSubmission.STATUS_APPROVED,
        )
        LessonProgress.objects.create(enrollment=self.enrollment, lesson=self.lesson_1, is_completed=True)
        LessonProgress.objects.create(enrollment=self.enrollment, lesson=self.lesson_2, is_completed=True)

        response = self.client.post(self.start_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["attempt_number"], 1)

    def test_exam_start_blocks_until_assignment_and_lesson_requirements_met(self):
        ExamAttempt.objects.create(
            student=self.student,
            exam=self.visa,
            is_completed=True,
            is_reviewed=True,
            passed=True,
            score=80,
            completed_time=timezone.now(),
        ).ensure_section_reviews()

        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "assignment_prerequisite")

        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            answer_text="Approved answer",
            status=AssignmentSubmission.STATUS_APPROVED,
        )

        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "lesson_completion_prerequisite")

        LessonProgress.objects.create(enrollment=self.enrollment, lesson=self.lesson_1, is_completed=True)
        LessonProgress.objects.create(enrollment=self.enrollment, lesson=self.lesson_2, is_completed=True)

        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, 200)


class CertificatePolicyTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="cert-policy-teacher",
            email="cert-policy-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="cert-policy-student",
            email="cert-policy-student@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="Certificate Policy Course",
            description="Certificate policy test",
            instructor=self.instructor,
            level="beginner",
            certificate_requires_all_assignments_approved=True,
        )
        self.module = Module.objects.create(course=self.course, title="1-modul", order=1)
        self.lesson = Lesson.objects.create(module=self.module, title="1-dars", order=1)
        self.assignment = Assignment.objects.create(
            lesson=self.lesson,
            title="Certificate homework",
            description="<p>Homework</p>",
            max_xp=20,
        )
        self.cohort = Cohort.objects.create(
            name="Certificate Cohort",
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
        )
        self.visa = Exam.objects.create(
            course=self.course,
            title="Certificate Visa",
            exam_type="visa",
            weight_percentage=40,
            passing_score=60,
        )
        self.final = Exam.objects.create(
            course=self.course,
            title="Certificate Final",
            exam_type="final",
            weight_percentage=60,
            passing_score=60,
        )
        self.visa_section = ExamSection.objects.create(
            exam=self.visa,
            title="Visa section",
            section_type="reading",
            instructions="Read",
            max_score=50,
            order=1,
        )
        self.final_section = ExamSection.objects.create(
            exam=self.final,
            title="Final section",
            section_type="writing",
            instructions="Write",
            max_score=50,
            order=1,
        )

    def _create_reviewed_attempt(self, exam, section, score):
        attempt = ExamAttempt.objects.create(
            student=self.student,
            exam=exam,
            is_completed=True,
            completed_time=timezone.now(),
        )
        ExamSectionReview.objects.create(
            attempt=attempt,
            section=section,
            awarded_score=score,
        )
        return attempt

    def test_certificate_waits_until_course_policy_is_satisfied(self):
        visa_attempt = self._create_reviewed_attempt(self.visa, self.visa_section, 40)
        final_attempt = self._create_reviewed_attempt(self.final, self.final_section, 45)

        visa_attempt.finalize_review(reviewed_by=self.instructor)
        certificate, created = final_attempt.finalize_review(reviewed_by=self.instructor)

        self.assertIsNone(certificate)
        self.assertFalse(created)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.completion_state, Enrollment.COMPLETION_STATE_IN_PROGRESS)

        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            answer_text="Done",
            status=AssignmentSubmission.STATUS_APPROVED,
        )

        certificate, created, enrollment = evaluate_course_completion(
            student=self.student,
            course=self.course,
        )

        self.assertIsNotNone(certificate)
        self.assertTrue(created)
        self.assertEqual(enrollment.id, self.enrollment.id)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.completion_state, Enrollment.COMPLETION_STATE_PROMOTION_READY)


class CourseDetailPageRenderTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="detail-teacher",
            email="detail-teacher@example.com",
            password="testpass123",
            first_name="Azure",
        )
        self.course = Course.objects.create(
            title="Detail Course",
            description="<p>Professional course detail content.</p>",
            instructor=self.instructor,
            level="beginner",
            duration=24,
            price=350000,
        )
        module = Module.objects.create(course=self.course, title="1-modul", order=1)
        Lesson.objects.create(module=module, title="Boshlanish darsi", order=1)

    def test_course_detail_page_renders_redesigned_sections(self):
        response = self.client.get(reverse("course_detail", kwargs={"pk": self.course.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)
        self.assertContains(response, "Dastur")
        self.assertContains(response, "O'qituvchi")


class CourseGradientCoverTests(TestCase):
    def test_gradient_cover_keeps_only_center_title_text(self):
        course = Course.objects.create(
            title="Turk tili B2",
            description="Gradient cover test",
            level="advanced",
            cover_mode="gradient",
            gradient_preset="midnight_wave",
            gradient_cover_label="Mukammal (C1-C2)",
        )

        prefix = "data:image/svg+xml;base64,"
        self.assertTrue(course.cover_media_url.startswith(prefix))
        svg = base64.b64decode(course.cover_media_url[len(prefix):]).decode("utf-8")

        self.assertIn("Turk tili B2", svg)
        self.assertNotIn("Mukammal (C1-C2)", svg)
        self.assertNotIn("AZURELMS COURSE", svg)


class LessonDetailPageRenderTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="lesson-teacher",
            email="lesson-teacher@example.com",
            password="testpass123",
            first_name="Aziz",
        )
        self.student = User.objects.create_user(
            username="lesson-student",
            email="lesson-student@example.com",
            password="testpass123",
            first_name="Ali",
        )
        self.course = Course.objects.create(
            title="Lesson Flow Course",
            description="<p>Structured lesson flow.</p>",
            instructor=self.instructor,
            level="beginner",
            duration=18,
        )
        self.module = Module.objects.create(course=self.course, title="1-modul", order=1)
        self.lesson = Lesson.objects.create(
            module=self.module,
            title="Boshlanish darsi",
            order=1,
            video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            content="<p>Dars bayoni</p>",
        )
        Lesson.objects.create(module=self.module, title="Keyingi dars", order=2)
        Assignment.objects.create(
            lesson=self.lesson,
            title="Uyga vazifa",
            description="<p>Vazifa matni</p>",
            max_xp=30,
        )
        quiz = Quiz.objects.create(title="Lesson Quiz", lesson=self.lesson, xp_reward=20)
        question = Question.objects.create(quiz=quiz, text="Savol", points=1)
        Choice.objects.create(question=question, text="To'g'ri", is_correct=True)
        Choice.objects.create(question=question, text="Noto'g'ri", is_correct=False)
        cohort = Cohort.objects.create(
            name="Lesson Cohort",
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )
        Enrollment.objects.create(student=self.student, cohort=cohort, status="active")
        self.client.force_login(self.student)

    def test_lesson_detail_page_renders_redesigned_workspace(self):
        response = self.client.get(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.lesson.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.lesson.title)
        self.assertContains(response, "Notelar")
        self.assertContains(response, "Videodars")

    def test_lesson_detail_visit_does_not_mark_lesson_progress(self):
        """Ochish o'rganish emas.

        Ilgari sahifani ochishning o'zi darsni tugatilgan deb belgilardi,
        ya'ni chap ustundagi ro'yxatni bosib chiqqan o'quvchi hamma darsni
        yashil qilib qo'yardi va foiz haqiqatni ko'rsatmasdi.
        """
        response = self.client.get(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.lesson.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            LessonProgress.objects.filter(
                enrollment__student=self.student,
                enrollment__cohort__course=self.course,
                lesson=self.lesson,
                is_completed=True,
            ).exists()
        )


class LessonAccessFlowTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="drip-teacher",
            email="drip-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="drip-student",
            email="drip-student@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="Drip Course",
            description="Drip access test",
            instructor=self.instructor,
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="1-modul", order=1)
        self.lesson_1 = Lesson.objects.create(module=self.module, title="1-dars", order=1)
        self.lesson_2 = Lesson.objects.create(module=self.module, title="2-dars", order=2)
        self.lesson_3 = Lesson.objects.create(module=self.module, title="3-dars", order=3)
        self.assignment = Assignment.objects.create(
            lesson=self.lesson_1,
            title="Uyga vazifa",
            description="<p>Topshiriq</p>",
            max_xp=20,
        )
        self.cohort = Cohort.objects.create(
            name="Drip Cohort",
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )
        Enrollment.objects.create(student=self.student, cohort=self.cohort, status="active")
        self.client.force_login(self.student)

    def test_next_lesson_stays_locked_until_previous_assignment_is_approved(self):
        CohortLessonRelease.objects.create(cohort=self.cohort, lesson=self.lesson_1, is_released=True)
        CohortLessonRelease.objects.create(cohort=self.cohort, lesson=self.lesson_2, is_released=True)

        locked_response = self.client.get(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.lesson_2.id})
        )
        self.assertEqual(locked_response.status_code, 302)
        self.assertIn(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.lesson_1.id}),
            locked_response.url,
        )

        AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            answer_text="Javob",
            status=AssignmentSubmission.STATUS_APPROVED,
        )
        unlocked_response = self.client.get(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.lesson_2.id})
        )
        self.assertEqual(unlocked_response.status_code, 200)
        self.assertContains(unlocked_response, self.lesson_2.title)

    def test_sidebar_shows_lock_icon_for_unreleased_lessons(self):
        CohortLessonRelease.objects.create(cohort=self.cohort, lesson=self.lesson_1, is_released=True)

        response = self.client.get(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.lesson_1.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bi-lock")
        self.assertContains(response, "o&#x27;qituvchi tomonidan ochilmagan")

    def test_assignment_submission_endpoint_creates_pending_submission(self):
        CohortLessonRelease.objects.create(cohort=self.cohort, lesson=self.lesson_1, is_released=True)

        response = self.client.post(
            reverse(
                "assignment_submit",
                kwargs={
                    "course_id": self.course.id,
                    "lesson_id": self.lesson_1.id,
                    "assignment_id": self.assignment.id,
                },
            ),
            data={"answer_text": "Ustoz, vazifa bajarildi"},
        )

        self.assertEqual(response.status_code, 302)
        submission = AssignmentSubmission.objects.get(assignment=self.assignment, student=self.student)
        self.assertEqual(submission.status, AssignmentSubmission.STATUS_PENDING)
        self.assertEqual(submission.answer_text, "Ustoz, vazifa bajarildi")


class CourseEnrollmentSelectionTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username="multi-teacher",
            email="multi-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="multi-student",
            email="multi-student@example.com",
            password="testpass123",
        )
        self.course = Course.objects.create(
            title="Shared Course",
            description="Multi cohort study flow test",
            instructor=self.instructor,
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="1-modul", order=1)
        self.lesson_1 = Lesson.objects.create(module=self.module, title="1-dars", order=1)
        self.lesson_2 = Lesson.objects.create(module=self.module, title="2-dars", order=2)
        self.cohort_one = Cohort.objects.create(
            name="1-guruh",
            course=self.course,
            start_date=datetime.date(2026, 3, 1),
        )
        self.cohort_two = Cohort.objects.create(
            name="2-guruh",
            course=self.course,
            start_date=datetime.date(2026, 3, 15),
        )
        self.enrollment_one = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort_one,
            status="active",
        )
        self.enrollment_two = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort_two,
            status="frozen",
        )
        self.client.force_login(self.student)

    def test_second_active_enrollment_for_same_course_is_not_allowed(self):
        with self.assertRaisesMessage(
            ValidationError,
            "Talabada ushbu kurs uchun allaqachon faol enrollment mavjud.",
        ):
            Enrollment.objects.create(
                student=self.student,
                cohort=self.cohort_two,
                status="active",
            )

    def test_course_study_redirect_ignores_requested_inactive_same_course_history(self):
        response = self.client.get(
            reverse("course_study", kwargs={"course_id": self.course.id}),
            {"cohort": self.cohort_two.id},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f"{reverse('lesson_detail', kwargs={'course_id': self.course.id, 'lesson_id': self.lesson_1.id})}?cohort={self.cohort_one.id}",
            response.url,
        )

    def test_course_study_redirect_preserves_requested_active_cohort(self):
        response = self.client.get(
            reverse("course_study", kwargs={"course_id": self.course.id}),
            {"cohort": self.cohort_one.id},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f"{reverse('lesson_detail', kwargs={'course_id': self.course.id, 'lesson_id': self.lesson_1.id})}?cohort={self.cohort_one.id}",
            response.url,
        )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CourseCoverImageTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(
            username='cover-teacher',
            email='cover-teacher@example.com',
            password='testpass123',
        )

    def _build_uploaded_image(self, size=(700, 1400), color=(20, 118, 203)):
        buffer = BytesIO()
        Image.new("RGB", size, color).save(buffer, format="PNG")
        return SimpleUploadedFile("portrait-cover.png", buffer.getvalue(), content_type="image/png")

    def test_uploaded_image_is_normalized_to_standard_cover_size(self):
        course = Course.objects.create(
            title='Turk tili B1',
            description='Cover normalization test',
            instructor=self.instructor,
            level='intermediate',
            cover_mode='image',
            thumbnail=self._build_uploaded_image(),
        )

        course.thumbnail.open("rb")
        with Image.open(course.thumbnail) as normalized:
            self.assertEqual(normalized.size, Course.STANDARD_COVER_SIZE)

    def test_uploaded_image_cover_enables_text_overlay(self):
        course = Course.objects.create(
            title='Turk tili A2',
            description='Overlay test',
            instructor=self.instructor,
            level='beginner',
            cover_mode='image',
            thumbnail=self._build_uploaded_image(size=(1400, 700), color=(184, 134, 11)),
        )

        self.assertTrue(course.show_cover_text_overlay)
        response = self.client.get(reverse('courses'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'course-cover-overlay--showcase')
        self.assertContains(response, course.cover_display_title)
