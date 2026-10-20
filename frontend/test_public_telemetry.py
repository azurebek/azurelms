"""PUB1.8a — maxfiylikka mos ochiq voronka o'lchovi.

Asosiy da'volar:
* flag o'chiq — hech narsa yozilmaydi; yoqilgan — faqat ruxsat etilgan hodisalar, kunlik son;
* mehmon ko'rishlari (bosh, katalog, kurs) sanaladi; kirgan, bot, preview va HEAD — yo'q;
* niyat → kirish → qaytish → checkout → chek zanjiri: har o'tish bir marta (yangilash,
  qayta urinish, ikki marta bosish takror sanamaydi), chek esa tranzaksiyadan keyin;
* jadvalda shaxsiy ma'lumot yo'q: foydalanuvchi, email, qidiruv matni, nonce, token — 0;
* o'lchov xatosi sahifa yoki kirishni buzmaydi; takror kalitlari muddati o'tgach o'chadi;
* hisobot surat/maxraj bilan, ayni ma'lumotdan ayni natija.
"""

import re
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag
from cohorts.models import Cohort, Enrollment, PaymentReceipt
from courses.models import Course
from frontend import public_intent, public_telemetry
from frontend.models import PublicFunnelDay, PublicFunnelReceipt
from subscriptions.models import Plan

PASSWORD = "Voronka-sinov-2026!"
WRITE_TABLE = re.compile(r'^\s*(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+"?(\w+)"?', re.IGNORECASE)


def set_flag(slug, enabled):
    FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": enabled})


def counts():
    return {(row.event, row.course_id, row.dimension): row.count for row in PublicFunnelDay.objects.all()}


class FunnelWorld(TestCase):
    def setUp(self):
        Plan.objects.update(is_available_for_purchase=False)
        self.plan = Plan.objects.create(name="Oddiy", price=Decimal("200000"), order=1)
        self.course = Course.objects.create(title="Turk tili A1", description="<p>d</p>", level="beginner")
        self.cohort = Cohort.objects.create(course=self.course, name="Ochiq", start_date=timezone.localdate() + timedelta(days=3))
        self.user = get_user_model().objects.create_user("voronka", email="voronka@example.test", password=PASSWORD,
                                                         first_name="Ali")
        set_flag("public_registration", True)
        set_flag(public_telemetry.FLAG, True)

    def intent_url(self):
        return public_intent.continue_url(public_intent.COURSE_CHECKOUT, course_id=self.course.pk)


class SwitchTests(FunnelWorld):
    def test_off_means_nothing_is_written(self):
        set_flag(public_telemetry.FLAG, False)
        self.client.get(reverse("home"))
        self.client.get(reverse("course_detail", args=[self.course.pk]))
        self.client.get(reverse("login"), {"next": self.intent_url()})
        self.assertEqual((PublicFunnelDay.objects.count(), PublicFunnelReceipt.objects.count()), (0, 0))

    def test_only_allowlisted_events(self):
        with self.assertRaises(ValueError):
            public_telemetry.record("email_seen")
        self.assertTrue(public_telemetry.record(public_telemetry.AUTH_COMPLETED, dimension="istalgan matn"))
        self.assertEqual(counts(), {(public_telemetry.AUTH_COMPLETED, 0, ""): 1})


class ViewEventTests(FunnelWorld):
    def test_guest_views_are_counted_and_others_are_not(self):
        detail = reverse("course_detail", args=[self.course.pk])
        for flag in (False, True):  # ikkala renderer
            set_flag("frontend_v1_public", flag)
            self.client.get(reverse("home"))
            self.client.get(reverse("courses"), {"q": "maxfiy qidiruv matni"})
            self.client.get(detail)
        self.client.get(detail, HTTP_USER_AGENT="Googlebot/2.1 (+http://www.google.com/bot.html)")
        self.client.head(detail)
        self.client.force_login(self.user)
        self.client.get(detail)
        self.assertEqual(counts(), {
            (public_telemetry.LANDING, 0, ""): 2,
            (public_telemetry.CATALOG, 0, ""): 2,
            (public_telemetry.COURSE, self.course.pk, ""): 2,
        })

    def test_unavailable_offer_is_counted_with_its_reason(self):
        closed = Course.objects.create(title="Yopiq kurs", description="<p>d</p>", level="beginner")
        self.client.get(reverse("course_detail", args=[closed.pk]))
        self.assertEqual(counts()[(public_telemetry.UNAVAILABLE, closed.pk, "not_open")], 1)


class JourneyTests(FunnelWorld):
    def test_each_step_counts_once_even_with_refresh_and_retries(self):
        next_url = self.intent_url()
        login = reverse("login")
        self.client.get(login, {"next": next_url})
        self.client.get(login, {"next": next_url})  # yangilash
        self.client.post(login, {"username": "voronka", "password": "noto'g'ri", "next": next_url})
        response = self.client.post(login, {"username": "voronka", "password": PASSWORD, "next": next_url})
        self.assertEqual(response.status_code, 302)
        landing = self.client.get(next_url)
        self.client.get(next_url)  # ikki marta bosish
        self.assertEqual(landing.status_code, 302)
        checkout = reverse("cohorts:checkout", kwargs={"course_id": self.course.pk})
        self.assertEqual(self.client.get(checkout).status_code, 200)
        self.client.get(checkout)
        found = counts()
        self.assertEqual(found[(public_telemetry.INTENT, self.course.pk, "login")], 1)
        self.assertEqual(found[(public_telemetry.AUTH_STARTED, self.course.pk, "login")], 1)
        self.assertEqual(found[(public_telemetry.AUTH_COMPLETED, self.course.pk, "checkout")], 1)
        self.assertEqual(found[(public_telemetry.QUOTE, self.course.pk, "")], 1)

    def test_a_new_intent_is_a_new_journey(self):
        for _ in range(2):
            self.client.get(reverse("register"), {"next": self.intent_url()})
        self.assertEqual(counts()[(public_telemetry.INTENT, self.course.pk, "register")], 2)

    def test_receipt_is_counted_after_commit_once(self):
        enrollment = Enrollment.objects.create(student=self.user, cohort=self.cohort, status="pending")
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            receipt = PaymentReceipt.objects.create(enrollment=enrollment, plan=self.plan, amount=200000, base_amount=200000)
        self.assertNotIn(public_telemetry.RECEIPT, {event for event, *_ in counts()})  # hali commit emas
        for callback in callbacks:
            callback()
        for callback in callbacks:  # qayta chaqirish ham bir marta
            callback()
        self.assertEqual(counts()[(public_telemetry.RECEIPT, self.course.pk, "")], 1)
        receipt.save()  # yangilash — yangi chek emas
        self.assertEqual(counts()[(public_telemetry.RECEIPT, self.course.pk, "")], 1)


class PrivacyTests(FunnelWorld):
    def test_tables_hold_no_personal_or_free_text(self):
        next_url = self.intent_url()
        self.client.get(reverse("courses"), {"q": "maxfiy qidiruv matni"})
        self.client.get(reverse("login"), {"next": next_url})
        self.client.post(reverse("login"), {"username": "voronka", "password": PASSWORD, "next": next_url})
        self.client.get(next_url)
        self.assertEqual({f.name for f in PublicFunnelDay._meta.fields}, {"id", "day", "event", "course_id", "dimension", "count"})
        self.assertEqual({f.name for f in PublicFunnelReceipt._meta.fields}, {"id", "key", "event", "created_at"})
        stored = " ".join(f"{r.event} {r.dimension}" for r in PublicFunnelDay.objects.all())
        stored += " ".join(r.key for r in PublicFunnelReceipt.objects.all())
        for secret in ("voronka", "voronka@example.test", "maxfiy", "Ali", next_url.split("intent=")[1][:12], str(self.user.pk) + ":"):
            self.assertNotIn(secret, stored)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}", r.key) for r in PublicFunnelReceipt.objects.all()))

    def test_get_writes_only_to_telemetry_tables(self):
        with CaptureQueriesContext(connection) as queries:
            self.client.get(reverse("home"))
            self.client.get(reverse("courses"))
            self.client.get(reverse("course_detail", args=[self.course.pk]))
        tables = {WRITE_TABLE.match(q["sql"]).group(1) for q in queries.captured_queries if WRITE_TABLE.match(q["sql"])}
        self.assertTrue(tables)
        self.assertLessEqual(tables, {"frontend_publicfunnelday", "frontend_publicfunnelreceipt"})


class ResilienceTests(FunnelWorld):
    def test_a_broken_telemetry_store_never_breaks_pages_or_login(self):
        broken = mock.patch.object(PublicFunnelDay.objects, "filter", side_effect=RuntimeError("baza yiqildi"))
        with broken, self.assertLogs("frontend.public_telemetry", level="WARNING") as logs:
            self.assertEqual(self.client.get(reverse("course_detail", args=[self.course.pk])).status_code, 200)
            response = self.client.post(reverse("login"), {"username": "voronka", "password": PASSWORD, "next": self.intent_url()})
            self.assertEqual(response.status_code, 302)
            self.assertFalse(public_telemetry.record(public_telemetry.LANDING))
        self.assertTrue(any("public_telemetry_failed" in line for line in logs.output))

    def test_old_receipts_are_pruned_and_counts_stay(self):
        public_telemetry.record(public_telemetry.AUTH_COMPLETED, dedupe="eski")
        PublicFunnelReceipt.objects.update(created_at=timezone.now() - timedelta(days=5))
        public_telemetry.record(public_telemetry.AUTH_COMPLETED, dedupe="yangi")
        self.assertEqual(public_telemetry.prune_receipts(), 1)
        self.assertEqual(PublicFunnelReceipt.objects.count(), 1)
        self.assertEqual(counts()[(public_telemetry.AUTH_COMPLETED, 0, "")], 2)


class ReportTests(FunnelWorld):
    def test_report_shows_numerator_denominator_and_is_reproducible(self):
        today = timezone.localdate()
        PublicFunnelDay.objects.bulk_create([
            PublicFunnelDay(day=today, event=public_telemetry.COURSE, course_id=self.course.pk, count=40),
            PublicFunnelDay(day=today, event=public_telemetry.INTENT, course_id=self.course.pk, dimension="login", count=8),
            PublicFunnelDay(day=today, event=public_telemetry.AUTH_COMPLETED, course_id=self.course.pk, dimension="checkout", count=6),
            PublicFunnelDay(day=today, event=public_telemetry.AUTH_COMPLETED, course_id=self.course.pk, dimension="closed", count=2),
            PublicFunnelDay(day=today, event=public_telemetry.RECEIPT, course_id=self.course.pk, count=2),
            PublicFunnelDay(day=today - timedelta(days=40), event=public_telemetry.COURSE, count=999),
        ])
        report = public_telemetry.funnel_report(days=28)
        rates = {title: (top, bottom, percent) for title, top, bottom, percent, _ in report["rates"]}
        self.assertEqual(rates["Kurs sahifasidan xarid niyati"], (8, 40, 20.0))
        self.assertEqual(rates["Niyatdan kirishga"], (8, 8, 100.0))
        self.assertEqual(rates["Kirishdan checkout'ga"], (6, 8, 75.0))
        self.assertEqual(rates["Kurs sahifasidan chekka (taxminiy)"], (2, 40, 5.0))
        first, second = StringIO(), StringIO()
        call_command("public_funnel_report", stdout=first)
        call_command("public_funnel_report", stdout=second)
        self.assertEqual(first.getvalue(), second.getvalue())
        self.assertIn("8 / 40 = 20.0%", first.getvalue())
        self.assertIn("ta'rif:", first.getvalue())

    def test_empty_denominators_are_not_faked(self):
        report = public_telemetry.funnel_report(days=7)
        self.assertTrue(all(percent is None for _, _, _, percent, _ in report["rates"]))
