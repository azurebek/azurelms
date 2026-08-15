"""A1a — Telegram outbox: bir qatorni faqat bitta worker olishi kerak.

Ilgari worker `status=pending` bo'yicha shunchaki tanlardi. Ikki worker bir
vaqtda ishlaganda — masalan `runbot` ichidagi worker va alohida
`telegram_outbox --loop` — ikkalasi ham bir xil qatorlarni olib, foydalanuvchiga
bir xil DM'ni ikki marta yuborardi. Shu sabab `05-launch-ops.md` da "aynan 1
replica xavfsizroq" deb yozilgan edi.

Endi qatorlar shartli `UPDATE` bilan band qilinadi va lease muddati bor.
Kafolat baribir **at-least-once**: Telegram'ga yuborish muvaffaqiyatli bo'lib,
DB yangilanishidan oldin process o'lsa, lease tugagach xabar takrorlanishi
mumkin. Lease bu oynani qisqartiradi, yo'q qilmaydi.

Contention testlari haqiqiy fayl bazasini talab qiladi (shared-cache in-memory
SQLite qulflash semantikasi boshqacha):

    AZURELMS_TEST_FILE_DB=1 python manage.py test bot.test_outbox_lease
"""

import threading
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from bot.models import TelegramOutbox
from bot.outbox import (
    LEASE_SECONDS,
    claim_pending_outbox,
    mark_outbox_attempt_failed,
    mark_outbox_sent,
    reclaim_expired_outbox,
)
from core.qa_support import skip_unless_file_backed_db

User = get_user_model()


def _make_outbox(count, telegram_id=555001):
    from users.models import Notification

    user = User.objects.create_user(
        username=f"ob_{telegram_id}", email=f"ob{telegram_id}@t.uz", password="pass-12345",
    )
    items = []
    for index in range(count):
        note = Notification.objects.create(
            recipient=user, title=f"Xabar {index}", message="matn",
        )
        items.append(
            TelegramOutbox.objects.create(notification=note, telegram_id=telegram_id)
        )
    return items


class OutboxLeaseTests(TestCase):
    """Lease mantig'i — ketma-ket, tez tekshiruvlar."""

    def test_claim_moves_rows_out_of_the_pending_queue(self):
        _make_outbox(3)
        claimed = claim_pending_outbox(limit=2)
        self.assertEqual(len(claimed), 2)
        self.assertTrue(all(item.status == TelegramOutbox.STATUS_SENDING for item in claimed))
        self.assertEqual(
            TelegramOutbox.objects.filter(status=TelegramOutbox.STATUS_PENDING).count(), 1
        )

    def test_a_second_claim_does_not_see_already_claimed_rows(self):
        _make_outbox(2)
        first = claim_pending_outbox(limit=2)
        second = claim_pending_outbox(limit=2)
        self.assertEqual(len(first), 2)
        self.assertEqual(second, [])

    def test_expired_lease_returns_the_row_to_the_queue(self):
        """Worker o'lib qolsa qator `sending` da muzlab qolmasligi kerak."""
        _make_outbox(1)
        claimed = claim_pending_outbox()
        TelegramOutbox.objects.filter(pk=claimed[0].pk).update(
            claimed_at=timezone.now() - timedelta(seconds=LEASE_SECONDS + 5)
        )

        self.assertEqual(reclaim_expired_outbox(), 1)
        row = TelegramOutbox.objects.get(pk=claimed[0].pk)
        self.assertEqual(row.status, TelegramOutbox.STATUS_PENDING)
        self.assertEqual(row.claim_token, "")

    def test_fresh_lease_is_not_reclaimed(self):
        _make_outbox(1)
        claim_pending_outbox()
        self.assertEqual(reclaim_expired_outbox(), 0)

    def test_failed_attempt_releases_the_claim_for_retry(self):
        item = _make_outbox(1)[0]
        claimed = claim_pending_outbox()[0]
        mark_outbox_attempt_failed(claimed, "network xatosi")

        row = TelegramOutbox.objects.get(pk=item.pk)
        self.assertEqual(row.status, TelegramOutbox.STATUS_PENDING)
        self.assertEqual(row.attempts, 1)
        self.assertEqual(row.claim_token, "")
        # Qayta navbatga tushgani uchun keyingi sikl uni yana oladi.
        self.assertEqual(len(claim_pending_outbox()), 1)

    def test_row_stops_retrying_after_max_attempts(self):
        from bot.outbox import MAX_ATTEMPTS

        item = _make_outbox(1)[0]
        for _ in range(MAX_ATTEMPTS):
            claimed = claim_pending_outbox()
            self.assertEqual(len(claimed), 1)
            mark_outbox_attempt_failed(claimed[0], "yana xato")

        row = TelegramOutbox.objects.get(pk=item.pk)
        self.assertEqual(row.status, TelegramOutbox.STATUS_FAILED)
        self.assertEqual(claim_pending_outbox(), [])

    def test_sent_row_leaves_the_queue(self):
        _make_outbox(1)
        mark_outbox_sent(claim_pending_outbox()[0])
        self.assertEqual(claim_pending_outbox(), [])
        self.assertEqual(
            TelegramOutbox.objects.filter(status=TelegramOutbox.STATUS_SENT).count(), 1
        )


class OutboxClaimContentionTests(TransactionTestCase):
    """Parallel workerlar bitta qatorni ikki marta olmasligi kerak."""

    reset_sequences = True
    WORKERS = 6
    ROWS = 12

    def setUp(self):
        skip_unless_file_backed_db(self)
        TelegramOutbox.objects.all().delete()
        _make_outbox(self.ROWS)

    def test_parallel_workers_never_claim_the_same_row_twice(self):
        barrier = threading.Barrier(self.WORKERS)
        results = [None] * self.WORKERS

        def worker(index):
            try:
                barrier.wait(timeout=15)
                results[index] = [item.pk for item in claim_pending_outbox(limit=self.ROWS)]
            except BaseException as exc:  # noqa: BLE001
                results[index] = exc
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(self.WORKERS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        failures = [r for r in results if isinstance(r, BaseException)]
        self.assertEqual(failures, [], f"worker xato bilan tugadi: {failures}")

        claimed = [pk for batch in results for pk in batch]
        self.assertEqual(
            len(claimed), len(set(claimed)),
            "bir qator bir necha workerga berildi — DM takrorlanardi",
        )
        self.assertEqual(sorted(set(claimed)), sorted(
            TelegramOutbox.objects.filter(
                status=TelegramOutbox.STATUS_SENDING
            ).values_list("pk", flat=True)
        ))
