"""Attempt access is current; learner runtime JSON is not a grading oracle."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from core.flags import set_flag
from courses.exam_section_service import save_question_answer, toggle_question_review_flag
from courses.models import (Choice, Course, Exam, ExamAttempt, ExamSection,
                            ExamSectionAttemptState, ExamSectionReview, Lesson,
                            Module, Question, Quiz, ReadingAcceptedAnswer,
                            ReadingItem, ReadingResponse, ReadingTask, StudentAnswer)
from courses.reading_service import toggle_reading_review_flag


class ExamAPISecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user('security.teacher', 'security.teacher@example.test', is_staff=True)
        cls.student = User.objects.create_user('security.student', 'security.student@example.test')
        cls.peer = User.objects.create_user('security.peer', 'security.peer@example.test')
        cls.course = Course.objects.create(title='Exam access', instructor=cls.teacher)
        cls.foreign_course = Course.objects.create(title='Other course', instructor=cls.teacher)
        cls.cohort = Cohort.objects.create(course=cls.course, name='Active', start_date=timezone.localdate())
        cls.enrollment = Enrollment.objects.create(student=cls.student, cohort=cls.cohort, status='active')
        cls.exam = Exam.objects.create(course=cls.course, title='Exam', exam_type='final', weight_percentage=100, max_attempts=2)
        cls.foreign_exam = Exam.objects.create(course=cls.foreign_course, title='Other exam', exam_type='final', weight_percentage=100)
        cls.section = ExamSection.objects.create(exam=cls.exam, title='Questions', section_type='grammar_quiz', max_score=10, time_limit_minutes=20, audio_play_limit=2)
        cls.foreign_section = ExamSection.objects.create(exam=cls.foreign_exam, title='Other section', section_type='writing', max_score=10)
        cls.question = Question.objects.create(exam_section=cls.section, text='Choose', points=10)
        cls.foreign_question = Question.objects.create(exam_section=cls.foreign_section, text='Other question', points=10)
        cls.choice = Choice.objects.create(question=cls.question, text='Right', is_correct=True)
        cls.wrong = Choice.objects.create(question=cls.question, text='Wrong', is_correct=False)
        module = Module.objects.create(course=cls.course, title='Module', order=1)
        lesson = Lesson.objects.create(module=module, title='Lesson', order=1)
        quiz = Quiz.objects.create(lesson=lesson, title='Quiz')
        cls.quiz_question = Question.objects.create(quiz=quiz, text='Not an exam question', points=10)
        cls.reading = ExamSection.objects.create(exam=cls.exam, title='Reading', section_type='reading', max_score=10)
        task = ReadingTask.objects.create(section=cls.reading, title='Fill', task_type='text_input')
        cls.item = ReadingItem.objects.create(task=task, prompt='City', order=1, points=10)
        ReadingAcceptedAnswer.objects.create(item=cls.item, value='ankara', order=1)
        foreign_task = ReadingTask.objects.create(section=cls.foreign_section, title='Other task', task_type='text_input')
        cls.foreign_item = ReadingItem.objects.create(task=foreign_task, prompt='Other item', order=1, points=10)

    def setUp(self):
        self.client.force_login(self.student)
        self.attempt = ExamAttempt.objects.create(student=self.student, exam=self.exam)

    def url(self, name, *, course=None, exam=None, section=None):
        args = [course or self.course.pk, exam or self.exam.pk]
        if name == 'section_state':
            args.append(section or self.section.pk)
        return reverse('api_exam_' + name, args=args)

    def request(self, name, **kwargs):
        url = self.url(name, **kwargs)
        if name == 'section_state':
            return self.client.get(url)
        if name == 'audio_upload':
            return self.client.post(url, {'question_id': self.question.pk})
        data = {'question_id': self.question.pk, 'answer_text': 'Merhaba', 'flagged': True, 'section_id': self.section.pk}
        return self.client.post(url, data, content_type='application/json')

    def snapshot(self):
        models = (ExamAttempt, StudentAnswer, ReadingResponse, ExamSectionAttemptState, ExamSectionReview)
        return [list(model.objects.order_by('pk').values()) for model in models]

    def assert_denied_no_write(self, status, **kwargs):
        before = self.snapshot()
        with patch('core.private_storage.private_media_storage') as storage:
            for name in ('start', 'section_state', 'save', 'review_flag', 'audio_upload', 'audio_play', 'blur', 'submit'):
                with self.subTest(endpoint=name, **kwargs):
                    response = self.request(name, **kwargs)
                    self.assertEqual(response.status_code, status)
                    self.assertIn('no-store', response['Cache-Control'])
                    self.assertIn('private', response['Cache-Control'])
            storage.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_anonymous_all_endpoints_redirect_without_writes(self):
        self.client.logout()
        self.assert_denied_no_write(302)

    def test_all_endpoints_recheck_frozen_pending_expired_membership(self):
        for enabled in (False, True):
            set_flag('frontend_v1_exams', enabled=enabled, reason='Security parity')
            for status in ('frozen', 'pending', 'expired'):
                with self.subTest(flag=enabled, membership=status):
                    Enrollment.objects.filter(pk=self.enrollment.pk).update(status=status)
                    self.assert_denied_no_write(403)

    def test_active_but_overdue_membership_denied(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).update(next_payment_deadline=timezone.localdate() - timedelta(days=3))
        self.assert_denied_no_write(403)

    def test_missing_membership_denied(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).delete()
        self.assert_denied_no_write(403)

    def test_another_course_membership_does_not_authorize_exam(self):
        self.assert_denied_no_write(403, course=self.foreign_course.pk, exam=self.foreign_exam.pk)

    def test_course_exam_pair_must_match_for_every_endpoint(self):
        self.assert_denied_no_write(404, course=self.foreign_course.pk)

    def test_nonexistent_exam_denied(self):
        self.assert_denied_no_write(404, exam=self.foreign_exam.pk + 100)

    def test_staff_role_does_not_bypass_learner_membership(self):
        self.client.force_login(self.teacher)
        self.assert_denied_no_write(403)

    def test_denial_precedes_expiry_side_effect(self):
        ExamAttempt.objects.filter(pk=self.attempt.pk).update(start_time=timezone.now() - timedelta(days=1))
        Enrollment.objects.filter(pk=self.enrollment.pk).update(status='frozen')
        self.assert_denied_no_write(403)

    def test_peer_attempt_is_not_resolved(self):
        Enrollment.objects.create(student=self.peer, cohort=self.cohort, status='active')
        self.client.force_login(self.peer)
        before = self.snapshot()
        for name in ('section_state', 'save', 'review_flag', 'audio_upload', 'audio_play', 'blur', 'submit'):
            self.assertEqual(self.request(name).status_code, 404)
        self.assertEqual(self.snapshot(), before)

    def test_closed_attempt_rejects_every_runtime_endpoint(self):
        ExamAttempt.objects.filter(pk=self.attempt.pk).update(is_completed=True)
        before = self.snapshot()
        for name in ('section_state', 'save', 'review_flag', 'audio_upload', 'audio_play', 'blur', 'submit'):
            self.assertEqual(self.request(name).status_code, 404)
        self.assertEqual(self.snapshot(), before)

    def test_other_section_state_and_play_denied(self):
        before = self.snapshot()
        self.assertEqual(self.client.get(self.url('section_state', section=self.foreign_section.pk)).status_code, 404)
        response = self.client.post(self.url('audio_play'), {'section_id': self.foreign_section.pk}, content_type='application/json')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.snapshot(), before)

    def test_foreign_and_quiz_questions_cannot_save_flag_or_upload(self):
        before = self.snapshot()
        for question in (self.foreign_question, self.quiz_question):
            for name in ('save', 'review_flag', 'audio_upload'):
                with self.subTest(question=question.pk, endpoint=name):
                    data = {'question_id': question.pk, 'answer_text': 'Must not write'}
                    with patch('core.private_storage.private_media_storage') as storage:
                        response = (self.client.post(self.url(name), data) if name == 'audio_upload' else
                                    self.client.post(self.url(name), data, content_type='application/json'))
                        self.assertEqual(response.status_code, 404)
                        storage.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_foreign_reading_item_cannot_save_or_flag(self):
        before = self.snapshot()
        for name in ('save', 'review_flag'):
            response = self.client.post(self.url(name), {'reading_item_id': self.foreign_item.pk, 'text_answer': 'Denied'}, content_type='application/json')
            self.assertEqual(response.status_code, 404)
        self.assertEqual(self.snapshot(), before)

    def test_domain_question_and_reading_flag_invariants(self):
        for question in (self.foreign_question, self.quiz_question):
            with self.assertRaises(ValidationError):
                save_question_answer(attempt=self.attempt, question=question, payload={'answer_text': 'Denied'})
            with self.assertRaises(ValidationError):
                toggle_question_review_flag(attempt=self.attempt, question=question)
        with self.assertRaises(ValidationError):
            toggle_reading_review_flag(attempt=self.attempt, item=self.foreign_item)
        self.assertFalse(StudentAnswer.objects.exists())
        self.assertFalse(ReadingResponse.objects.exists())

    def assert_no_grading(self, data):
        if isinstance(data, dict):
            self.assertTrue({'awarded_score', 'is_graded', 'grader_feedback', 'is_correct', 'accepted_answers'}.isdisjoint(data), data.keys())
            for value in data.values():
                self.assert_no_grading(value)
        elif isinstance(data, list):
            for value in data:
                self.assert_no_grading(value)

    def test_question_scores_stay_in_database_never_in_save_or_state(self):
        for choice, score in ((self.wrong, 0), (self.choice, 10)):
            response = self.client.post(self.url('save'), {'question_id': self.question.pk, 'choice_id': choice.pk}, content_type='application/json')
            self.assertEqual(response.status_code, 200)
            self.assert_no_grading(response.json())
            answer = StudentAnswer.objects.get(attempt=self.attempt, question=self.question)
            self.assertEqual(answer.awarded_score, Decimal(score))
            self.assertTrue(answer.is_graded)
            state = self.request('section_state')
            self.assert_no_grading(state.json())
            self.assertEqual(state.json()['questions'][0]['response']['selected_choice_id'], choice.pk)
            self.assertIn('no-store', state['Cache-Control'])

    def test_blank_and_draft_feedback_state_is_private(self):
        self.assert_no_grading(self.request('section_state').json())
        StudentAnswer.objects.create(attempt=self.attempt, question=self.question, answer_text='Learner text', awarded_score=8, is_graded=True, grader_feedback='SECRET UNPUBLISHED')
        response = self.request('section_state')
        self.assert_no_grading(response.json())
        self.assertNotContains(response, 'SECRET UNPUBLISHED')
        self.assertContains(response, 'Learner text')

    def test_rich_reading_scoring_is_internal(self):
        self.assert_no_grading(self.request('section_state', section=self.reading.pk).json())
        for value, score in (('istanbul', 0), ('ankara', 10)):
            response = self.client.post(self.url('save'), {'reading_item_id': self.item.pk, 'text_answer': value}, content_type='application/json')
            self.assertEqual(response.status_code, 200)
            self.assert_no_grading(response.json())
            stored = ReadingResponse.objects.get(attempt=self.attempt, item=self.item)
            self.assertEqual(stored.awarded_score, Decimal(score))
            self.assertTrue(stored.is_graded)
            state = self.request('section_state', section=self.reading.pk)
            self.assert_no_grading(state.json())
            self.assertEqual(state.json()['tasks'][0]['items'][0]['response']['text_answer'], value)

    def test_client_cannot_bind_private_storage_key_via_json(self):
        before = self.snapshot()
        response = self.client.post(self.url('save'), {'question_id': self.question.pk, 'audio_key': 'exam_audio/other/private.webm'}, content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.snapshot(), before)

    def test_valid_upload_still_uses_private_writer_and_safe_playback_url(self):
        from core.private_storage import private_media_storage
        upload = SimpleUploadedFile('answer.webm', b'\x1a\x45\xdf\xa3' + b'\x00' * 64, content_type='audio/webm')
        response = self.client.post(self.url('audio_upload'), {'question_id': self.question.pk, 'audio': upload})
        self.assertEqual(response.status_code, 200)
        self.assert_no_grading(response.json())
        answer = StudentAnswer.objects.get(attempt=self.attempt, question=self.question)
        self.assertTrue(private_media_storage().exists(answer.audio_key))
        self.assertEqual(response.json()['audio_url'], reverse('exam_answer_audio', args=[answer.pk]))
        self.assertNotContains(response, answer.audio_key)
        self.assertIn('no-store', response['Cache-Control'])

    def test_invalid_audio_upload_does_not_create_answer(self):
        before = self.snapshot()
        upload = SimpleUploadedFile('bad.webm', b'not audio', content_type='audio/webm')
        with patch('core.private_storage.private_media_storage') as storage:
            response = self.client.post(self.url('audio_upload'), {'question_id': self.question.pk, 'audio': upload})
            self.assertEqual(response.status_code, 400)
            storage.assert_not_called()
        self.assertEqual(self.snapshot(), before)

    def test_permitted_runtime_keeps_start_save_flag_audio_play_blur_submit(self):
        for name in ('start', 'save', 'review_flag', 'audio_play', 'blur', 'submit'):
            with self.subTest(endpoint=name):
                response = self.request(name)
                self.assertEqual(response.status_code, 200)
                self.assertIn('no-store', response['Cache-Control'])
                self.assert_no_grading(response.json())
        self.attempt.refresh_from_db()
        self.assertTrue(self.attempt.is_completed)
        self.assertFalse(self.attempt.is_reviewed)
        self.assertEqual(self.attempt.blur_warnings, 1)

    def test_restored_access_and_canonical_payment_grace_work(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).update(status='frozen')
        self.assertEqual(self.request('save').status_code, 403)
        Enrollment.objects.filter(pk=self.enrollment.pk).update(status='active', next_payment_deadline=timezone.localdate() - timedelta(days=2))
        self.assertEqual(self.request('save').status_code, 200)

    def test_mutations_still_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        before = self.snapshot()
        for name in ('start', 'save', 'review_flag', 'audio_upload', 'audio_play', 'blur', 'submit'):
            self.assertEqual(client.post(self.url(name)).status_code, 403)
        self.assertEqual(self.snapshot(), before)
