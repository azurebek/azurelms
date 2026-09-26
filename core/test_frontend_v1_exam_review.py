"""I8c: native review, draft/publication boundary and serialized stale forms."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connections
from django.test import Client, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from core.flags import flag_by_slug, set_flag
from courses.models import Course, Exam, ExamAttempt, ExamSection, ExamSectionReview, Question, StudentAnswer, ExamResultPublication


def fixtures(cls):
    User = get_user_model()
    cls.teacher = User.objects.create_user('review.teacher', 'teacher@example.test', is_staff=True)
    cls.student = User.objects.create_user('review.student', 'student@example.test')
    cls.other = User.objects.create_user('review.other', 'other@example.test', is_staff=True)
    cls.course = Course.objects.create(title='Turk tili A1', instructor=cls.teacher)
    cls.exam = Exam.objects.create(course=cls.course, title='Yakuniy imtihon', exam_type='final', weight_percentage=100)
    cls.section = ExamSection.objects.create(exam=cls.exam, title='Yozish', section_type='writing', max_score=10)
    cls.question = Question.objects.create(exam_section=cls.section, text='Kendinizi tanıtın.', points=10)
    cls.attempt = ExamAttempt.objects.create(exam=cls.exam, student=cls.student, is_completed=True, completed_time=timezone.now())
    cls.review = ExamSectionReview.objects.create(attempt=cls.attempt, section=cls.section, awarded_score=3, feedback='Old section')
    cls.answer = StudentAnswer.objects.create(attempt=cls.attempt, question=cls.question, answer_text='<learner text>', awarded_score=3, grader_feedback='Old answer')


class ExamTeacherV1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures(cls)

    def setUp(self):
        set_flag('frontend_v1_exam_review', enabled=True, reason='I8c test')
        self.client.force_login(self.teacher)
        self.url = reverse('teacher_grade_exam', args=[self.attempt.pk])

    def payload(self, action='save', **changes):
        page = self.client.get(self.url)
        form = page.context['publish_form' if action == 'finalize' else 'review_form']
        data = {name: form[name].value() for name in form.fields}
        data.update(v1_exam_review='1', action=action, confirm_scope='on')
        data.update(changes)
        return data

    def test_default_flag_off_rollback_independent_no_get_writes(self):
        self.assertFalse(flag_by_slug('frontend_v1_exam_review').default)
        self.review.delete()
        for method in ('get', 'head'):
            response = getattr(self.client, method)(self.url)
            self.assertTemplateUsed(response, 'frontend_v1/teacher/grade_exam.html')
            self.assertIn('no-store', response['Cache-Control'])
        self.assertFalse(ExamSectionReview.objects.exists())
        self.assertFalse(ExamResultPublication.objects.exists())
        set_flag('frontend_v1_exam_review', enabled=False, reason='Rollback')
        self.assertTemplateUsed(self.client.get(self.url), 'teacher/grade_exam.html')

    def test_readonly_answers_escaped_private_audio_no_raw_key(self):
        self.answer.audio_key = 'private/speaking/synthetic.wav'
        self.answer.save()
        response = self.client.get(self.url)
        self.assertContains(response, '&lt;learner text&gt;')
        self.assertNotContains(response, self.answer.audio_key)
        self.assertContains(response, reverse('exam_answer_audio', args=[self.answer.pk]))
        self.assertContains(response, 'preload="none"')

    def test_scope_roles_and_unsubmitted(self):
        for user in (self.other, self.student):
            self.client.force_login(user)
            for method in ('get', 'post'):
                response = getattr(self.client, method)(self.url)
                self.assertEqual(response.status_code, 404 if user.is_staff else 302)
        self.client.force_login(self.teacher)
        ExamAttempt.objects.filter(pk=self.attempt.pk).update(is_completed=False)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_csrf_and_flag_disabled_inflight_fail_closed(self):
        data = self.payload()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.teacher)
        self.assertEqual(client.post(self.url, data).status_code, 403)
        set_flag('frontend_v1_exam_review', enabled=False, reason='Rollback')
        self.assertEqual(self.client.post(self.url, data).status_code, 400)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.review_revision, 0)

    def test_save_native_prg_preserves_scope_and_no_publication(self):
        data = self.payload(**{f'score_{self.section.pk}': '7.25', f'answer_score_{self.answer.pk}': '6.5', 'review_notes': 'New draft'})
        url = self.url + '?return_status=all&exams_page=2'
        self.assertRedirects(self.client.post(url, data), url)
        self.review.refresh_from_db(); self.answer.refresh_from_db(); self.attempt.refresh_from_db()
        self.assertEqual(self.review.awarded_score, Decimal('7.25'))
        self.assertEqual(self.answer.awarded_score, Decimal('6.5'))
        self.assertEqual(self.attempt.review_notes, 'New draft')
        self.assertEqual(self.attempt.review_revision, 1)
        self.assertFalse(ExamResultPublication.objects.exists())

    def test_publish_only_saved_values_then_republish_existing_canonical(self):
        data = self.payload('finalize', review_notes='DO NOT PUBLISH unsaved', **{f'score_{self.section.pk}': '10'})
        self.assertRedirects(self.client.post(self.url, data), self.url)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.score, 30)
        self.assertEqual(self.attempt.review_notes, '')
        original = ExamResultPublication.objects.get(attempt=self.attempt).payload
        self.client.post(self.url, self.payload(review_notes='New draft'))
        self.assertEqual(ExamResultPublication.objects.get(attempt=self.attempt).payload, original)
        self.client.post(self.url, self.payload('finalize'))
        self.assertNotEqual(ExamResultPublication.objects.get(attempt=self.attempt).payload, original)

    def test_replayed_save_and_publish_are_409_no_reexecution(self):
        for action in ('save', 'finalize'):
            data = self.payload(action)
            self.assertEqual(self.client.post(self.url, data).status_code, 302)
            self.attempt.refresh_from_db(); revision = self.attempt.review_revision
            self.assertEqual(self.client.post(self.url, data).status_code, 409)
            self.attempt.refresh_from_db(); self.assertEqual(self.attempt.review_revision, revision)

    def test_invalid_scores_are_atomic_and_preserve_bound_draft(self):
        for value in ('NaN', 'Infinity', '-1', '11', '3.456', '', 'bad'):
            response = self.client.post(self.url, self.payload(review_notes='<keep>', **{f'score_{self.section.pk}': value}))
            self.assertContains(response, '&lt;keep&gt;', status_code=400)
            self.assertFalse(response.context['review_form']['confirm_scope'].value())
        self.attempt.refresh_from_db(); self.review.refresh_from_db()
        self.assertEqual((self.attempt.review_revision, self.review.awarded_score), (0, 3))

    def test_action_revision_confirmation_required(self):
        for changes in ({'action': 'delete'}, {'confirm_scope': ''}, {'revision': ''}):
            response = self.client.post(self.url, self.payload(**changes))
            self.assertIn(response.status_code, (400, 409))
        self.attempt.refresh_from_db(); self.assertEqual(self.attempt.review_revision, 0)

    def test_stale_draft_preserved_fresh_saved_values_and_new_consent(self):
        old = self.payload(review_notes='My unsaved words')
        self.client.post(self.url, self.payload(**{f'feedback_{self.section.pk}': 'New server feedback'}))
        response = self.client.post(self.url, old)
        self.assertContains(response, 'My unsaved words', status_code=409)
        self.assertContains(response, 'New server feedback', status_code=409)
        self.assertFalse(response.context['review_form']['confirm_scope'].value())
        self.assertNotEqual(response.context['review_form']['revision'].value(), old['revision'])

    def test_cross_user_and_attempt_snapshot_rejected(self):
        data = self.payload()
        owner = get_user_model().objects.create_superuser('owner', 'owner@example.test', 'test')
        self.client.force_login(owner)
        self.assertEqual(self.client.post(self.url, data).status_code, 409)
        self.client.force_login(self.teacher)
        other = ExamAttempt.objects.create(exam=self.exam, student=self.student, attempt_number=2, is_completed=True)
        self.assertEqual(self.client.post(reverse('teacher_grade_exam', args=[other.pk]), data).status_code, 409)

    def test_changed_rubric_or_answer_invalidates_snapshot(self):
        data = self.payload()
        self.question.points = 9; self.question.save()
        self.assertEqual(self.client.post(self.url, data).status_code, 409)
        data = self.payload()
        self.answer.answer_text = 'New submitted answer'; self.answer.save()
        self.assertEqual(self.client.post(self.url, data).status_code, 409)

    def test_legacy_notes_only_aba_and_admin_publish_advance_revision(self):
        data = self.payload()
        set_flag('frontend_v1_exam_review', enabled=False, reason='Legacy writer')
        with patch('django.utils.timezone.now', return_value=timezone.now()):
            self.client.post(self.url, {'action': 'save', 'review_notes': 'B'})
            self.client.post(self.url, {'action': 'save', 'review_notes': ''})
        set_flag('frontend_v1_exam_review', enabled=True, reason='Back')
        self.assertEqual(self.client.post(self.url, data).status_code, 409)
        data = self.payload()
        self.attempt.finalize_review(reviewed_by=self.teacher)
        self.assertEqual(self.client.post(self.url, data).status_code, 409)

    def test_failure_rolls_back_scores_revision_and_publication(self):
        data = self.payload('finalize')
        with patch('courses.models.ExamResultPublication.objects.update_or_create', side_effect=RuntimeError('synthetic')):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url, data)
        self.attempt.refresh_from_db()
        self.assertEqual((self.attempt.review_revision, self.attempt.is_reviewed), (0, False))

    def test_safe_queue_return_no_arbitrary_redirect(self):
        page = self.client.get(self.url + '?return_status=all&exams_page=2&next=https://evil.example')
        self.assertContains(page, '?status=all&amp;exams_page=2')
        self.assertNotContains(page, 'evil.example')


class ExamTeacherConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_two_teachers_same_revision_one_write_one_conflict(self):
        fixtures(self)
        set_flag('frontend_v1_exam_review', enabled=True, reason='PG race')
        url = reverse('teacher_grade_exam', args=[self.attempt.pk])
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(self.teacher)
        form = clients[0].get(url).context['review_form']
        data = {name: form[name].value() for name in form.fields}
        data.update(v1_exam_review='1', confirm_scope='on')
        barrier = Barrier(2)

        def write(client):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return client.post(url, data).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(write, clients))
        self.assertEqual(sorted(statuses), [302, 409])
        self.attempt.refresh_from_db(); self.assertEqual(self.attempt.review_revision, 1)
