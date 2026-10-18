"""PUB1.3d — kurs sahifasidan boshlangan niyat auth'dan keyin aynan o'sha checkout'ga qaytadi.

Niyat imzoli va turlangan (`frontend/public_intent.py`): mijoz kurs/tarifni
o'zgartira olmaydi, unda URL yoki narx yo'q. Qaytishda kurs, a'zolik, qabul va
tarif qayta tekshiriladi (`courses.public_offer.resolve_purchase_intent`);
yaroqsiz yoki eskirgan havola katalogga tushunarli xabar bilan olib boradi.
"""

import re
import time
from datetime import timedelta
from decimal import Decimal
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core import signing
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag
from cohorts.models import Cohort, Enrollment
from core.models import OperationalSettings
from courses.models import Course
from frontend import public_intent
from subscriptions.models import Plan

PASSWORD = "Kurs-qaytish-2026!"


def set_flag(slug, enabled):
    FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": enabled})


def renderers():
    for enabled, name in ((False, "legacy"), (True, "v1")):
        set_flag("frontend_v1_public", enabled)
        set_flag("frontend_v1_auth", enabled)
        yield name


def writes(queries):
    return [q["sql"] for q in queries.captured_queries
            if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) and "django_session" not in q["sql"]]


def message_texts(response):
    return [str(message) for message in get_messages(response.wsgi_request)]


class IntentWorld(TestCase):
    def setUp(self):
        Plan.objects.update(is_available_for_purchase=False)
        self.plan = Plan.objects.create(name="Oddiy", price=Decimal("200000"), order=1)
        self.course = Course.objects.create(title="Turk tili A1", description="<p>d</p>", level="beginner")
        self.cohort = Cohort.objects.create(course=self.course, name="Ochiq", start_date=timezone.localdate() + timedelta(days=3))
        self.user = get_user_model().objects.create_user("qaytuvchi", email="q@example.test", password=PASSWORD)
        self.checkout = reverse("cohorts:checkout", kwargs={"course_id": self.course.pk})
        self.detail = reverse("course_detail", args=[self.course.pk])
        set_flag("public_registration", True)

    def continue_url(self, **kwargs):
        kwargs.setdefault("course_id", self.course.pk)
        return public_intent.continue_url(public_intent.COURSE_CHECKOUT, **kwargs)

    def resolve(self, url):
        self.client.force_login(self.user)
        return self.client.get(url)


class TokenTests(IntentWorld):
    def token(self, url):
        return parse_qs(urlsplit(url).query)[public_intent.PARAM][0]

    def test_round_trip_carries_only_the_typed_envelope(self):
        token = self.token(self.continue_url(plan_code=self.plan.code))
        intent = public_intent.read(token)
        self.assertEqual((intent.destination, intent.course_id, intent.plan_code), ("course_checkout", self.course.pk, self.plan.code))
        payload = signing.loads(token, salt=public_intent.SALT)
        self.assertEqual(set(payload), {"v", "d", "c", "p", "n"})  # URL, narx, foydalanuvchi yo'q

    def test_tampered_foreign_and_malformed_tokens_are_rejected(self):
        token = self.token(self.continue_url())
        forged = signing.dumps({"v": 1, "d": "course_checkout", "c": self.course.pk, "p": None, "n": "x"}, salt="frontend-v1.checkout.quote")
        cases = {
            "tampered": token[:-2] + ("AA" if not token.endswith("AA") else "BB"),
            "foreign": forged,
            "unknown_destination": signing.dumps({"v": 1, "d": "admin", "c": 1, "p": None, "n": "x"}, salt=public_intent.SALT),
            "old_version": signing.dumps({"v": 0, "d": "catalog", "c": None, "p": None, "n": "x"}, salt=public_intent.SALT),
            "bool_course": signing.dumps({"v": 1, "d": "course_detail", "c": True, "p": None, "n": "x"}, salt=public_intent.SALT),
            "oversized": "a" * 600,
            "empty": "",
        }
        for name, value in cases.items():
            with self.subTest(case=name), self.assertRaises(public_intent.InvalidIntent):
                public_intent.read(value)

    def test_owner_setting_decides_how_long_a_link_lives(self):
        OperationalSettings.objects.update_or_create(singleton=True, defaults={"public_intent_minutes": 5})
        token = self.token(self.continue_url())
        now = time.time()
        with mock.patch("django.core.signing.time.time", return_value=now + 4 * 60):
            public_intent.read(token)
        with mock.patch("django.core.signing.time.time", return_value=now + 6 * 60), \
                self.assertRaises(public_intent.InvalidIntent) as caught:
            public_intent.read(token)
        self.assertEqual(caught.exception.reason, "expired")

    def test_resolution_is_logged_once_per_link_without_personal_data(self):
        url = self.continue_url()
        with self.assertLogs("frontend.public_intent", level="INFO") as logs:
            self.resolve(url)
            self.client.get(url)
        replays = [record.intent_replay for record in logs.records]
        self.assertEqual(replays, [False, True])
        for record in logs.records:
            self.assertNotIn("qaytuvchi", record.getMessage())
            self.assertEqual(record.intent_course, self.course.pk)


class ResolverTests(IntentWorld):
    def test_course_intent_lands_on_its_checkout_and_writes_nothing(self):
        url = self.continue_url()
        self.client.force_login(self.user)
        for attempt in range(2):  # ikki marta bosish ham xavfsiz
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get(url)
            with self.subTest(attempt=attempt):
                self.assertRedirects(response, self.checkout, fetch_redirect_response=False)
                self.assertEqual(writes(queries), [])
        self.assertFalse(Enrollment.objects.exists())

    def test_plan_intent_keeps_the_chosen_plan_or_explains(self):
        response = self.resolve(self.continue_url(plan_code=self.plan.code))
        self.assertRedirects(response, f"{self.checkout}?plan_id={self.plan.pk}", fetch_redirect_response=False)
        archived = Plan.objects.create(name="Arxiv", price=Decimal("1"), is_available_for_purchase=False)
        response = self.client.get(self.continue_url(plan_code=archived.code))
        self.assertRedirects(response, self.checkout, fetch_redirect_response=False)
        self.assertIn("Tanlangan tarif hozir mavjud emas", " ".join(message_texts(response)))

    def test_closed_admission_gone_course_and_enrolled_learner_are_explained(self):
        url = self.continue_url()
        self.cohort.is_active = False
        self.cohort.save()
        response = self.resolve(url)
        self.assertRedirects(response, self.detail, fetch_redirect_response=False)
        self.assertIn("qabul hozircha ochilmagan", " ".join(message_texts(response)))

        self.cohort.is_active = True
        self.cohort.save()
        Enrollment.objects.create(student=self.user, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
                                  next_payment_deadline=timezone.localdate() + timedelta(days=20))
        response = self.client.get(url)
        self.assertRedirects(response, self.detail, fetch_redirect_response=False)
        self.assertIn("allaqachon o‘qiyapsiz", " ".join(message_texts(response)))

        Course.objects.filter(pk=self.course.pk).update(is_active=False)
        response = self.client.get(url)
        self.assertRedirects(response, reverse("courses"), fetch_redirect_response=False)
        self.assertIn("hozir mavjud emas", " ".join(message_texts(response)))

    def test_invalid_or_expired_links_go_to_the_catalog_with_an_explanation(self):
        self.client.force_login(self.user)
        base = reverse("public_intent_continue")
        for value in ("", "bad-token", "a" * 600):
            response = self.client.get(base, {public_intent.PARAM: value})
            with self.subTest(token=value[:10]):
                self.assertRedirects(response, reverse("courses"), fetch_redirect_response=False)
                self.assertIn("yaroqsiz", " ".join(message_texts(response)))
        url = self.continue_url()
        with mock.patch("django.core.signing.time.time", return_value=time.time() + 24 * 3600):
            response = self.client.get(url)
        self.assertIn("muddati o‘tgan", " ".join(message_texts(response)))

    def test_anonymous_visit_is_sent_to_login_with_the_intent_kept(self):
        url = self.continue_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        target = parse_qs(urlsplit(response["Location"]).query)["next"][0]
        self.assertEqual(target, url)


class AuthJourneyTests(IntentWorld):
    def guest_links(self):
        """Asosiy CTA havolalari: `next` imzoli niyat va tarif tanlanmagan (sarlavhadagi umumiy “Kirish” emas)."""
        body = self.client.get(self.detail).content.decode().replace("&amp;", "&")
        resolver = reverse("public_intent_continue")
        links = {}
        for path in (reverse("login"), reverse("register")):
            for raw in re.findall(r'href="' + re.escape(path) + r'\?([^"]+)"', body):
                target = parse_qs(raw).get("next", [""])[0]
                if not target.startswith(resolver):
                    continue
                intent = public_intent.read(parse_qs(urlsplit(target).query)[public_intent.PARAM][0])
                if intent.plan_code is None:
                    links[path] = target
        return links

    def test_course_page_links_carry_the_signed_intent_in_both_renderers(self):
        for name in renderers():
            links = self.guest_links()
            with self.subTest(renderer=name):
                self.assertEqual(set(links), {reverse("login"), reverse("register")})
                for target in links.values():
                    intent = public_intent.read(parse_qs(urlsplit(target).query)[public_intent.PARAM][0])
                    self.assertEqual((intent.destination, intent.course_id), ("course_checkout", self.course.pk))

    def test_login_returns_to_the_exact_checkout(self):
        for name in renderers():
            self.client.logout()
            target = self.guest_links()[reverse("login")]
            response = self.client.post(f"{reverse('login')}?next={target}",
                                        {"username": "qaytuvchi", "password": PASSWORD, "next": target}, follow=True)
            with self.subTest(renderer=name):
                self.assertEqual(response.redirect_chain[-1][0], self.checkout)
                self.assertEqual(response.status_code, 200)

    def test_registration_and_onboarding_keep_the_intent(self):
        set_flag("frontend_v1_auth", False)
        target = self.continue_url()
        response = self.client.post(f"{reverse('register')}?next={target}", {
            "first_name": "Yangi", "last_name": "O‘quvchi", "email": "yangi@example.test",
            "password1": PASSWORD, "password2": PASSWORD, "next": target,
        })
        onboarding = response["Location"]
        self.assertTrue(onboarding.startswith(reverse("onboarding_choice")))
        page = self.client.get(onboarding).content.decode().replace("&amp;", "&")
        self.assertIn(f'href="{target}"', page)  # “o'tkazib yuborish” aynan niyatga olib boradi
        self.assertRedirects(self.client.get(target), self.checkout, fetch_redirect_response=False)

    def test_closed_registration_keeps_the_intent_on_the_login_path(self):
        set_flag("public_registration", False)
        for name in renderers():
            links = self.guest_links()
            with self.subTest(renderer=name):
                self.assertEqual(set(links), {reverse("login")})
                closed = self.client.get(reverse("register"), {"next": links[reverse("login")]}).content.decode()
                self.assertIn(f'{reverse("login")}?next=', closed.replace("&amp;", "&"))

    def test_external_next_is_still_refused(self):
        response = self.client.post(f"{reverse('login')}?next=//evil.example/", {
            "username": "qaytuvchi", "password": PASSWORD, "next": "//evil.example/",
        })
        self.assertNotIn("evil.example", response["Location"])


class SettingsSurfaceTests(TestCase):
    def test_owner_changes_the_link_lifetime_through_the_audited_panel(self):
        from aicontrol.models import SystemAuditEvent

        owner = get_user_model().objects.create_superuser("muddat-egasi", "m@example.test", PASSWORD)
        self.client.force_login(owner)
        url = reverse("backoffice_runtime_settings")
        self.assertContains(self.client.get(url), "id_public_intent_public_intent_minutes")
        response = self.client.post(url, {"form_name": "public_intent", "public_intent_minutes": 45,
                                          "change_reason": "Sinov: qisqaroq havola", "confirm_change": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(OperationalSettings.load().public_intent_minutes, 45)
        self.assertTrue(SystemAuditEvent.objects.filter(action="settings.public_intent.update").exists())
        for value in (4, 1441):
            response = self.client.post(url, {"form_name": "public_intent", "public_intent_minutes": value,
                                              "change_reason": "x", "confirm_change": "on"})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(OperationalSettings.load().public_intent_minutes, 45)
