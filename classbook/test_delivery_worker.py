import asyncio
from types import SimpleNamespace

from asgiref.sync import sync_to_async
from django.db import connections
from django.test import TestCase, TransactionTestCase

from aicontrol.models import WorkerHeartbeat
from bot.outbox import process_outbox_once
from users.models import Notification

from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import _telegram_probe

from .delivery import claim_pending_group_deliveries, mark_group_delivery_failed
from .models import TelegramGroupDelivery


class _FakeMethod:
    """Aiogram xatolari `method` talab qiladi; unga faqat nom kerak."""

    chat_id = 1


def _retry_after(seconds):
    return TelegramRetryAfter(_FakeMethod(), "Too Many Requests", seconds)
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


class ClassbookGroupDeliveryRetryTests(ClassbookFixtureMixin, TestCase):
    """Guruh navbati DM navbati bilan **bitta** siyosatni ishlatadimi (F10).

    Ilgari `classbook/delivery.py` o'zining `MAX_ATTEMPTS = 3` ini yuritardi va
    hamma nosozlikni bir xil hisoblardi. Guruh xabari uchun bu sezilarli: `429`
    bitta urinishni yeb qo'ysa, o'qituvchi "Ochish" bosgan mashq e'loni guruhga
    umuman bormasligi mumkin — va jonli dars o'rtasida buni tuzatib bo'lmaydi.
    """

    def _pending(self):
        session = self.start()
        return TelegramGroupDelivery.objects.filter(
            session=session, status=TelegramGroupDelivery.STATUS_PENDING
        ).first()

    def test_flood_control_does_not_spend_an_attempt(self):
        delivery = self._pending()
        self.assertIsNotNone(delivery)
        mark_group_delivery_failed(delivery, _retry_after(4))

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, TelegramGroupDelivery.STATUS_PENDING)
        self.assertEqual(delivery.attempts, 0)
        self.assertEqual(delivery.failure_kind, "rate_limited")
        self.assertIsNotNone(delivery.next_attempt_at)
        # Backoff tugamaguncha qator olinmaydi.
        claimed_ids = [row.id for row in claim_pending_group_deliveries()]
        self.assertNotIn(delivery.id, claimed_ids)

    def test_kicked_from_the_group_dead_letters_at_once(self):
        """Bot guruhdan chiqarilgan bo'lsa qayta urinish hech narsa bermaydi."""
        delivery = self._pending()
        mark_group_delivery_failed(
            delivery, TelegramForbiddenError(_FakeMethod(), "bot was kicked from the group chat")
        )

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, TelegramGroupDelivery.STATUS_FAILED)
        self.assertEqual(delivery.attempts, 1)
        self.assertEqual(delivery.failure_kind, "permanent")

    def test_control_center_separates_permanent_failures_from_backoff_waits(self):
        """Owner uchun "hech qachon tuzalmaydi" va "o'zi tuzaladi" bir xil ko'rinmasin."""
        session = self.start()
        rows = list(
            TelegramGroupDelivery.objects.filter(session=session).order_by("id")[:1]
        )
        mark_group_delivery_failed(
            rows[0], TelegramForbiddenError(_FakeMethod(), "bot was kicked from the group chat")
        )
        extra = TelegramGroupDelivery.objects.create(
            session=session,
            external_key="retry-backoff-probe",
            chat_id=session.chat_id,
            text="kutayotgan xabar",
        )
        mark_group_delivery_failed(extra, _retry_after(60))

        result = _telegram_probe(capability_by_slug("telegram_outbox"))
        details = dict(result.details)
        self.assertEqual(details["dead_permanent"], "1")
        self.assertEqual(details["waiting_backoff"], "1")
