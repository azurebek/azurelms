import io
import json
from contextlib import redirect_stdout

from django.test import TestCase, override_settings
from django.urls import reverse


WEBHOOK_URL = reverse("bot:telegram_webhook")
BODY = json.dumps({"update_id": 1}).encode()


class WebhookSecretSecurityTests(TestCase):
    """Telegram webhook secret bilan fail-closed himoyalanadi.

    Ilgari secret uchun taniqli default (`YOUR_SECRET_TOKEN_HERE`) bor edi
    va mos kelmagan token logga yozilardi.
    """

    def _post(self, **headers):
        return self.client.post(
            WEBHOOK_URL, data=BODY, content_type="application/json", **headers
        )

    @override_settings(TELEGRAM_WEBHOOK_SECRET="", APP_ENV="production")
    def test_missing_secret_config_rejects_all_updates(self):
        # Secret sozlanmagan bo'lsa hech qanday update qabul qilinmaydi.
        response = self._post(HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="anything")
        self.assertEqual(response.status_code, 403)

    @override_settings(TELEGRAM_WEBHOOK_SECRET="s3cret-value", APP_ENV="production")
    def test_wrong_secret_is_rejected(self):
        response = self._post(HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="wrong")
        self.assertEqual(response.status_code, 403)

    @override_settings(TELEGRAM_WEBHOOK_SECRET="s3cret-value", APP_ENV="production")
    def test_no_secret_header_is_rejected(self):
        response = self._post()
        self.assertEqual(response.status_code, 403)

    @override_settings(TELEGRAM_WEBHOOK_SECRET="s3cret-value", APP_ENV="production")
    def test_attacker_supplied_token_is_not_logged(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            response = self._post(HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="s3cr3t-guess-attempt")
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("s3cr3t-guess-attempt", buffer.getvalue())

    @override_settings(
        TELEGRAM_WEBHOOK_SECRET="",
        APP_ENV="local",
        TELEGRAM_ALLOW_INSECURE_LOCAL_WEBHOOK=True,
    )
    def test_local_insecure_flag_allows_no_secret(self):
        # Lokal test rejimi (flag yoqilgan) secret talab qilmaydi.
        # Ichkarida update parse xatosi bo'lishi mumkin, lekin 403 bo'lmasligi kerak.
        response = self._post()
        self.assertNotEqual(response.status_code, 403)
