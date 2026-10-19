"""PUB1.5c — sertifikatni tasodifiy kod bilan ochiq tekshirish.

Asosiy da'volar:
* kod 192 bitli, noyob, to'qnashuvda qayta yaratiladi; ketma-ket ID hech narsa ochmaydi;
* sahifa faqat holat, ism ko'rinishi, kurs va sanani ko'rsatadi — ball, email,
  username, eski raqam yoki boshqa yozuv yo'q, bog'liq jadvallarga so'rov ham yo'q;
* yashirin, yo'q va noto'g'ri kod bir xil "topilmadi"; bekor qilinganlik rost
  aytiladi, sababi esa ochiq emas;
* noto'g'ri kodlar IP bo'yicha cheklanadi; kod logga, auditga, hisoblagichga yozilmaydi;
* owner qarorigacha (PUB-D4) yangi havola o'chiq — 404.
"""

from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag, SystemAuditEvent
from core.models import OperationalSettings
from courses import certificate_verifier as verifier
from courses.models import Certificate, Course
from users.models import AuthThrottleBucket

User = get_user_model()


def set_flag(slug, enabled):
    FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": enabled})


class VerifierWorld(TestCase):
    def setUp(self):
        set_flag("certificate_public_verifier", True)
        set_flag("auth_throttle_enforcement", True)
        self.student = User.objects.create_user(
            "alivaliyev", email="ali.maxfiy@example.test", password="Parol-2026!", first_name="Ali", last_name="Valiyev",
        )
        self.course = Course.objects.create(title="Turk tili A1", description="<p>d</p>", level="beginner")
        self.certificate = Certificate.objects.create(
            student=self.student, course=self.course, certificate_id=f"AZ-{self.course.pk}-{self.student.pk}-ABC123",
            final_score=91,
        )
        self.token = verifier.ensure_public_token(self.certificate)

    def url(self, token=None):
        return reverse("certificate_verify", args=[token or self.token])

    def change(self, status, name_mode=None, reason="Sinov"):
        self.certificate.refresh_from_db()
        return verifier.set_public_status(self.certificate, status=status, name_mode=name_mode, actor=None,
                                          reason=reason, expected_revision=self.certificate.verification_revision)


class TokenTests(VerifierWorld):
    def test_tokens_are_long_random_unique_and_stable(self):
        self.assertRegex(self.token, verifier.TOKEN_RE)
        self.assertEqual(verifier.ensure_public_token(self.certificate), self.token)
        tokens = set()
        for index in range(40):
            course = Course.objects.create(title=f"Kurs {index}", description="d", level="beginner")
            cert = Certificate.objects.create(student=self.student, course=course, certificate_id=f"X-{index}", final_score=80)
            tokens.add(verifier.ensure_public_token(cert))
        self.assertEqual(len(tokens), 40)
        self.assertNotIn(str(self.student.pk), self.token.split("-"))

    def test_a_collision_is_retried_with_a_fresh_token(self):
        other = Certificate.objects.create(
            student=self.student, course=Course.objects.create(title="B", description="d", level="beginner"),
            certificate_id="X-collide", final_score=70,
        )
        fresh = "B" * 32
        with mock.patch.object(verifier, "new_token", side_effect=[self.token, fresh]):
            self.assertEqual(verifier.ensure_public_token(other), fresh)
        with mock.patch.object(verifier, "new_token", return_value=self.token):
            third = Certificate.objects.create(
                student=self.student, course=Course.objects.create(title="C", description="d", level="beginner"),
                certificate_id="X-exhaust", final_score=70,
            )
            with self.assertRaises(RuntimeError):
                verifier.ensure_public_token(third)

    def test_completing_a_course_issues_a_token(self):
        from courses.completion_service import evaluate_course_completion

        course = Course.objects.create(title="B1", description="d", level="beginner")
        with mock.patch("courses.completion_service.build_course_completion_snapshot",
                        return_value=SimpleNamespace(is_completed=True, final_grade=88)), \
                mock.patch("courses.completion_service.check_certificate_policy",
                           return_value=SimpleNamespace(is_allowed=True)):
            certificate, created, _ = evaluate_course_completion(student=self.student, course=course)
        self.assertTrue(created)
        self.assertRegex(certificate.public_token, verifier.TOKEN_RE)
        self.assertEqual(Certificate.objects.get(pk=certificate.pk).public_token, certificate.public_token)


class PublicPageTests(VerifierWorld):
    def test_the_verifier_is_off_until_the_owner_turns_it_on(self):
        set_flag("certificate_public_verifier", False)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "Valiyev", status_code=404)
        self.assertFalse(AuthThrottleBucket.objects.exists())
        # O'chiq imkoniyat "topilmadi"dan farq qilmaydi.
        set_flag("certificate_public_verifier", True)
        self.assertEqual(response.content, self.client.get(reverse("certificate_verify", args=["A" * 32])).content)

    def test_a_valid_token_shows_only_the_minimal_projection(self):
        response = self.client.get(self.url())
        html = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Haqiqiy sertifikat", html)
        self.assertIn("Ali V.", html)
        self.assertIn("Turk tili A1", html)
        self.assertIn(timezone.localtime(self.certificate.issued_at).strftime("%d.%m.%Y"), html)
        for secret in ("Valiyev", "91", "ali.maxfiy", "alivaliyev", self.certificate.certificate_id,
                       reverse("certificate_detail", args=[self.certificate.certificate_id])):
            self.assertNotIn(secret, html)

    def test_name_modes(self):
        self.change(Certificate.PUBLIC_VERIFIABLE, name_mode=Certificate.NAME_FULL)
        self.assertContains(self.client.get(self.url()), "Ali Valiyev")
        self.change(Certificate.PUBLIC_VERIFIABLE, name_mode=Certificate.NAME_OMITTED)
        response = self.client.get(self.url())
        self.assertContains(response, "Ism ko‘rsatilmaydi")
        self.assertNotContains(response, "Ali")

    def test_hidden_unknown_and_malformed_look_identical(self):
        self.change(Certificate.PUBLIC_HIDDEN)
        bodies = []
        for token in (self.token, "A" * 32, "qisqa", "x" * 200, "yomon belgi!" * 3):
            response = self.client.get(reverse("certificate_verify", args=[token]))
            with self.subTest(token=token[:8]):
                self.assertEqual(response.status_code, 404)
                self.assertContains(response, "Sertifikat topilmadi", status_code=404)
                self.assertNotContains(response, "Turk tili", status_code=404)
            bodies.append(response.content)
        self.assertEqual(len(set(bodies)), 1)

    def test_revocation_is_truthful_and_the_reason_stays_private(self):
        self.change(Certificate.PUBLIC_REVOKED, reason="MAXFIY-SABAB: imtihon qayta ko'rildi")
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bekor qilingan sertifikat")
        self.assertContains(response, "Bekor qilingan sana")
        self.assertNotContains(response, "MAXFIY-SABAB")
        self.assertNotContains(response, "Haqiqiy sertifikat")
        # Izoh ham rost: bekor qilingan sertifikat "amalda" deb ko'rsatilmaydi.
        self.assertContains(response, "endi haqiqiy hisoblanmaydi")
        self.assertNotContains(response, "amalda")

    def test_lookup_touches_only_the_certificate_row(self):
        with CaptureQueriesContext(connection) as queries:
            self.client.get(self.url())
        certificate_sql = [q["sql"] for q in queries.captured_queries if "courses_certificate" in q["sql"]]
        self.assertEqual(len(certificate_sql), 1)
        for sql in (q["sql"].lower() for q in queries.captured_queries):
            for table in ("examattempt", "enrollment", "lessonprogress", "paymentreceipt"):
                self.assertNotIn(table, sql)
        with CaptureQueriesContext(connection) as malformed:
            self.client.get(reverse("certificate_verify", args=["qisqa"]))
        self.assertFalse([q for q in malformed.captured_queries if "courses_certificate" in q["sql"]])

    def test_privacy_headers_and_no_third_party_resources(self):
        response = self.client.get(self.url())
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("noindex", response["X-Robots-Tag"])
        self.assertIn("noarchive", response["X-Robots-Tag"])
        self.assertEqual(response["Referrer-Policy"], "same-origin")
        html = response.content.decode()
        self.assertIn('lang="uz"', html)
        self.assertIn('content="noindex, nofollow, noarchive"', html)
        self.assertNotRegex(html, r'<(script|link)[^>]+(src|href)="https?://')


@override_settings(TRUSTED_PROXY_HOPS=0)
class BruteBudgetTests(VerifierWorld):
    def setUp(self):
        super().setUp()
        row = OperationalSettings.load()
        row.certificate_verify_ip_limit = 3
        row.save()

    def test_wrong_tokens_are_limited_while_correct_ones_are_not_counted(self):
        for _ in range(5):
            self.assertEqual(self.client.get(self.url()).status_code, 200)
        self.assertFalse(AuthThrottleBucket.objects.exists())
        for index in range(3):
            self.assertEqual(self.client.get(reverse("certificate_verify", args=[f"{index}" * 32])).status_code, 404)
        blocked = self.client.get(self.url())
        self.assertEqual(blocked.status_code, 429)
        self.assertTrue(blocked["Retry-After"].isdigit())
        self.assertContains(blocked, "Juda ko‘p urinish", status_code=429)
        self.assertNotContains(blocked, "Turk tili", status_code=429)

    def test_the_window_end_reopens_verification(self):
        for index in range(4):
            self.client.get(reverse("certificate_verify", args=[f"{index}" * 32]))
        with mock.patch("users.auth_abuse.timezone.now", return_value=timezone.now() + timedelta(minutes=16)):
            self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_tokens_never_reach_the_counter_or_the_audit(self):
        self.client.get(reverse("certificate_verify", args=["Z" * 32]))
        self.change(Certificate.PUBLIC_REVOKED, reason="Sinov")
        stored = list(AuthThrottleBucket.objects.values_list("key_digest", flat=True))
        self.assertTrue(stored)
        self.assertFalse([value for value in stored if "Z" * 32 in value or self.token in value])
        for event in SystemAuditEvent.objects.all():
            self.assertNotIn(self.token, f"{event.target_label} {event.reason} {event.before} {event.after}")


class StatusChangeTests(VerifierWorld):
    def test_changes_need_a_reason_and_the_current_revision(self):
        with self.assertRaises(ValueError):
            self.change(Certificate.PUBLIC_REVOKED, reason=" ")
        stale = self.certificate.verification_revision
        self.change(Certificate.PUBLIC_REVOKED)
        with self.assertRaises(verifier.VerifierConflict):
            verifier.set_public_status(self.certificate, status=Certificate.PUBLIC_VERIFIABLE, actor=None,
                                       reason="Eski oyna", expected_revision=stale)
        event = SystemAuditEvent.objects.get(action="certificate.public_status")
        self.assertEqual(event.after["status"], Certificate.PUBLIC_REVOKED)

    def test_making_it_verifiable_again_clears_the_revocation(self):
        self.change(Certificate.PUBLIC_REVOKED, reason="Xato")
        row = self.change(Certificate.PUBLIC_VERIFIABLE, reason="Qayta tekshirildi")
        self.assertIsNone(row.revoked_at)
        self.assertEqual(row.revocation_reason, "")
        self.assertContains(self.client.get(self.url()), "Haqiqiy sertifikat")

    def test_the_command_shows_and_changes_status_without_printing_the_token(self):
        out = StringIO()
        call_command("certificate_public_status", str(self.certificate.pk), stdout=out)
        call_command("certificate_public_status", str(self.certificate.pk), "--status", "revoked",
                     "--reason", "Buyruq bilan", stdout=out)
        self.certificate.refresh_from_db()
        self.assertEqual(self.certificate.public_status, Certificate.PUBLIC_REVOKED)
        self.assertNotIn(self.token, out.getvalue())

    def test_legacy_routes_are_unchanged_for_now(self):
        # Eski havolani ko'chirish va ilovani yopish — PUB1.5d.
        response = self.client.get(reverse("certificate_detail", args=[self.certificate.certificate_id]))
        self.assertEqual(response.status_code, 200)
