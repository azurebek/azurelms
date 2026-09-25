"""I2b native/JSON adapters and canonical no-write/XP invariants."""
import json
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connections
from django.test import Client, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from core.flags import set_flag
from courses.models import Assignment, AssignmentSubmission, Choice, CohortLessonRelease, Course, Lesson, Module, Question, Quiz, QuizAttempt, QuizAnswer
from courses.submission_service import grade_quiz, review_assignment_submission, submit_assignment
from library.test_resources import PDF_BYTES, pdf_upload


def fixtures(target):
    User = get_user_model()
    target.teacher = User.objects.create_user('practice-teacher', 'p-teacher@example.test', is_staff=True)
    target.student = User.objects.create_user('practice-student', 'p-student@example.test')
    target.other = User.objects.create_user('practice-other', 'p-other@example.test')
    target.course = Course.objects.create(title='Practice course', instructor=target.teacher)
    module = Module.objects.create(course=target.course, title='Module', order=1)
    target.lesson = Lesson.objects.create(module=module, title='Practice lesson', content='<p>Real content</p>', order=1)
    target.cohort = Cohort.objects.create(course=target.course, name='Morning', start_date=timezone.localdate())
    target.enrollment = Enrollment.objects.create(student=target.student, cohort=target.cohort, status='active')
    target.assignment = Assignment.objects.create(lesson=target.lesson, title='My day', description='<p>Write in Turkish.</p>')
    target.quiz = Quiz.objects.create(lesson=target.lesson, title='Real quiz', xp_reward=20)
    target.q1 = Question.objects.create(quiz=target.quiz, text='<p>Bir?</p>')
    target.q2 = Question.objects.create(quiz=target.quiz, text='<p>İki?</p>')
    target.c1 = Choice.objects.create(question=target.q1, text='One', is_correct=True)
    target.c2 = Choice.objects.create(question=target.q2, text='Two', is_correct=True)
    target.wrong = Choice.objects.create(question=target.q2, text='Wrong')


class PracticeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures(cls)

    def setUp(self):
        directory = TemporaryDirectory(prefix='v1-practice-')
        self.addCleanup(directory.cleanup)
        override = override_settings(PRIVATE_MEDIA_ROOT=directory.name, MEDIA_ROOT=directory.name)
        override.enable()
        self.addCleanup(override.disable)
        set_flag('frontend_v1_lesson', enabled=True, reason='I2b test')
        self.client.force_login(self.student)
        args = [self.course.pk, self.lesson.pk]
        self.lesson_url = reverse('lesson_detail', args=args) + f'?cohort={self.cohort.pk}'
        self.assignment_url = reverse('assignment_submit', args=args + [self.assignment.pk]) + f'?cohort={self.cohort.pk}'
        self.quiz_url = reverse('api_quiz_submit', args=args + [self.quiz.pk]) + f'?cohort={self.cohort.pk}'

    def native_answers(self):
        return {f'answer_{self.q1.pk}': str(self.c1.pk), f'answer_{self.q2.pk}': str(self.c2.pk)}

    def test_multiple_forms_and_no_correct_choices_before_attempt(self):
        extra = Quiz.objects.create(lesson=self.lesson, title='Empty quiz')
        Assignment.objects.create(lesson=self.lesson, title='Second assignment', description='More')
        response = self.client.get(self.lesson_url + '&tab=quiz')
        self.assertTemplateUsed(response, 'frontend_v1/lesson.html')
        self.assertContains(response, 'Quiz savollari hali kiritilmagan')
        self.assertNotContains(response, 'To‘g‘ri javob</dt>')
        self.assertNotContains(response, 'is_correct')
        self.assertContains(response, str(extra.title))
        self.assertContains(self.client.get(self.lesson_url + '&tab=homework'), 'Second assignment')

    def test_empty_assignment_no_row_and_validation_keeps_text(self):
        response = self.client.post(self.assignment_url, {'answer_text': ''})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AssignmentSubmission.objects.exists())
        response = self.client.post(self.assignment_url, {
            'answer_text': '<my unsaved answer>',
            'attachment': SimpleUploadedFile('bad.exe', b'MZ-bad'),
        })
        self.assertContains(response, '&lt;my unsaved answer&gt;', status_code=400)
        self.assertContains(response, 'Faylni qayta tanlang', status_code=400)
        self.assertContains(response, reverse('lesson_detail', args=[self.course.pk, self.lesson.pk]) + '?cohort=', status_code=400)
        self.assertFalse(AssignmentSubmission.objects.exists())
        self.assertIn('no-store', response['Cache-Control'])

    def test_native_assignment_and_private_file_then_teacher_review_projection(self):
        response = self.client.post(self.assignment_url, {'answer_text': 'Ben öğrenciyim.', 'attachment': pdf_upload()})
        self.assertRedirects(response, self.lesson_url + '&tab=homework', fetch_redirect_response=False)
        submission = AssignmentSubmission.objects.get()
        file_url = reverse('submission_file', args=[submission.pk])
        response = self.client.get(self.lesson_url + '&tab=homework')
        self.assertContains(response, file_url)
        self.assertNotContains(response, submission.attachment.name)
        stream = self.client.get(file_url)
        self.assertEqual(b''.join(stream.streaming_content), PDF_BYTES)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(file_url).status_code, 404)
        self.client.force_login(self.teacher)
        response = self.client.post(reverse('teacher_grade_assignment', args=[submission.pk]), {
            'action': 'approve', 'awarded_xp': 15, 'teacher_feedback': 'Ajoyib ish!',
        })
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.student)
        response = self.client.get(self.lesson_url + '&tab=homework')
        self.assertContains(response, 'Ajoyib ish!')
        self.assertContains(response, '15 XP')
        self.assertContains(response, 'name="replace_review"')

    def test_pending_duplicate_is_noop_and_resubmit_confirmation_resets_xp_consistently(self):
        self.client.post(self.assignment_url, {'answer_text': 'first'})
        submission = AssignmentSubmission.objects.get()
        timestamp = submission.updated_at
        self.client.post(self.assignment_url, {'answer_text': 'first'})
        submission.refresh_from_db()
        self.assertEqual(submission.updated_at, timestamp)
        review_assignment_submission(submission=submission, approved=True, reviewer=self.teacher, awarded_xp=15, feedback='Good')
        response = self.client.post(self.assignment_url, {'answer_text': 'revised'})
        self.assertContains(response, 'revised', status_code=400)
        submission.refresh_from_db()
        self.assertEqual(submission.status, 'approved')
        self.client.post(self.assignment_url, {'answer_text': 'revised', 'replace_review': 'yes'})
        submission.refresh_from_db(); self.student.refresh_from_db()
        self.assertEqual((submission.status, submission.awarded_xp, self.student.total_xp), ('pending', 0, 0))
        self.assertEqual(submission.teacher_feedback, '')
        review_assignment_submission(submission=submission, approved=True, reviewer=self.teacher, awarded_xp=15)
        self.student.refresh_from_db()
        self.assertEqual(self.student.total_xp, 15)

    def test_stale_review_object_does_not_repeat_xp(self):
        submission = submit_assignment(user=self.student, assignment=self.assignment, answer_text='answer').submission
        stale = AssignmentSubmission.objects.get(pk=submission.pk)
        review_assignment_submission(submission=submission, approved=True, reviewer=self.teacher, awarded_xp=15)
        review_assignment_submission(submission=stale, approved=True, reviewer=self.teacher, awarded_xp=15)
        self.student.refresh_from_db()
        self.assertEqual(self.student.total_xp, 15)

    def test_locked_submission_preserves_own_text_without_lesson_content(self):
        CohortLessonRelease.objects.create(cohort=self.cohort, lesson=self.lesson, is_released=False)
        response = self.client.post(self.assignment_url, {'answer_text': 'keep this answer'})
        self.assertContains(response, 'keep this answer', status_code=403)
        self.assertNotContains(response, 'Real content', status_code=403)
        self.assertFalse(AssignmentSubmission.objects.exists())
        response = self.client.post(self.quiz_url, self.native_answers())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(QuizAttempt.objects.exists())

    def test_explicit_cohort_never_falls_back_and_selected_open_cohort_works(self):
        second = Cohort.objects.create(course=self.course, name='Evening', start_date=timezone.localdate())
        Enrollment.objects.create(student=self.other, cohort=second, status='active')
        CohortLessonRelease.objects.create(cohort=second, lesson=self.lesson, is_released=False)
        self.assertEqual(self.client.post(self.quiz_url, self.native_answers()).status_code, 302)
        for target in ('999999', str(second.pk), '²', '9' * 4400, ''):
            for url in (self.lesson_url, self.assignment_url, self.quiz_url):
                invalid = url.split('?')[0] + '?cohort=' + target
                response = self.client.get(invalid) if url == self.lesson_url else self.client.post(invalid, {})
                self.assertEqual(response.status_code, 404)
        self.assertEqual(QuizAttempt.objects.count(), 1)

    def test_inactive_and_foreign_user_cannot_post(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.assignment_url, {'answer_text': 'bad'}).status_code, 404)
        self.client.force_login(self.student)
        Enrollment.objects.filter(pk=self.enrollment.pk).update(status='frozen')
        self.assertEqual(self.client.post(self.quiz_url, self.native_answers()).status_code, 404)
        self.assertFalse(QuizAttempt.objects.exists())

    def test_csrf_on_both_native_forms(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        for url in (self.assignment_url, self.quiz_url):
            self.assertEqual(client.post(url, {}).status_code, 403)
        self.assertFalse(AssignmentSubmission.objects.exists())
        self.assertFalse(QuizAttempt.objects.exists())

    def test_incomplete_native_quiz_preserves_choices_without_write_until_confirmed(self):
        data = {f'answer_{self.q1.pk}': str(self.c1.pk)}
        response = self.client.post(self.quiz_url, data)
        self.assertContains(response, 'Barcha savolga javob bering', status_code=400)
        self.assertContains(response, f'value="{self.c1.pk}" data-draft-field checked', status_code=400)
        self.assertFalse(QuizAttempt.objects.exists())
        response = self.client.post(self.quiz_url, {**data, 'accept_incomplete': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(QuizAttempt.objects.get().score, 50)

    def test_native_quiz_latest_result_repeat_and_xp(self):
        self.client.post(self.quiz_url, self.native_answers())
        self.client.post(self.quiz_url, {**self.native_answers(), f'answer_{self.q2.pk}': self.wrong.pk})
        self.student.refresh_from_db()
        self.assertEqual(self.student.total_xp, 20)
        response = self.client.get(self.lesson_url + '&tab=quiz')
        self.assertContains(response, '50.00%')
        self.assertEqual(response.context['quizzes'][0].latest_attempt.pk, QuizAttempt.objects.first().pk)
        self.assertContains(response, 'Oxirgi saqlangan natija')
        self.assertFalse(self.enrollment.lesson_progress.filter(is_completed=True).exists())

    def test_bad_json_payloads_are_rejected_without_partial_attempts(self):
        invalid = [[], 'x', True, 42, {str(self.q1.pk): 'junk'}, {str(self.q1.pk): []},
                   {str(self.q1.pk): True}, {str(self.q1.pk): 1.1}, {str(self.q1.pk): self.c2.pk},
                   {'999999': self.c1.pk}, {str(self.q1.pk): '9' * 4400}]
        for answers in invalid:
            response = self.client.post(self.quiz_url, json.dumps({'answers': answers}), content_type='application/json')
            self.assertEqual(response.status_code, 400, answers)
            self.assertFalse(QuizAttempt.objects.exists())
        self.assertFalse(QuizAnswer.objects.exists())

    def test_json_and_canonical_bot_shapes_share_grade_and_delta(self):
        result = grade_quiz(user=self.student, quiz=self.quiz, answers={self.q1.pk: self.c1.pk})
        self.assertEqual((result.score, result.xp_earned), (50, 10))
        response = self.client.post(self.quiz_url, json.dumps({'answers': {str(self.q1.pk): self.c1.pk, str(self.q2.pk): self.c2.pk}}), content_type='application/json')
        self.assertEqual(response.json()['xp_earned'], 10)
        self.assertEqual(response.json()['score'], 100)

    def test_quiz_write_failure_rolls_back_attempt_answers_and_xp(self):
        with patch('users.streak.record_activity', side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):
                grade_quiz(user=self.student, quiz=self.quiz, answers={self.q1.pk: self.c1.pk})
        self.assertFalse(QuizAttempt.objects.exists())
        self.assertFalse(QuizAnswer.objects.exists())
        self.student.refresh_from_db()
        self.assertEqual(self.student.total_xp, 0)

    def test_draft_scope_changes_with_authenticated_session(self):
        first = self.client.get(self.lesson_url).context['practice_scope']
        self.client.logout(); self.client.force_login(self.student)
        second = self.client.get(self.lesson_url).context['practice_scope']
        self.assertNotEqual(first, second)

    def test_flag_off_keeps_legacy_and_json_contract(self):
        set_flag('frontend_v1_lesson', enabled=False, reason='Rollback')
        self.assertTemplateUsed(self.client.get(self.lesson_url), 'courses/lesson_detail.html')
        self.assertEqual(self.client.post(self.quiz_url, self.native_answers()).status_code, 400)
        response = self.client.post(self.quiz_url, json.dumps({'answers': {str(self.q1.pk): self.c1.pk}}), content_type='application/json')
        self.assertEqual(response.status_code, 200)


@skipUnlessDBFeature('has_select_for_update')
class PracticeConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures(self)

    def test_parallel_quiz_attempts_credit_improvement_once(self):
        barrier = Barrier(2)
        def attempt():
            try:
                user = get_user_model().objects.get(pk=self.student.pk)
                quiz = Quiz.objects.get(pk=self.quiz.pk)
                barrier.wait(timeout=10)
                return grade_quiz(user=user, quiz=quiz, answers={self.q1.pk: self.c1.pk, self.q2.pk: self.c2.pk}).xp_earned
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(attempt) for _ in range(2)]
            awarded = [future.result(timeout=20) for future in futures]
        self.assertEqual(sorted(awarded), [0, 20])
        self.student.refresh_from_db()
        self.assertEqual(self.student.total_xp, 20)
        self.assertEqual(QuizAttempt.objects.count(), 2)
