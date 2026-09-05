"""To'lov jarayoni tizimga kirgan odamni ilova qobig'idan chiqarib yubormaydi.

UX auditning 10-topilmasi. Checkout `base_public.html` da chizilardi. Ya'ni
o'quvchi panelidan «To'lov» tugmasini bosgan odam birdan boshqa saytga
tushgandek bo'lardi:

* yon panel yo'qoladi — kursga, xabarlarga, sozlamalarga yo'l qolmaydi;
* sarlavha marketing navigatsiyasiga («Kurslar / Narxlar / Blog») va
  «Kirish / Ro'yxatdan o'tish» tugmalariga almashadi — garchi odam
  allaqachon kirgan bo'lsa ham;
* to'lovni tugatib panelga qaytishning yagona yo'li brauzerning «orqaga»
  tugmasi edi.

Yechim: sahifa `{% extends base_template %}` bilan qobiqni tanlaydi.
`base_app.html` ichidagi `{% block content %}` `base_public.html` dagi bilan
bir xil nom — shu tufayli sahifaning o'zi umuman o'zgarmadi.

Uchala to'lov sahifasi ham shu yo'ldan o'tadi: checkout, «tasdiq kutilmoqda»
va «muvaffaqiyatli». Oraliqda qobiq almashib turishi eng yomon variant
bo'lardi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort, Enrollment, PaymentReceipt
from courses.models import Course
from subscriptions.models import Plan

User = get_user_model()


class CheckoutShellFixture:
    def setUp(self):
        super().setUp()
        today = timezone.localdate()
        teacher = User.objects.create_user(
            username="qobiq-teacher", email="t@example.test", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="qobiq-student", email="s@example.test", password="x"
        )
        self.course = Course.objects.create(
            title="Kurs", description="d", level="beginner", instructor=teacher
        )
        self.cohort = Cohort.objects.create(
            name="Guruh", course=self.course, start_date=today, is_checkout_default=True,
        )
        self.plan = Plan.objects.create(
            code="qobiq-starter", name="Starter", price=99000, description="d"
        )
        self.today = today

    def checkout(self):
        self.client.force_login(self.student)
        return self.client.get(
            reverse("cohorts:checkout", kwargs={"course_id": self.course.id})
        )

    def receipt(self):
        enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_PENDING,
            next_payment_deadline=self.today + datetime.timedelta(days=30),
        )
        return PaymentReceipt.objects.create(
            enrollment=enrollment, plan=self.plan, amount=99000,
            period_start=self.today,
            period_end=self.today + datetime.timedelta(days=30),
        )


class TheSignedInLearnerKeepsTheirShellTests(CheckoutShellFixture, TestCase):
    def test_the_sidebar_is_still_there(self):
        response = self.checkout()

        self.assertContains(response, 'class="app-side"')

    def test_the_way_back_to_the_courses_is_still_there(self):
        """Eng muhimi: to'lovni tashlab ketish uchun «orqaga» kerak emas."""
        response = self.checkout()

        self.assertContains(response, reverse("my_courses"))
        self.assertContains(response, reverse("dashboard"))

    def test_the_marketing_header_is_gone(self):
        response = self.checkout()

        self.assertNotContains(response, 'class="pub-nav"')

    def test_it_no_longer_offers_to_sign_in(self):
        """Kirgan odamga «Kirish / Ro'yxatdan o'tish» ko'rsatilardi."""
        response = self.checkout()

        self.assertNotContains(response, reverse("register"))

    def test_the_billing_entry_is_highlighted(self):
        response = self.checkout()

        self.assertContains(response, 'class="app-nav-item active" href="/users/subscriptions/"')


class ThePageItselfIsUnchangedTests(CheckoutShellFixture, TestCase):
    """Qobiq almashdi, sahifa mazmuni emas."""

    def test_the_plans_are_still_listed(self):
        response = self.checkout()

        self.assertContains(response, "Starter")
        self.assertContains(response, "99000")

    def test_the_receipt_upload_is_still_there(self):
        response = self.checkout()

        self.assertContains(response, 'name="receipt_image"')

    def test_the_page_specific_styles_still_load(self):
        """`page_css`/`page_js` ikkala qobiqda ham bir xil nomda."""
        response = self.checkout()

        self.assertContains(response, "checkout-plan.js")


class TheWholePaymentFlowStaysInOnePlaceTests(CheckoutShellFixture, TestCase):
    """Oraliqda qobiq almashib tursa, bu tuzatishdan ham yomon bo'lardi."""

    def test_the_pending_page_is_in_the_app_shell(self):
        receipt = self.receipt()
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("cohorts:checkout_pending", kwargs={"receipt_id": receipt.id})
        )

        self.assertContains(response, 'class="app-side"')

    def test_the_success_page_is_in_the_app_shell(self):
        receipt = self.receipt()
        receipt.is_verified = True
        receipt.save(update_fields=["is_verified"])
        self.client.force_login(self.student)

        response = self.client.get(
            reverse("cohorts:checkout_success", kwargs={"receipt_id": receipt.id})
        )

        self.assertContains(response, 'class="app-side"')


class TheFallbackIsStillThereTests(CheckoutShellFixture, TestCase):
    """Sahifalar `@login_required`, ammo zaxira qobiq saqlanadi.

    Qoida kelajakda o'zgarsa (masalan mehmon ham tarifni ko'ra olsa),
    sahifa `TemplateDoesNotExist` bilan yiqilmasin.
    """

    def test_the_template_names_a_default(self):
        from pathlib import Path

        from django.conf import settings

        base = Path(settings.BASE_DIR)
        for name in ("checkout", "checkout_pending", "checkout_success"):
            with self.subTest(template=name):
                first_line = (
                    base / f"templates/cohorts/{name}.html"
                ).read_text(encoding="utf-8").splitlines()[0]
                self.assertIn('default:"base_public.html"', first_line)

    def test_a_guest_is_sent_to_the_login_page(self):
        response = self.client.get(
            reverse("cohorts:checkout", kwargs={"course_id": self.course.id})
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])
