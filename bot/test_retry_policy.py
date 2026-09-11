"""Telegram qayta urinish siyosati testlari (F10).

Ikki qatlam: sof siyosat (`bot/retry_policy.py`) va uning ikkala navbatga
haqiqatan ulangani (`bot/outbox.py`, `classbook/delivery.py`). Ikkinchisi
ataylab: siyosat to'g'ri bo'lib, navbat uni chaqirmay qo'yishi mumkin va
o'shanda test yashil bo'lib turgan holda xabar baribir yo'qolardi.
"""

from datetime import timedelta
from unittest import mock

from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNotFound,
    TelegramRetryAfter,
    TelegramServerError,
    TelegramUnauthorizedError,
)
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone

from bot import retry_policy
from bot.models import TelegramOutbox
from bot.outbox import claim_pending_outbox, mark_outbox_attempt_failed, mark_outbox_sent
from bot.retry_policy import (
    KIND_CONFIG,
    KIND_PERMANENT,
    KIND_RATE_LIMITED,
    KIND_TRANSIENT,
    MAX_ATTEMPTS,
    backoff_seconds,
    classify,
    plan_retry,
)
from users.models import Notification


class _FakeMethod:
    """Aiogram xatolari `method` talab qiladi; unga faqat nom kerak."""

    chat_id = 1


def _retry_after(seconds):
    return TelegramRetryAfter(_FakeMethod(), "Too Many Requests", seconds)


def _forbidden():
    return TelegramForbiddenError(_FakeMethod(), "bot was blocked by the user")


class ClassifyTests(SimpleTestCase):
    def test_flood_control_is_rate_limited_with_the_server_delay(self):
        kind, delay = classify(_retry_after(7))
        self.assertEqual(kind, KIND_RATE_LIMITED)
        self.assertEqual(delay, 7)

    def test_zero_retry_after_still_waits(self):
        """Telegram `retry_after=0` berishi mumkin; darhol urinish yana 429."""
        kind, delay = classify(_retry_after(0))
        self.assertEqual(kind, KIND_RATE_LIMITED)
        self.assertGreaterEqual(delay, retry_policy.MIN_RATE_LIMIT_DELAY_SECONDS)

    def test_blocked_by_user_is_permanent(self):
        kind, _ = classify(_forbidden())
        self.assertEqual(kind, KIND_PERMANENT)

    def test_missing_chat_is_permanent(self):
        kind, _ = classify(TelegramNotFound(_FakeMethod(), "chat not found"))
        self.assertEqual(kind, KIND_PERMANENT)

    def test_bad_token_is_a_config_failure_not_a_permanent_one(self):
        """Sabab xabarda emas, **butun botda** — shuning uchun terminal emas.

        Codex review (PR #101, P1): noto'g'ri/eskirgan token bilan chiqilgan
        deploy har bir claim qilingan qatorga `401` beradi. Agar u permanent
        bo'lsa, butun navbat dead-letter bo'ladi va tokenni tuzatish ularni
        qaytarmaydi — replay amali hali yo'q. To'xtab turgan navbat esa
        ko'rinadi (Control Center eng qadimgi pending uchun RED beradi) va
        tuzatilgach o'zi ketadi.
        """
        kind, _ = classify(TelegramUnauthorizedError(_FakeMethod(), "Unauthorized"))
        self.assertEqual(kind, KIND_CONFIG)

    def test_bad_request_about_a_dead_chat_is_permanent(self):
        kind, _ = classify(TelegramBadRequest(_FakeMethod(), "Bad Request: chat not found"))
        self.assertEqual(kind, KIND_PERMANENT)

    def test_other_bad_requests_stay_transient(self):
        """Ularni permanent deb yopish xabarni jim yo'qotardi."""
        kind, _ = classify(
            TelegramBadRequest(_FakeMethod(), "Bad Request: can't parse entities")
        )
        self.assertEqual(kind, KIND_TRANSIENT)

    def test_server_and_network_errors_are_transient(self):
        self.assertEqual(classify(TelegramServerError(_FakeMethod(), "Bad Gateway"))[0], KIND_TRANSIENT)
        self.assertEqual(classify(OSError("tarmoq uzildi"))[0], KIND_TRANSIENT)


class PlanRetryTests(SimpleTestCase):
    def test_rate_limit_does_not_spend_an_attempt(self):
        """Eng muhim qoida (F10).

        50 o'quvchiga natija DM ketayotganda 429 oddiy hol. Agar har 429 bitta
        urinishni yesa, xabar uch siklda `failed` bo'lib qolardi va o'quvchi
        natijasini **hech qachon** ko'rmasdi — sabab esa faqat bizning
        tezligimiz bo'lgan.
        """
        now = timezone.now()
        kind, attempts, give_up, next_at = plan_retry(
            error=_retry_after(5), attempts=2, now=now
        )
        self.assertEqual(kind, KIND_RATE_LIMITED)
        self.assertEqual(attempts, 2)
        self.assertFalse(give_up)
        self.assertEqual(next_at, now + timedelta(seconds=5))

    def test_rate_limit_never_dead_letters_however_often_it_repeats(self):
        attempts = 0
        for _ in range(MAX_ATTEMPTS * 3):
            _, attempts, give_up, _ = plan_retry(error=_retry_after(1), attempts=attempts)
            self.assertFalse(give_up)
        self.assertEqual(attempts, 0)

    def test_permanent_failure_dead_letters_on_the_first_attempt(self):
        """Botni bloklagan foydalanuvchiga uch marta urinish faqat rate yeydi."""
        kind, attempts, give_up, next_at = plan_retry(error=_forbidden(), attempts=0)
        self.assertEqual(kind, KIND_PERMANENT)
        self.assertEqual(attempts, 1)
        self.assertTrue(give_up)
        self.assertIsNone(next_at)

    def test_config_failure_keeps_every_row_recoverable(self):
        """Token tuzatilgach navbatdagi hamma xabar yetib borishi kerak."""
        attempts = 0
        for _ in range(MAX_ATTEMPTS * 3):
            kind, attempts, give_up, next_at = plan_retry(
                error=TelegramUnauthorizedError(_FakeMethod(), "Unauthorized"),
                attempts=attempts,
            )
            self.assertEqual(kind, KIND_CONFIG)
            self.assertFalse(give_up, "noto'g'ri token butun navbatni o'ldirmasin")
            self.assertIsNotNone(next_at)
        self.assertEqual(attempts, 0, "urinish sarflanmasligi kerak")

    def test_transient_failure_schedules_a_future_attempt(self):
        now = timezone.now()
        kind, attempts, give_up, next_at = plan_retry(
            error=OSError("tarmoq"), attempts=0, now=now
        )
        self.assertEqual(kind, KIND_TRANSIENT)
        self.assertEqual(attempts, 1)
        self.assertFalse(give_up)
        self.assertGreater(next_at, now)

    def test_transient_failure_dead_letters_at_the_limit(self):
        _, attempts, give_up, next_at = plan_retry(
            error=OSError("tarmoq"), attempts=MAX_ATTEMPTS - 1
        )
        self.assertEqual(attempts, MAX_ATTEMPTS)
        self.assertTrue(give_up)
        self.assertIsNone(next_at)

    def test_backoff_grows_and_is_capped(self):
        first = backoff_seconds(1, base=30, cap=900)
        second = backoff_seconds(2, base=30, cap=900)
        self.assertLess(first, second)
        # Jitter bilan ham kappadan oshmasin.
        for attempt in range(1, 30):
            self.assertLessEqual(backoff_seconds(attempt, base=30, cap=900), 900 * 1.2)

    def test_backoff_is_never_zero(self):
        """Aks holda "backoff" darhol qayta urinishga aylanib qolardi."""
        for attempt in range(0, 5):
            self.assertGreaterEqual(backoff_seconds(attempt, base=1, cap=900), 1.0)


def _make_outbox(telegram_id=555):
    user = get_user_model().objects.create_user(
        username=f"rp_{telegram_id}",
        email=f"rp{telegram_id}@azurelms.test",
        password="pass-12345",
    )
    note = Notification.objects.create(
        recipient=user, title="Natija", message="Ball: 9/10"
    )
    return TelegramOutbox.objects.create(notification=note, telegram_id=telegram_id)


class OutboxUsesThePolicyTests(TestCase):
    """Siyosat DM navbatiga haqiqatan ulanganmi."""

    def test_flood_control_keeps_the_message_in_the_queue(self):
        row = _make_outbox()
        mark_outbox_attempt_failed(claim_pending_outbox()[0], _retry_after(3))

        row.refresh_from_db()
        self.assertEqual(row.status, TelegramOutbox.STATUS_PENDING)
        self.assertEqual(row.attempts, 0, "429 urinish sarflamasligi kerak")
        self.assertEqual(row.failure_kind, KIND_RATE_LIMITED)
        self.assertIsNotNone(row.next_attempt_at)

    def test_fifty_flood_controls_never_lose_the_message(self):
        """50 o'quvchilik Classbook darsining aynan regressiyasi."""
        row = _make_outbox()
        for _ in range(50):
            claimed = claim_pending_outbox()
            if not claimed:
                # Backoff kutyapti — muddatni o'tkazamiz va davom etamiz.
                TelegramOutbox.objects.filter(pk=row.pk).update(
                    next_attempt_at=timezone.now() - timedelta(seconds=1)
                )
                claimed = claim_pending_outbox()
            mark_outbox_attempt_failed(claimed[0], _retry_after(1))

        row.refresh_from_db()
        self.assertEqual(row.status, TelegramOutbox.STATUS_PENDING)
        self.assertEqual(row.attempts, 0)

    def test_blocked_user_is_dead_lettered_at_once(self):
        row = _make_outbox()
        mark_outbox_attempt_failed(claim_pending_outbox()[0], _forbidden())

        row.refresh_from_db()
        self.assertEqual(row.status, TelegramOutbox.STATUS_FAILED)
        self.assertEqual(row.attempts, 1, "uch urinish rate budjetini bekorga yeydi")
        self.assertEqual(row.failure_kind, KIND_PERMANENT)
        self.assertEqual(claim_pending_outbox(), [])

    def test_sending_clears_the_previous_failure_marks(self):
        row = _make_outbox()
        mark_outbox_attempt_failed(claim_pending_outbox()[0], _retry_after(1))
        TelegramOutbox.objects.filter(pk=row.pk).update(
            next_attempt_at=timezone.now() - timedelta(seconds=1)
        )
        mark_outbox_sent(claim_pending_outbox()[0])

        row.refresh_from_db()
        self.assertEqual(row.status, TelegramOutbox.STATUS_SENT)
        self.assertIsNone(row.next_attempt_at)
        self.assertEqual(row.failure_kind, "")


class ClaimRespectsBackoffUnderRaceTests(TestCase):
    """Backoff sharti shartli `UPDATE` da ham bormi (Codex review P1 #101, P2).

    Ikki replika sahnasi: A qatorni tanlaydi va oladi, tez `429` oladi,
    `next_attempt_at` ni kelajakka qo'yib `pending` ga qaytaradi. B esa
    o'zining **eskirgan** nomzod ro'yxati bilan keladi. Agar `UPDATE` faqat
    `status=pending` ni tekshirsa, B qatorni darhol olib, Telegram so'ragan
    kutishni chetlab o'tib yana `429` chaqiradi.

    Test aynan o'sha eskirgan ro'yxatni taqlid qiladi: tanlash qadami qatorni
    baribir qaytaradi, himoya esa faqat `UPDATE` da qolgan bo'lishi kerak.
    """

    def test_stale_candidate_list_cannot_claim_a_backing_off_row(self):
        row = _make_outbox(801)
        mark_outbox_attempt_failed(claim_pending_outbox()[0], _retry_after(60))
        row.refresh_from_db()
        self.assertEqual(row.status, TelegramOutbox.STATUS_PENDING)
        self.assertGreater(row.next_attempt_at, timezone.now())

        with mock.patch("bot.outbox.eligible_outbox_ids", return_value=[row.pk]):
            self.assertEqual(claim_pending_outbox(), [])

        row.refresh_from_db()
        self.assertEqual(row.status, TelegramOutbox.STATUS_PENDING, "qator olinmasligi kerak")
        self.assertEqual(row.claim_token, "")

    def test_stale_candidate_list_still_claims_an_eligible_row(self):
        """Himoya kerakligidan ko'p ushlamasin."""
        row = _make_outbox(802)
        with mock.patch("bot.outbox.eligible_outbox_ids", return_value=[row.pk]):
            claimed = claim_pending_outbox()
        self.assertEqual([item.pk for item in claimed], [row.pk])


class SendSpacingTests(TransactionTestCase):
    """Sikl ichida yuborishlar orasida oraliq bormi.

    `TransactionTestCase` ataylab: `process_outbox_once` `sync_to_async` orqali
    boshqa ulanishdan o'qiydi, oddiy `TestCase` da esa fixture tranzaksiya
    ichida qolib, o'sha ulanish uni ko'rmaydi (`database table is locked`).
    """

    def test_each_send_is_followed_by_the_configured_pause(self):
        """Ilgari 25 ta `send_message` orasiz otilardi — 429 ning bevosita sababi."""
        import asyncio

        from bot.outbox import process_outbox_once

        for index in range(3):
            _make_outbox(600 + index)

        class _Bot:
            async def send_message(self, *args, **kwargs):
                return mock.Mock(message_id=1)

        sleeps = []

        async def _fake_sleep(seconds):
            sleeps.append(seconds)

        with mock.patch("bot.outbox.asyncio.sleep", _fake_sleep):
            sent = asyncio.run(process_outbox_once(_Bot()))

        self.assertEqual(sent, 3)
        self.assertEqual(len(sleeps), 3)
        self.assertTrue(all(value == retry_policy.SEND_INTERVAL_SECONDS for value in sleeps))

    def test_zero_interval_disables_the_pause(self):
        """Testlar va lokal debug uchun oraliqni o'chirib bo'lishi kerak."""
        import asyncio

        from bot.outbox import process_outbox_once

        _make_outbox(700)

        class _Bot:
            async def send_message(self, *args, **kwargs):
                return mock.Mock(message_id=1)

        sleeps = []

        async def _fake_sleep(seconds):
            sleeps.append(seconds)

        with mock.patch.object(retry_policy, "SEND_INTERVAL_SECONDS", 0), mock.patch(
            "bot.outbox.asyncio.sleep", _fake_sleep
        ):
            asyncio.run(process_outbox_once(_Bot()))

        self.assertEqual(sleeps, [])
