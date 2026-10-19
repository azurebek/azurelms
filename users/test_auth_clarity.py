"""PUB1.4b — auth formalarida aniq, bir martalik xatolar (UX-04 porti).

Har xato bir marta (maydon yonida), xulosa faqat nechta maydonni tekshirishni
aytadi; maydon va xato `aria-describedby` orqali haqiqatan bog'langan; parol
qaytarib chizilmaydi; xato bilan qaytgan sahifada fokus nomga emas, xatoga;
kursdan kelgan mehmonga qaytish manzili aytiladi; CSRF rad etilsa o'zbekcha sahifa.
"""

import re
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from aicontrol.models import FeatureFlag
from cohorts.models import Cohort
from courses.models import Course
from frontend import public_intent
from subscriptions.models import Plan

SECRET = "Maxfiy-Sinov-Parol-98"
DESCRIBED = re.compile(r'aria-describedby="([^"]+)"')


def renderers():
    for enabled, name in ((False, "legacy"), (True, "v1")):
        FeatureFlag.objects.update_or_create(slug="frontend_v1_auth", defaults={"enabled": enabled})
        yield name


class ClarityWorld(TestCase):
    def setUp(self):
        FeatureFlag.objects.update_or_create(slug="public_registration", defaults={"enabled": True})
        self.user = get_user_model().objects.create_user("mavjud", email="bor@example.test", password=SECRET)

    def register_invalid(self):
        return self.client.post(reverse("register"), {
            "first_name": "", "last_name": "Uzunfamiliya", "email": "bor@example.test",
            "password1": SECRET, "password2": SECRET + "x",
        })

    def assert_described_ids_exist(self, html):
        for value in DESCRIBED.findall(html):
            for element_id in value.split():
                self.assertIn(f'id="{element_id}"', html, f"aria-describedby → yo‘q element: {element_id}")


class SingleErrorTests(ClarityWorld):
    def test_registration_errors_appear_once_with_a_counting_summary(self):
        for name in renderers():
            response = self.register_invalid()
            html = response.content.decode()
            with self.subTest(renderer=name):
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("Ma&#x27;lumotlarda xatolik bor", html)  # flash takrori yo'q
                self.assertNotIn("Belgilangan maydonlarni tekshiring", html)
                self.assertEqual(html.count("3 ta maydonni tekshiring."), 1)
                self.assertEqual(html.count('id="id_first_name_error"'), 1)
                self.assertEqual(html.count("Bu maydonni to‘ldiring."), 1)
                self.assertNotIn("This field is required.", html)
                self.assertEqual(html.count("Ikkala parol bir xil emas"), 1)
                self.assert_described_ids_exist(html)
                self.assertRegex(html, r'<input[^>]*name="first_name"[^>]*aria-invalid="true"')

    def test_login_failure_is_one_notice_and_focus_leaves_the_name_field(self):
        for name in renderers():
            fresh = self.client.get(reverse("login")).content.decode()
            response = self.client.post(reverse("login"), {"username": "mavjud", "password": "noto‘g‘ri"})
            html = response.content.decode()
            with self.subTest(renderer=name):
                self.assertRegex(fresh, r'<input[^>]*name="username"[^>]*autofocus')
                self.assertNotRegex(html, r'<input[^>]*name="username"[^>]*autofocus')
                self.assertEqual(len(re.findall(r'class="errorlist nonfield"', html)), 1)
                self.assertIn("Email yoki username va parol mos kelmadi", html)  # legacy ham o'zbekcha
                # Son qatori faqat maydon xatosi bo'lsa ko'rinadi; bu yerda umumiy xato.
                self.assertNotRegex(html, r"<p data-error-count(?![^>]*hidden)[^>]*>")

    def test_secrets_are_never_rendered_back_and_safe_values_are(self):
        for name in renderers():
            register = self.register_invalid().content.decode()
            login = self.client.post(reverse("login"), {"username": "mavjud", "password": SECRET + "-noto"}).content.decode()
            with self.subTest(renderer=name):
                for html in (register, login):
                    self.assertNotIn(SECRET, html)
                self.assertIn('value="Uzunfamiliya"', register)
                self.assertIn('value="bor@example.test"', register)
                self.assertIn('value="mavjud"', login)

    def test_reset_confirm_mismatch_is_reported_once_without_echo(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        for name in renderers():
            opened = self.client.get(reverse("password_reset_confirm", args=[uid, default_token_generator.make_token(self.user)]))
            response = self.client.post(opened["Location"], {"new_password1": "Yangi-Qatiy-Kalit-77", "new_password2": "Boshqa-Qatiy-Kalit-78"})
            html = response.content.decode()
            with self.subTest(renderer=name):
                self.assertEqual(response.status_code, 200)
                self.assertEqual(html.count("1 ta maydonni tekshiring."), 1)
                self.assertNotIn("Yangi-Qatiy-Kalit-77", html)
                self.assert_described_ids_exist(html)


class EnhancementWiringTests(ClarityWorld):
    PAGES = ("login", "register", "password_reset")

    def test_every_auth_form_opts_into_the_shared_validation(self):
        for name in renderers():
            for page in self.PAGES:
                html = self.client.get(reverse(page)).content.decode()
                with self.subTest(renderer=name, page=page):
                    self.assertIn("frontend_v1/js/auth-validation.js", html)
                    self.assertRegex(html, r"<form[^>]*data-auth-validate")
                    self.assertIn("data-form-errors", html)  # JS xulosa konteyneri doim bor

    def test_autocomplete_and_input_types_help_password_managers(self):
        expected = {
            "login": ('name="username"[^>]*autocomplete="username"', 'name="password"[^>]*autocomplete="current-password"'),
            "register": ('type="email"[^>]*name="email"|name="email"[^>]*type="email"', 'autocomplete="new-password"',
                         'autocomplete="given-name"', 'autocomplete="email"'),
        }
        for name in renderers():
            for page, patterns in expected.items():
                html = self.client.get(reverse(page)).content.decode()
                for pattern in patterns:
                    with self.subTest(renderer=name, page=page, pattern=pattern):
                        self.assertRegex(html, pattern)

    def test_legal_links_are_present_and_the_fake_language_switch_is_gone(self):
        for name in renderers():
            html = self.client.get(reverse("login")).content.decode()
            with self.subTest(renderer=name):
                self.assertIn(f'href="{reverse("privacy_policy")}"', html)
                self.assertIn(f'href="{reverse("terms_of_service")}"', html)
                self.assertNotRegex(html, r">EN</span>")
        legacy_css = (Path(settings.BASE_DIR) / "templates/registration/base_auth.html").read_text(encoding="utf-8")
        v1_css = (Path(settings.BASE_DIR) / "static/frontend_v1/css/auth.css").read_text(encoding="utf-8")
        self.assertRegex(legacy_css, r"\.auth-legal a\{[^}]*min-height:44px")
        self.assertRegex(v1_css, r"\.s-auth-footer a \{[^}]*min-height: var\(--az-control\)")


class IntentNoteTests(ClarityWorld):
    def setUp(self):
        super().setUp()
        Plan.objects.update(is_available_for_purchase=False)
        self.plan = Plan.objects.create(name="Pro", price=Decimal("199000"))
        self.course = Course.objects.create(title="Turk tili A1", description="<p>d</p>", level="beginner")
        Cohort.objects.create(course=self.course, name="G", start_date=timezone.localdate() + timedelta(days=2))

    def test_auth_pages_say_where_a_course_visitor_returns(self):
        target = public_intent.continue_url(public_intent.COURSE_CHECKOUT, course_id=self.course.pk, plan_code=self.plan.code)
        for name in renderers():
            for page in ("login", "register"):
                html = self.client.get(reverse(page), {"next": target}).content.decode()
                with self.subTest(renderer=name, page=page):
                    self.assertIn("«Turk tili A1» kursining to‘lov sahifasiga qaytasiz (Pro tarifi).", html)

    def test_onboarding_after_registration_keeps_saying_it(self):
        target = public_intent.continue_url(public_intent.COURSE_CHECKOUT, course_id=self.course.pk, plan_code=self.plan.code)
        self.client.force_login(self.user)
        for name in renderers():
            html = self.client.get(reverse("onboarding_choice"), {"next": target}).content.decode()
            with self.subTest(renderer=name):
                self.assertEqual(html.count("data-auth-intent"), 1)
                self.assertIn("«Turk tili A1» kursining to‘lov sahifasiga qaytasiz (Pro tarifi).", html)

    def test_raw_or_tampered_next_gets_no_note(self):
        good = public_intent.continue_url(public_intent.COURSE_CHECKOUT, course_id=self.course.pk)
        for name in renderers():
            foreign_path = "/users/profile/?" + good.split("?", 1)[1]  # haqiqiy token, lekin boshqa manzil
            for value in (reverse("course_detail", args=[self.course.pk]), good[:-3] + "zzz", "https://evil.example/", foreign_path):
                html = self.client.get(reverse("login"), {"next": value}).content.decode()
                with self.subTest(renderer=name, next=value[:30]):
                    self.assertNotIn("data-auth-intent", html)


class CsrfFailureTests(ClarityWorld):
    def test_rejected_form_explains_in_uzbek_without_technical_detail(self):
        client = Client(enforce_csrf_checks=True)
        path = reverse("login") + "?next=/courses/"
        response = client.post(path, {"username": "mavjud", "password": SECRET})
        html = response.content.decode()
        self.assertEqual(response.status_code, 403)
        self.assertIn("Sahifa eskirgan", html)
        self.assertIn(f'href="{path}"', html)
        self.assertNotIn("CSRF verification failed", html)
        self.assertNotIn(SECRET, html)
