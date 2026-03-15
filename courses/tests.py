import datetime
import json
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.test.utils import override_settings
from PIL import Image

from cohorts.models import Cohort, Enrollment
from courses.models import (
    Choice,
    Course,
    Exam,
    ExamAttempt,
    ExamSection,
    ExamSectionReview,
    Lesson,
    Module,
    Question,
    Quiz,
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

        certificate, created = final_attempt.finalize_review(reviewed_by=self.instructor)
        self.assertIsNotNone(certificate)
        self.assertTrue(created)
        self.assertEqual(self.student.course_certificates.count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 1)

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
        self.assertContains(response, "AzureLMS Signature Course")
        self.assertContains(response, "Faqat video emas, to'liq o'quv sistemasi")
        self.assertContains(response, "Kursni olib boradigan o'qituvchi")


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
