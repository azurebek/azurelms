from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from courses.models import Course, Exam, ExamAttempt, ExamSection, ExamSectionReview, Module
from users.models import Notification


User = get_user_model()


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
