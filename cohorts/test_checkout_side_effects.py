"""A4 — checkout sahifasi owner holatini o'zgartirmasligi kerak.

Ikki nuqson bir joyda uchrashadi:

1. **Yopilgan qabul o'zidan-o'zi ochiladi.** `ensure_checkout_cohort()` default
   cohortni `is_active=True` qilib qo'yadi va `start_date`ni bugunga tortadi.
   Ya'ni owner qabulni yopgandan keyin bitta o'quvchining sahifani ochishi uni
   qayta ochib yuboradi. Backlog A4 buni aniq man qiladi: "inactive cohortni
   tasodifiy reactivation qilmaslik".

2. **GET yozuv qiladi.** Sahifani ko'rishning o'zi `Enrollment` yaratadi —
   promo preview AJAX endpointi ham. Ya'ni har ochilgan sahifa, har crawler,
   har qayta yuklash bazaga qator qo'shadi.

Ikkalasi ham bir sababdan: o'qish yo'li bilan yozish yo'li ajratilmagan.
"""

import base64

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from courses.models import Course
from subscriptions.models import Plan

from .checkout_service import CheckoutUnavailable, resolve_checkout_enrollment
from .models import Cohort, Enrollment, PaymentReceipt

User = get_user_model()

# 1x1 PNG — upload gate'i baytlarni tekshiradi, nomni emas.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)

TEST_TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
            "loaders": [
                (
                    "django.template.loaders.locmem.Loader",
                    {
                        "cohorts/checkout.html": "Checkout page",
                        "cohorts/checkout_pending.html": "Pending receipt {{ receipt.id }}",
                    },
                )
            ],
        },
    }
]


class CheckoutFixtureMixin:
    def build_course_with_cohort(self):
        self.student = User.objects.create_user(
            username="a4-student",
            email="a4-student@example.com",
            password="testpass123",
        )
        self.teacher = User.objects.create_user(
            username="a4-teacher",
            email="a4-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.course = Course.objects.create(
            title="A4 Course",
            description="Acquisition test",
            instructor=self.teacher,
            level="beginner",
        )
        self.cohort = Cohort.objects.create(
            name="A4 Cohort",
            course=self.course,
            start_date="2026-12-01",
            is_active=True,
            is_checkout_default=True,
        )
        self.plan = Plan.objects.create(name="A4 Plan", price=100000, order=1)


class ClosedAdmissionsStayClosedTests(CheckoutFixtureMixin, TestCase):
    """Owner qabulni yopsa, uni faqat owner qayta ocha oladi."""

    def setUp(self):
        self.build_course_with_cohort()
        Cohort.objects.filter(course=self.course).update(is_active=False)

    def test_a_learner_opening_checkout_does_not_reopen_the_cohort(self):
        with self.assertRaises(CheckoutUnavailable):
            resolve_checkout_enrollment(student=self.student, course=self.course)

        self.cohort.refresh_from_db()
        self.assertFalse(
            self.cohort.is_active,
            "Yopilgan cohort checkout ochilgani uchun qayta faollashdi",
        )

    def test_a_learner_opening_checkout_does_not_move_the_start_date(self):
        try:
            resolve_checkout_enrollment(student=self.student, course=self.course)
        except CheckoutUnavailable:
            pass

        self.cohort.refresh_from_db()
        self.assertEqual(
            str(self.cohort.start_date),
            "2026-12-01",
            "Yopilgan cohortning boshlanish sanasi bugunga tortildi",
        )

    def test_an_existing_learner_can_still_pay_after_admissions_close(self):
        """"Qabul yopildi" — yangi a'zo olinmaydi, o'qiyotgan odam to'xtatilmaydi."""
        existing = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status=Enrollment.STATUS_EXPIRED,
        )

        enrollment, created, checkout_cohort = resolve_checkout_enrollment(
            student=self.student,
            course=self.course,
        )

        self.assertFalse(created)
        self.assertEqual(enrollment, existing)
        self.assertEqual(checkout_cohort, self.cohort)
        self.cohort.refresh_from_db()
        self.assertFalse(self.cohort.is_active, "Renewal yo'li cohortni qayta ochdi")

    def test_no_enrollment_is_created_for_a_closed_course(self):
        try:
            resolve_checkout_enrollment(student=self.student, course=self.course)
        except CheckoutUnavailable:
            pass

        self.assertEqual(Enrollment.objects.filter(student=self.student).count(), 0)


@override_settings(TEMPLATES=TEST_TEMPLATES)
class CheckoutPageIsReadOnlyTests(CheckoutFixtureMixin, TestCase):
    """Sahifani ko'rish — o'qish amali. Yozuv faqat forma yuborilganda."""

    def setUp(self):
        self.build_course_with_cohort()
        self.client.force_login(self.student)

    def test_viewing_the_checkout_page_creates_no_enrollment(self):
        response = self.client.get(reverse("cohorts:checkout", args=[self.course.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            Enrollment.objects.filter(student=self.student).count(),
            0,
            "Sahifani ochishning o'zi enrollment yaratdi",
        )

    def test_the_promo_preview_endpoint_creates_no_enrollment(self):
        response = self.client.get(
            reverse("cohorts:checkout_promo_preview", args=[self.course.id]),
            {"plan_id": self.plan.id, "code": "YOQ"},
        )

        self.assertIn(response.status_code, (200, 400))
        self.assertEqual(
            Enrollment.objects.filter(student=self.student).count(),
            0,
            "Promo preview AJAX chaqirig'i enrollment yaratdi",
        )

    def test_reloading_the_page_many_times_stays_at_zero(self):
        for _ in range(3):
            self.client.get(reverse("cohorts:checkout", args=[self.course.id]))

        self.assertEqual(Enrollment.objects.filter(student=self.student).count(), 0)


@override_settings(TEMPLATES=TEST_TEMPLATES)
class SubmittingCheckoutStillWorksTests(CheckoutFixtureMixin, TestCase):
    """Qarama-qarshi tomon: GET'ni tozalash POST'ni buzmasligi kerak."""

    def setUp(self):
        self.build_course_with_cohort()
        self.client.force_login(self.student)

    def test_submitting_a_receipt_creates_the_enrollment_and_the_receipt(self):
        response = self.client.post(
            reverse("cohorts:checkout", args=[self.course.id]),
            {
                "plan_id": self.plan.id,
                "receipt_image": SimpleUploadedFile(
                    "receipt.png", PNG_1X1, content_type="image/png"
                ),
            },
        )

        self.assertEqual(response.status_code, 302)
        enrollment = Enrollment.objects.get(student=self.student)
        self.assertEqual(enrollment.cohort, self.cohort)
        self.assertIsNone(enrollment.plan)
        self.assertEqual(enrollment.pending_plan, self.plan)
        self.assertEqual(PaymentReceipt.objects.filter(enrollment=enrollment).count(), 1)
