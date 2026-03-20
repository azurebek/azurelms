from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from subscriptions.models import Plan

from .models import Cohort, Enrollment, PaymentReceipt


User = get_user_model()


class CheckoutPlanSelectionTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="checkout-student",
            email="checkout-student@example.com",
            password="testpass123",
        )
        self.teacher = User.objects.create_user(
            username="checkout-teacher",
            email="checkout-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.course = Course.objects.create(
            title="Checkout Plan Course",
            description="Checkout plan test",
            instructor=self.teacher,
            level="beginner",
            price=123000,
        )
        self.cohort = Cohort.objects.create(
            name="Checkout Cohort",
            course=self.course,
            start_date="2026-03-01",
            is_active=True,
        )
        self.plan_standard = Plan.objects.create(
            name="Standard",
            price=99000,
            description="Standard tarif",
            order=1,
        )
        self.plan_pro = Plan.objects.create(
            name="Pro",
            price=149000,
            description="Pro tarif",
            order=2,
        )
        self.checkout_url = reverse("cohorts:checkout", args=[self.course.id])
        self.client.force_login(self.student)

    def _fake_receipt(self):
        return SimpleUploadedFile("receipt.png", b"fake-image-content", content_type="image/png")

    def test_checkout_uses_selected_plan_price_and_assigns_plan_to_enrollment(self):
        response = self.client.post(
            self.checkout_url,
            {
                "plan_id": str(self.plan_pro.id),
                "receipt_image": self._fake_receipt(),
            },
        )

        self.assertRedirects(response, reverse("cohorts:checkout_success"), fetch_redirect_response=False)

        enrollment = Enrollment.objects.get(student=self.student, cohort=self.cohort)
        receipt = PaymentReceipt.objects.get(enrollment=enrollment)

        self.assertEqual(enrollment.plan_id, self.plan_pro.id)
        self.assertEqual(receipt.amount, self.plan_pro.price)

    def test_checkout_rejects_invalid_plan_id(self):
        response = self.client.post(
            self.checkout_url,
            {
                "plan_id": "999999",
                "receipt_image": self._fake_receipt(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Iltimos, mavjud tariflardan birini tanlang.")
        self.assertEqual(PaymentReceipt.objects.count(), 0)
