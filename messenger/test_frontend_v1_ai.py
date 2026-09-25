import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from aicontrol.models import FeatureFlag
from cohorts.models import Cohort, Enrollment
from courses.models import Course, Module, Lesson
from core.flags import flag_enabled
from messenger.models import ChatRoom, Message, AIResponseRun, AIFeedback
from messenger.signals import suppress_ai_signal


class AIMessengerV1Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('ai-v1', email='ai-v1@example.test', password='local-test-only')
        self.other = get_user_model().objects.create_user('ai-v1-other', email='ai-other@example.test')
        self.room = ChatRoom.objects.create(name='Private AI', room_type='ai')
        self.room.participants.add(self.user)
        self.foreign = ChatRoom.objects.create(name='Foreign private name', room_type='ai')
        self.foreign.participants.add(self.other)
        self.client.force_login(self.user)
        self.url = reverse('messenger:ai_room', args=[self.room.pk])
        self.history = reverse('messenger:get_room_messages', args=[self.room.pk])
        self.flag = FeatureFlag.objects.create(slug='frontend_v1_ai_messenger', enabled=True)

    def message(self, text='Question', **kwargs):
        with suppress_ai_signal():
            return Message.objects.create(room=self.room, text=text, **kwargs)

    def lesson(self, enrolled):
        course = Course.objects.create(title='Context course', level='beginner')
        module = Module.objects.create(course=course, title='Context module')
        lesson = Lesson.objects.create(module=module, title='Context lesson')
        cohort = Cohort.objects.create(course=course, name='Context group', start_date=datetime.date(2026, 9, 1))
        if enrolled:
            Enrollment.objects.create(student=self.user, cohort=cohort, status='active')
        return lesson

    def test_default_off_independent_of_human_flag(self):
        self.flag.delete()
        self.assertFalse(flag_enabled('frontend_v1_ai_messenger'))
        FeatureFlag.objects.create(slug='frontend_v1_messenger', enabled=True)
        self.assertTemplateUsed(self.client.get(self.url), 'messenger/ai.html')

    def test_v1_namespace_and_exact_room_no_provider_call(self):
        with patch('messenger.tasks.generate_ai_response.delay') as call:
            response = self.client.get(self.url)
        call.assert_not_called()
        self.assertTemplateUsed(response, 'frontend_v1/ai_messenger.html')
        self.assertContains(response, 'messenger-ai.mjs')
        self.assertNotContains(response, 'messenger-chat.js')
        self.assertNotContains(response, 'Foreign private name')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response.context['active_chat_room'].pk, self.room.pk)
        self.assertEqual(response.context['active_nav'], 'messenger:ai')

    def test_foreign_room_and_history_denied_and_login_required(self):
        self.assertEqual(self.client.get(reverse('messenger:ai_room', args=[self.foreign.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('messenger:get_room_messages', args=[self.foreign.pk])).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_teacher_ai_nav_with_human_flag_off(self):
        self.user.is_staff = True
        self.user.save(update_fields=['is_staff'])
        FeatureFlag.objects.create(slug='frontend_v1_teacher', enabled=True)
        response = self.client.get(self.url)
        self.assertEqual(response.context['frontend_v1_workspace'], 'Ustoz maydoni')
        self.assertEqual(response.context['active_nav'], 'messenger:ai')

    def test_navigation_does_not_label_ai_legacy_when_enabled(self):
        response = self.client.get(self.url)
        self.assertIn('messenger:ai', [p['name'] for p in response.context['frontend_v1_nav']])
        self.assertNotIn(reverse('messenger:ai'), [p['url'] for p in response.context['frontend_v1_legacy_nav']])

    def test_choices_are_canonical(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context['ai_model_choices'], self.user.effective_ai_model_choices())
        self.assertEqual(response.context['ai_skill_choices'], self.user.effective_ai_skill_choices())

    def test_context_survives_room_link_and_new_chat(self):
        lesson = self.lesson(True)
        response = self.client.get(self.url, {'lesson': lesson.pk})
        self.assertContains(response, f'data-context-lesson="{lesson.pk}"')
        self.assertContains(response, self.url + f'?lesson={lesson.pk}')
        new = self.client.post(reverse('messenger:new_ai_chat'), {'lesson': lesson.pk})
        self.assertTrue(new.url.endswith(f'?lesson={lesson.pk}'))

    def test_foreign_or_invalid_context_does_not_survive_post(self):
        lesson = self.lesson(False)
        response = self.client.get(self.url, {'lesson': lesson.pk})
        self.assertContains(response, 'data-context-lesson=""')
        for value in [str(lesson.pk), '9' * 500, 'https://example.test']:
            response = self.client.post(reverse('messenger:new_ai_chat'), {'lesson': value})
            self.assertNotIn('?', response.url)

    def test_new_chat_post_csrf_and_empty_room_reuse(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(reverse('messenger:new_ai_chat')).status_code, 403)
        self.assertEqual(self.client.get(reverse('messenger:new_ai_chat')).status_code, 405)
        one = self.client.post(reverse('messenger:new_ai_chat'))
        two = self.client.post(reverse('messenger:new_ai_chat'))
        self.assertEqual(one.url, two.url)

    def test_run_history_latest_only_safe_and_scoped(self):
        prompt = self.message(sender=self.user)
        AIResponseRun.objects.create(room=self.room, student=self.user, user_message=prompt, status='failed', error_message='secret provider detail')
        latest = AIResponseRun.objects.create(room=self.room, student=self.user, user_message=prompt, status='running', user_question='private raw prompt', metadata={'secret': 'never export'})
        # Even inconsistent foreign-room/student telemetry must not leak.
        AIResponseRun.objects.create(room=self.foreign, student=self.other, user_message=prompt, status='failed')
        response = self.client.get(self.history)
        self.assertEqual(response.json()['ai_runs'], [{'run_id': latest.pk, 'user_message_id': prompt.pk, 'status': 'running', 'ai_message_id': None}])
        for secret in ['secret provider', 'private raw', 'never export']:
            self.assertNotContains(response, secret)

    def test_feedback_history_roundtrip_and_foreign_denial(self):
        prompt = self.message(sender=self.user)
        answer = self.message(text='Test answer', is_ai_response=True)
        AIResponseRun.objects.create(room=self.room, student=self.user, user_message=prompt, ai_message=answer, status='fallback')
        url = reverse('messenger:submit_ai_feedback', args=[answer.pk])
        self.assertEqual(self.client.post(url, {'rating': 1}, content_type='application/json').status_code, 200)
        payload = self.client.get(self.history).json()
        self.assertEqual(payload['messages'][-1]['feedback']['rating'], 1)
        self.assertEqual(payload['messages'][-1]['regenerate_user_message_id'], prompt.pk)
        self.assertEqual(payload['ai_runs'][0]['status'], 'fallback')
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url, {'rating': -1}, content_type='application/json').status_code, 403)
        self.assertEqual(AIFeedback.objects.get(message=answer).rating, 1)

    def test_preferences_keep_existing_backend_and_no_provider_request(self):
        model = self.user.effective_ai_model_choices()[0][0]
        with patch('messenger.tasks.generate_ai_response.delay') as call:
            response = self.client.post(reverse('update_ai_model'), {'ai_model': model}, HTTP_ACCEPT='application/json')
            self.assertEqual(response.json()['ai_model'], model)
            response = self.client.post(reverse('update_ai_skill'), {'ai_skill': 'auto'}, HTTP_ACCEPT='application/json')
            self.assertEqual(response.json()['ai_skill'], 'auto')
        call.assert_not_called()
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_model, model)

    def test_flag_rollback_keeps_exact_room_messages_and_preferences(self):
        prompt = self.message(sender=self.user)
        self.flag.enabled = False
        self.flag.save()
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'messenger/ai.html')
        self.assertEqual(response.context['active_chat_room'].pk, self.room.pk)
        self.assertTrue(Message.objects.filter(pk=prompt.pk).exists())
