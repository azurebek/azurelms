"""Delivery support reads existing evidence without impersonating a learner."""

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from bot.models import TelegramOutbox
from core.flags import set_flag
from core.student_support_delivery import PAGE_SIZE, build_student_delivery
from users.models import Notification, NotificationBroadcast, ReminderSettings
from users.notification_service import send_broadcast


@override_settings(GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='')
class StudentSupportDeliveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(
            username='delivery-owner', email='delivery-owner@example.test', is_superuser=True, is_staff=True,
        )
        cls.staff = User.objects.create_user(
            username='delivery-staff', email='delivery-staff@example.test', is_staff=True,
        )
        cls.student = User.objects.create_user(username='delivery-student', email='delivery-student@example.test')
        cls.other = User.objects.create_user(username='delivery-other', email='delivery-other@example.test')

    def inspect(self, **kwargs):
        params = {'actor': self.owner, 'student_id': self.student.pk}
        params.update(kwargs)
        return build_student_delivery(**params)

    def note(self, *, student=None, **kwargs):
        return Notification.objects.create(
            recipient=student or self.student, message='Private message body',
            **{'title': 'Dars haqida', **kwargs},
        )

    def outbox(self, *, status=TelegramOutbox.STATUS_PENDING, note=None, **kwargs):
        note = note or self.note()
        return TelegramOutbox.objects.create(
            notification=note, telegram_id=99112233, status=status, **kwargs,
        )

    def test_owner_can_inspect_unenrolled_and_inactive_learner_account(self):
        get_user_model().objects.filter(pk=self.student.pk).update(is_active=False)
        note = self.note()
        result = self.inspect()
        self.assertEqual([row['id'] for row in result['rows']], [note.pk])
        self.assertIn('barcha kurslari', result['scope_label'])
        self.assertIn('cheklamaydi', result['scope_note'])

    def test_anonymous_staff_and_student_are_denied(self):
        for actor in (AnonymousUser(), self.staff, self.student):
            with self.subTest(actor=actor), self.assertRaises(PermissionDenied):
                self.inspect(actor=actor)

    def test_owner_permissions_are_reloaded_not_trusted_from_stale_object(self):
        User = get_user_model()
        for changes in ({'is_superuser': False}, {'is_superuser': True, 'is_active': False}):
            User.objects.filter(pk=self.owner.pk).update(**changes)
            with self.subTest(changes=changes), self.assertRaises(PermissionDenied):
                self.inspect()
        User.objects.filter(pk=self.owner.pk).delete()
        with self.assertRaises(PermissionDenied):
            self.inspect()

    def test_staff_superuser_and_deleted_targets_are_excluded(self):
        for target in (self.staff, self.owner):
            with self.subTest(target=target.pk), self.assertRaises(get_user_model().DoesNotExist):
                self.inspect(student_id=target.pk)
        get_user_model().objects.filter(pk=self.student.pk).update(is_staff=True)
        with self.assertRaises(get_user_model().DoesNotExist):
            self.inspect()
        get_user_model().objects.filter(pk=self.student.pk).delete()
        with self.assertRaises(get_user_model().DoesNotExist):
            self.inspect()

    def test_empty_evidence_does_not_claim_a_failed_or_suppressed_notification(self):
        self.note(student=self.other, title='Other learner private title')
        result = self.inspect()
        self.assertEqual(result['summary']['total'], 0)
        self.assertEqual(result['rows'], [])
        self.assertIn('isbotlamaydi', result['empty_message'])

    def test_website_read_flag_is_separate_from_telegram_delivery(self):
        unread_sent = self.note(is_read=False)
        self.outbox(note=unread_sent, status=TelegramOutbox.STATUS_SENT, sent_at=timezone.now())
        read_failed = self.note(is_read=True, read_at=timezone.now())
        self.outbox(note=read_failed, status=TelegramOutbox.STATUS_FAILED)
        rows = {row['id']: row for row in self.inspect()['rows']}
        self.assertEqual(rows[unread_sent.pk]['telegram_state'], 'sent')
        self.assertIn('belgilanmagan', rows[unread_sent.pk]['website_label'])
        self.assertIn('o‘qiganini bildirmaydi', rows[unread_sent.pk]['detail'])
        self.assertEqual(rows[read_failed.pk]['telegram_state'], 'failed')
        self.assertIn('o‘qilgan deb belgilangan', rows[read_failed.pk]['website_label'])

    def test_no_outbox_is_honest_when_current_telegram_is_absent(self):
        self.note()
        result = self.inspect()
        row = result['rows'][0]
        self.assertFalse(result['telegram_connected'])
        self.assertEqual(row['telegram_state'], 'absent')
        self.assertIn('Hozir', row['detail'])
        self.assertIn('qayd etilmagan', row['detail'])
        self.assertEqual(row['action_url'], '')

    def test_broadcast_without_outbox_does_not_claim_current_link_caused_it(self):
        # Canonical broadcasts bulk-create notes, bypassing the mirror signal.
        # A current link is insufficient evidence for a historical cause.
        get_user_model().objects.filter(pk=self.student.pk).update(telegram_id=99112233)
        broadcast = NotificationBroadcast.objects.create(
            target_type=NotificationBroadcast.TARGET_USERS, title='E’lon', message='Private broadcast',
        )
        broadcast.recipients.add(self.student)
        self.assertEqual(send_broadcast(broadcast), 1)
        result = self.inspect()
        self.assertTrue(result['telegram_connected'])
        self.assertEqual(result['rows'][0]['telegram_state'], 'absent')
        self.assertIn('qayd etilmagan', result['rows'][0]['detail'])
        self.assertNotIn('bog‘lanmagan', result['rows'][0]['detail'])

    def test_pause_preserves_queued_sending_sent_and_failed_evidence(self):
        ids = {}
        for state in ('pending', 'sending', 'sent', 'failed'):
            ids[state] = self.outbox(status=state).notification_id
        set_flag('telegram_outbox_sending', enabled=False, reason='Synthetic delivery pause')
        result = self.inspect()
        rows = {row['id']: row for row in result['rows']}
        self.assertFalse(result['sending_enabled'])
        self.assertEqual(rows[ids['pending']]['telegram_state'], 'queued')
        self.assertIn('vaqtincha to‘xtatilgan', rows[ids['pending']]['detail'])
        for state in ('sending', 'sent', 'failed'):
            self.assertEqual(rows[ids[state]]['telegram_state'], state)
            self.assertNotIn('vaqtincha to‘xtatilgan', rows[ids[state]]['detail'])

    def test_quiet_hours_use_canonical_policy_and_only_hold_reminders(self):
        now = timezone.now()
        hour = timezone.localtime(now).hour
        ReminderSettings.objects.create(quiet_hours_start=hour, quiet_hours_end=(hour + 1) % 24)
        reminder = self.note(category=Notification.CATEGORY_REMINDER)
        subscription = self.note(category=Notification.CATEGORY_SUBSCRIPTION)
        self.outbox(note=reminder)
        self.outbox(note=subscription)
        with patch('core.student_support_delivery.timezone.now', return_value=now):
            rows = {row['id']: row for row in self.inspect()['rows']}
        self.assertIn('tinch vaqt', rows[reminder.pk]['detail'])
        self.assertNotIn('tinch vaqt', rows[subscription.pk]['detail'])
        self.assertEqual(rows[reminder.pk]['telegram_state'], 'queued')

    def test_retry_reasons_and_timestamp_do_not_claim_a_successful_send(self):
        future = timezone.now() + timedelta(hours=1)
        ids = {}
        for kind in ('config', 'rate_limited', 'transient'):
            ids[kind] = self.outbox(failure_kind=kind, next_attempt_at=future).notification_id
        rows = {row['id']: row for row in self.inspect()['rows']}
        self.assertIn('sozlamasida muammo', rows[ids['config']]['detail'])
        self.assertEqual(rows[ids['config']]['action_url'], '')
        self.assertIn('sekinlatishni', rows[ids['rate_limited']]['detail'])
        self.assertIn('Keyingi avtomatik', rows[ids['transient']]['detail'])
        for row in rows.values():
            self.assertEqual(row['telegram_state'], 'queued')
            self.assertEqual(row['next_attempt_at'], future)

    def test_terminal_action_selects_exact_learner_and_notification(self):
        item = self.outbox(status=TelegramOutbox.STATUS_FAILED, failure_kind='permanent')
        row = self.inspect()['rows'][0]
        self.assertIn('mumkin', row['detail'])
        self.assertEqual(row['action_url'], reverse('backoffice_dead_letter')
                         + f'?student={self.student.pk}&notification={item.notification_id}')
        self.assertEqual(row['action_label'], 'Shu xabarni tekshirish')

    def test_changed_and_removed_telegram_binding_keep_historical_state_and_warn(self):
        item = self.outbox(status=TelegramOutbox.STATUS_SENT, sent_at=timezone.now())
        User = get_user_model()
        User.objects.filter(pk=self.student.pk).update(telegram_id=item.telegram_id)
        self.assertEqual(self.inspect()['rows'][0]['target_warning'], '')
        User.objects.filter(pk=self.student.pk).update(telegram_id=44556677)
        row = self.inspect()['rows'][0]
        self.assertEqual(row['telegram_state'], 'sent')
        self.assertIn('mos emas', row['target_warning'])
        User.objects.filter(pk=self.student.pk).update(telegram_id=None)
        self.assertIn('avvalgi', self.inspect()['rows'][0]['target_warning'])

    def test_pagination_is_bounded_and_counts_only_selected_learner(self):
        notes = [self.note(title=f'Xabar {index}') for index in range(PAGE_SIZE + 3)]
        same_time = timezone.now()
        Notification.objects.filter(pk__in=[note.pk for note in notes]).update(created_at=same_time)
        self.note(student=self.other)
        first, second = self.inspect(), self.inspect(page=2)
        self.assertEqual(first['summary']['total'], PAGE_SIZE + 3)
        self.assertEqual(first['summary']['absent'], PAGE_SIZE + 3)
        self.assertEqual(len(first['rows']), PAGE_SIZE)
        self.assertEqual(len(second['rows']), 3)
        self.assertEqual([row['id'] for row in first['rows'] + second['rows']],
                         sorted([note.pk for note in notes], reverse=True))
        self.assertTrue(first['page_obj'].has_next())
        self.assertTrue(second['page_obj'].has_previous())

    def test_projection_does_not_load_or_expose_bodies_errors_tokens_or_target_ids(self):
        note = self.note(title='Public short title', external_key='private-external-key', url='/private/secret-path/')
        self.outbox(note=note, status=TelegramOutbox.STATUS_FAILED,
                    last_error='private-provider-error-secret', claim_token='private-claim-token')
        with CaptureQueriesContext(connection) as queries:
            result = self.inspect()
        text = repr(result['rows'])
        for private in ('Private message body', 'private-provider-error-secret', 'private-claim-token',
                        'private-external-key', '/private/secret-path/', '99112233', self.student.email):
            self.assertNotIn(private, text)
        sql = '\n'.join(query['sql'] for query in queries if 'FROM "users_notification"' in query['sql'])
        for field in ('"message"', '"last_error"', '"claim_token"', '"external_key"', '"url"', '"email"'):
            self.assertNotIn(field, sql)
        self.assertIn('LIMIT 1', sql)

    def test_projection_executes_no_writes_and_does_not_initialize_settings(self):
        self.outbox(next_attempt_at=timezone.now() + timedelta(minutes=10))
        before_notes = list(Notification.objects.values())
        before_outbox = list(TelegramOutbox.objects.values())
        self.assertFalse(ReminderSettings.objects.exists())
        with CaptureQueriesContext(connection) as queries:
            self.inspect()
        write_queries = [query['sql'] for query in queries
                         if query['sql'].lstrip().upper().startswith(('UPDATE', 'INSERT', 'DELETE'))]
        self.assertEqual(write_queries, [])
        self.assertFalse(ReminderSettings.objects.exists())
        self.assertEqual(list(Notification.objects.values()), before_notes)
        self.assertEqual(list(TelegramOutbox.objects.values()), before_outbox)

    def test_many_rows_do_not_cause_per_notification_queries(self):
        self.outbox()
        with CaptureQueriesContext(connection) as first_queries:
            self.inspect()
        for _ in range(PAGE_SIZE + 2):
            self.outbox()
        with CaptureQueriesContext(connection) as many_queries:
            result = self.inspect()
        self.assertEqual(len(many_queries), len(first_queries))
        self.assertEqual(len(result['rows']), PAGE_SIZE)

    def test_unknown_stored_state_is_not_presented_as_delivered(self):
        self.outbox(status='legacy')
        row = self.inspect()['rows'][0]
        self.assertEqual(row['telegram_state'], 'unknown')
        self.assertIn('aniqlanmagan', row['status_label'])

    def test_failed_filter_finds_older_rows_and_paginates_with_account_wide_counts(self):
        failed_ids = [self.outbox(status=TelegramOutbox.STATUS_FAILED).notification_id for _ in range(20)]
        for index in range(20):
            self.note(title=f'Yangi xabar {index}')
        self.outbox(note=self.note(student=self.other), status=TelegramOutbox.STATUS_FAILED)
        all_rows = self.inspect()
        self.assertEqual(all_rows['selected_status'], 'all')
        self.assertTrue(all(row['telegram_state'] == 'absent' for row in all_rows['rows']))
        first, second = self.inspect(status='failed'), self.inspect(status='failed', page=2)
        self.assertEqual(first['summary'], all_rows['summary'])
        self.assertEqual(first['summary']['total'], 40)
        self.assertEqual(first['summary']['failed'], 20)
        self.assertEqual(first['summary']['absent'], 20)
        self.assertEqual(first['page_obj'].paginator.count, 20)
        self.assertEqual(first['page_obj'].paginator.num_pages, 2)
        self.assertEqual(first['selected_status'], 'failed')
        self.assertEqual(len(first['rows']), PAGE_SIZE)
        self.assertEqual([row['id'] for row in first['rows'] + second['rows']], list(reversed(failed_ids)))
        self.assertTrue(all(row['telegram_state'] == 'failed' for row in first['rows'] + second['rows']))

    def test_empty_failed_filter_does_not_claim_account_has_no_notifications(self):
        self.outbox(status=TelegramOutbox.STATUS_SENT)
        result = self.inspect(status='failed')
        self.assertEqual(result['rows'], [])
        self.assertEqual(result['page_obj'].paginator.count, 0)
        self.assertEqual(result['summary']['total'], 1)
        self.assertEqual(result['summary']['sent'], 1)
        self.assertIn('yuborishi to‘xtagan', result['empty_message'])
        self.assertNotIn('saqlangan bildirishnoma topilmadi', result['empty_message'])

    def test_invalid_delivery_filter_is_rejected(self):
        for value in ('pending', '', None, 1, ['failed']):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.inspect(status=value)
