import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import connection, connections
from django.test import Client, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from bot.models import TelegramLessonSession
from core.flags import set_flag
from courses.models import Lesson
from .frontend_v1 import FLAG, revision
from .models import Exercise, LessonPlaybook, PlaybookExercise, TelegramGroupDelivery
from .tests import ClassbookFixtureMixin


class PreparationV1Tests(ClassbookFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        set_flag(FLAG, enabled=True, reason='V1 test')
        self.client.force_login(self.teacher)
        self.edit_url = reverse('classbook:exercise_edit', args=[self.exercise.pk])
        self.play_url = reverse('classbook:playbook_edit', args=[self.cohort.pk, self.lesson.pk])

    def exercise_data(self, url=None):
        page = self.client.get(url or self.edit_url)
        form = page.context['form']
        data = {name: form[name].value() for name in form.fields if name != 'media'}
        data = {name: value if value is not None else '' for name, value in data.items()}
        data.update(frontend_v1_classbook='1', revision=page.context['revision'],
                    creation_key=page.context['creation_key'], confirm_scope='yes')
        return data

    def play_data(self, url=None):
        page = self.client.get(url or self.play_url)
        form = page.context['form']
        data = {name: form[name].value() for name in form.fields}
        data = {name: value for name, value in data.items() if value is not False}
        data.update(frontend_v1_classbook='1', revision=page.context['revision'], action='save', confirm_scope='yes')
        return data

    def action(self, action, item=None):
        self.playbook.refresh_from_db()
        return {'frontend_v1_classbook': '1', 'confirm_scope': 'yes', 'revision': revision(
            self.teacher, action, item or self.playbook, cohort=self.cohort, lesson=self.lesson)}

    def test_all_preparation_pages_render_v1_without_preview_or_legacy_assets(self):
        for name, args in [('teacher_home', []), ('exercise_list', []), ('exercise_create', []),
                           ('exercise_edit', [self.exercise.pk]), ('playbook_edit', [self.cohort.pk, self.lesson.pk])]:
            with self.subTest(page=name):
                response = self.client.get(reverse('classbook:' + name, args=args))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'frontend_v1/css/classbook.css')
                self.assertNotContains(response, '/_preview/')
                self.assertNotContains(response, 'classbook/classbook.css')
                self.assertIn('no-store', response['Cache-Control'])

    def test_get_and_head_do_not_create_playbook_or_session(self):
        lesson = Lesson.objects.create(module=self.module, title='New lesson', order=2)
        url = reverse('classbook:playbook_edit', args=[self.cohort.pk, lesson.pk])
        for method in (self.client.get, self.client.head):
            self.assertEqual(method(url).status_code, 200)
        self.assertFalse(LessonPlaybook.objects.filter(lesson=lesson).exists())
        self.assertEqual(TelegramLessonSession.objects.count(), 0)
        self.assertEqual(TelegramGroupDelivery.objects.count(), 0)

    def test_unknown_teacher_student_anonymous_and_foreign_ids(self):
        for user in (self.other_teacher, self.student, self.outsider):
            self.client.force_login(user)
            for url in (self.edit_url, self.play_url):
                self.assertIn(self.client.get(url).status_code, (302, 404))
        self.client.logout()
        self.assertEqual(self.client.get(self.edit_url).status_code, 302)

    def test_empty_teacher_lists_remain_scoped(self):
        self.client.force_login(self.other_teacher)
        self.assertContains(self.client.get(reverse('classbook:teacher_home')), 'Biriktirilgan faol guruh yo‘q')
        self.assertNotContains(self.client.get(reverse('classbook:exercise_list')), self.exercise.title)

    def test_csrf_and_confirmation_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.teacher)
        self.assertEqual(client.post(self.edit_url, self.exercise_data()).status_code, 403)
        data = self.exercise_data(); data.pop('confirm_scope')
        self.assertEqual(self.client.post(self.edit_url, data).status_code, 400)

    def test_exercise_save_and_same_payload_replay(self):
        data = self.exercise_data(); data['title'] = 'Updated exercise'
        self.assertEqual(self.client.post(self.edit_url, data).status_code, 302)
        self.assertEqual(self.client.post(self.edit_url, data).status_code, 409)
        self.exercise.refresh_from_db()
        self.assertEqual((self.exercise.title, self.exercise.edit_revision), ('Updated exercise', 1))

    def test_two_tabs_keep_stale_text_without_overwrite(self):
        first = self.exercise_data(); old = dict(first)
        first['title'] = 'Fresh saved'; old['title'] = 'My unsaved draft'
        self.client.post(self.edit_url, first)
        response = self.client.post(self.edit_url, old)
        self.assertContains(response, 'My unsaved draft', status_code=409)
        self.assertContains(response, 'data-library-unsaved', status_code=409)
        self.exercise.refresh_from_db(); self.assertEqual(self.exercise.title, 'Fresh saved')

    def test_same_clock_model_aba_invalidates_exercise(self):
        data = self.exercise_data()
        with patch('django.utils.timezone.now', return_value=timezone.now()):
            self.exercise.title = 'B'; self.exercise.save()
            self.exercise.title = 'Poytaxt'; self.exercise.save()
        self.assertEqual(self.client.post(self.edit_url, data).status_code, 409)

    def test_create_once_and_replay_does_not_duplicate(self):
        url = reverse('classbook:exercise_create')
        data = self.exercise_data(url)
        data.update(course=self.course.pk, lesson=self.lesson.pk, title='Created once', kind='single_choice',
                    prompt='Test question?', definition='*A\nB', time_limit_seconds=60, max_points=100, speed_bonus_percent=10)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.client.post(url, data).status_code, 409)
        self.assertEqual(Exercise.objects.filter(title='Created once').count(), 1)

    def test_tampered_or_other_user_create_token_rejected(self):
        url = reverse('classbook:exercise_create')
        data = self.exercise_data(url)
        data['creation_key'] = str(uuid.uuid4())
        self.assertEqual(self.client.post(url, data).status_code, 409)
        data = self.exercise_data(url)
        self.client.force_login(self.other_teacher)
        self.assertEqual(self.client.post(url, data).status_code, 409)

    def test_invalid_definition_and_cross_course_lesson_preserve_draft(self):
        data = self.exercise_data(); data['definition'] = '*A\n*B'; data['title'] = 'Keep my text'
        response = self.client.post(self.edit_url, data)
        self.assertContains(response, 'Keep my text', status_code=400)
        self.exercise.refresh_from_db(); self.assertEqual(self.exercise.title, 'Poytaxt')
        data = self.exercise_data(); data['lesson'] = 999999
        self.assertEqual(self.client.post(self.edit_url, data).status_code, 400)

    def test_all_ten_types_use_canonical_parser(self):
        samples = {'single_choice': '*A\nB', 'multiple_choice': '*A\nB\n*C', 'true_false': 'ha',
                   'short_answer': 'merhaba', 'fill_blank': 'geliyorum', 'matching': 'a = b\nc = d',
                   'ordering': 'bir\nikki', 'categorization': 'A: bir, ikki\nB: uch',
                   'unscramble': 'Türkçe\nöğreniyorum', 'poll': 'Oson\nQiyin'}
        from .grading import parse_author_definition
        for kind, definition in samples.items():
            with self.subTest(kind=kind):
                data = self.exercise_data(); data.update(kind=kind, definition=definition)
                response = self.client.post(self.edit_url, data)
                self.assertEqual(response.status_code, 302, response.context['form'].errors if response.context else '')
                self.exercise.refresh_from_db()
                self.assertEqual((self.exercise.config, self.exercise.answer_key), parse_author_definition(kind, definition))

    def test_private_media_render_preserve_and_explicit_clear(self):
        self.exercise.media.name = 'private-secret-media.png'; self.exercise.media_kind = 'image'; self.exercise.save()
        page = self.client.get(self.edit_url)
        self.assertContains(page, 'Media fayl biriktirilgan')
        self.assertNotContains(page, 'private-secret-media.png')
        data = self.exercise_data(); self.assertEqual(self.client.post(self.edit_url, data).status_code, 302)
        self.exercise.refresh_from_db(); self.assertEqual(self.exercise.media.name, 'private-secret-media.png')
        data = self.exercise_data(); data.update({'media-clear': 'on', 'media_kind': ''})
        self.assertEqual(self.client.post(self.edit_url, data).status_code, 302)
        self.exercise.refresh_from_db(); self.assertFalse(self.exercise.media)

    def test_new_playbook_save_and_stale_second_create(self):
        lesson = Lesson.objects.create(module=self.module, title='Next', order=2)
        url = reverse('classbook:playbook_edit', args=[self.cohort.pk, lesson.pk])
        data = self.play_data(url)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.client.post(url, data).status_code, 409)
        self.assertEqual(LessonPlaybook.objects.filter(lesson=lesson).count(), 1)

    def test_playbook_settings_no_delivery_or_live_snapshot_change(self):
        session = self.start(); activity = session.classbook_activities.get(); before = activity.snapshot
        delivery_count = TelegramGroupDelivery.objects.count()
        data = self.play_data(); data.update(opening_message='Changed', status='draft')
        self.assertEqual(self.client.post(self.play_url, data).status_code, 302)
        self.assertEqual(TelegramGroupDelivery.objects.count(), delivery_count)
        activity.refresh_from_db(); self.assertEqual(activity.snapshot, before)
        self.assertEqual(self.client.post(self.play_url, data).status_code, 409)

    def test_add_replay_move_remove_and_bank_preserved(self):
        url = reverse('classbook:playbook_add_exercise', args=[self.playbook.pk])
        data = self.action('add'); data['exercise_id'] = self.exercise.pk
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.client.post(url, data).status_code, 409)
        second = self.playbook.exercise_steps.order_by('order').last()
        move = reverse('classbook:playbook_move_exercise', args=[second.pk, 'up'])
        data = self.action(f'up:{second.pk}')
        self.assertEqual(self.client.post(move, data).status_code, 302)
        self.assertEqual(self.client.post(move, data).status_code, 409)
        remove = reverse('classbook:playbook_remove_exercise', args=[second.pk])
        self.assertEqual(self.client.post(remove, self.action(f'remove:{second.pk}')).status_code, 302)
        self.assertTrue(Exercise.objects.filter(pk=self.exercise.pk).exists())
        self.assertEqual(list(self.playbook.exercise_steps.values_list('order', flat=True)), [1])

    def test_playbook_aba_and_child_change_invalidate(self):
        data = self.play_data()
        old = self.playbook.opening_message
        with patch('django.utils.timezone.now', return_value=timezone.now()):
            self.playbook.opening_message = 'B'; self.playbook.save()
            self.playbook.opening_message = old; self.playbook.save()
        response = self.client.post(self.play_url, data)
        self.assertContains(response, 'Kirish xabari', status_code=409)
        self.assertNotContains(response, '>Opening message', status_code=409)
        data = self.play_data(); self.exercise.title = 'Changed exercise'; self.exercise.save()
        self.assertEqual(self.client.post(self.play_url, data).status_code, 409)

    def test_action_token_cannot_be_repurposed(self):
        url = reverse('classbook:playbook_remove_exercise', args=[self.step.pk])
        self.assertEqual(self.client.post(url, self.action('save')).status_code, 409)
        self.assertTrue(PlaybookExercise.objects.filter(pk=self.step.pk).exists())

    def test_start_explicit_canonical_and_replay_safe(self):
        url = reverse('classbook:session_start', args=[self.cohort.pk, self.lesson.pk])
        data = self.action('start')
        without_consent = dict(data); without_consent.pop('confirm_scope')
        self.assertEqual(self.client.post(url, without_consent).status_code, 400)
        self.assertEqual(TelegramLessonSession.objects.count(), 0)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.client.post(url, data).status_code, 409)
        self.assertEqual(TelegramLessonSession.objects.count(), 1)
        self.assertEqual(TelegramLessonSession.objects.get().classbook_activities.count(), 1)

    def test_start_rejects_changed_exercise_definition(self):
        url = reverse('classbook:session_start', args=[self.cohort.pk, self.lesson.pk])
        data = self.action('start')
        self.exercise.prompt = 'New question'; self.exercise.save()
        self.assertEqual(self.client.post(url, data).status_code, 409)
        self.assertEqual(TelegramLessonSession.objects.count(), 0)

    def test_rollback_inflight_no_write_and_legacy_get(self):
        exercise_data = self.exercise_data(); play_data = self.play_data()
        add = self.action('add'); add['exercise_id'] = self.exercise.pk
        set_flag(FLAG, enabled=False, reason='Rollback')
        for url, data in [(self.edit_url, exercise_data), (self.play_url, play_data),
                          (reverse('classbook:playbook_add_exercise', args=[self.playbook.pk]), add)]:
            self.assertEqual(self.client.post(url, data).status_code, 400)
        self.assertTemplateUsed(self.client.get(self.edit_url), 'classbook/exercise_form.html')
        self.exercise.refresh_from_db(); self.assertEqual(self.exercise.edit_revision, 0)


class PreparationConcurrencyTests(ClassbookFixtureMixin, TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    def test_start_locks_exercises_before_creating_immutable_snapshots(self):
        set_flag(FLAG, enabled=True, reason='PG snapshot lock')
        self.client.force_login(self.teacher)
        data = {'frontend_v1_classbook': '1', 'confirm_scope': 'yes', 'revision': revision(
            self.teacher, 'start', self.playbook, cohort=self.cohort, lesson=self.lesson)}
        with CaptureQueriesContext(connection) as queries:
            response = self.client.post(reverse('classbook:session_start', args=[self.cohort.pk, self.lesson.pk]), data)
        self.assertEqual(response.status_code, 302)
        sql = [q['sql'] for q in queries.captured_queries]
        lock = next(i for i, query in enumerate(sql) if 'FROM "classbook_exercise"' in query and 'FOR UPDATE' in query)
        snapshot = next(i for i, query in enumerate(sql) if 'INSERT INTO "classbook_activityrun"' in query)
        self.assertLess(lock, snapshot)

    @skipUnlessDBFeature('has_select_for_update')
    def test_parallel_add_same_snapshot_once(self):
        set_flag(FLAG, enabled=True, reason='PG race')
        data = {'frontend_v1_classbook': '1', 'confirm_scope': 'yes', 'exercise_id': self.exercise.pk,
                'revision': revision(self.teacher, 'add', self.playbook, cohort=self.cohort, lesson=self.lesson)}
        url = reverse('classbook:playbook_add_exercise', args=[self.playbook.pk])
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(self.teacher)
        barrier = Barrier(2)

        def post(client):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return client.post(url, data).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(post, clients))
        self.assertEqual(sorted(statuses), [302, 409])
        self.assertEqual(self.playbook.exercise_steps.count(), 2)
