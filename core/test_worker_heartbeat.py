"""A2 — worker tirikligi to'g'ridan-to'g'ri o'lchanishi kerak.

Hozir Control Center Telegram outbox'ning sog'lig'ini **navbat yoshidan
taxmin qiladi**: navbatda 15 daqiqadan oshgan xabar bo'lsa AMBER, bir soatdan
oshsa RED. Bu ko'r nuqta qoldiradi — **navbat bo'sh bo'lsa o'lik worker ham
yashil ko'rinadi**. Worker tunda o'lib qolsa, ertalab birinchi bildirishnoma
yuborilmaguncha va 15 daqiqa turmaguncha hech kim bilmaydi.

Backlog A2 buni "active worker heartbeat" deb sanaydi: jarayon o'zi "men
tirikman" deb yozib turadi, holat esa navbatdan emas, shu yozuvdan o'qiladi.
"""

import datetime

from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from aicontrol.models import WorkerHeartbeat
from core.control_center import build_control_center_snapshot


class WorkerHeartbeatModelTests(TestCase):
    def test_recording_a_heartbeat_creates_the_row(self):
        WorkerHeartbeat.record("telegram-outbox", detail={"batch": 5})

        beat = WorkerHeartbeat.objects.get(name="telegram-outbox")
        self.assertEqual(beat.detail["batch"], 5)
        self.assertIsNotNone(beat.last_seen_at)

    def test_recording_again_updates_instead_of_duplicating(self):
        WorkerHeartbeat.record("telegram-outbox")
        first = WorkerHeartbeat.objects.get(name="telegram-outbox").last_seen_at

        WorkerHeartbeat.record("telegram-outbox")

        self.assertEqual(WorkerHeartbeat.objects.count(), 1)
        self.assertGreaterEqual(
            WorkerHeartbeat.objects.get(name="telegram-outbox").last_seen_at, first
        )

    def test_a_fresh_heartbeat_is_alive(self):
        WorkerHeartbeat.record("telegram-outbox")

        self.assertTrue(WorkerHeartbeat.objects.get(name="telegram-outbox").is_alive())

    def test_a_stale_heartbeat_is_not_alive(self):
        WorkerHeartbeat.record("telegram-outbox")
        WorkerHeartbeat.objects.filter(name="telegram-outbox").update(
            last_seen_at=timezone.now() - datetime.timedelta(minutes=30)
        )

        self.assertFalse(WorkerHeartbeat.objects.get(name="telegram-outbox").is_alive())


class WorkerHeartbeatCapabilityTests(TestCase):
    """Control Center endi worker tirikligini alohida ko'rsatadi."""

    def _worker_result(self):
        snapshot = build_control_center_snapshot()
        return next(
            (item for item in snapshot.results if item.definition.slug == "workers"),
            None,
        )

    def test_the_capability_is_registered(self):
        self.assertIsNotNone(self._worker_result(), "Worker capability ro'yxatda yo'q")

    def test_a_worker_that_never_reported_is_not_green(self):
        """Asl ko'r nuqta: navbat bo'sh, worker esa hech qachon ishga tushmagan."""
        result = self._worker_result()

        self.assertNotEqual(result.status, "green")

    def test_the_empty_queue_blind_spot_is_now_covered(self):
        """Ko'r nuqta yonma-yon: navbat bo'sh, worker esa yo'q.

        Outbox probe'i bu holatda yashil qaytaradi va bu to'g'ri — navbatda
        haqiqatan muammo yo'q. Ammo shu paytgacha Control Center'da faqat
        o'sha ko'rsatkich bor edi, ya'ni o'lik worker umuman ko'rinmasdi.
        """
        # Token sozlangan bo'lsin, aks holda outbox probe'i boshqa sababdan
        # sarg'ayadi va taqqoslash ma'nosini yo'qotadi.
        with override_settings(TELEGRAM_BOT_TOKEN="1234567890:sozlangan-token"):
            snapshot = build_control_center_snapshot()
        outbox = next(item for item in snapshot.results if item.definition.slug == "telegram_outbox")
        workers = next(item for item in snapshot.results if item.definition.slug == "workers")

        self.assertEqual(outbox.status, "green", "Bo'sh navbat — outbox o'zi sog'lom")
        self.assertNotEqual(workers.status, "green", "Worker yo'qligi ko'rinmadi")

    def test_a_fresh_heartbeat_turns_it_green(self):
        WorkerHeartbeat.record("telegram-outbox")

        self.assertEqual(self._worker_result().status, "green")

    def test_a_stale_heartbeat_is_reported_red(self):
        WorkerHeartbeat.record("telegram-outbox")
        WorkerHeartbeat.objects.filter(name="telegram-outbox").update(
            last_seen_at=timezone.now() - datetime.timedelta(hours=2)
        )

        result = self._worker_result()
        self.assertEqual(result.status, "red")
        self.assertIn("outbox", result.summary.lower())


class OutboxWorkerReportsItselfTests(TransactionTestCase):
    """Worker sikli haqiqatan heartbeat yozadi.

    `TransactionTestCase` — sikl async va ORM'ga boshqa oqimdan tegadi;
    `TestCase` ning o'rab turgan tranzaksiyasi SQLite'da qulflanib qolardi.
    """

    def test_one_outbox_cycle_records_a_heartbeat(self):
        import asyncio

        from bot.outbox import process_outbox_once

        class _NoopBot:
            async def send_message(self, *args, **kwargs):  # pragma: no cover
                raise AssertionError("bo'sh navbatda xabar yuborilmasligi kerak")

        asyncio.run(process_outbox_once(_NoopBot()))

        self.assertTrue(WorkerHeartbeat.objects.filter(name="telegram-outbox").exists())
