import datetime
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connections
from django.test import Client, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from core.flags import set_flag
from cohorts.models import Attendance
from .frontend_v1_live import FLAG, action_revision
from .grading import parse_author_definition
from .models import ActivityRun, StudentResponse
from .services import close_activity, finish_class_session, open_activity, submit_response
from .tests import ClassbookFixtureMixin


class LiveV1Tests(ClassbookFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        set_flag(FLAG, enabled=True, reason='Live V1 test')
        self.session = self.start()
        self.activity = self.session.classbook_activities.get()
        self.client.force_login(self.teacher)

    def url(self, name, pk=None):
        return reverse('classbook:' + name, args=[] if pk is None else [pk])

    def action(self, action):
        self.session.refresh_from_db()
        return {'frontend_v1_classbook_live':'1', 'confirm_scope':'yes',
                'revision':action_revision(self.teacher, self.session, action)}

    def open(self):
        self.assertTrue(open_activity(actor=self.teacher, activity=self.activity).ok)
        self.activity.refresh_from_db()

    def payload(self):
        return self.client.get(self.url('live_activity', self.activity.pk)).context['exercise_payload']

    def submit(self, answer, revision=None):
        revision = revision or self.payload()['revision']
        return self.client.post(self.url('live_activity_submit', self.activity.pk),
                                json.dumps({'answer':answer, 'revision':revision}),
                                content_type='application/json', HTTP_X_CLASSBOOK_V1='1')

    def test_six_renderers_and_reveal_privacy(self):
        self.open()
        for name, pk in [('teacher_session', self.session.pk), ('teacher_activity_result', self.activity.pk)]:
            response = self.client.get(self.url(name, pk))
            self.assertTemplateUsed(response, f'frontend_v1/classbook/{name}.html')
            self.assertIn('no-store', response['Cache-Control'])
            self.assertNotContains(response, 'classbook/teacher-live.js')
        self.client.force_login(self.student)
        for name, pk in [('live_home', None), ('live_session', self.session.pk), ('live_activity', self.activity.pk)]:
            response = self.client.get(self.url(name, pk))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, f'frontend_v1/classbook/{name}.html')
            self.assertIn('no-store', response['Cache-Control'])
            self.assertNotContains(response, 'classbook/live-activity.js')
            self.assertNotContains(response, 'answer_key')
            self.assertNotContains(response, self.exercise.explanation)
        self.assertEqual(self.client.get(self.url('activity_result', self.activity.pk)).status_code, 404)
        close_activity(actor=self.teacher, activity=self.activity)
        self.assertTemplateUsed(self.client.get(self.url('activity_result', self.activity.pk)), 'frontend_v1/classbook/activity_result.html')

    def test_scope_and_get_no_write(self):
        for name, pk in [('teacher_session', self.session.pk), ('teacher_activity_result', self.activity.pk), ('live_home', None)]:
            self.client.get(self.url(name, pk)); self.client.head(self.url(name, pk))
        self.activity.refresh_from_db(); self.assertEqual(self.activity.status, 'queued')
        self.assertEqual(StudentResponse.objects.count(), 0)
        self.assertEqual(Attendance.objects.count(), 0)
        self.open()
        self.client.force_login(self.outsider)
        for name, pk in [('live_session', self.session.pk), ('live_activity', self.activity.pk), ('live_activity_state', self.activity.pk), ('activity_result', self.activity.pk)]:
            self.assertEqual(self.client.get(self.url(name, pk)).status_code, 404)
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.get(self.url('teacher_session', self.session.pk)).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url('live_home')).status_code, 302)

    def test_teacher_confirmation_csrf_replay_and_action_binding(self):
        url = self.url('activity_open', self.activity.pk)
        data = self.action(f'open:{self.activity.pk}')
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.teacher)
        self.assertEqual(csrf.post(url, data).status_code, 403)
        invalid = dict(data); invalid.pop('confirm_scope')
        self.assertEqual(self.client.post(url, invalid).status_code, 400)
        self.assertEqual(self.client.post(self.url('activity_close', self.activity.pk), data).status_code, 409)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.client.post(url, data).status_code, 409)

    def test_finish_from_old_page_cannot_publish_newly_opened_activity(self):
        data = self.action('finish')
        self.open()
        self.assertEqual(self.client.post(self.url('session_finish', self.session.pk), data).status_code, 409)
        self.session.refresh_from_db(); self.assertEqual(self.session.status, 'open')
        self.activity.refresh_from_db(); self.assertEqual(self.activity.status, 'open')
        self.assertEqual(Attendance.objects.count(), 0)

    def test_finish_canonical_effects_and_replay(self):
        self.open()
        data = self.action('finish')
        url = self.url('session_finish', self.session.pk)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.client.post(url, data).status_code, 409)
        self.session.refresh_from_db(); self.activity.refresh_from_db()
        self.assertEqual(self.session.status, 'closed'); self.assertEqual(self.activity.status, 'revealed')
        self.assertEqual(Attendance.objects.filter(lesson=self.lesson).count(), 3)

    def test_learner_submit_single_response_reconcile_and_reveal(self):
        self.open(); self.client.force_login(self.student)
        payload = self.payload()
        first = self.submit('o2', payload['revision'])
        self.assertTrue(first.json()['ok']); self.assertNotIn('score', first.json())
        self.assertEqual(self.submit('o1', payload['revision']).json()['code'], 'already_submitted')
        self.assertEqual(StudentResponse.objects.get().answer, 'o2')
        state = self.client.get(self.url('live_activity_state', self.activity.pk))
        self.assertTrue(state.json()['submitted']); self.assertIn('no-store', state['Cache-Control'])
        self.assertNotIn('score', state.json()); self.assertNotIn('answer', state.json())
        self.assertEqual(self.client.get(self.url('activity_result', self.activity.pk)).status_code, 404)
        close_activity(actor=self.teacher, activity=self.activity)
        self.assertContains(self.client.get(self.url('activity_result', self.activity.pk)), 'Istanbul')

    def test_ten_kinds_use_canonical_grading_with_private_aliases(self):
        cases = [
            ('single_choice', '*Bir\nIkki', 'o1'), ('multiple_choice', '*Bir\n*Ikki\nUch', ['o1','o2']),
            ('true_false', 'ha', 'true'), ('short_answer', 'Merhaba', 'Merhaba'),
            ('fill_blank', 'ev', 'ev'), ('matching', 'a = b\nc = d', {'l1':'r1','l2':'r2'}),
            ('ordering', 'bir\nikki', ['i1','i2']), ('unscramble', 'Ben\ngeldim', ['i1','i2']),
            ('categorization', 'a: bir\nb: ikki', {'i1':'c1','i2':'c2'}), ('poll', 'Ha\nYoq', 'o1')]
        self.open(); self.client.force_login(self.student)
        from .frontend_v1_live import alias
        for kind, raw, answer in cases:
            with self.subTest(kind=kind):
                StudentResponse.objects.all().delete()
                config, key = parse_author_definition(kind, raw)
                self.activity.snapshot.update(kind=kind, config=config, answer_key=key)
                self.activity.save(update_fields=['snapshot'])
                payload = self.payload()
                self.assertNotIn('answer_key', payload); self.assertNotIn('explanation', payload)
                self.assertNotIn('media_name', payload)
                if kind in {'ordering', 'unscramble'}:
                    answer = [alias(self.student, self.activity, 'items', value) for value in answer]
                    self.assertNotIn('i1', json.dumps(payload['config']))
                elif kind in {'matching', 'categorization'}:
                    left, right = ('left','right') if kind == 'matching' else ('items','categories')
                    answer = {alias(self.student, self.activity, left, a):alias(self.student, self.activity, right, b) for a,b in answer.items()}
                    self.assertNotIn('r1' if kind == 'matching' else 'i1', json.dumps(payload['config']))
                result = self.submit(answer, payload['revision'])
                self.assertEqual(result.status_code, 200, result.content)
                response = StudentResponse.objects.get()
                if kind != 'poll': self.assertEqual(response.accuracy, 1)
                else: self.assertEqual(response.score, 0)

    def test_answer_token_binds_user_snapshot_and_activity(self):
        self.open(); self.client.force_login(self.student)
        token = self.payload()['revision']
        self.client.force_login(self.second)
        self.assertEqual(self.submit('o2', token).status_code, 409)
        self.client.force_login(self.student)
        self.activity.snapshot['prompt'] = 'Changed snapshot'
        self.activity.save(update_fields=['snapshot'])
        self.assertEqual(self.submit('o2', token).status_code, 409)
        self.assertEqual(StudentResponse.objects.count(), 0)

    def test_expired_and_closed_state_retains_honest_status(self):
        self.open(); self.client.force_login(self.student)
        self.activity.closes_at = timezone.now() - datetime.timedelta(seconds=1)
        self.activity.save(update_fields=['closes_at'])
        self.assertTrue(self.client.get(self.url('live_activity_state', self.activity.pk)).json()['expired'])
        self.assertEqual(self.submit('o2').json()['code'], 'deadline')
        close_activity(actor=self.teacher, activity=self.activity, publish=False)
        self.assertEqual(self.client.get(self.url('live_activity_state', self.activity.pk)).json()['status'], 'closed')
        self.assertEqual(self.client.get(self.url('activity_result', self.activity.pk)).status_code, 404)

    def test_flag_rollback_native_and_json_no_write_legacy_render(self):
        data = self.action(f'open:{self.activity.pk}')
        self.open(); self.client.force_login(self.student); payload = self.payload()
        set_flag(FLAG, enabled=False, reason='Rollback')
        self.assertEqual(self.submit('o2', payload['revision']).status_code, 400)
        self.assertEqual(StudentResponse.objects.count(), 0)
        self.assertTemplateUsed(self.client.get(self.url('live_activity', self.activity.pk)), 'classbook/live_activity.html')
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(self.url('activity_open', self.activity.pk), data).status_code, 400)

    def test_non_object_payload_is_rejected_not_500(self):
        self.open(); self.client.force_login(self.student)
        for raw in ('null', '[]', 'true', '"text"'):
            self.assertEqual(self.client.post(self.url('live_activity_submit', self.activity.pk), raw, content_type='application/json').status_code, 400)

    def test_duplicate_json_and_extra_payload_fields_are_rejected(self):
        self.open(); self.client.force_login(self.student)
        token = self.payload()['revision']
        for raw in ('{"answer":"o1","answer":"o2","revision":"' + token + '"}',
                    json.dumps({'answer':'o2','revision':token,'score':100})):
            self.assertEqual(self.client.post(self.url('live_activity_submit', self.activity.pk), raw, content_type='application/json', HTTP_X_CLASSBOOK_V1='1').status_code,400)
        self.assertFalse(StudentResponse.objects.exists())

    def test_live_home_empty_and_session_list_hide_queued_questions(self):
        self.client.force_login(self.student)
        response = self.client.get(self.url('live_session', self.session.pk))
        self.assertNotContains(response, self.exercise.title)
        self.assertEqual(self.client.get(self.url('live_session_state', self.session.pk)).json()['activities'], [])
        self.client.force_login(self.outsider)
        self.assertContains(self.client.get(self.url('live_home')), 'Hozir jonli dars yo‘q')


class LiveV1ConcurrencyTests(ClassbookFixtureMixin, TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_submit_and_finish_share_parent_first_order(self):
        session = self.start(); activity = session.classbook_activities.get()
        self.assertTrue(open_activity(actor=self.teacher, activity=activity).ok)
        barrier = Barrier(2)
        def run(action):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                if action == 'submit':
                    return submit_response(user=self.student, activity=activity, answer='o2')
                return finish_class_session(actor=self.teacher, session=session)
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            submitted, finished = list(pool.map(run, ['submit', 'finish']))
        self.assertTrue(finished.ok)
        session.refresh_from_db(); activity.refresh_from_db()
        self.assertEqual((session.status, activity.status), ('closed', 'revealed'))
        self.assertEqual(StudentResponse.objects.filter(activity=activity).count(), int(submitted.ok))
        if not submitted.ok:
            self.assertIn(submitted.code, ['session_closed', 'activity_closed'])
        attendance = Attendance.objects.get(enrollment=self.enrollment, lesson=self.lesson)
        self.assertEqual(attendance.status, Attendance.STATUS_PRESENT if submitted.ok else Attendance.STATUS_ABSENT)

    @skipUnlessDBFeature('has_select_for_update')
    def test_parallel_teacher_open_same_page_once(self):
        set_flag(FLAG, enabled=True, reason='PG race')
        session = self.start(); activity = session.classbook_activities.get()
        data = {'frontend_v1_classbook_live':'1', 'confirm_scope':'yes',
                'revision':action_revision(self.teacher, session, f'open:{activity.pk}')}
        url = reverse('classbook:activity_open', args=[activity.pk])
        clients = [Client(), Client()]
        for client in clients: client.force_login(self.teacher)
        barrier = Barrier(2)
        def post(client):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return client.post(url, data).status_code
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(post, clients))
        self.assertEqual(sorted(results), [302,409])
        self.assertEqual(ActivityRun.objects.filter(session=session, status='open').count(), 1)
