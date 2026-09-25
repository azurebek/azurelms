import datetime
import tempfile
from unittest.mock import AsyncMock, patch

from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from aicontrol.models import FeatureFlag
from cohorts.models import Cohort, Enrollment
from courses.models import Course
from messenger.consumers import ChatConsumer
from messenger.models import ChatRoom, ChatRoomUserState, Message
from messenger.views import _message_payload


class HumanMessengerV1Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('chat-v1', password='test-pass', email='chat@example.test')
        self.teacher = User.objects.create_user('chat-teacher', is_staff=True, email='teacher@example.test')
        self.other = User.objects.create_user('chat-other', email='other@example.test')
        self.groups = []
        for name in ['First group', 'Second group']:
            course = Course.objects.create(title=name, level='beginner')
            cohort = Cohort.objects.create(name=name, course=course, start_date=datetime.date(2026, 9, 1))
            Enrollment.objects.create(student=self.user, cohort=cohort, status='active')
            self.groups.append(ChatRoom.objects.get(room_type='group', cohort=cohort))
        self.room = self.groups[0]
        self.room.participants.add(self.teacher)
        self.private = ChatRoom.objects.get(room_type='private', participants=self.user)
        self.private.participants.add(self.teacher)
        FeatureFlag.objects.create(slug='frontend_v1_messenger', enabled=True)
        self.client.force_login(self.user)

    def history(self, room=None, **params):
        return self.client.get(reverse('messenger:get_room_messages', args=[(room or self.room).pk]), params)

    def test_flag_selects_only_human_templates_and_no_legacy_assets(self):
        for name in ['group', 'tutor']:
            response = self.client.get(reverse('messenger:' + name))
            self.assertTemplateUsed(response, 'frontend_v1/messenger.html')
            self.assertContains(response, 'data-chat-root')
            self.assertContains(response, 'messenger-state.mjs')
            self.assertNotContains(response, 'messenger-chat.js')
            self.assertIn('no-store', response['Cache-Control'])
        self.assertTemplateUsed(self.client.get(reverse('messenger:ai')), 'messenger/ai.html')
        FeatureFlag.objects.filter(slug='frontend_v1_messenger').delete()
        self.assertTemplateUsed(self.client.get(reverse('messenger:group')), 'messenger/group.html')

    def test_all_allowed_rooms_and_exact_selection(self):
        response = self.client.get(reverse('messenger:group'), {'room': self.room.pk})
        self.assertEqual(response.context['active_chat_room'].pk, self.room.pk)
        self.assertEqual({r.pk for r in response.context['human_rooms']}, {r.pk for r in self.groups} | {self.private.pk})
        for room in self.groups:
            self.assertContains(response, f'?room={room.pk}')

    def test_invalid_room_never_falls_back_or_marks_a_different_room_read(self):
        for value in ['0', '-1', 'nope', '１２', str(self.private.pk), str(10**30)]:
            with self.subTest(value=value):
                self.assertEqual(self.client.get(reverse('messenger:group'), {'room': value}).status_code, 404)
        self.assertEqual(self.client.get(reverse('messenger:group') + f'?room={self.room.pk}&room={self.groups[1].pk}').status_code, 404)
        self.assertFalse(ChatRoomUserState.objects.filter(user=self.user, last_read_at__isnull=False).exists())

    def test_only_selected_room_marked_read(self):
        self.client.get(reverse('messenger:group'), {'room': self.room.pk})
        self.assertIsNotNone(ChatRoomUserState.objects.get(room=self.room, user=self.user).last_read_at)
        self.assertIsNone(ChatRoomUserState.objects.get(room=self.groups[1], user=self.user).last_read_at)

    def test_flag_rollback_keeps_explicit_room_identity_and_rejects_foreign_type(self):
        FeatureFlag.objects.filter(slug='frontend_v1_messenger').update(enabled=False)
        response = self.client.get(reverse('messenger:group'), {'room': self.room.pk})
        self.assertTemplateUsed(response, 'messenger/group.html')
        self.assertEqual(response.context['active_chat_room'].pk, self.room.pk)
        self.assertEqual(response.context['group_room'].pk, self.room.pk)
        self.assertEqual(self.client.get(reverse('messenger:group'), {'room': self.private.pk}).status_code, 404)

    def test_staff_membership_survives_page_and_room_list(self):
        self.client.force_login(self.teacher)
        for url in [reverse('messenger:group') + f'?room={self.room.pk}', reverse('messenger:get_user_rooms')]:
            self.assertEqual(self.client.get(url).status_code, 200)
            self.assertTrue(self.room.participants.filter(pk=self.teacher.pk).exists())

    def test_navigation_retains_teacher_workspace_and_links_from_dashboard(self):
        FeatureFlag.objects.create(slug='frontend_v1_learning', enabled=True)
        FeatureFlag.objects.create(slug='frontend_v1_teacher', enabled=True)
        dashboard = self.client.get(reverse('dashboard'))
        self.assertTrue(any(item['name'] == 'messenger:group' for item in dashboard.context['frontend_v1_nav']))
        self.client.force_login(self.teacher)
        chat = self.client.get(reverse('messenger:group'), {'room': self.room.pk})
        home = self.client.get(reverse('teacher_dashboard'))
        self.assertEqual(chat.context['frontend_v1_workspace'], 'Ustoz maydoni')
        self.assertEqual(chat.context['frontend_v1_nav'], home.context['frontend_v1_nav'])

    def test_empty_expired_and_anonymous(self):
        Enrollment.objects.filter(student=self.user).update(status='expired')
        response = self.client.get(reverse('messenger:group'))
        self.assertContains(response, 'Hozircha ruxsatli suhbat yo‘q')
        self.assertNotContains(response, 'data-composer')
        self.assertEqual(self.client.get(reverse('messenger:group'), {'room': self.room.pk}).status_code, 404)
        self.assertEqual(self.history().status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('messenger:group')).status_code, 302)

    def test_scope_changes_after_login_and_room_name_is_escaped(self):
        self.room.name = '<script>alert(1)</script>'; self.room.save()
        first = self.client.get(reverse('messenger:group'), {'room': self.room.pk})
        self.assertContains(first, '&lt;script&gt;')
        self.client.logout(); self.client.force_login(self.user)
        second = self.client.get(reverse('messenger:group'))
        self.assertNotEqual(first.context['chat_scope'], second.context['chat_scope'])

    def test_latest_history_pages_ties_no_gaps_and_scoped_cursor(self):
        Message.objects.bulk_create([Message(room=self.room, sender=self.user, text=f'Message {i}') for i in range(205)])
        from django.utils import timezone
        Message.objects.filter(room=self.room).update(created_at=timezone.now())
        expected = list(Message.objects.filter(room=self.room).order_by('pk').values_list('pk', flat=True))
        first = self.history().json()
        self.assertEqual([m['id'] for m in first['messages']], expected[-100:])
        second = self.history(before=first['before']).json()
        third = self.history(before=second['before']).json()
        self.assertEqual([m['id'] for m in third['messages'] + second['messages'] + first['messages']], expected)
        self.assertFalse(third['has_more'])
        foreign = Message.objects.create(room=self.private, sender=self.user, text='Elsewhere')
        self.assertEqual(self.history(before=foreign.pk).status_code, 404)
        for value in ['bad', '１２', str(10**30)]:
            self.assertEqual(self.history(before=value).status_code, 400)

    def test_exact_message_lookup_is_room_scoped(self):
        message = Message.objects.create(room=self.room, sender=self.user, text='Own')
        self.assertEqual(self.history(message=message.pk).json()['messages'][0]['text'], 'Own')
        self.assertEqual(self.history(room=self.private, message=message.pk).status_code, 404)

    def test_edit_delete_revision_and_foreign_ownership(self):
        message = Message.objects.create(room=self.room, sender=self.user, text='Original')
        revision = _message_payload(message, self.user)['revision']
        edit = reverse('messenger:edit_message', args=[message.pk])
        response = self.client.post(edit, {'revision': revision, 'text': 'Changed'}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post(edit, {'revision': revision, 'text': 'Stale'}, content_type='application/json').status_code, 409)
        delete = reverse('messenger:delete_message', args=[message.pk])
        self.assertEqual(self.client.post(delete, {'revision': revision}, content_type='application/json').status_code, 409)
        message.refresh_from_db(); self.assertEqual(message.text, 'Changed')
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(edit, {'text': 'Not own'}, content_type='application/json').status_code, 403)
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(delete, {'revision': _message_payload(message, self.user)['revision']}, content_type='application/json').status_code, 200)
        message.refresh_from_db(); self.assertTrue(message.is_deleted)

    def test_csrf_required_for_all_mutations(self):
        client = Client(enforce_csrf_checks=True); client.force_login(self.user)
        message = Message.objects.create(room=self.room, sender=self.user, text='Original')
        for name, args in [('edit_message', [message.pk]), ('delete_message', [message.pk]), ('upload_message_attachment', []), ('toggle_room_pin', [self.room.pk])]:
            self.assertEqual(client.post(reverse('messenger:' + name, args=args)).status_code, 403)

    def test_attachment_real_validator_private_download_and_deleted_gate(self):
        from library.test_resources import pdf_upload
        with tempfile.TemporaryDirectory() as media, override_settings(PRIVATE_MEDIA_ROOT=media):
            response = self.client.post(reverse('messenger:upload_message_attachment'), {'room_id': self.room.pk, 'text': 'PDF', 'file': pdf_upload()})
            self.assertEqual(response.status_code, 200)
            payload = response.json()['message']
            self.assertTrue(payload['attachment']['url'].startswith('/messenger/attachment/'))
            response = self.client.get(payload['attachment']['url']); self.assertEqual(response.status_code, 200); response.close()
            self.client.force_login(self.other)
            self.assertEqual(self.client.get(payload['attachment']['url']).status_code, 404)
            self.client.force_login(self.user)
            self.client.post(reverse('messenger:delete_message', args=[payload['id']]))
            self.assertEqual(self.client.get(payload['attachment']['url']).status_code, 404)


class HumanSocketV1Tests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user('socket-v1', is_staff=True, email='socket@example.test')
        self.peer = User.objects.create_user('peer-v1', is_staff=True, email='peer@example.test')
        self.room = ChatRoom.objects.create(room_type='private', name='Human')
        self.room.participants.add(self.user, self.peer)

    async def connect(self, user):
        ws = WebsocketCommunicator(ChatConsumer.as_asgi(), f'/ws/chat/{self.room.pk}/')
        ws.scope.update(user=user, url_route={'kwargs': {'room_id': str(self.room.pk)}})
        self.assertTrue((await ws.connect())[0]); return ws

    async def test_echo_and_peer_delivery_use_server_identity(self):
        one, two = await self.connect(self.user), await self.connect(self.peer)
        try:
            with patch.object(ChatConsumer, 'dispatch_telegram_notification', new_callable=AsyncMock):
                await one.send_json_to({'action': 'message', 'message': 'Real human message', 'sender_id': self.peer.pk, 'client_message_id': 'nonce-1'})
                a, b = await one.receive_json_from(timeout=5), await two.receive_json_from(timeout=5)
                self.assertEqual(a, b); self.assertEqual(a['sender_id'], self.user.pk)
                self.assertEqual(a['client_message_id'], 'nonce-1')
                self.assertTrue(await sync_to_async(Message.objects.filter(pk=a['message_id'], text='Real human message').exists)())
        finally:
            await one.disconnect(); await two.disconnect()

    async def test_read_only_revoked_socket_receives_no_new_message_or_edit(self):
        for event in [
            {'type': 'chat_message', 'message': 'Private', 'sender_id': self.peer.pk},
            {'type': 'message_update', 'payload': {'text': 'Private edit'}},
        ]:
            await sync_to_async(self.room.participants.add)(self.user)
            ws = await self.connect(self.user)
            try:
                await sync_to_async(self.room.participants.remove)(self.user)
                await get_channel_layer().group_send(f'chat_{self.room.pk}', event)
                self.assertEqual((await ws.receive_json_from(timeout=5))['type'], 'access_revoked')
                self.assertEqual((await ws.receive_output(timeout=5))['code'], 4403)
            finally:
                await ws.disconnect()
