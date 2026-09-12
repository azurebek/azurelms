"""`setwebhook` deploy yo'lida turadi, ya'ni fail-safe bo'lishi kerak (F10).

2026-09-13 deploy oldi auditi uch nuqson topdi va uchalasi ham **bir xil**
oqibatga olib borardi: bot jimgina ishlamay qoladi, buyruq esa muvaffaqiyat
deb ko'rinadi.

1. Secret almashsa ham «allaqachon o'rnatilgan» deb chiqib ketardi. Telegram
   `getWebhookInfo` da secret'ni **qaytarmaydi**, ya'ni URL tengligi secret
   tengligini isbotlamaydi. `bot/views.py` fail-closed bo'lgani uchun eski
   secret bilan kelgan **har bir update rad etilardi**.
2. `except Exception` xatoni `stdout` ga yozib, exit-code `0` qoldirardi —
   deploy skripti buni muvaffaqiyat deb hisoblardi.
3. `drop_pending_updates=True` doim yoqilgan edi: bot to'xtab turgan vaqtda
   o'quvchilar yozgan xabarlar jimgina o'chirilardi.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

BASE = "https://lms.example.test"
EXPECTED_URL = f"{BASE}/bot/webhook/"


def fake_bot(*, current_url="", pending=0, set_side_effect=None, info_side_effect=None):
    """`aiogram.Bot` o'rnini bosuvchi — tarmoqqa chiqmaydi."""
    bot = MagicMock()
    info = MagicMock()
    info.url = current_url
    info.pending_update_count = pending
    bot.get_webhook_info = AsyncMock(return_value=info, side_effect=info_side_effect)
    bot.set_webhook = AsyncMock(side_effect=set_side_effect)
    bot.session = MagicMock()
    bot.session.close = AsyncMock()
    return bot


@override_settings(
    TELEGRAM_MODE="webhook",
    TELEGRAM_BOT_TOKEN="123:abc",
    TELEGRAM_WEBHOOK_SECRET="s3cr3t",
)
class SetWebhookTests(SimpleTestCase):
    def _run(self, bot, *args):
        with patch("bot.management.commands.setwebhook.Bot", return_value=bot):
            call_command("setwebhook", BASE, *args)

    def test_the_secret_is_always_sent_even_when_the_url_is_unchanged(self):
        """Eng og'ir nuqson: secret rotatsiyasi jim o'tib ketardi.

        Telegram secret'ni qaytarmaydi, demak «URL bir xil» degan xulosadan
        «secret ham bir xil» kelib chiqmaydi. Yagona ishonchli yo'l —
        har safar qayta o'rnatish.
        """
        bot = fake_bot(current_url=EXPECTED_URL)

        self._run(bot)

        bot.set_webhook.assert_awaited_once()
        self.assertEqual(bot.set_webhook.await_args.kwargs["secret_token"], "s3cr3t")

    def test_a_new_url_is_set_with_the_secret(self):
        bot = fake_bot(current_url="https://eski.example.test/bot/webhook/")

        self._run(bot)

        kwargs = bot.set_webhook.await_args.kwargs
        self.assertEqual(kwargs["url"], EXPECTED_URL)
        self.assertEqual(kwargs["secret_token"], "s3cr3t")

    def test_pending_updates_are_kept_by_default(self):
        """Bot to'xtab turganda kelgan xabarlar o'chirilmasligi kerak."""
        bot = fake_bot(current_url="", pending=12)

        self._run(bot)

        self.assertFalse(bot.set_webhook.await_args.kwargs["drop_pending_updates"])

    def test_dropping_pending_updates_must_be_asked_for(self):
        bot = fake_bot(current_url="", pending=12)

        self._run(bot, "--drop-pending")

        self.assertTrue(bot.set_webhook.await_args.kwargs["drop_pending_updates"])

    def test_an_api_failure_is_not_reported_as_success(self):
        """Ilgari xato `stdout` ga yozilib, exit-code `0` qolardi."""
        bot = fake_bot(set_side_effect=RuntimeError("Bad Request: bad webhook"))

        with self.assertRaises(CommandError) as caught:
            self._run(bot)

        self.assertIn("setWebhook", str(caught.exception))

    def test_a_lookup_failure_is_not_reported_as_success(self):
        bot = fake_bot(info_side_effect=RuntimeError("tarmoq yo'q"))

        with self.assertRaises(CommandError):
            self._run(bot)

    def test_the_session_is_closed_even_when_the_call_fails(self):
        """Yopilmagan sessiya konteynerni to'xtatmay qoldirishi mumkin."""
        bot = fake_bot(set_side_effect=RuntimeError("xato"))

        with self.assertRaises(CommandError):
            self._run(bot)

        bot.session.close.assert_awaited()

    @override_settings(TELEGRAM_WEBHOOK_SECRET="")
    def test_a_missing_secret_stops_the_command(self):
        """Secret'siz webhook = fail-closed view = hamma update rad etiladi."""
        bot = fake_bot()

        with self.assertRaises(CommandError) as caught:
            self._run(bot)

        self.assertIn("TELEGRAM_WEBHOOK_SECRET", str(caught.exception))
        bot.set_webhook.assert_not_awaited()

    @override_settings(TELEGRAM_BOT_TOKEN="")
    def test_a_missing_token_stops_the_command(self):
        bot = fake_bot()

        with self.assertRaises(CommandError):
            self._run(bot)

    def test_a_plain_http_url_is_refused(self):
        """Telegram HTTPS'siz webhookni qabul qilmaydi."""
        bot = fake_bot()

        with patch("bot.management.commands.setwebhook.Bot", return_value=bot):
            with self.assertRaises(CommandError) as caught:
                call_command("setwebhook", "http://lms.example.test")

        self.assertIn("HTTPS", str(caught.exception))
        bot.set_webhook.assert_not_awaited()

    def test_a_trailing_slash_does_not_double_up(self):
        bot = fake_bot()

        with patch("bot.management.commands.setwebhook.Bot", return_value=bot):
            call_command("setwebhook", BASE + "/")

        self.assertEqual(bot.set_webhook.await_args.kwargs["url"], EXPECTED_URL)

    def test_the_path_matches_the_urlconf(self):
        """Yo'l URLconf bilan ajralib ketsa webhook 404 ga urilardi."""
        from django.urls import reverse

        from bot.management.commands.setwebhook import WEBHOOK_PATH

        self.assertEqual(reverse("bot:telegram_webhook"), WEBHOOK_PATH)
