from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from bot.services import handle_telegram_auth_token
from users.models import TelegramAuthSession


User = get_user_model()
TELEGRAM_ID = 555000111


class TelegramAuthTokenSecurityTests(TestCase):
    """Telegram deep-link kirish tokeni bir martalik va brauzerga bog'liq.

    Ilgari `authenticated` bo'lgan sessiya cheksiz yashardi: tokenni bilgan
    istalgan kishi, istalgan brauzerdan, istalgan vaqtda o'sha hisobga
    kira olardi.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="tg-owner",
            email="tg-owner@example.test",
            password="pass-12345",
            telegram_id=TELEGRAM_ID,
        )

    def _start_flow(self, client):
        response = client.get(reverse("telegram_auth_init"))
        self.assertEqual(response.status_code, 200)
        return response.json()["token"]

    def _confirm_in_bot(self, token):
        result = handle_telegram_auth_token(f"auth_{token}", TELEGRAM_ID)
        self.assertTrue(result.ok, result.message)

    def _claim(self, client, token):
        return client.get(reverse("telegram_auth_status", args=[token]))

    def _is_logged_in(self, client):
        return client.session.get("_auth_user_id") == str(self.user.pk)

    # --- happy path -----------------------------------------------------

    def test_the_browser_that_started_the_flow_can_log_in(self):
        token = self._start_flow(self.client)
        self._confirm_in_bot(token)

        response = self._claim(self.client, token)

        self.assertEqual(response.json()["status"], "authenticated")
        self.assertTrue(self._is_logged_in(self.client))

    # --- replay ---------------------------------------------------------

    def test_token_cannot_be_claimed_twice(self):
        token = self._start_flow(self.client)
        self._confirm_in_bot(token)
        self._claim(self.client, token)

        replay_client = Client()
        # Ikkinchi brauzer o'zining oqimini boshlaydi, lekin eski tokenni
        # ishlatmoqchi bo'ladi.
        self._start_flow(replay_client)
        response = self._claim(replay_client, token)

        self.assertNotEqual(response.json().get("status"), "authenticated")
        self.assertIsNone(replay_client.session.get("_auth_user_id"))

        session = TelegramAuthSession.objects.get(token=token)
        self.assertEqual(session.status, TelegramAuthSession.STATUS_USED)
        self.assertIsNotNone(session.consumed_at)

    def test_same_browser_cannot_reuse_a_consumed_token(self):
        token = self._start_flow(self.client)
        self._confirm_in_bot(token)
        self._claim(self.client, token)

        response = self._claim(self.client, token)
        self.assertNotEqual(response.json().get("status"), "authenticated")

    # --- boshqa brauzer -------------------------------------------------

    def test_another_browser_knowing_the_token_cannot_log_in(self):
        token = self._start_flow(self.client)
        self._confirm_in_bot(token)

        attacker = Client()
        attacker.get(reverse("telegram_auth_init"))  # o'z client_key'i bor
        response = self._claim(attacker, token)

        self.assertEqual(response.json()["status"], "not_found")
        self.assertIsNone(attacker.session.get("_auth_user_id"))
        # Haqiqiy egasi hali ham kira oladi.
        self.assertEqual(self._claim(self.client, token).json()["status"], "authenticated")

    def test_client_without_any_session_key_is_rejected(self):
        token = self._start_flow(self.client)
        self._confirm_in_bot(token)

        bare = Client()
        response = self._claim(bare, token)

        self.assertEqual(response.json()["status"], "not_found")
        self.assertIsNone(bare.session.get("_auth_user_id"))

    # --- muddat ---------------------------------------------------------

    def test_authenticated_token_expires(self):
        token = self._start_flow(self.client)
        self._confirm_in_bot(token)

        session = TelegramAuthSession.objects.get(token=token)
        session.created_at = timezone.now() - (TelegramAuthSession.TOKEN_TTL + timezone.timedelta(minutes=1))
        session.save(update_fields=["created_at"])

        response = self._claim(self.client, token)

        self.assertNotEqual(response.json().get("status"), "authenticated")
        self.assertIsNone(self.client.session.get("_auth_user_id"))

    def test_bot_rejects_an_expired_pending_token(self):
        token = self._start_flow(self.client)
        session = TelegramAuthSession.objects.get(token=token)
        session.created_at = timezone.now() - (TelegramAuthSession.TOKEN_TTL + timezone.timedelta(minutes=1))
        session.save(update_fields=["created_at"])

        result = handle_telegram_auth_token(f"auth_{token}", TELEGRAM_ID)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "expired")
