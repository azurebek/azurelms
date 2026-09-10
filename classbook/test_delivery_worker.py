import asyncio
from types import SimpleNamespace

from asgiref.sync import sync_to_async
from django.db import connections
from django.test import TransactionTestCase

from aicontrol.models import WorkerHeartbeat
from bot.outbox import process_outbox_once
from users.models import Notification

from .models import TelegramGroupDelivery
from .tests import ClassbookFixtureMixin


class ClassbookDeliveryWorkerTests(ClassbookFixtureMixin, TransactionTestCase):
    reset_sequences = True

    def test_existing_outbox_worker_sends_group_messages_and_persists_message_id(self):
        session = self.start()
        Notification.objects.create(
            recipient=self.student,
            external_key="classbook-worker-priority",
            title="Eski DM",
            message="Guruh buyrug'idan keyin borishi kerak.",
        )

        class FakeBot:
            def __init__(self):
                self.calls = []

            async def send_message(self, chat_id, text, **kwargs):
                self.calls.append((chat_id, text, kwargs))
                return SimpleNamespace(message_id=700 + len(self.calls))

        bot = FakeBot()

        async def run_cycle():
            sent = await process_outbox_once(bot)
            await sync_to_async(connections.close_all)()
            return sent

        sent = asyncio.run(run_cycle())
        session.refresh_from_db()

        self.assertEqual(sent, 3)
        self.assertEqual(len(bot.calls), 3)
        self.assertEqual(bot.calls[0][0], self.cohort.telegram_chat_id)
        self.assertEqual(bot.calls[1][0], self.cohort.telegram_chat_id)
        self.assertEqual(bot.calls[2][0], self.student.telegram_id)
        self.assertEqual(
            TelegramGroupDelivery.objects.filter(status=TelegramGroupDelivery.STATUS_SENT).count(),
            2,
        )
        self.assertIsNotNone(session.attendance_message_id)
        self.assertTrue(WorkerHeartbeat.objects.filter(name="telegram-outbox").exists())
