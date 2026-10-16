"""PUB1.0d — Telegram kirish: init/consume POST+CSRF, status faqat o'qiydi.

Ilgari `GET status` muddat tugaganini bazaga yozar va tasdiqlangan tokenni
o'sha GET ichida login qilardi: holat o'zgartiradigan GET CSRF himoyasidan
tashqarida edi. Endi:

- ``POST init`` — CSRF, cheklov, bir brauzerda bitta faol oqim, xavfsiz `next`;
- ``GET status`` — hech narsa yozmaydi;
- ``POST consume`` — CSRF, brauzer kaliti, row lock, bir martalik login;
- ``POST cancel`` — faqat shu brauzer oqimini yopadi.
"""

import threading
from datetime import timedelta
from io import StringIO
from unittest import skipUnless

from django.contrib.auth import get_user_model, user_logged_in
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from django.core.management import call_command
from django.db import connection
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from bot.services import handle_telegram_auth_token
from core.models import OperationalSettings
from users import telegram_auth_service as telegram_auth
from users.models import TelegramAuthSession


User = get_user_model()
TELEGRAM_ID = 555000222
WRITE_PREFIXES = ("INSERT", "UPDATE", "DELETE", "REPLACE")


def status_url(token):
    return reverse("telegram_auth_status", args=[token])


def consume_url(token):
    return reverse("telegram_auth_consume", args=[token])


def age(token, delta):
    TelegramAuthSession.objects.filter(token=token).update(created_at=timezone.now() - delta)


class FlowMixin:
    def setUp(self):
        self.user = User.objects.create_user(
            username="tg-split", email="tg-split@example.test", password="pass-12345", telegram_id=TELEGRAM_ID,
        )

    def start(self, client=None, **data):
        response = (client or self.client).post(reverse("telegram_auth_init"), data)
        self.assertEqual(response.status_code, 200)
        return response.json()["token"]

    def confirm(self, token):
        result = handle_telegram_auth_token(f"auth_{token}", TELEGRAM_ID)
        self.assertTrue(result.ok, result.message)

    def logged_in(self, client=None):
        return (client or self.client).session.get("_auth_user_id") == str(self.user.pk)


class MethodContractTests(FlowMixin, TestCase):
    def test_state_changing_endpoints_reject_get_with_405_and_write_nothing(self):
        token = self.start()
        self.confirm(token)
        before = list(TelegramAuthSession.objects.values_list("token", "status", "consumed_at"))
        for url in (reverse("telegram_auth_init"), consume_url(token), reverse("telegram_auth_cancel")):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(list(TelegramAuthSession.objects.values_list("token", "status", "consumed_at")), before)
        self.assertFalse(self.logged_in())

    def test_status_rejects_post_with_405(self):
        token = self.start()
        self.assertEqual(self.client.post(status_url(token)).status_code, 405)

    def test_init_answers_with_the_shared_polling_contract(self):
        data = self.client.post(reverse("telegram_auth_init")).json()
        self.assertEqual(data["poll_ms"], telegram_auth.POLL_INTERVAL_MS)
        self.assertEqual(data["expires_in"], int(TelegramAuthSession.TOKEN_TTL.total_seconds()))
        self.assertTrue(data["bot_link"].startswith("https://t.me/"))
        self.assertTrue(data["bot_link"].endswith(f"?start=auth_{data['token']}"))


class CsrfTests(FlowMixin, TestCase):
    def browser(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("login"))
        return client, client.cookies["csrftoken"].value

    def test_missing_or_bad_csrf_is_rejected_with_403(self):
        client, _ = self.browser()
        before = TelegramAuthSession.objects.count()
        self.assertEqual(client.post(reverse("telegram_auth_init")).status_code, 403)
        self.assertEqual(
            client.post(reverse("telegram_auth_init"), HTTP_X_CSRFTOKEN="noto-g-ri-token").status_code, 403,
        )
        self.assertEqual(TelegramAuthSession.objects.count(), before)

    def test_consume_without_csrf_cannot_log_in(self):
        client, csrf = self.browser()
        token = client.post(reverse("telegram_auth_init"), HTTP_X_CSRFTOKEN=csrf).json()["token"]
        self.confirm(token)
        self.assertEqual(client.post(consume_url(token)).status_code, 403)
        self.assertEqual(client.post(reverse("telegram_auth_cancel")).status_code, 403)
        self.assertFalse(self.logged_in(client))
        self.assertEqual(TelegramAuthSession.objects.get(token=token).status, TelegramAuthSession.STATUS_AUTHENTICATED)

    def test_full_flow_with_valid_csrf(self):
        client, csrf = self.browser()
        token = client.post(reverse("telegram_auth_init"), HTTP_X_CSRFTOKEN=csrf).json()["token"]
        self.confirm(token)
        self.assertEqual(client.get(status_url(token)).json()["status"], "authenticated")
        response = client.post(consume_url(token), HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(response.json()["status"], "authenticated")
        self.assertTrue(self.logged_in(client))


class ReadOnlyStatusTests(FlowMixin, TestCase):
    def assert_read_only(self, token):
        session_before = dict(self.client.session.items())
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(status_url(token))
        writes = [q["sql"] for q in queries.captured_queries if q["sql"].lstrip().upper().startswith(WRITE_PREFIXES)]
        self.assertEqual(writes, [])
        self.assertEqual(dict(self.client.session.items()), session_before)
        self.assertNotIn("sessionid", response.cookies)
        self.assertIn("no-store", response["Cache-Control"])
        return response.json()

    def test_every_state_is_read_without_a_write(self):
        token = self.start()
        self.assertEqual(self.assert_read_only(token)["status"], "pending")
        self.confirm(token)
        self.assertEqual(self.assert_read_only(token)["status"], "authenticated")
        self.assertFalse(self.logged_in())
        self.client.post(consume_url(token))
        self.assertEqual(self.assert_read_only(token)["status"], "used")

    def test_expiry_is_computed_not_stored(self):
        token = self.start()
        age(token, TelegramAuthSession.TOKEN_TTL + timedelta(seconds=1))
        self.assertEqual(self.assert_read_only(token)["status"], "expired")
        self.assertEqual(TelegramAuthSession.objects.get(token=token).status, TelegramAuthSession.STATUS_PENDING)

    def test_confirmed_but_expired_token_reads_expired_and_cannot_be_consumed(self):
        token = self.start()
        self.confirm(token)
        age(token, TelegramAuthSession.TOKEN_TTL + timedelta(seconds=1))
        self.assertEqual(self.assert_read_only(token)["status"], "expired")
        self.assertEqual(self.client.post(consume_url(token)).json()["status"], "expired")
        self.assertFalse(self.logged_in())
        self.assertIsNone(TelegramAuthSession.objects.get(token=token).consumed_at)

    def test_unknown_token_is_also_read_only(self):
        self.start()
        self.assertEqual(self.assert_read_only("mavjud-emas")["status"], "not_found")


class OtherBrowserTests(FlowMixin, TestCase):
    def test_other_browser_cannot_tell_a_real_token_from_a_missing_one(self):
        token = self.start()
        self.confirm(token)
        attacker = Client()
        self.start(attacker)
        bare = Client()

        responses = {
            "status-real": attacker.get(status_url(token)).content,
            "status-missing": attacker.get(status_url("mavjud-emas")).content,
            "status-bare": bare.get(status_url(token)).content,
            "consume-real": attacker.post(consume_url(token)).content,
            "consume-missing": attacker.post(consume_url("mavjud-emas")).content,
            "consume-bare": bare.post(consume_url(token)).content,
        }
        self.assertEqual(len(set(responses.values())), 1, responses)
        self.assertFalse(self.logged_in(attacker))
        self.assertFalse(self.logged_in(bare))
        self.assertEqual(TelegramAuthSession.objects.get(token=token).status, TelegramAuthSession.STATUS_AUTHENTICATED)
        # Haqiqiy egasi hali ham kira oladi.
        self.assertEqual(self.client.post(consume_url(token)).json()["status"], "authenticated")

    def test_other_browser_cancel_does_not_touch_the_owner_flow(self):
        token = self.start()
        self.confirm(token)
        attacker = Client()
        self.start(attacker)
        self.assertEqual(attacker.post(reverse("telegram_auth_cancel")).status_code, 200)
        self.assertEqual(TelegramAuthSession.objects.get(token=token).status, TelegramAuthSession.STATUS_AUTHENTICATED)
        self.assertEqual(self.client.post(consume_url(token)).json()["status"], "authenticated")


class OneTimeConsumeTests(FlowMixin, TestCase):
    def test_pending_token_is_not_consumed(self):
        token = self.start()
        self.assertEqual(self.client.post(consume_url(token)).json()["status"], "pending")
        row = TelegramAuthSession.objects.get(token=token)
        self.assertEqual(row.status, TelegramAuthSession.STATUS_PENDING)
        self.assertIsNone(row.consumed_at)
        self.assertFalse(self.logged_in())

    def test_repeat_consume_from_the_same_browser_logs_in_once(self):
        token = self.start()
        self.confirm(token)
        logins = []
        receiver = lambda **kwargs: logins.append(kwargs["user"].pk)  # noqa: E731
        user_logged_in.connect(receiver)
        try:
            twin = Client()
            twin.cookies = self.client.cookies  # bir brauzerdan ikki parallel so'rov
            first = self.client.post(consume_url(token)).json()
            second = twin.post(consume_url(token)).json()
        finally:
            user_logged_in.disconnect(receiver)
        self.assertEqual(first["status"], "authenticated")
        self.assertNotEqual(second["status"], "authenticated")
        self.assertEqual(logins, [self.user.pk])

    def test_bot_cannot_confirm_the_same_token_twice(self):
        token = self.start()
        self.confirm(token)
        other = User.objects.create_user("tg-boshqa", email="tgb2@example.test", telegram_id=TELEGRAM_ID + 1)
        result = handle_telegram_auth_token(f"auth_{token}", other.telegram_id)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "expired")
        self.assertEqual(TelegramAuthSession.objects.get(token=token).user, self.user)

    def test_service_refuses_to_authenticate_a_closed_row(self):
        token = self.start()
        row = TelegramAuthSession.objects.get(token=token)
        row.status = TelegramAuthSession.STATUS_USED
        with self.assertRaises(ValueError):
            telegram_auth.mark_authenticated(row, self.user)


class OneActiveFlowTests(FlowMixin, TestCase):
    def test_new_init_closes_the_previous_flow_of_the_same_browser(self):
        first = self.start()
        second = self.start()
        self.assertEqual(TelegramAuthSession.objects.get(token=first).status, TelegramAuthSession.STATUS_EXPIRED)
        self.assertEqual(TelegramAuthSession.objects.get(token=second).status, TelegramAuthSession.STATUS_PENDING)
        result = handle_telegram_auth_token(f"auth_{first}", TELEGRAM_ID)
        self.assertEqual(result.code, "expired")
        self.assertEqual(self.client.get(status_url(first)).json()["status"], "not_found")

    def test_new_init_closes_a_confirmed_but_unclaimed_flow(self):
        first = self.start()
        self.confirm(first)
        self.start()
        self.assertEqual(TelegramAuthSession.objects.get(token=first).status, TelegramAuthSession.STATUS_EXPIRED)

    def test_cancel_closes_only_this_browser_flow_and_clears_its_state(self):
        token = self.start(next="/users/my-courses/")
        self.confirm(token)
        self.assertEqual(self.client.post(reverse("telegram_auth_cancel")).json()["status"], "cancelled")
        self.assertEqual(TelegramAuthSession.objects.get(token=token).status, TelegramAuthSession.STATUS_EXPIRED)
        for key in (telegram_auth.SESSION_CLIENT_KEY, telegram_auth.SESSION_TOKEN_KEY, telegram_auth.SESSION_INTENT_KEY):
            self.assertNotIn(key, self.client.session)
        self.assertEqual(self.client.post(consume_url(token)).json()["status"], "not_found")
        self.assertFalse(self.logged_in())

    def test_cancel_never_reopens_a_used_flow(self):
        token = self.start()
        self.confirm(token)
        self.client.post(consume_url(token))
        self.client.post(reverse("telegram_auth_cancel"))
        self.assertEqual(TelegramAuthSession.objects.get(token=token).status, TelegramAuthSession.STATUS_USED)


class SafeIntentTests(FlowMixin, TestCase):
    def redirect_for(self, next_url):
        token = self.start(next=next_url)
        self.confirm(token)
        return self.client.post(consume_url(token)).json()["redirect_url"]

    def test_internal_next_is_honoured(self):
        self.assertEqual(self.redirect_for("/users/my-courses/"), "/users/my-courses/")
        self.assertNotIn(telegram_auth.SESSION_INTENT_KEY, self.client.session)

    def test_external_or_scheme_relative_next_falls_back_to_dashboard(self):
        for candidate in ("https://evil.example/x", "//evil.example/x", "javascript:alert(1)", ""):
            with self.subTest(candidate=candidate):
                self.client.logout()
                self.assertEqual(self.redirect_for(candidate), reverse("dashboard"))


@override_settings(TRUSTED_PROXY_HOPS=0)
class InitThrottleTests(FlowMixin, TestCase):
    def test_rejected_get_does_not_spend_the_init_budget(self):
        row = OperationalSettings.load()
        row.auth_telegram_init_ip_limit = 1
        row.save()
        for _ in range(3):
            self.assertEqual(self.client.get(reverse("telegram_auth_init")).status_code, 405)
        self.assertEqual(self.client.post(reverse("telegram_auth_init")).status_code, 200)
        throttled = self.client.post(reverse("telegram_auth_init"))
        self.assertEqual(throttled.status_code, 429)
        self.assertEqual(throttled.json()["status"], "throttled")


class PurgeTests(FlowMixin, TestCase):
    def make_rows(self, count, old):
        rows = TelegramAuthSession.objects.bulk_create(
            [TelegramAuthSession(token=f"{'eski' if old else 'yangi'}-{i}") for i in range(count)]
        )
        if old:
            TelegramAuthSession.objects.filter(pk__in=[r.pk for r in rows]).update(
                created_at=timezone.now() - telegram_auth.RETENTION - timedelta(minutes=1),
            )

    def test_purge_removes_only_rows_past_retention(self):
        self.make_rows(3, old=True)
        self.make_rows(2, old=False)
        self.assertEqual(telegram_auth.purge_expired(), 3)
        self.assertEqual(TelegramAuthSession.objects.count(), 2)

    def test_purge_is_bounded_per_call(self):
        self.make_rows(5, old=True)
        self.assertEqual(telegram_auth.purge_expired(limit=2), 2)
        self.assertEqual(TelegramAuthSession.objects.count(), 3)

    def test_init_trims_a_bounded_batch(self):
        self.make_rows(telegram_auth.PURGE_BATCH + 3, old=True)
        token = self.start()
        self.assertEqual(TelegramAuthSession.objects.filter(token__startswith="eski-").count(), 3)
        self.assertTrue(TelegramAuthSession.objects.filter(token=token).exists())

    def test_command_purges_everything_past_retention(self):
        self.make_rows(4, old=True)
        out = StringIO()
        call_command("prune_telegram_auth", stdout=out)
        self.assertIn("4", out.getvalue())
        self.assertFalse(TelegramAuthSession.objects.filter(token__startswith="eski-").exists())


@skipUnless(connection.vendor == "postgresql", "Haqiqiy qator qulfi faqat PostgreSQL'da sinaladi.")
class ParallelConsumeTests(TransactionTestCase):
    def test_parallel_consume_logs_in_exactly_once(self):
        user = User.objects.create_user("tg-parallel", email="tgp@example.test", telegram_id=TELEGRAM_ID)
        browser = SessionStore()
        browser[telegram_auth.SESSION_CLIENT_KEY] = "parallel-browser-key"
        browser.save()
        TelegramAuthSession.objects.create(
            token="parallel-token", client_key="parallel-browser-key",
            user=user, status=TelegramAuthSession.STATUS_AUTHENTICATED,
        )
        barrier = threading.Barrier(6)
        results, errors = [], []

        def worker():
            try:
                request = RequestFactory().post(consume_url("parallel-token"))
                request.session = SessionStore(session_key=browser.session_key)
                request.user = AnonymousUser()
                # G'olibning `login()`i eski sessiya qatorini o'chiradi: kalit oldindan o'qiladi.
                request.session.get(telegram_auth.SESSION_CLIENT_KEY)
                barrier.wait()
                results.append(telegram_auth.consume(request, "parallel-token").status)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(results.count(TelegramAuthSession.STATUS_AUTHENTICATED), 1, results)
        self.assertEqual(results.count(TelegramAuthSession.STATUS_USED), 5, results)
