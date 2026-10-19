"""PUB1.0c — auth urinishlari cheklovi va P0 enforcement.

Asosiy da'vo: login, ro'yxat, parol tiklash va Telegram init oynadagi limitdan
keyin generik `429` + `Retry-After` qaytaradi va hech narsa yozmaydi/yubormaydi;
oyna tugashi bilan qonuniy foydalanuvchi qaytadi; hisoblagich raw identity
saqlamaydi va javob hisob mavjudligini oshkor qilmaydi. Limitlar owner
sozlamasi, yoqish/o'chirish flagda.
"""

import threading
from datetime import timedelta
from io import StringIO
from unittest import mock, skipUnless

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.db import DatabaseError, connection
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag, SystemAuditEvent
from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import PROBE_FUNCTIONS
from core.models import OperationalSettings
from users import auth_abuse
from users.models import AuthThrottleBucket, TelegramAuthSession

User = get_user_model()
PASSWORD = "Kuchli-parol-2026"


def set_limits(**values):
    row = OperationalSettings.load()
    for name, value in values.items():
        setattr(row, name, value)
    row.save()


def set_enforcement(enabled):
    FeatureFlag.objects.update_or_create(slug="auth_throttle_enforcement", defaults={"enabled": enabled})


def later(minutes):
    return timezone.now() + timedelta(minutes=minutes)


class ClientIpTests(TestCase):
    def request(self, remote="10.0.0.5", forwarded=None):
        meta = {"REMOTE_ADDR": remote}
        if forwarded is not None:
            meta["HTTP_X_FORWARDED_FOR"] = forwarded
        return RequestFactory().get("/", **meta)

    @override_settings(TRUSTED_PROXY_HOPS=0)
    def test_without_trusted_proxy_forwarded_header_is_ignored(self):
        self.assertEqual(auth_abuse.client_ip(self.request(forwarded="1.2.3.4")), "10.0.0.5")

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_one_trusted_hop_uses_the_rightmost_value(self):
        # Mijoz chapga istalgan narsani yoza oladi; o'ngdagini Caddy qo'ygan.
        self.assertEqual(auth_abuse.client_ip(self.request(forwarded="6.6.6.6, 9.9.9.9")), "9.9.9.9")
        self.assertEqual(auth_abuse.client_ip(self.request(forwarded="")), "10.0.0.5")
        self.assertEqual(auth_abuse.client_ip(self.request(forwarded="not-an-ip")), "10.0.0.5")
        self.assertEqual(auth_abuse.client_ip(self.request(forwarded="2001:db8::1")), "2001:db8::1")


class ThrottleCoreTests(TestCase):
    def setUp(self):
        set_limits(auth_login_account_limit=3, auth_login_window_minutes=15)

    def test_exact_boundary_for_record_and_peek(self):
        for _ in range(3):
            self.assertTrue(auth_abuse.record(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test").allowed)
        self.assertFalse(auth_abuse.peek(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test").allowed)
        denied = auth_abuse.record(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test")
        self.assertFalse(denied.allowed)
        self.assertGreater(denied.retry_after, 0)
        self.assertLessEqual(denied.retry_after, 15 * 60)
        self.assertTrue(auth_abuse.peek(auth_abuse.SCOPE_LOGIN_ACCOUNT, "boshqa@example.test").allowed)

    def test_window_end_resets_the_counter(self):
        for _ in range(4):
            auth_abuse.record(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test")
        self.assertFalse(auth_abuse.peek(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test").allowed)
        self.assertTrue(auth_abuse.peek(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test", now=later(16)).allowed)

    def test_no_permanent_lockout_blocked_until_is_the_window_end(self):
        for _ in range(3):
            auth_abuse.record(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test")
        bucket = AuthThrottleBucket.objects.get()
        self.assertEqual(bucket.blocked_until, bucket.expires_at)
        self.assertLessEqual(bucket.expires_at - bucket.window_start, timedelta(minutes=15))

    def test_identity_is_never_stored_raw(self):
        auth_abuse.record(auth_abuse.SCOPE_LOGIN_ACCOUNT, "maxfiy@example.test")
        auth_abuse.record(auth_abuse.SCOPE_LOGIN_IP, "203.0.113.7")
        for bucket in AuthThrottleBucket.objects.all():
            stored = f"{bucket.scope}|{bucket.key_digest}"
            self.assertNotIn("maxfiy", stored)
            self.assertNotIn("203.0.113.7", stored)
            self.assertEqual(len(bucket.key_digest), 64)
        digests = set(AuthThrottleBucket.objects.values_list("key_digest", flat=True))
        self.assertEqual(len(digests), 2)

    def test_identifier_is_normalized(self):
        auth_abuse.record(auth_abuse.SCOPE_LOGIN_ACCOUNT, auth_abuse.normalize_identifier("  Ali@Example.TEST "))
        auth_abuse.record(auth_abuse.SCOPE_LOGIN_ACCOUNT, auth_abuse.normalize_identifier("ali@example.test"))
        self.assertEqual(AuthThrottleBucket.objects.get().count, 2)

    def test_clear_resets_only_the_current_key(self):
        for key in ("a@example.test", "b@example.test"):
            auth_abuse.record(auth_abuse.SCOPE_LOGIN_ACCOUNT, key)
        auth_abuse.clear(auth_abuse.SCOPE_LOGIN_ACCOUNT, "a@example.test")
        self.assertEqual(AuthThrottleBucket.objects.count(), 1)

    def test_enforcement_off_counts_but_never_denies(self):
        set_enforcement(False)
        for _ in range(5):
            decision = auth_abuse.record(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test")
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.enforced)
        self.assertEqual(AuthThrottleBucket.objects.get().count, 5)

    def test_storage_failure_fails_open(self):
        with mock.patch.object(type(AuthThrottleBucket.objects), "get_or_create", side_effect=DatabaseError("x")):
            self.assertTrue(auth_abuse.record(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test").allowed)
        with mock.patch.object(type(AuthThrottleBucket.objects), "filter", side_effect=DatabaseError("x")):
            self.assertTrue(auth_abuse.peek(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test").allowed)

    def test_owner_limit_change_applies_without_deploy(self):
        for _ in range(3):
            auth_abuse.record(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test")
        self.assertFalse(auth_abuse.peek(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test").allowed)
        set_limits(auth_login_account_limit=10)
        self.assertTrue(auth_abuse.peek(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test").allowed)

    def test_cleanup_is_bounded_and_rerunnable(self):
        past = timezone.now() - timedelta(hours=2)
        AuthThrottleBucket.objects.bulk_create([
            AuthThrottleBucket(scope="login_ip", key_digest=f"{i:064d}", window_start=past, count=1, expires_at=past)
            for i in range(5)
        ])
        auth_abuse.record(auth_abuse.SCOPE_LOGIN_ACCOUNT, "ali@example.test")  # opportunistic cleanup
        self.assertEqual(AuthThrottleBucket.objects.count(), 1)
        out = StringIO()
        call_command("prune_auth_throttle", stdout=out)
        self.assertIn("O'chirildi: 0", out.getvalue())
        self.assertEqual(AuthThrottleBucket.objects.count(), 1)


@override_settings(TRUSTED_PROXY_HOPS=0)
class LoginEnforcementTests(TestCase):
    def setUp(self):
        set_limits(auth_login_account_limit=2, auth_login_ip_limit=50, auth_login_window_minutes=15)
        self.user = User.objects.create_user("ali", email="ali@example.test", password=PASSWORD)

    def login(self, username, password, **extra):
        return self.client.post(reverse("login"), {"username": username, "password": password}, **extra)

    def test_account_limit_blocks_even_the_correct_password(self):
        for _ in range(2):
            self.assertEqual(self.login("ali", "noto'g'ri").status_code, 200)
        with mock.patch("django.contrib.auth.forms.authenticate") as authenticate:
            response = self.login("ali", PASSWORD)
        authenticate.assert_not_called()
        self.assertEqual(response.status_code, 429)
        self.assertTrue(response["Retry-After"].isdigit())
        self.assertContains(response, "Juda ko‘p urinish", status_code=429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unknown_and_existing_accounts_behave_the_same(self):
        responses = {}
        for username in ("ali", "mavjud-emas"):
            for _ in range(2):
                self.login(username, "xato")
            responses[username] = self.login(username, "xato")
        self.assertEqual(responses["ali"].status_code, responses["mavjud-emas"].status_code)
        self.assertEqual(responses["ali"].status_code, 429)

    def test_window_end_lets_the_legitimate_user_back_in(self):
        for _ in range(3):
            self.login("ali", "xato")
        with mock.patch("users.auth_abuse.timezone.now", return_value=later(16)):
            response = self.login("ali", PASSWORD)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get("_auth_user_id"), str(self.user.pk))

    def test_success_resets_the_account_counter(self):
        self.login("ali", "xato")
        self.assertEqual(self.login("ali", PASSWORD).status_code, 302)
        self.client.logout()
        self.login("ali", "xato")
        self.assertEqual(self.login("ali", "xato").status_code, 200)

    def test_ip_layer_stops_spraying_across_accounts(self):
        set_limits(auth_login_account_limit=100, auth_login_ip_limit=3)
        for name in ("u1", "u2", "u3"):
            self.login(name, "xato")
        self.assertEqual(self.login("u4", "xato").status_code, 429)

    def test_enforcement_flag_off_never_returns_429(self):
        set_enforcement(False)
        for _ in range(4):
            response = self.login("ali", "xato")
        self.assertEqual(response.status_code, 200)

    @override_settings(TRUSTED_PROXY_HOPS=1)
    def test_spoofed_forwarded_header_does_not_reset_the_ip_counter(self):
        set_limits(auth_login_account_limit=100, auth_login_ip_limit=2)
        for i in range(2):
            self.login(f"x{i}", "xato", HTTP_X_FORWARDED_FOR=f"6.6.6.{i}, 9.9.9.9")
        response = self.login("x9", "xato", HTTP_X_FORWARDED_FOR="7.7.7.7, 9.9.9.9")
        self.assertEqual(response.status_code, 429)


@override_settings(TRUSTED_PROXY_HOPS=0)
class RegistrationEnforcementTests(TestCase):
    form = {
        "username": "yangi-{n}", "email": "yangi{n}@example.test", "first_name": "Yangi",
        "last_name": "O'quvchi", "password1": PASSWORD, "password2": PASSWORD,
    }

    def payload(self, n):
        return {key: value.format(n=n) for key, value in self.form.items()}

    def test_ip_limit_stops_mass_account_creation(self):
        FeatureFlag.objects.update_or_create(slug="public_registration", defaults={"enabled": True})
        set_limits(auth_register_ip_limit=1)
        self.assertEqual(self.client.post(reverse("register"), self.payload(1)).status_code, 302)
        self.client.logout()
        before = User.objects.count()
        response = self.client.post(reverse("register"), self.payload(2))
        self.assertEqual(response.status_code, 429)
        self.assertTrue(response["Retry-After"].isdigit())
        self.assertEqual(User.objects.count(), before)


@override_settings(TRUSTED_PROXY_HOPS=0)
class PasswordResetEnforcementTests(TestCase):
    def setUp(self):
        set_limits(auth_reset_account_limit=1, auth_reset_ip_limit=50)
        User.objects.create_user("ali", email="ali@example.test", password=PASSWORD)

    def reset(self, email):
        return self.client.post(reverse("password_reset"), {"email": email})

    def test_second_request_for_the_same_email_sends_nothing(self):
        self.assertEqual(self.reset("ali@example.test").status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        response = self.reset("ali@example.test")
        self.assertEqual(response.status_code, 429)
        self.assertTrue(response["Retry-After"].isdigit())
        self.assertEqual(len(mail.outbox), 1)

    def test_unknown_email_follows_the_same_sequence(self):
        self.assertEqual(self.reset("hech-kim@example.test").status_code, 302)
        self.assertEqual(self.reset("hech-kim@example.test").status_code, 429)
        self.assertEqual(len(mail.outbox), 0)

    def test_ip_limit_stops_spraying_many_emails(self):
        set_limits(auth_reset_account_limit=100, auth_reset_ip_limit=2)
        self.reset("a@example.test")
        self.reset("b@example.test")
        self.assertEqual(self.reset("c@example.test").status_code, 429)


@override_settings(TRUSTED_PROXY_HOPS=0)
class TelegramInitEnforcementTests(TestCase):
    def test_init_limit_writes_no_session(self):
        set_limits(auth_telegram_init_ip_limit=2)
        for _ in range(2):
            self.assertEqual(self.client.post(reverse("telegram_auth_init")).status_code, 200)
        before = TelegramAuthSession.objects.count()
        response = self.client.post(reverse("telegram_auth_init"))
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["status"], "throttled")
        self.assertTrue(response["Retry-After"].isdigit())
        self.assertEqual(TelegramAuthSession.objects.count(), before)


class OwnerPanelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser("egasi", email="owner@example.test", password=PASSWORD)
        self.client.force_login(self.owner)

    def post(self, **overrides):
        payload = {name: getattr(OperationalSettings.load(), name) for name in (
            "auth_login_account_limit", "auth_login_ip_limit", "auth_login_window_minutes",
            "auth_register_ip_limit", "auth_register_attempt_ip_limit", "auth_register_window_minutes",
            "auth_reset_account_limit", "auth_reset_ip_limit", "auth_reset_window_minutes",
            "auth_telegram_init_ip_limit", "auth_telegram_init_window_minutes", "auth_throttle_rows_amber",
        )}
        payload.update(form_name="auth_throttle", change_reason="Jonli darsda o'quvchilar bloklandi", confirm_change="on")
        payload.update(overrides)
        return self.client.post(reverse("backoffice_runtime_settings"), payload)

    def test_change_is_audited(self):
        self.assertEqual(self.post(auth_login_ip_limit=40).status_code, 302)
        self.assertEqual(OperationalSettings.load().auth_login_ip_limit, 40)
        event = SystemAuditEvent.objects.get(action="settings.auth_throttle.update")
        self.assertIn("auth_login_ip_limit", str(event.after))

    def test_out_of_range_and_missing_reason_write_nothing(self):
        self.assertEqual(self.post(auth_login_window_minutes=0).status_code, 200)
        self.assertEqual(self.post(auth_login_ip_limit=40, change_reason="").status_code, 200)
        self.assertEqual(OperationalSettings.load().auth_login_ip_limit, 20)
        self.assertFalse(SystemAuditEvent.objects.filter(action="settings.auth_throttle.update").exists())


class ControlCenterProbeTests(TestCase):
    def probe(self):
        return PROBE_FUNCTIONS["auth_throttle"](capability_by_slug("auth_throttle"))

    def test_green_by_default_and_amber_when_disabled(self):
        self.assertEqual(self.probe().status, "green")
        set_enforcement(False)
        self.assertEqual(self.probe().status, "amber")

    @override_settings(IS_LOCAL=False, TRUSTED_PROXY_HOPS=0)
    def test_amber_when_production_trusts_no_proxy(self):
        self.assertEqual(self.probe().status, "amber")

    def test_amber_when_the_table_grows_past_the_owner_threshold(self):
        set_limits(auth_throttle_rows_amber=100)
        now = timezone.now()
        AuthThrottleBucket.objects.bulk_create([
            AuthThrottleBucket(scope="login_ip", key_digest=f"{i:064d}", window_start=now, count=1,
                               expires_at=now + timedelta(minutes=5))
            for i in range(101)
        ])
        result = self.probe()
        self.assertEqual(result.status, "amber")
        self.assertIn(("rows", "101"), result.details)


@skipUnless(connection.vendor == "postgresql", "Haqiqiy qator qulfi faqat PostgreSQL'da sinaladi.")
class ConcurrentRecordTests(TransactionTestCase):
    def test_parallel_records_lose_no_increment(self):
        set_limits(auth_login_ip_limit=1000)
        errors = []

        def worker():
            try:
                auth_abuse.record(auth_abuse.SCOPE_LOGIN_IP, "198.51.100.9")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(AuthThrottleBucket.objects.get().count, 10)
