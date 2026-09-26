import json
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, TransactionTestCase, skipUnlessDBFeature, override_settings
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from core.flags import set_flag
from courses.models import ExamAttempt, ExamActionGate, ExamActionReceipt, ExamSection, ExamSectionAttemptState, Question, StudentAnswer, ReadingResponse
from courses.exam_section_service import save_question_answer, toggle_question_review_flag
from courses import test_exam_api_security as fixtures
from cohorts.models import Enrollment


class ExamAttemptV1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ExamAPISecurityTests.setUpTestData.__func__(cls)
        cls.speaking = ExamSection.objects.create(exam=cls.exam, title='Speaking', section_type='speaking', max_score=10)
        cls.audio_question = Question.objects.create(exam_section=cls.speaking, text='Gapiring', points=10)
        cls.listening = ExamSection.objects.create(exam=cls.exam, title='Listening', section_type='listening',
                                                  max_score=10, media_url='/media/listen.wav', audio_play_limit=2)

    def setUp(self):
        self.client.force_login(self.student)
        set_flag('frontend_v1_exam_attempt', enabled=True, reason='Test')
        self.attempt = ExamAttempt.objects.create(student=self.student, exam=self.exam)
        self.url = reverse('api_exam_v1', args=[self.course.pk, self.exam.pk])
        self.page = reverse('exam_detail', args=[self.course.pk, self.exam.pk])
        self.key = f'q:{self.question.pk}'
        self.epoch = self.client.get(self.url).json()['state']['operation_epoch']

    def payload(self, command='save', **kwargs):
        return {'operation_id': str(uuid.uuid4()), 'operation_epoch': self.epoch, 'command': command, 'attempt_id': self.attempt.pk,
                'key': self.key, 'version': 0, 'value': {'choice_id': str(self.choice.pk), 'flagged': False}, **kwargs}

    def post(self, payload):
        return self.client.post(self.url, payload, content_type='application/json')

    def test_get_does_not_start_and_flag_off_is_legacy(self):
        self.attempt.delete()
        self.assertEqual(self.client.get(self.url).json()['state']['status'], 'not_started')
        self.assertContains(self.client.get(self.page), 'data-start')
        self.assertEqual(ExamAttempt.objects.count(), 0)
        set_flag('frontend_v1_exam_attempt', enabled=False, reason='Rollback')
        self.assertTemplateUsed(self.client.get(self.page), 'courses/exam_detail.html')
        self.assertEqual(self.post(self.payload('start', attempt_id=None, confirmed=True)).status_code, 409)

    def test_page_uses_frozen_shell_and_sanitizes_content(self):
        Question.objects.filter(pk=self.question.pk).update(text='<script>alert(1)</script><b>Merhaba</b>')
        response = self.client.get(self.page)
        self.assertTemplateUsed(response, 'frontend_v1/exams/attempt.html')
        self.assertContains(response, 'data-answer=')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertNotContains(response, 'exam-shell.js')
        self.assertIn('no-store', response['Cache-Control'])

    def test_start_confirmation_and_same_operation_replay(self):
        self.attempt.delete()
        data = self.payload('start', attempt_id=None, confirmed=False)
        self.assertEqual(self.post(data).status_code, 400)
        self.assertEqual(ExamAttempt.objects.count(), 0)
        data['confirmed'] = True
        first = self.post(data)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.post(data).json()['receipt'], first.json()['receipt'])
        self.assertEqual(ExamAttempt.objects.count(), 1)
        self.assertEqual(ExamActionReceipt.objects.count(), 1)

    def test_save_receipt_retry_exactly_once_and_read_ack(self):
        data = self.payload()
        self.assertEqual(self.post(data).status_code, 200)
        self.assertEqual(self.post(data).status_code, 200)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.input_revision, 1)
        self.assertEqual(self.attempt.answer_versions, {self.key: 1})
        response = self.client.get(self.url, {'operation': data['operation_id']})
        self.assertEqual(response.json()['receipt']['id'], data['operation_id'])
        self.assertEqual(StudentAnswer.objects.get().awarded_score, self.question.points)
        for field in ('awarded_score', 'is_graded', 'grader_feedback', 'is_correct'):
            self.assertNotIn(field, response.content.decode())

    def test_same_id_different_payload_rejected(self):
        data = self.payload()
        self.post(data)
        data['value']['choice_id'] = str(self.wrong.pk)
        self.assertEqual(self.post(data).status_code, 409)
        self.assertEqual(StudentAnswer.objects.get().selected_choice_id, self.choice.pk)

    def test_two_tab_stale_save_and_finish_are_no_write(self):
        self.post(self.payload())
        for data in (self.payload(value={'choice_id': str(self.wrong.pk), 'flagged': False}), self.payload('submit', confirmed=True)):
            self.assertEqual(self.post(data).status_code, 409)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.input_revision, 1)
        self.assertFalse(self.attempt.is_completed)
        self.assertEqual(ExamActionReceipt.objects.count(), 1)

    def test_legacy_save_and_flag_increment_versions(self):
        save_question_answer(attempt=self.attempt, question=self.question, payload={'choice_id': self.choice.pk})
        toggle_question_review_flag(attempt=self.attempt, question=self.question, flagged=True)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.answer_versions[self.key], 2)
        self.assertEqual(self.post(self.payload()).status_code, 409)

    def test_rebase_then_explicit_save_and_confirmed_submit(self):
        self.post(self.payload())
        self.assertEqual(self.post(self.payload(version=1, value={'choice_id': str(self.wrong.pk), 'flagged': True})).status_code, 200)
        self.assertEqual(self.post(self.payload('submit', version=2, confirmed=False)).status_code, 400)
        data = self.payload('submit', version=2, confirmed=True)
        self.assertEqual(self.post(data).status_code, 200)
        self.assertEqual(self.post(data).status_code, 200)
        self.attempt.refresh_from_db()
        self.assertTrue(self.attempt.is_completed)
        self.assertFalse(self.attempt.is_reviewed)
        self.assertEqual(self.post(self.payload(version=2)).status_code, 400)

    def test_reading_writer_grades_without_publishing(self):
        data = self.payload(key=f'r:{self.item.pk}', value={'answer_text': 'ankara', 'flagged': True})
        response = self.post(data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ReadingResponse.objects.get().awarded_score, self.item.points)
        self.assertEqual(response.json()['state']['answers'][data['key']]['version'], 1)
        self.assertNotIn('awarded_score', response.content.decode())

    def test_expiry_commits_only_saved_answers(self):
        self.post(self.payload())
        ExamAttempt.objects.filter(pk=self.attempt.pk).update(start_time=timezone.now() - timedelta(days=1))
        response = self.post(self.payload(version=1, value={'choice_id': str(self.wrong.pk), 'flagged': False}))
        self.assertEqual(response.status_code, 409)
        self.attempt.refresh_from_db()
        self.assertTrue(self.attempt.is_completed)
        self.assertEqual(StudentAnswer.objects.get().selected_choice_id, self.choice.pk)

    def test_clock_is_server_owned_and_get_can_expire(self):
        self.assertGreater(self.client.get(self.url).json()['state']['remaining_seconds'], 0)
        ExamAttempt.objects.filter(pk=self.attempt.pk).update(start_time=timezone.now() - timedelta(days=1))
        self.assertEqual(self.client.get(self.url).json()['state']['status'], 'pending')

    def test_missing_receipt_get_is_read_only_then_cancel_barrier_blocks_late_write(self):
        data = self.payload()
        self.assertIsNone(self.client.get(self.url, {'operation': data['operation_id']}).json()['receipt'])
        self.assertFalse(ExamActionReceipt.objects.exists())
        cancelled = self.post(self.payload('reconcile', operation_id=data['operation_id']))
        self.assertEqual(cancelled.json()['receipt']['command'], 'cancelled')
        self.assertEqual(self.post(data).status_code, 409)
        self.assertFalse(StudentAnswer.objects.exists())

    def test_cancel_before_first_start_has_no_attempt_side_effect(self):
        self.attempt.delete()
        data = self.payload('start', attempt_id=None, confirmed=True)
        self.post(self.payload('reconcile', operation_id=data['operation_id']))
        self.assertEqual(self.post(data).status_code, 409)
        self.assertFalse(ExamAttempt.objects.exists())

    def test_reconcile_after_save_and_with_flag_off_never_repeats_write(self):
        data = self.payload()
        self.post(data)
        set_flag('frontend_v1_exam_attempt', enabled=False, reason='Rollback')
        for _ in range(2):
            self.assertEqual(self.post(self.payload('reconcile', operation_id=data['operation_id'])).json()['receipt']['command'], 'save')
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.input_revision, 1)

    def test_current_access_precedes_read_expiry_and_reconcile(self):
        ExamAttempt.objects.filter(pk=self.attempt.pk).update(start_time=timezone.now() - timedelta(days=1))
        for status in ('frozen', 'pending', 'expired'):
            Enrollment.objects.filter(pk=self.enrollment.pk).update(status=status)
            self.assertEqual(self.client.get(self.url).status_code, 403)
            self.assertEqual(self.post(self.payload()).status_code, 403)
            self.assertEqual(self.post(self.payload('reconcile')).status_code, 403)
        self.attempt.refresh_from_db()
        self.assertFalse(self.attempt.is_completed)
        self.assertFalse(ExamActionReceipt.objects.exists())

    def test_wrong_course_foreign_quiz_item_and_malformed_inputs_no_write(self):
        wrong_url = reverse('api_exam_v1', args=[self.foreign_course.pk, self.exam.pk])
        self.assertEqual(self.client.get(wrong_url).status_code, 404)
        for key in (f'q:{self.foreign_question.pk}', f'q:{self.quiz_question.pk}', f'r:{self.foreign_item.pk}'):
            self.assertEqual(self.post(self.payload(key=key)).status_code, 404)
        for patch_data in ({'key': []}, {'key': 1}, {'key': 'oops'}, {'version': True}, {'value': []}, {'value': {'flagged': 'yes'}}, {'audio_key': 'foreign'}, {'operation_id': 'invalid'}):
            with self.subTest(data=patch_data): self.assertEqual(self.post(self.payload(**patch_data)).status_code, 400)
        self.assertFalse(StudentAnswer.objects.exists())
        self.assertFalse(ExamActionReceipt.objects.exists())

    def test_csrf_and_anonymous_no_write(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        self.assertEqual(client.post(self.url, self.payload(), content_type='application/json').status_code, 403)
        self.client.logout()
        self.assertEqual(self.post(self.payload()).status_code, 302)
        self.assertFalse(StudentAnswer.objects.exists())

    def test_peer_cannot_reuse_attempt_or_receipt(self):
        data = self.payload()
        self.post(data)
        Enrollment.objects.create(student=self.peer, cohort=self.cohort, status='active')
        self.client.force_login(self.peer)
        self.assertIsNone(self.client.get(self.url, {'operation': data['operation_id']}).json()['receipt'])
        self.assertEqual(self.post(data).status_code, 409)

    def test_listen_duplicate_consumes_once_and_limit_enforced(self):
        data = self.payload('listen', section_id=self.listening.pk, media_url='http://testserver/media/listen.wav')
        for _ in range(2): self.assertEqual(self.post(data).status_code, 200)
        self.assertEqual(self.post(dict(data, operation_id=str(uuid.uuid4()))).status_code, 200)
        self.assertEqual(self.post(dict(data, operation_id=str(uuid.uuid4()))).status_code, 403)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.input_revision, 0)

    def test_valid_audio_uses_private_writer_and_stale_does_not_upload(self):
        data = self.payload(key=f'q:{self.audio_question.pk}')
        def upload():
            return SimpleUploadedFile('answer.webm', b'\x1a\x45\xdf\xa3' + b'\x00' * 64, content_type='audio/webm')
        response = self.client.post(self.url, {'payload': json.dumps(data), 'audio': upload()})
        self.assertEqual(response.status_code, 200)
        self.assertIn('/courses/exam/answer/', response.json()['state']['answers'][data['key']]['audio_url'])
        self.assertEqual(self.client.post(self.url, {'payload': json.dumps(data), 'audio': upload()}).status_code, 200)
        data['operation_id'] = str(uuid.uuid4())
        with patch('core.private_storage.private_media_storage') as storage:
            self.assertEqual(self.client.post(self.url, {'payload': json.dumps(data), 'audio': upload()}).status_code, 409)
            storage.assert_not_called()

    def test_invalid_audio_no_answer_revision_or_receipt(self):
        data = self.payload(key=f'q:{self.audio_question.pk}')
        response = self.client.post(self.url, {'payload': json.dumps(data), 'audio': SimpleUploadedFile('fake.webm', b'not audio')})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(StudentAnswer.objects.exists())
        self.assertFalse(ExamActionReceipt.objects.exists())

    def test_validation_rollback_does_not_leave_partial_answer(self):
        self.assertEqual(self.post(self.payload(value={'choice_id': self.foreign_question.pk + 900, 'flagged': False})).status_code, 400)
        self.attempt.refresh_from_db()
        self.assertFalse(StudentAnswer.objects.exists())
        self.assertEqual(self.attempt.input_revision, 0)

    def test_zero_limit_also_blocks_first_attempt(self):
        self.attempt.delete()
        self.exam.max_attempts = 0
        self.exam.save(update_fields=['max_attempts'])
        self.assertEqual(self.post(self.payload('start', attempt_id=None, confirmed=True)).status_code, 400)
        self.assertFalse(ExamAttempt.objects.exists())
        self.assertNotContains(self.client.get(self.page), 'data-start')

    def test_center_handoff_copy_matches_independent_attempt_flag(self):
        set_flag('frontend_v1_exams', enabled=True, reason='Center test')
        self.assertContains(self.client.get(reverse('exam_center')), 'Javoblar har savolda alohida saqlanadi.')
        set_flag('frontend_v1_exam_attempt', enabled=False, reason='Rollback')
        self.assertContains(self.client.get(reverse('exam_center')), 'Urinish sahifasi hozircha avvalgi ko‘rinishda ochiladi.')

    def test_draft_scope_changes_between_sessions_and_never_exposes_session_key(self):
        first = self.client.get(self.page).context['attempt_config']['scope']
        self.assertNotEqual(first, self.client.session.session_key)
        self.client.logout()
        self.client.force_login(self.student)
        self.assertNotEqual(first, self.client.get(self.page).context['attempt_config']['scope'])

    def test_cancelled_uuid_flood_is_bounded_and_old_epoch_is_read_only(self):
        self.attempt.delete()
        for enabled in (True, False):
            set_flag('frontend_v1_exam_attempt', enabled=enabled, reason='Bounded cancellation')
            for _ in range(12):
                # Even a client obtaining each new epoch cannot grow the ledger.
                self.epoch = str(ExamActionGate.objects.get().epoch)
                result = self.post(self.payload('reconcile'))
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json()['receipt']['command'], 'cancelled')
                epoch = ExamActionGate.objects.get().epoch
                self.post(self.payload('reconcile'))  # old epoch, a different UUID
                self.assertEqual(ExamActionGate.objects.get().epoch, epoch)
        self.assertEqual(ExamActionGate.objects.count(), 1)
        self.assertEqual(ExamActionReceipt.objects.count(), 0)
        self.assertFalse(ExamAttempt.objects.exists())

    def test_unissued_epoch_and_off_get_cannot_allocate_gate_or_receipt(self):
        ExamActionGate.objects.all().delete()
        set_flag('frontend_v1_exam_attempt', enabled=False, reason='Rollback')
        self.assertIsNone(self.client.get(self.url).json()['state']['operation_epoch'])
        for _ in range(12):
            self.assertEqual(self.post(self.payload('reconcile', operation_epoch=str(uuid.uuid4()))).status_code, 409)
        self.assertFalse(ExamActionGate.objects.exists())
        self.assertFalse(ExamActionReceipt.objects.exists())

    def test_cancel_invalidates_all_late_actions_but_fresh_epoch_preserves_draft_save(self):
        old = self.payload()
        result = self.post(self.payload('reconcile'))
        self.assertEqual(self.post(old).status_code, 409)
        self.assertEqual(self.post(self.payload('listen', section_id=self.listening.pk)).status_code, 409)
        self.assertEqual(self.post(self.payload('submit', confirmed=True)).status_code, 409)
        self.assertFalse(StudentAnswer.objects.exists())
        self.epoch = result.json()['state']['operation_epoch']
        self.assertEqual(self.post(self.payload()).status_code, 200)
        self.assertEqual(StudentAnswer.objects.count(), 1)

    def test_applied_receipt_survives_rotation_and_gate_is_user_exam_scoped(self):
        data = self.payload()
        self.post(data)
        self.post(self.payload('reconcile'))
        self.assertEqual(self.post(data).json()['receipt']['command'], 'save')
        Enrollment.objects.create(student=self.peer, cohort=self.cohort, status='active')
        self.client.force_login(self.peer)
        other_epoch = self.client.get(self.url).json()['state']['operation_epoch']
        self.post(self.payload('reconcile'))
        self.assertEqual(str(ExamActionGate.objects.get(student=self.peer).epoch), other_epoch)
        self.assertEqual(self.post(data).status_code, 409)

    def test_missing_or_malformed_epoch_never_writes(self):
        for value in (None, '', 'invalid', [], True):
            self.assertEqual(self.post(self.payload(operation_epoch=value)).status_code, 400)
        self.assertFalse(ExamActionReceipt.objects.exists())
        self.assertFalse(StudentAnswer.objects.exists())

    def test_unplayable_sources_never_consume_listen_quota(self):
        for source in ('https://outside.example/audio.mp3', '//outside.example/audio.mp3',
                       'http://testserver:8080/audio.mp3', 'http://user@testserver/audio.mp3',
                       'javascript:alert(1)', 'data:audio/wav;base64,AA', 'blob:http://testserver/id',
                       '/\\outside.example/audio.mp3', '/audio\n.mp3', ''):
            with self.subTest(source=source):
                ExamSection.objects.filter(pk=self.listening.pk).update(media_url=source)
                state = self.client.get(self.url).json()['state']
                section = next(s for s in state['sections'] if s['id'] == self.listening.pk)
                self.assertEqual(section['media_url'], '')
                self.assertTrue(section['media_unavailable'])
                self.assertEqual(self.post(self.payload('listen', section_id=self.listening.pk, media_url=source)).status_code, 400)
        self.assertFalse(ExamSectionAttemptState.objects.filter(state__plays_used__gt=0).exists())
        self.assertFalse(ExamActionReceipt.objects.exists())
        self.assertContains(self.client.get(self.page), 'Audio manbasi bu sahifada ochilmaydi.')

    def test_changed_source_and_non_listening_section_do_not_consume(self):
        response = self.post(self.payload('listen', section_id=self.listening.pk, media_url='http://testserver/media/old.wav'))
        self.assertEqual(response.status_code, 409)
        self.assertIn('state', response.json())
        self.assertEqual(self.post(self.payload('listen', section_id=self.section.pk, media_url='http://testserver/a.wav')).status_code, 400)
        self.assertFalse(ExamSectionAttemptState.objects.filter(state__plays_used__gt=0).exists())

    def test_strict_csp_local_preview_exception_only_on_v1_attempt(self):
        from core.csp_policy import build_csp_policy
        with override_settings(CONTENT_SECURITY_POLICY=build_csp_policy(),
                               MIDDLEWARE=['csp.middleware.CSPMiddleware', *settings.MIDDLEWARE]):
            strict_client = Client()
            strict_client.force_login(self.student)
            response = strict_client.get(self.page)
            self.assertIn("media-src 'self' blob:", response['Content-Security-Policy'])
            self.assertIn("object-src 'none'", response['Content-Security-Policy'])
            session = strict_client.session
            session['telegram_miniapp'] = True
            session.save()
            mini_policy = strict_client.get(self.page)['Content-Security-Policy']
            self.assertIn("media-src 'self' blob:", mini_policy)
            self.assertIn('https://web.telegram.org', mini_policy)
            set_flag('frontend_v1_exam_attempt', enabled=False, reason='Rollback')
            legacy = strict_client.get(self.page)['Content-Security-Policy']
            self.assertIn("media-src 'self'", legacy)
            self.assertNotIn('blob:', legacy)


@skipUnlessDBFeature('has_select_for_update')
class ExamAttemptV1ConcurrencyTests(TransactionTestCase):
    """Real overlapping transactions in the required PostgreSQL CI job."""
    def setUp(self):
        fixtures.ExamAPISecurityTests.setUpTestData.__func__(type(self))
        set_flag('frontend_v1_exam_attempt', enabled=True, reason='Concurrency test')
        self.attempt = ExamAttempt.objects.create(student=self.student, exam=self.exam)
        self.url = reverse('api_exam_v1', args=[self.course.pk, self.exam.pk])
        self.client.force_login(self.student)
        self.epoch = self.client.get(self.url).json()['state']['operation_epoch']

    def race(self, *payloads, urls=None):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections, close_old_connections
        clients = [Client() for _ in payloads]
        for client in clients: client.force_login(self.student)
        barrier = Barrier(len(payloads))
        def request(pair):
            client, payload, url = pair
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                return client.post(url, payload, content_type='application/json').status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(payloads)) as pool:
            return list(pool.map(request, zip(clients, payloads, urls or [self.url] * len(payloads))))

    def data(self, **extra):
        return {'command': 'save', 'operation_id': str(uuid.uuid4()), 'operation_epoch': self.epoch, 'attempt_id': self.attempt.pk,
                'key': f'q:{self.question.pk}', 'version': 0, 'value': {'choice_id': self.choice.pk, 'flagged': False}, **extra}

    def test_concurrent_stale_writers_only_one_commits(self):
        self.assertEqual(sorted(self.race(self.data(), self.data())), [200, 409])
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.input_revision, 1)

    def test_duplicate_operation_only_one_receipt_and_revision(self):
        data = self.data()
        self.assertEqual(self.race(data, data), [200, 200])
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.input_revision, 1)
        self.assertEqual(ExamActionReceipt.objects.count(), 1)

    def test_reconcile_racing_save_is_applied_or_cancelled_never_both(self):
        data = self.data()
        outcomes = self.race(data, {'command': 'reconcile', 'operation_id': data['operation_id'], 'operation_epoch': self.epoch})
        self.assertEqual(outcomes[1], 200)
        self.assertIn(outcomes[0], (200, 409))
        self.assertEqual(ExamActionReceipt.objects.count(), int(outcomes[0] == 200))
        self.assertEqual(StudentAnswer.objects.count(), int(outcomes[0] == 200))
        self.assertEqual(ExamActionGate.objects.count(), 1)

    def test_two_initial_starts_create_one_attempt(self):
        self.attempt.delete()
        data = self.data(command='start', attempt_id=None, confirmed=True)
        other = dict(data, operation_id=str(uuid.uuid4()))
        self.assertEqual(sorted(self.race(data, other)), [200, 409])
        self.assertEqual(ExamAttempt.objects.count(), 1)

    def test_legacy_submit_and_v1_save_share_lock_order_and_cannot_reopen_attempt(self):
        old_url = reverse('api_exam_submit', args=[self.course.pk, self.exam.pk])
        statuses = self.race({}, self.data(), urls=[old_url, self.url])
        self.assertEqual(statuses[0], 200)
        self.assertIn(statuses[1], (200, 400))
        self.attempt.refresh_from_db()
        self.assertTrue(self.attempt.is_completed)
        self.assertEqual(self.attempt.input_revision, int(statuses[1] == 200))
