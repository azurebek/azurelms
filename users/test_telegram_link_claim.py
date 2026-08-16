"""A4 — Telegram hisobini ulash havolasi (credential claim).

Ulash havolasi `t.me/<bot>?start=<token>` ko'rinishida profil sahifasida
ko'rsatiladi. Token `Signer().sign(user.id)` ning base64'i edi, va bundan
ikkita muammo kelib chiqadi:

1. **Muddat yo'q.** `Signer` vaqt qo'shmaydi, ya'ni token abadiy yaroqli va
   har safar bir xil. Havola bir marta sizib chiqsa (skrinshot, forward
   qilingan xabar, brauzer tarixi), uni topgan odam **o'z** Telegramini
   o'quvchining hisobiga ulaydi va botda o'sha o'quvchi sifatida ishlaydi.
   Yonidagi login oqimi (`TelegramAuthSession`) esa 5 daqiqalik, bir martalik
   va brauzerga bog'langan — ya'ni ulash yo'li ataylab emas, tasodifan
   zaifroq qolgan.

2. **Havola `user.id >= 10000` da umuman ishlamaydi.** Telegram `start`
   payloadiga 64 belgi chegara qo'yadi; imzolangan ID ning base64'i 4 xonali
   IDda aynan 64 ga yetadi va 5 xonalida 66 bo'lib chegaradan oshadi.
   Koddagi izoh "Signer is compact enough" deb turibdi — bu faqat dastlabki
   o'n ming foydalanuvchi uchun rost.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bot.services import link_user_from_start_token
from users.views import _build_telegram_link_context

User = get_user_model()

# Telegram Bot API: `start` payload 1-64 belgi, faqat A-Z a-z 0-9 _ -
TELEGRAM_START_PAYLOAD_LIMIT = 64
ALLOWED = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")


def token_from_context(user):
    context = _build_telegram_link_context(user)
    return context["telegram_bot_link"].split("start=", 1)[1]


class ClaimLinkFitsTelegramLimitTests(TestCase):
    def test_the_link_fits_for_a_five_digit_user_id(self):
        """10 000-chi foydalanuvchining havolasi ham ishlashi kerak."""
        user = User.objects.create_user(
            username="big-id", email="big-id@example.com", password="testpass123"
        )
        User.objects.filter(pk=user.pk).update(id=54321)
        user = User.objects.get(id=54321)

        token = token_from_context(user)

        self.assertLessEqual(
            len(token),
            TELEGRAM_START_PAYLOAD_LIMIT,
            f"Deep-link payload {len(token)} belgi — Telegram {TELEGRAM_START_PAYLOAD_LIMIT} dan "
            "uzunini rad etadi, ya'ni havola umuman ochilmaydi",
        )

    def test_the_token_uses_only_characters_telegram_accepts(self):
        user = User.objects.create_user(
            username="charset", email="charset@example.com", password="testpass123"
        )
        token = token_from_context(user)

        self.assertTrue(set(token) <= ALLOWED, f"Ruxsat etilmagan belgi: {set(token) - ALLOWED}")
        self.assertTrue(token)


class ClaimLinkExpiresTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="claim-owner", email="claim-owner@example.com", password="testpass123"
        )

    def _backdate(self, minutes):
        from users.models import TelegramLinkToken

        TelegramLinkToken.objects.filter(user=self.user).update(
            created_at=timezone.now() - datetime.timedelta(minutes=minutes)
        )

    def test_a_fresh_link_works(self):
        token = token_from_context(self.user)

        result = link_user_from_start_token(token, 555000111, "claimer")

        self.assertTrue(result.ok, result.message)
        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_id, 555000111)

    def test_a_stale_link_is_refused(self):
        """Sizib chiqqan eski havola ishlamasligi kerak."""
        token = token_from_context(self.user)
        self._backdate(minutes=120)

        result = link_user_from_start_token(token, 555000222, "attacker")

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "expired_token")
        self.user.refresh_from_db()
        self.assertIsNone(self.user.telegram_id)

    def test_a_link_cannot_be_replayed_after_use(self):
        """Bir marta ishlatilgan token ikkinchi Telegram hisobini ulamaydi."""
        token = token_from_context(self.user)
        link_user_from_start_token(token, 555000333, "first")

        result = link_user_from_start_token(token, 555000444, "second")

        self.assertFalse(result.ok)
        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_id, 555000333)

    def test_an_unknown_token_is_refused(self):
        result = link_user_from_start_token("mutlaqo-notanish-token", 555000555, "nobody")

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "invalid_token")

    def test_a_telegram_account_already_used_elsewhere_is_refused(self):
        other = User.objects.create_user(
            username="already-linked", email="already@example.com", password="x"
        )
        other.telegram_id = 555000666
        other.save(update_fields=["telegram_id"])

        token = token_from_context(self.user)
        result = link_user_from_start_token(token, 555000666, "dupe")

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "telegram_used")

    def test_refreshing_the_profile_page_keeps_the_same_valid_token(self):
        """Sahifani qayta ochish endigina nusxalangan havolani bekor qilmasin."""
        first = token_from_context(self.user)
        second = token_from_context(self.user)

        self.assertEqual(first, second)
