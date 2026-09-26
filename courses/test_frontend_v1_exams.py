"""I8a: real access/attempts, explicit publication and read-only V1 renderers."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from core.flags import flag_by_slug, set_flag
from courses.models import (Certificate, Course, Exam, ExamAttempt,
                            ExamResultPublication, ExamSection, ExamSectionReview,
                            Question, StudentAnswer)


class ExamV1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user('exam.teacher', 'teacher@example.test', is_staff=True)
        cls.student = User.objects.create_user('exam.student', 'student@example.test')
        cls.other = User.objects.create_user('exam.other', 'other@example.test', is_staff=True)
        cls.course = Course.objects.create(title='A1 real course', instructor=cls.teacher)
        cls.foreign = Course.objects.create(title='Hidden course', instructor=cls.other)
        cls.cohort = Cohort.objects.create(course=cls.course, name='Morning', start_date=timezone.localdate())
        cls.enrollment = Enrollment.objects.create(student=cls.student, cohort=cls.cohort, status='active')
        cls.exam = Exam.objects.create(course=cls.course, title='A1 final', exam_type='final', weight_percentage=100, max_attempts=2)
        cls.section = ExamSection.objects.create(exam=cls.exam, title='Yozish', section_type='writing', instructions='Write.', max_score=10, time_limit_minutes=17)
        cls.question = Question.objects.create(exam_section=cls.section, text='Merhaba?', points=10)

    def setUp(self):
        self.client.force_login(self.student)
        set_flag('frontend_v1_exams', enabled=True, reason='I8 acceptance')
        self.center = reverse('exam_center')
        self.detail = reverse('exam_detail', args=[self.course.pk, self.exam.pk])
        self.result = reverse('exam_result', args=[self.course.pk, self.exam.pk])

    def attempt(self, **kwargs):
        return ExamAttempt.objects.create(student=self.student, exam=self.exam, **kwargs)

    def pending(self):
        attempt = self.attempt(is_completed=True, completed_time=timezone.now(), review_notes='SECRET draft notes')
        review = ExamSectionReview.objects.create(attempt=attempt, section=self.section, awarded_score=Decimal('7.25'), feedback='SECRET section feedback')
        answer = StudentAnswer.objects.create(attempt=attempt, question=self.question, answer_text='Merhaba', awarded_score=Decimal('7.25'), grader_feedback='SECRET answer feedback', is_graded=True)
        return attempt, review, answer

    def publish(self):
        attempt, review, answer = self.pending()
        attempt.finalize_review(reviewed_by=self.teacher)
        return attempt, review, answer

    def test_flag_default_off_independent_and_reversible(self):
        self.assertFalse(flag_by_slug('frontend_v1_exams').default)
        self.assertTemplateUsed(self.client.get(self.center), 'frontend_v1/exams/center.html')
        self.assertTemplateUsed(self.client.get(reverse('dashboard')), 'users/dashboard.html')
        set_flag('frontend_v1_exams', enabled=False, reason='Rollback')
        self.assertTemplateUsed(self.client.get(self.center), 'courses/exam_center.html')

    def test_anonymous_login_redirect(self):
        self.client.logout()
        for url in (self.center, self.result, self.detail):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_navigation_no_duplicate_and_current_page(self):
        response = self.client.get(self.center)
        self.assertEqual(response.context['active_nav'], 'exam_center')
        self.assertEqual(sum(item['url'] == self.center for item in response.context['frontend_v1_nav']), 1)
        self.assertFalse(any(item['url'] == self.center for item in response.context['frontend_v1_legacy_nav']))
        self.assertContains(response, 'aria-current="page"')
        self.assertIn('no-store', response['Cache-Control'])

    def test_no_attempt_created_by_get_head_refresh_or_query(self):
        for method, url in [('get', self.center), ('head', self.center), ('get', self.center + '?start=1&exam=1'), ('get', self.detail)]:
            self.assertEqual(getattr(self.client, method)(url).status_code, 200)
        self.assertFalse(ExamAttempt.objects.exists())
        self.assertFalse(ExamSectionReview.objects.exists())
        self.assertFalse(ExamResultPublication.objects.exists())

    def test_empty_scope_does_not_offer_foreign_exams(self):
        Exam.objects.create(course=self.foreign, title='Hidden exam', exam_type='visa', weight_percentage=100)
        self.client.force_login(self.other)
        response = self.client.get(self.center)
        self.assertContains(response, 'Hozircha imtihon yo‘q')
        self.assertNotContains(response, self.exam.title)
        self.assertNotContains(response, 'Hidden exam')

    def test_inactive_enrollment_cannot_see_exam_or_result(self):
        self.pending()
        for status in ('pending', 'frozen', 'expired'):
            Enrollment.objects.filter(pk=self.enrollment.pk).update(status=status)
            self.assertNotContains(self.client.get(self.center), self.exam.title)
            self.assertEqual(self.client.get(self.result).status_code, 302)

    def test_multiple_course_memberships_do_not_duplicate_card(self):
        cohort = Cohort.objects.create(course=self.course, name='Evening', start_date=timezone.localdate())
        Enrollment.objects.create(student=self.student, cohort=cohort, status='pending')
        response = self.client.get(self.center)
        self.assertEqual(len(response.context['exams']), 1)
        self.assertContains(response, f'data-exam-id="{self.exam.pk}"', count=1)

    def test_only_own_latest_attempt_is_shown(self):
        self.attempt(is_completed=True, is_reviewed=True, score=95, passed=True)
        latest = self.attempt(attempt_number=2)
        ExamAttempt.objects.create(student=self.other, exam=self.exam, is_completed=True, is_reviewed=True, score=99, passed=True)
        response = self.client.get(self.center)
        exam = response.context['exams'][0]
        self.assertEqual(exam.latest_attempt.pk, latest.pk)
        self.assertEqual(exam.attempts_used, 2)
        self.assertContains(response, 'Jarayonda')
        self.assertNotContains(response, '95%')
        self.assertNotContains(response, '99%')

    def test_unstarted_in_progress_pending_and_reviewed_actions(self):
        response = self.client.get(self.center)
        self.assertContains(response, 'Shartlarni ko‘rish')
        self.assertContains(response, '17 daqiqa')
        attempt = self.attempt()
        self.assertContains(self.client.get(self.center), 'Davom etish')
        attempt.is_completed = True
        attempt.save(update_fields=['is_completed'])
        self.assertContains(self.client.get(self.center), 'Topshirish holatini ko‘rish')
        attempt.is_reviewed = True
        attempt.save(update_fields=['is_reviewed'])
        self.assertContains(self.client.get(self.center), 'Natijani ko‘rish')

    def test_zero_limit_no_fake_start(self):
        Exam.objects.filter(pk=self.exam.pk).update(max_attempts=0)
        response = self.client.get(self.center)
        self.assertContains(response, 'Urinishlar limiti tugagan')
        self.assertNotContains(response, 'Shartlarni ko‘rish')

    def test_zero_duration_is_not_presented_as_zero_time_available(self):
        ExamSection.objects.filter(pk=self.section.pk).update(time_limit_minutes=0)
        self.assertContains(self.client.get(self.center), 'Umumiy vaqt cheklanmagan')

    def test_pending_draft_never_reaches_either_renderer(self):
        self.pending()
        for enabled in (True, False):
            set_flag('frontend_v1_exams', enabled=enabled, reason='Publication parity')
            response = self.client.get(self.result)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'SECRET')
            self.assertEqual(response.context['section_reviews'], [])
            self.assertEqual(response.context['feedback_answers'], [])
            self.assertEqual(response.context['result']['review_notes'], '')
            self.assertIn('no-store', response['Cache-Control'])
        self.assertFalse(ExamResultPublication.objects.exists())

    def test_finalize_atomically_publishes_exact_decimal_result(self):
        attempt, _, _ = self.publish()
        response = self.client.get(self.result)
        self.assertTemplateUsed(response, 'frontend_v1/exams/result.html')
        self.assertEqual(response.context['result']['score'], Decimal('72.50'))
        for text in ('SECRET draft notes', 'SECRET section feedback', 'SECRET answer feedback'):
            self.assertContains(response, text)
        self.assertEqual(ExamResultPublication.objects.get(attempt=attempt).payload['section_reviews'][0]['awarded_score'], '7.25')

    def test_draft_edit_after_publication_cannot_change_learner_data(self):
        attempt, review, answer = self.publish()
        self.client.force_login(self.teacher)
        response = self.client.post(reverse('teacher_grade_exam', args=[attempt.pk]), {
            'action': 'save', 'review_notes': 'NEW UNPUBLISHED notes',
            f'section_score_{review.pk}': '1', f'section_feedback_{review.pk}': 'NEW UNPUBLISHED section',
            f'answer_score_{answer.pk}': '1', f'answer_feedback_{answer.pk}': 'NEW UNPUBLISHED answer',
        })
        self.assertEqual(response.status_code, 302)
        attempt.refresh_from_db()
        self.assertEqual(attempt.review_notes, 'NEW UNPUBLISHED notes')
        self.client.force_login(self.student)
        for enabled in (True, False):
            set_flag('frontend_v1_exams', enabled=enabled, reason='Draft isolation')
            response = self.client.get(self.result)
            self.assertNotContains(response, 'NEW UNPUBLISHED')
            self.assertContains(response, 'SECRET draft notes')
            self.assertContains(response, 'SECRET section feedback')
            self.assertEqual(response.context['result']['score'], Decimal('72.50'))

    def test_explicit_republication_replaces_snapshot_not_on_get(self):
        attempt, review, _ = self.publish()
        original = ExamResultPublication.objects.get(attempt=attempt).payload
        review.feedback = 'Published second version'
        review.awarded_score = 5
        review.save()
        self.client.get(self.result)
        self.assertEqual(ExamResultPublication.objects.get(attempt=attempt).payload, original)
        attempt.finalize_review(reviewed_by=self.teacher)
        self.assertEqual(ExamResultPublication.objects.filter(attempt=attempt).count(), 1)
        response = self.client.get(self.result)
        self.assertContains(response, 'Published second version')
        self.assertEqual(response.context['result']['score'], Decimal('50'))

    def test_publication_failure_rolls_back_grade(self):
        attempt, _, _ = self.pending()
        with patch('courses.models.ExamResultPublication.objects.update_or_create', side_effect=RuntimeError('storage failed')):
            with self.assertRaises(RuntimeError):
                attempt.finalize_review(reviewed_by=self.teacher)
        attempt.refresh_from_db()
        self.assertFalse(attempt.is_reviewed)
        self.assertEqual(attempt.score, 0)
        self.assertFalse(ExamResultPublication.objects.exists())
        self.assertFalse(Certificate.objects.exists())

    def test_teacher_finalize_failure_rolls_back_draft_and_grade_together(self):
        attempt, review, _ = self.pending()
        self.client.force_login(self.teacher)
        with patch('courses.models.ExamResultPublication.objects.update_or_create', side_effect=RuntimeError('storage failed')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('teacher_grade_exam', args=[attempt.pk]), {
                    'action': 'finalize', 'review_notes': 'Should rollback', f'section_score_{review.pk}': '9',
                })
        attempt.refresh_from_db()
        review.refresh_from_db()
        self.assertEqual(attempt.review_notes, 'SECRET draft notes')
        self.assertEqual(review.awarded_score, Decimal('7.25'))
        self.assertFalse(attempt.is_reviewed)

    def test_old_reviewed_attempt_has_no_unprovable_detail_backfill(self):
        attempt, _, _ = self.pending()
        ExamAttempt.objects.filter(pk=attempt.pk).update(is_reviewed=True, score=55)
        for enabled in (True, False):
            set_flag('frontend_v1_exams', enabled=enabled, reason='Historical result')
            response = self.client.get(self.result)
            self.assertNotContains(response, 'SECRET')
            self.assertEqual(response.context['result']['score'], 55)
            self.assertTrue(response.context['result']['details_unavailable'])
        self.assertFalse(ExamResultPublication.objects.exists())

    def test_revoked_review_does_not_expose_old_snapshot(self):
        attempt, _, _ = self.publish()
        ExamAttempt.objects.filter(pk=attempt.pk).update(is_reviewed=False)
        self.assertNotContains(self.client.get(self.result), 'SECRET')

    def test_wrong_course_and_foreign_results_are_inaccessible(self):
        self.publish()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.result).status_code, 302)
        self.client.force_login(self.student)
        second = Course.objects.create(title='Other enrolled course')
        cohort = Cohort.objects.create(course=second, name='Other', start_date=timezone.localdate())
        Enrollment.objects.create(student=self.student, cohort=cohort, status='active')
        self.assertEqual(self.client.get(reverse('exam_result', args=[second.pk, self.exam.pk])).status_code, 404)

    def test_missing_and_in_progress_result_redirect_to_detail(self):
        self.assertRedirects(self.client.get(self.result), self.detail)
        self.attempt()
        self.assertRedirects(self.client.get(self.result), self.detail)

    def test_retake_read_only_instructions_then_existing_start_api(self):
        attempt, review, _ = self.pending()
        review.awarded_score = 1
        review.save()
        attempt.finalize_review(reviewed_by=self.teacher)
        self.assertContains(self.client.get(self.result), f'{self.detail}?retake=1')
        self.assertRedirects(self.client.get(self.detail), self.result)
        for _ in range(2):
            self.assertEqual(self.client.get(self.detail + '?retake=1').status_code, 200)
        self.assertEqual(ExamAttempt.objects.count(), 1)
        response = self.client.post(reverse('api_exam_start', args=[self.course.pk, self.exam.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['attempt_number'], 2)
        self.assertEqual(ExamAttempt.objects.count(), 2)

    def test_retake_link_does_not_bypass_pending_passed_or_limit(self):
        attempt, _, _ = self.pending()
        for reviewed, passed, number in [(False, False, 1), (True, True, 1), (True, False, 2)]:
            ExamAttempt.objects.filter(pk=attempt.pk).update(is_reviewed=reviewed, passed=passed, attempt_number=number)
            response = self.client.get(self.result)
            self.assertFalse(response.context['can_retake'])
            self.assertRedirects(self.client.get(self.detail + '?retake=1'), self.result)

    def test_retake_still_checks_canonical_entry_policy(self):
        attempt = self.attempt(is_completed=True, is_reviewed=True)
        prerequisite = Exam.objects.create(course=self.course, title='Required earlier exam', exam_type='visa', weight_percentage=40)
        Exam.objects.filter(pk=self.exam.pk).update(prerequisite_exam=prerequisite)
        response = self.client.get(self.detail + '?retake=1')
        self.assertFalse(response.context['can_start_exam'])
        response = self.client.post(reverse('api_exam_start', args=[self.course.pk, self.exam.pk]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(ExamAttempt.objects.count(), 1)

    def test_teacher_scope_and_csrf_are_not_bypassed(self):
        attempt, _, _ = self.pending()
        url = reverse('teacher_grade_exam', args=[attempt.pk])
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url, {'action': 'finalize'}).status_code, 404)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.teacher)
        self.assertEqual(protected.post(url, {'action': 'finalize'}).status_code, 403)
        self.assertFalse(ExamResultPublication.objects.exists())

    def test_feedback_html_escaped_in_both_renderers(self):
        attempt, review, _ = self.pending()
        review.feedback = '<script>alert("draft")</script>'
        review.save()
        attempt.finalize_review(reviewed_by=self.teacher)
        for enabled in (True, False):
            set_flag('frontend_v1_exams', enabled=enabled, reason='Escaping')
            response = self.client.get(self.result)
            self.assertNotContains(response, '<script>alert("draft")</script>')
            self.assertContains(response, '&lt;script&gt;')

    def test_published_rubric_survives_content_changes(self):
        attempt, _, _ = self.publish()
        ExamSection.objects.filter(pk=self.section.pk).update(title='Changed section', max_score=100)
        Question.objects.filter(pk=self.question.pk).update(text='Changed prompt', points=100)
        response = self.client.get(self.result)
        self.assertContains(response, 'Yozish')
        self.assertContains(response, 'Merhaba?')
        self.assertNotContains(response, 'Changed section')
        self.assertNotContains(response, 'Changed prompt')

    def test_legacy_uses_published_threshold_not_changed_live_threshold(self):
        self.publish()
        Exam.objects.filter(pk=self.exam.pk).update(passing_score=90)
        set_flag('frontend_v1_exams', enabled=False, reason='Published threshold parity')
        response = self.client.get(self.result)
        self.assertEqual(response.context['result_passing_score'], 60)
        self.assertContains(response, "O'tish bali: 60%.")
        self.assertNotContains(response, "O'tish bali: 90%.")

    def test_published_zero_threshold_is_not_replaced_by_fallback(self):
        Exam.objects.filter(pk=self.exam.pk).update(passing_score=0)
        self.exam.refresh_from_db()
        self.publish()
        Exam.objects.filter(pk=self.exam.pk).update(passing_score=90)
        set_flag('frontend_v1_exams', enabled=False, reason='Zero threshold parity')
        response = self.client.get(self.result)
        self.assertEqual(response.context['result_passing_score'], 0)
        self.assertContains(response, "O'tish bali: 0%.")

    def test_legacy_without_snapshot_retains_current_threshold_fallback(self):
        self.attempt(is_completed=True, is_reviewed=True, passed=False, score=55)
        Exam.objects.filter(pk=self.exam.pk).update(passing_score=73)
        set_flag('frontend_v1_exams', enabled=False, reason='Historical threshold fallback')
        response = self.client.get(self.result)
        self.assertEqual(response.context['result_passing_score'], 73)
        self.assertContains(response, "O'tish uchun 73% kerak edi.")

    def test_public_appendix_uses_published_sections_not_live_drafts(self):
        attempt, review, _ = self.publish()
        certificate = Certificate.objects.create(student=self.student, course=self.course, final_score=Decimal('72.50'), certificate_id='I8-QA-CERT')
        review.awarded_score = Decimal('1.11')
        review.save()
        response = Client().get(reverse('certificate_appendix', args=[certificate.certificate_id]))
        self.assertContains(response, '7.25 / 10')
        self.assertNotContains(response, '1.11 / 10')
        self.assertNotContains(response, 'SECRET')

    def test_get_does_not_expire_or_restart_a_timed_out_attempt(self):
        attempt = self.attempt()
        old = timezone.now() - timedelta(days=1)
        ExamAttempt.objects.filter(pk=attempt.pk).update(start_time=old)
        self.client.get(self.center)
        attempt.refresh_from_db()
        self.assertFalse(attempt.is_completed)
        self.assertEqual(attempt.start_time, old)

    def test_no_fake_certificate_or_completion_claim_while_pending(self):
        self.pending()
        response = self.client.get(self.result)
        self.assertNotContains(response, 'Sertifikatni ko‘rish')
        self.assertFalse(Certificate.objects.exists())
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.completion_state, Enrollment.COMPLETION_STATE_IN_PROGRESS)
