import datetime
import json
import base64
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
        self.assertContains(response, "Umumiy progress")
        self.assertContains(response, "Dars materiallari")
        self.assertContains(response, "Videodars")

    def test_lesson_detail_visit_marks_lesson_progress(self):
        response = self.client.get(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.lesson.id})
        )

        self.assertEqual(response.status_code, 200)
        progress = LessonProgress.objects.filter(
            enrollment__student=self.student,
            enrollment__cohort__course=self.course,
            lesson=self.lesson,
            is_completed=True,
        ).first()
        self.assertIsNotNone(progress)


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
        self.assertContains(unlocked_response, "Current lesson")

    def test_sidebar_shows_lock_icon_for_unreleased_lessons(self):
        CohortLessonRelease.objects.create(cohort=self.cohort, lesson=self.lesson_1, is_released=True)

        response = self.client.get(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.lesson_1.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bi-lock-fill")
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


class MultiCohortStudySelectionTests(TestCase):
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
            status="active",
        )
        self.client.force_login(self.student)

    def test_course_study_redirect_preserves_requested_cohort(self):
        response = self.client.get(
            reverse("course_study", kwargs={"course_id": self.course.id}),
            {"cohort": self.cohort_one.id},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f"{reverse('lesson_detail', kwargs={'course_id': self.course.id, 'lesson_id': self.lesson_1.id})}?cohort={self.cohort_one.id}",
            response.url,
        )

    def test_lesson_access_and_progress_follow_selected_cohort(self):
        CohortLessonRelease.objects.create(cohort=self.cohort_one, lesson=self.lesson_1, is_released=True)
        CohortLessonRelease.objects.create(cohort=self.cohort_two, lesson=self.lesson_1, is_released=True)
        CohortLessonRelease.objects.create(cohort=self.cohort_two, lesson=self.lesson_2, is_released=True)

        locked_response = self.client.get(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.lesson_2.id}),
            {"cohort": self.cohort_one.id},
        )
        self.assertEqual(locked_response.status_code, 302)
        self.assertIn(
            f"{reverse('lesson_detail', kwargs={'course_id': self.course.id, 'lesson_id': self.lesson_1.id})}?cohort={self.cohort_one.id}",
            locked_response.url,
        )

        unlocked_response = self.client.get(
            reverse("lesson_detail", kwargs={"course_id": self.course.id, "lesson_id": self.lesson_2.id}),
            {"cohort": self.cohort_two.id},
        )
        self.assertEqual(unlocked_response.status_code, 200)
        self.assertContains(
            unlocked_response,
            f"{reverse('lesson_detail', kwargs={'course_id': self.course.id, 'lesson_id': self.lesson_1.id})}?cohort={self.cohort_two.id}",
        )
        self.assertTrue(
            LessonProgress.objects.filter(
                enrollment=self.enrollment_two,
                lesson=self.lesson_2,
                is_completed=True,
            ).exists()
        )
        self.assertFalse(
            LessonProgress.objects.filter(
                enrollment=self.enrollment_one,
                lesson=self.lesson_2,
                is_completed=True,
            ).exists()
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
