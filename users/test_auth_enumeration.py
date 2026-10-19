"""PUB1.4c — enumeration va qolgan auth eshiklari.

Asosiy da'vo: login va parol tiklash javobi (matn, status, javobgacha
bajariladigan ish) hisob mavjudligini oshkor qilmaydi; ro'yxatda band email
majburiy email tasdig'isiz (PUB-D14) yashirib bo'lmaydi, shuning uchun uni
sinab chiqish cheklangan va limitdan keyin umuman tekshirilmaydi; admin
kirishi va parol o'zgartirish ham shu cheklovda; begona odam yopib qo'ygan
hisobning egasi parolni tiklab darhol qaytadi; doimiy blok yo'q.

Vaqt shartnomasi soat bilan emas, ish bilan o'lchanadi: devor soati CI'da
beqaror, "har yo'lda parol xeshi bir xil marta" va "javobdan oldin hisob
jadvaliga so'rov yo'q" esa aniq va qayta tekshiriladigan.
"""

from unittest import mock

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import MD5PasswordHasher
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.backends.db import SessionStore
from django.core import mail
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from aicontrol.models import FeatureFlag
from core.models import OperationalSettings
from users import auth_abuse
from users.admin import ThrottledAdminAuthenticationForm
from users.backends import find_login_user
from users.forms import CustomUserCreationForm, UzbekPasswordResetForm
from users.frontend_v1_auth import PasswordResetView
from users.models import AuthThrottleBucket

User = get_user_model()
PASSWORD = "Kuchli-parol-2026"
WRONG = "Notogri-parol-1"
INVALID_LOGIN = "Email yoki username va parol mos kelmadi"


def set_limits(**values):
    row = OperationalSettings.load()
    for name, value in values.items():
        setattr(row, name, value)
    row.save()


def enforce(enabled=True):
    FeatureFlag.objects.update_or_create(slug="auth_throttle_enforcement", defaults={"enabled": enabled})


def bucket_count(scope):
    return AuthThrottleBucket.objects.filter(scope=scope).count()


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class LoginHashWorkTests(TestCase):
    """Har login yo'lida parol xeshi bir xil marta: javob vaqti hisobni bildirmaydi."""

    def setUp(self):
        enforce(False)  # bu yerda faqat ish hajmi o'lchanadi
        User.objects.create_user("ali", email="ali@example.test", password=PASSWORD)
        User.objects.create_user("tg_777", email="")  # Telegram: parolsiz
        User.objects.create_user("nofaol", email="nofaol@example.test", password=PASSWORD, is_active=False)
        # Ikki hisobda bir xil email (admin/Telegram ulash orqali bo'lishi mumkin).
        User.objects.create_user("ikki1", email="ikki@example.test", password=PASSWORD)
        User.objects.create_user("ikki2", email="IKKI@example.test", password=PASSWORD)
        # Bir hisobning username'i boshqasining emailiga teng — ilgari 500 edi.
        User.objects.create_user("bir@example.test", email="boshqa@example.test", password=PASSWORD)
        User.objects.create_user("bir", email="bir@example.test", password=PASSWORD)

    def attempt(self, identifier):
        original = MD5PasswordHasher.encode
        with mock.patch.object(MD5PasswordHasher, "encode", autospec=True, side_effect=original) as spy:
            response = self.client.post(reverse("login"), {"username": identifier, "password": WRONG})
        return spy.call_count, response

    def test_every_failure_path_hashes_the_same_number_of_times(self):
        identifiers = (
            "ali@example.test", "ali", "yoq@example.test", "yoq",
            "tg_777", "nofaol@example.test", "nofaol", "ikki@example.test", "bir@example.test",
        )
        runs = {}
        for identifier in identifiers:
            count, response = self.attempt(identifier)
            runs[identifier] = count
            with self.subTest(identifier=identifier):
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, INVALID_LOGIN)
                self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(set(runs.values())), 1, runs)
        self.assertGreaterEqual(next(iter(runs.values())), 1)

    def test_lookup_prefers_exact_username_then_a_unique_email(self):
        self.assertEqual(find_login_user("bir@example.test").username, "bir@example.test")
        self.assertEqual(find_login_user("ALI@example.test").username, "ali")
        self.assertIsNone(find_login_user("ikki@example.test"))
        self.assertIsNone(find_login_user("yoq@example.test"))

    def test_the_right_password_still_signs_in_by_email_or_username(self):
        for identifier in ("ali@example.test", "ali"):
            response = self.client.post(reverse("login"), {"username": identifier, "password": PASSWORD})
            with self.subTest(identifier=identifier):
                self.assertEqual(response.status_code, 302)
            self.client.logout()


@override_settings(TRUSTED_PROXY_HOPS=0)
class RegistrationProbeTests(TestCase):
    def setUp(self):
        FeatureFlag.objects.update_or_create(slug="public_registration", defaults={"enabled": True})
        enforce()
        set_limits(auth_register_attempt_ip_limit=3, auth_register_ip_limit=50)
        User.objects.create_user("bor", email="bor@example.test", password=PASSWORD)

    def register(self, email, password2=PASSWORD):
        return self.client.post(reverse("register"), {
            "first_name": "Sinov", "last_name": "", "email": email,
            "password1": PASSWORD, "password2": password2,
        })

    def test_probing_emails_stops_and_the_blocked_page_checks_nothing(self):
        for email in ("bor@example.test", "yoq1@example.test", "BOR@example.test"):
            response = self.register(email, password2=PASSWORD if email.lower() == "bor@example.test" else "boshqa")
            self.assertEqual(response.status_code, 200)
        original = CustomUserCreationForm.clean_email
        with mock.patch.object(CustomUserCreationForm, "clean_email", autospec=True, side_effect=original) as spy:
            blocked = self.register("bor@example.test")
        spy.assert_not_called()
        self.assertEqual(blocked.status_code, 429)
        self.assertTrue(blocked["Retry-After"].isdigit())
        self.assertContains(blocked, "Juda ko‘p urinish", status_code=429)
        self.assertNotContains(blocked, "yangi hisob ochib bo‘lmaydi", status_code=429)
        # Kiritilgan email saqlanadi, parol esa qaytarib chizilmaydi.
        self.assertContains(blocked, 'value="bor@example.test"', status_code=429)
        self.assertNotContains(blocked, PASSWORD, status_code=429)

    def test_a_successful_registration_does_not_spend_the_attempt_budget(self):
        self.assertEqual(self.register("yangi@example.test").status_code, 302)
        self.assertEqual(bucket_count(auth_abuse.SCOPE_REGISTER_ATTEMPT_IP), 0)

    def test_window_end_reopens_the_form(self):
        for _ in range(4):
            self.register("bor@example.test")
        from datetime import timedelta

        from django.utils import timezone

        with mock.patch("users.auth_abuse.timezone.now", return_value=timezone.now() + timedelta(minutes=61)):
            self.assertEqual(self.register("yangi@example.test").status_code, 302)

    def test_duplicate_message_names_the_next_step_for_the_delivery_state(self):
        for available, offers_reset in ((True, True), (False, False)):
            with mock.patch("core.email_delivery.reset_delivery_available", return_value=available):
                response = self.register("bor@example.test")
            with self.subTest(delivery=available):
                self.assertContains(response, "Bu email bilan yangi hisob ochib bo‘lmaydi.")
                self.assertNotContains(response, "allaqachon ro")
                self.assertEqual("parolni tiklang" in response.content.decode(), offers_reset)


class PasswordResetDeferredWorkTests(TestCase):
    """Hisobni qidirish va xat — javobdan keyin: mavjud va noma'lum email bir xil yo'ldan."""

    def setUp(self):
        enforce()
        self.user = User.objects.create_user("ali", email="ali@example.test", password=PASSWORD)

    def run_view(self, email):
        request = RequestFactory().post(reverse("password_reset"), {"email": email})
        request._dont_enforce_csrf_checks = True
        request.session = SessionStore()
        request.user = AnonymousUser()
        with CaptureQueriesContext(connection) as queries:
            response = PasswordResetView.as_view()(request)
        return response, [query["sql"] for query in queries.captured_queries]

    def test_the_response_is_ready_before_any_account_lookup_or_mail(self):
        # Birinchi so'rov IP hisoblagich qatorini yaratadi (+INSERT) — ikkala holat
        # bir xil boshlanishi uchun oldindan isitiladi.
        self.run_view("isitish@example.test")[0].close()
        before_response, mails = {}, {}
        for email in ("ali@example.test", "yoq@example.test"):
            mail.outbox.clear()
            response, queries = self.run_view(email)
            with self.subTest(email=email):
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response["Location"], reverse("password_reset_done"))
                self.assertEqual(mail.outbox, [])
                self.assertFalse([sql for sql in queries if "users_customuser" in sql], queries)
            before_response[email] = len(queries)
            response.close()
            response.close()  # ikkinchi chaqiruv xatni qayta yubormaydi
            mails[email] = len(mail.outbox)
        self.assertEqual(before_response["ali@example.test"], before_response["yoq@example.test"])
        self.assertEqual(mails, {"ali@example.test": 1, "yoq@example.test": 0})

    def test_full_request_still_delivers_the_mail(self):
        response = self.client.post(reverse("password_reset"), {"email": "ali@example.test"})
        self.assertRedirects(response, reverse("password_reset_done"), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ali@example.test"])

    def test_a_failure_after_the_response_is_logged_not_raised(self):
        response, _ = self.run_view("ali@example.test")
        with mock.patch.object(UzbekPasswordResetForm, "save", side_effect=RuntimeError("shablon")):
            with self.assertLogs("users.frontend_v1_auth", level="ERROR"):
                response.close()
        self.assertEqual(mail.outbox, [])


@override_settings(TRUSTED_PROXY_HOPS=0)
class LegitimateRecoveryTests(TestCase):
    def setUp(self):
        enforce()
        set_limits(auth_login_account_limit=2, auth_login_ip_limit=50)
        self.user = User.objects.create_user("ali", email="ali@example.test", password=PASSWORD)

    def login(self, username, password, ip="10.0.0.1"):
        return self.client.post(reverse("login"), {"username": username, "password": password}, REMOTE_ADDR=ip)

    def test_attempts_from_many_addresses_still_close_the_account(self):
        for index in range(2):
            self.login("ali@example.test", WRONG, ip=f"10.0.1.{index}")
        self.assertEqual(self.login("ali@example.test", PASSWORD, ip="10.0.9.9").status_code, 429)

    def test_resetting_the_password_lets_the_owner_straight_back_in(self):
        for identifier in ("ali@example.test", "ali"):
            for _ in range(2):
                self.login(identifier, WRONG)
        self.assertEqual(self.login("ali", PASSWORD).status_code, 429)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        opened = self.client.get(reverse("password_reset_confirm", args=[uid, default_token_generator.make_token(self.user)]))
        new_password = "Yangi-Qatiy-Kalit-77"
        done = self.client.post(opened["Location"], {"new_password1": new_password, "new_password2": new_password})
        self.assertEqual(done.status_code, 302)
        for identifier in ("ali@example.test", "ali"):
            response = self.login(identifier, new_password)
            with self.subTest(identifier=identifier):
                self.assertEqual(response.status_code, 302)
            self.client.logout()


@override_settings(TRUSTED_PROXY_HOPS=0)
class PasswordChangeThrottleTests(TestCase):
    def setUp(self):
        enforce()
        set_limits(auth_login_account_limit=2)
        self.user = User.objects.create_user("ali", email="ali@example.test", password=PASSWORD)
        self.client.force_login(self.user)

    def change(self, old):
        return self.client.post(reverse("update_password"), {
            "old_password": old, "new_password1": "Yangi-Qatiy-Kalit-77", "new_password2": "Yangi-Qatiy-Kalit-77",
        }, follow=True)

    def test_guessing_the_current_password_is_limited(self):
        for _ in range(2):
            self.assertContains(self.change(WRONG), "Joriy parol noto")
        blocked = self.change(PASSWORD)
        self.assertContains(blocked, "Juda ko‘p urinish")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_the_right_password_clears_the_counter(self):
        self.change(WRONG)
        self.change(PASSWORD)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Yangi-Qatiy-Kalit-77"))
        self.assertEqual(bucket_count(auth_abuse.SCOPE_PASSWORD_CHANGE_ACCOUNT), 0)


@override_settings(TRUSTED_PROXY_HOPS=0)
class AdminLoginThrottleTests(TestCase):
    def setUp(self):
        enforce()
        set_limits(auth_login_account_limit=2, auth_login_ip_limit=50)
        self.staff = User.objects.create_user("egasi", email="egasi@example.test", password=PASSWORD, is_staff=True)

    def form(self, password):
        request = RequestFactory().post("/admin/login/", REMOTE_ADDR="10.0.0.1")
        return ThrottledAdminAuthenticationForm(request, data={"username": "egasi", "password": password})

    def test_the_admin_site_uses_the_throttled_form(self):
        self.assertIs(admin.site.login_form, ThrottledAdminAuthenticationForm)

    def test_admin_failures_share_the_login_counter(self):
        for _ in range(2):
            self.assertFalse(self.form(WRONG).is_valid())
        blocked = self.form(PASSWORD)
        with mock.patch("django.contrib.auth.forms.authenticate") as authenticate:
            self.assertFalse(blocked.is_valid())
        authenticate.assert_not_called()
        self.assertIn("Juda ko‘p urinish", str(blocked.non_field_errors()))
        # Asosiy login ham shu hisob uchun yopiq — ikki eshik, bitta hisoblagich.
        response = self.client.post(reverse("login"), {"username": "egasi", "password": PASSWORD}, REMOTE_ADDR="10.0.0.2")
        self.assertEqual(response.status_code, 429)

    def test_success_clears_the_account_counter(self):
        self.assertFalse(self.form(WRONG).is_valid())
        self.assertTrue(self.form(PASSWORD).is_valid())
        self.assertEqual(bucket_count(auth_abuse.SCOPE_LOGIN_ACCOUNT), 0)
