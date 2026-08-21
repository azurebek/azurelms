"""Flaglar haqiqatan biror narsani boshqarishini tekshiradi (A2).

Registr o'zi hech nimani o'chirmaydi — uni chaqiradigan joy kerak. Bu testlar
ikkala e'lon qilingan flag uchun **haqiqiy oqimni** tekshiradi, aks holda
registr Control Center'da chiroyli ko'rinadigan, ammo hech narsaga ta'sir
qilmaydigan ro'yxat bo'lib qolardi.
"""

import asyncio

from asgiref.sync import sync_to_async
from django.db import connections
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from aicontrol.models import WorkerHeartbeat
from bot.models import TelegramOutbox
from core.flags import set_flag
from users.models import CustomUser as User


class PublicRegistrationFlagTests(TestCase):
    def test_registration_is_open_by_default(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)

    def test_closing_the_flag_blocks_the_page(self):
        set_flag("public_registration", enabled=False, reason="demo oldidan yopamiz")

        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "yopiq")

    def test_closing_the_flag_blocks_the_post_too(self):
        """Sahifani yashirish yetmaydi — forma to'g'ridan-to'g'ri yuborilishi mumkin."""
        set_flag("public_registration", enabled=False, reason="yopiq")

        before = User.objects.count()
        self.client.post(
            reverse("register"),
            {"username": "yangi-hisob", "email": "yangi@example.com",
             "password1": "juda-kuchli-parol-123", "password2": "juda-kuchli-parol-123"},
        )
        self.assertEqual(User.objects.count(), before, "flag yopiq bo'lsa hisob yaratilmasligi kerak")

    def test_existing_users_can_still_log_in_when_registration_is_closed(self):
        """Yopilishi kerak bo'lgani ro'yxatdan o'tish, kirish emas."""
        User.objects.create_user(username="eski", email="eski@example.com", password="testpass123")
        set_flag("public_registration", enabled=False, reason="yopiq")

        self.assertTrue(self.client.login(username="eski", password="testpass123"))


class TelegramOutboxFlagTests(TransactionTestCase):
    """`TransactionTestCase`, chunki `process_outbox_once` `sync_to_async` orqali
    **boshqa ulanishdan** o'qiydi. Oddiy `TestCase` da fixture tranzaksiya ichida
    qolib, o'sha ulanish uni ko'rmaydi va SQLite `table is locked` beradi."""

    def setUp(self):
        from users.models import Notification

        self.user = User.objects.create_user(
            username="tg-user", email="tg@example.com", password="testpass123"
        )
        note = Notification.objects.create(
            recipient=self.user, title="Xabar", message="matn"
        )
        TelegramOutbox.objects.create(notification=note, telegram_id=555001)

    def _run_cycle(self, bot):
        async def run():
            from bot.outbox import process_outbox_once

            sent = await process_outbox_once(bot)
            await sync_to_async(connections.close_all)()
            return sent

        return asyncio.run(run())

    def test_paused_outbox_sends_nothing_and_keeps_the_message_queued(self):
        set_flag("telegram_outbox_sending", enabled=False, reason="bot noto'g'ri xabar yuboryapti")

        class _Bot:
            async def send_message(self, *args, **kwargs):
                raise AssertionError("flag yopiq bo'lsa xabar yuborilmasligi kerak")

        sent = self._run_cycle(_Bot())

        self.assertEqual(sent, 0)
        message = TelegramOutbox.objects.first()
        self.assertIsNotNone(message, "xabar navbatda saqlanib turishi kerak, yo'qolmasligi")
        self.assertNotEqual(message.status, TelegramOutbox.STATUS_SENT)

    def test_paused_outbox_still_records_a_heartbeat(self):
        """Pauza worker o'lgandek ko'rinmasligi kerak — bu Control Center'ni chalg'itardi."""
        set_flag("telegram_outbox_sending", enabled=False, reason="pauza")

        class _Bot:
            async def send_message(self, *args, **kwargs):
                raise AssertionError("yuborilmasligi kerak")

        self._run_cycle(_Bot())

        beat = WorkerHeartbeat.objects.filter(name="telegram-outbox").first()
        self.assertIsNotNone(beat, "pauza paytida ham worker tirikligini bildirishi kerak")
