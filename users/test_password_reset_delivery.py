"""PUB1.0f — parol tiklash xati: yetkazish release gate'i va halol javob.

Ilgari non-local profilda `EMAIL_HOST` bo'lmasa console backend tanlanardi:
sahifa "Havola yuborildi" derdi, xat hech kimga bormasdi, console esa tokenli
havolani konteyner logiga yozardi. Xat inglizcha (Django default'i) edi.
"""

import json
import re
import smtplib
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from aicontrol.models import FeatureFlag, SystemAuditEvent
from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import PROBE_FUNCTIONS
from core.email_delivery import RESET_DELIVERY_FAILED_ACTION, reset_delivery_available
from core.models import OperationalSettings
from users.checks import RESET_DELIVERY_CHECK_ID, check_reset_delivery


User = get_user_model()
CONSOLE = "django.core.mail.backends.console.EmailBackend"
LOCMEM = "django.core.mail.backends.locmem.EmailBackend"
SMTP = "django.core.mail.backends.smtp.EmailBackend"
KNOWN = "biladi@example.test"
RESET_LINK = re.compile(r"https?://[^\s\"<]+/users/password-reset-confirm/[^\s\"<]+/")


def set_v1(enabled):
    FeatureFlag.objects.update_or_create(slug="frontend_v1_auth", defaults={"enabled": enabled})


class ResetMixin:
    def setUp(self):
        row = OperationalSettings.load()
        row.auth_reset_account_limit = 100
        row.auth_reset_ip_limit = 100
        row.save()
        self.user = User.objects.create_user("biladi", email=KNOWN, password="Eski-parol-2026", first_name="Ali")

    def request_reset(self, email=KNOWN):
        return self.client.post(reverse("password_reset"), {"email": email})


# Non-local profilda xat yetib bormaydigan muhit. `locmem` ham jim backend —
# outbox esa hech narsa yuborilmaganini isbotlaydi.
@override_settings(IS_LOCAL=False, EMAIL_BACKEND=LOCMEM)
class FailClosedTests(ResetMixin, TestCase):
    def test_form_is_replaced_by_an_honest_notice(self):
        for enabled in (False, True):
            set_v1(enabled)
            with self.subTest(v1=enabled):
                response = self.client.get(reverse("password_reset"))
                self.assertContains(response, "data-reset-unavailable")
                self.assertContains(response, "tiklash hozircha ishlamayapti")
                self.assertNotContains(response, 'name="email"')

    def test_post_is_refused_identically_for_every_email_and_sends_nothing(self):
        bodies = set()
        for email in (KNOWN, "yoq@example.test"):
            response = self.request_reset(email)
            self.assertEqual(response.status_code, 503)
            self.assertContains(response, "tiklash hozircha ishlamayapti", status_code=503)
            bodies.add(re.sub(r'value="[^"]*"', "", response.content.decode()).replace(email, "EMAIL"))
        self.assertEqual(len(bodies), 1)
        self.assertEqual(mail.outbox, [])

    def test_release_check_fails(self):
        errors = check_reset_delivery(None)
        self.assertEqual([error.id for error in errors], [RESET_DELIVERY_CHECK_ID])

    @override_settings(EMAIL_BACKEND=CONSOLE)
    def test_console_in_production_is_red_in_control_center(self):
        self.assertFalse(reset_delivery_available())
        result = PROBE_FUNCTIONS["email"](capability_by_slug("email"))
        self.assertEqual(result.status, "red")


class LocalConsoleTests(ResetMixin, TestCase):
    @override_settings(IS_LOCAL=True, EMAIL_BACKEND=CONSOLE)
    def test_local_console_is_allowed(self):
        self.assertTrue(reset_delivery_available())
        self.assertEqual(check_reset_delivery(None), [])
        self.assertEqual(PROBE_FUNCTIONS["email"](capability_by_slug("email")).status, "green")
        self.assertContains(self.client.get(reverse("password_reset")), 'name="email"')

    @override_settings(IS_LOCAL=False, EMAIL_BACKEND=SMTP, EMAIL_HOST="smtp.example.test")
    def test_configured_smtp_passes_release_check_and_is_green(self):
        self.assertTrue(reset_delivery_available())
        self.assertEqual(check_reset_delivery(None), [])
        self.assertEqual(PROBE_FUNCTIONS["email"](capability_by_slug("email")).status, "green")


class SameResponseTests(ResetMixin, TestCase):
    def test_known_unknown_inactive_and_passwordless_accounts_look_the_same(self):
        User.objects.create_user("faolsiz", email="faolsiz@example.test", password="Parol-2026-x", is_active=False)
        telegram = User.objects.create_user("tg_1", email="tg_1@telegram.local", telegram_id=1)
        telegram.set_unusable_password()
        telegram.save()
        for enabled in (False, True):
            set_v1(enabled)
            mail.outbox = []
            locations = set()
            for email in (KNOWN, "yoq@example.test", "faolsiz@example.test", "tg_1@telegram.local"):
                with self.subTest(email=email, v1=enabled):
                    response = self.request_reset(email)
                    self.assertEqual(response.status_code, 302)
                    locations.add(response["Location"])
            self.assertEqual(locations, {reverse("password_reset_done")})
            self.assertEqual([message.to for message in mail.outbox], [[KNOWN]])

    def test_done_page_never_claims_delivery(self):
        for enabled in (False, True):
            set_v1(enabled)
            with self.subTest(v1=enabled):
                response = self.client.get(reverse("password_reset_done"))
                self.assertNotContains(response, "Havola yuborildi")
                self.assertNotContains(response, "yubordik")
                self.assertContains(response, "tasdiqlamaydi")


class UzbekEmailTests(ResetMixin, TestCase):
    def test_subject_plain_and_html_are_uzbek_and_carry_one_link(self):
        self.request_reset()
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Parolni tiklash — AzureLMS")
        self.assertIn("Assalomu alaykum, Ali!", message.body)
        self.assertIn("bir marta ishlaydi", message.body)
        self.assertIn("e’tiborsiz qoldiring", message.body)
        self.assertNotIn("You're receiving this email", message.body)
        # Oddiy matn qismi haqiqatan oddiy matn: HTML shablon unga tushib qolmasin.
        self.assertNotRegex(message.body, r"<[a-zA-Z!/]")
        self.assertEqual(len(RESET_LINK.findall(message.body)), 1)
        html, mimetype = message.alternatives[0]
        self.assertEqual(mimetype, "text/html")
        self.assertIn('lang="uz"', html)
        self.assertIn('content="no-referrer"', html)
        self.assertIn(RESET_LINK.search(message.body).group(0), html)
        self.assertNotIn("<img", html)


class DeliveryFailureTests(ResetMixin, TestCase):
    def test_smtp_failure_keeps_the_generic_answer_and_leaves_redacted_evidence(self):
        sent = {}

        def failing_send(message, *args, **kwargs):
            sent["body"] = message.body
            raise smtplib.SMTPServerDisconnected("ulanish uzildi")

        with mock.patch("django.core.mail.EmailMultiAlternatives.send", autospec=True, side_effect=failing_send):
            with self.assertLogs("users.forms", level="WARNING") as logs:
                failed = self.request_reset()
        unknown = self.request_reset("yoq@example.test")
        self.assertEqual((failed.status_code, failed["Location"]), (unknown.status_code, unknown["Location"]))

        event = SystemAuditEvent.objects.get(action=RESET_DELIVERY_FAILED_ACTION)
        self.assertEqual(event.outcome, SystemAuditEvent.OUTCOME_FAILURE)
        self.assertEqual(event.error, "SMTPServerDisconnected")
        self.assertEqual(event.target_id, str(self.user.pk))
        link = RESET_LINK.search(sent["body"]).group(0)
        token = link.rstrip("/").rsplit("/", 1)[-1]
        evidence = json.dumps([event.target_label, event.reason, event.error, event.before, event.after,
                               event.actor_label, event.user_agent]) + " ".join(logs.output)
        for secret in (link, token, KNOWN):
            self.assertNotIn(secret, evidence)
        self.assertIsNone(event.ip_address)

    @override_settings(IS_LOCAL=False, EMAIL_BACKEND=SMTP, EMAIL_HOST="smtp.example.test")
    def test_recent_failures_turn_the_email_light_amber(self):
        from core.email_delivery import record_reset_delivery_failure

        record_reset_delivery_failure(self.user, smtplib.SMTPException())
        result = PROBE_FUNCTIONS["email"](capability_by_slug("email"))
        self.assertEqual(result.status, "amber")
        self.assertIn(("reset_failures_24h", "1"), result.details)


class OneUseLinkTests(ResetMixin, TestCase):
    def test_link_sets_a_new_password_once_and_never_leaks_as_referrer(self):
        self.request_reset()
        link = RESET_LINK.search(mail.outbox[0].body).group(0)
        path = "/" + link.split("://", 1)[1].split("/", 1)[1]

        opened = self.client.get(path)
        self.assertEqual(opened.status_code, 302)
        self.assertEqual(opened["Referrer-Policy"], "no-referrer")
        form_page = self.client.get(opened["Location"])
        self.assertEqual(form_page["Referrer-Policy"], "no-referrer")
        done = self.client.post(opened["Location"], {"new_password1": "Yangi-parol-2026!", "new_password2": "Yangi-parol-2026!"})
        self.assertEqual(done.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Yangi-parol-2026!"))

        replay = self.client.get(path, follow=True)
        self.assertFalse(replay.context["validlink"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Yangi-parol-2026!"))
