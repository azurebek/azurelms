"""Tarif farqi uchun to'lov — owner so'raydi, o'quvchi chek yuklaydi.

Owner qarori (2026-09-04): tarif almashtirilganda farq uchun maxsus so'rov
o'quvchiga yuboriladi, u chekni yuklaydi, owner tasdiqlaydi va bu to'lovlar
sahifasida «tarif farqi» sifatida qayd etiladi.

Ikkita narsa ataylab:

* **farq to'lovi davrni uzaytirmaydi va tarifni o'zgartirmaydi** — tarif
  allaqachon ko'chirishda o'zgargan, bu esa faqat o'sha o'zgarishning pul
  tomonini yopadi. Aks holda o'quvchi bir oyning o'rniga ikki oy olardi;
* **farq so'rovi oddiy yangilanishni to'smaydi** — «bitta a'zolikda bitta
  ochiq chek» cheklovi endi turni ham hisobga oladi, aks holda to'lanmagan
  farq o'quvchini keyingi oyga to'lay olmaydigan holatga tushirardi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from cohorts.membership_service import (
    difference_between,
    request_tier_difference,
    suggest_difference_amount,
)
from cohorts.models import Cohort, Enrollment, PaymentReceipt
from cohorts.receipt_service import reject_receipt, verify_receipt
from cohorts.transition_service import transfer_enrollment_to_cohort
from courses.models import Course
from subscriptions.models import Plan
from subscriptions.promo_service import create_checkout_receipt_with_promo
from users.models import Notification

User = get_user_model()


class DifferenceFixture:
    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        self.owner = User.objects.create_superuser(
            username="farq-owner", email="owner@example.test", password="x"
        )
        self.student = User.objects.create_user(
            username="farq-talaba", email="talaba@example.test", password="x"
        )
        self.course = Course.objects.create(
            title="Kurs", description="d", level="beginner", instructor=self.owner
        )
        self.cheap = Plan.objects.create(
            code="farq-economic", name="Economic", price=89000,
            description="d", cohort_capacity_limit=60,
        )
        self.rich = Plan.objects.create(
            code="farq-intensive", name="Intensive", price=389000,
            description="d", cohort_capacity_limit=3,
        )
        self.cheap_cohort = Cohort.objects.create(
            name="Economic guruh", course=self.course, start_date=self.today,
            plan=self.cheap, capacity=60,
        )
        self.rich_cohort = Cohort.objects.create(
            name="Intensive guruh", course=self.course, start_date=self.today,
            plan=self.rich, capacity=3,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cheap_cohort, plan=self.cheap,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=self.today + datetime.timedelta(days=20),
        )

    def move_to_the_expensive_tier(self):
        result = transfer_enrollment_to_cohort(
            source_enrollment=self.enrollment, target_cohort=self.rich_cohort,
            created_by=self.owner, allow_tier_change=True,
        )
        return result.target_enrollment


class DifferenceAmountTests(DifferenceFixture, TestCase):
    def test_the_suggestion_is_the_gap_for_the_days_that_remain(self):
        moved = self.move_to_the_expensive_tier()

        # (389000 - 89000) / 30 * 20 = 200000
        self.assertEqual(suggest_difference_amount(moved), 200000)

    def test_there_is_no_suggestion_without_a_tier_change(self):
        self.assertIsNone(suggest_difference_amount(self.enrollment))

    def test_there_is_no_suggestion_for_a_cheaper_tier(self):
        self.assertIsNone(
            difference_between(
                new_plan=self.cheap, previous_plan=self.rich,
                deadline=self.today + datetime.timedelta(days=20),
            )
        )

    def test_there_is_no_suggestion_once_the_period_is_over(self):
        self.assertIsNone(
            difference_between(
                new_plan=self.rich, previous_plan=self.cheap,
                deadline=self.today - datetime.timedelta(days=1),
            )
        )

    def test_a_full_period_is_never_exceeded(self):
        """Muddat uzoq bo'lsa ham farq bir oylikdan oshmaydi."""
        self.assertEqual(
            difference_between(
                new_plan=self.rich, previous_plan=self.cheap,
                deadline=self.today + datetime.timedelta(days=200),
            ),
            300000,
        )


class DifferenceRequestTests(DifferenceFixture, TestCase):
    def test_the_owner_creates_an_invoice_the_learner_can_see(self):
        moved = self.move_to_the_expensive_tier()

        decision = request_tier_difference(
            moved.pk, self.owner, amount=200000, reason="Intensive ga o'tdi"
        )

        self.assertTrue(decision.ok, decision.message)
        receipt = PaymentReceipt.objects.get(enrollment=moved)
        self.assertEqual(receipt.kind, PaymentReceipt.KIND_DIFFERENCE)
        self.assertEqual(int(receipt.amount), 200000)
        self.assertFalse(receipt.receipt_image)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student, category=Notification.CATEGORY_SUBSCRIPTION
            ).exists()
        )

    def test_the_request_is_audited_with_its_reason(self):
        moved = self.move_to_the_expensive_tier()

        request_tier_difference(moved.pk, self.owner, amount=200000, reason="qolgan 20 kun")

        event = SystemAuditEvent.objects.filter(action="receipt.difference.request").latest("id")
        self.assertEqual(event.actor, self.owner)
        self.assertIn("qolgan 20 kun", event.reason)

    def test_a_learner_cannot_invoice_themselves(self):
        moved = self.move_to_the_expensive_tier()

        decision = request_tier_difference(moved.pk, self.student, amount=1000, reason="x")

        self.assertFalse(decision.ok)
        self.assertFalse(PaymentReceipt.objects.filter(enrollment=moved).exists())

    def test_a_zero_amount_is_refused(self):
        moved = self.move_to_the_expensive_tier()

        self.assertFalse(request_tier_difference(moved.pk, self.owner, amount=0).ok)

    def test_only_one_open_request_at_a_time(self):
        moved = self.move_to_the_expensive_tier()
        request_tier_difference(moved.pk, self.owner, amount=200000, reason="birinchi")

        decision = request_tier_difference(moved.pk, self.owner, amount=50000, reason="ikkinchi")

        self.assertFalse(decision.ok)
        self.assertEqual(PaymentReceipt.objects.filter(enrollment=moved).count(), 1)

    def test_an_open_difference_does_not_block_the_next_renewal(self):
        """Eng muhim natija: to'lanmagan farq keyingi oyni to'sib qo'ymaydi."""
        moved = self.move_to_the_expensive_tier()
        request_tier_difference(moved.pk, self.owner, amount=200000, reason="farq")

        renewal, _, _ = create_checkout_receipt_with_promo(
            enrollment=moved, plan=self.rich, receipt_image=None,
            period_start=moved.next_payment_deadline,
            period_end=moved.next_payment_deadline + datetime.timedelta(days=30),
        )

        self.assertEqual(renewal.kind, PaymentReceipt.KIND_PERIOD)
        self.assertEqual(PaymentReceipt.objects.filter(enrollment=moved).count(), 2)


class DifferenceDecisionTests(DifferenceFixture, TestCase):
    def test_approving_a_difference_does_not_extend_the_period(self):
        """Farq to'lovi pulni yopadi, vaqtni sotmaydi."""
        moved = self.move_to_the_expensive_tier()
        deadline_before = moved.next_payment_deadline
        request_tier_difference(moved.pk, self.owner, amount=200000, reason="farq")
        receipt = PaymentReceipt.objects.get(enrollment=moved)

        decision = verify_receipt(receipt.id, self.owner)

        moved.refresh_from_db()
        receipt.refresh_from_db()
        self.assertTrue(decision.ok, decision.message)
        self.assertTrue(receipt.is_verified)
        self.assertEqual(moved.next_payment_deadline, deadline_before)
        self.assertEqual(moved.plan_id, self.rich.pk)

    def test_approving_a_difference_does_not_touch_a_lapsed_membership(self):
        moved = self.move_to_the_expensive_tier()
        Enrollment.objects.filter(pk=moved.pk).update(status=Enrollment.STATUS_EXPIRED)
        request_tier_difference(moved.pk, self.owner, amount=200000, reason="farq")
        receipt = PaymentReceipt.objects.get(enrollment=moved)

        verify_receipt(receipt.id, self.owner)

        moved.refresh_from_db()
        self.assertEqual(moved.status, Enrollment.STATUS_EXPIRED)

    def test_rejecting_a_difference_removes_the_request(self):
        moved = self.move_to_the_expensive_tier()
        request_tier_difference(moved.pk, self.owner, amount=200000, reason="farq")
        receipt = PaymentReceipt.objects.get(enrollment=moved)

        decision = reject_receipt(receipt.id, self.owner, reason="kelishildi, kerak emas")

        self.assertTrue(decision.ok, decision.message)
        self.assertFalse(PaymentReceipt.objects.filter(pk=receipt.pk).exists())


@override_settings(PRIVATE_MEDIA_ROOT=None)
class DifferenceUploadTests(DifferenceFixture, TestCase):
    def setUp(self):
        super().setUp()
        import tempfile

        media = tempfile.TemporaryDirectory(prefix="azurelms-difference-")
        self.addCleanup(media.cleanup)
        override = override_settings(PRIVATE_MEDIA_ROOT=media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.moved = self.move_to_the_expensive_tier()
        request_tier_difference(self.moved.pk, self.owner, amount=200000, reason="farq")
        self.receipt = PaymentReceipt.objects.get(enrollment=self.moved)
        self.url = reverse("cohorts:difference_upload", args=[self.receipt.pk])

    def _image(self):
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
            b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05"
            b"\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return SimpleUploadedFile("chek.png", png, content_type="image/png")

    def test_the_learner_attaches_the_receipt_to_their_own_invoice(self):
        self.client.force_login(self.student)

        self.client.post(self.url, {"receipt_image": self._image()})

        self.receipt.refresh_from_db()
        self.assertTrue(self.receipt.receipt_image)
        self.assertFalse(self.receipt.is_verified)

    def test_someone_else_cannot_attach_a_receipt(self):
        outsider = User.objects.create_user(
            username="chetdagi", email="chetdagi@example.test", password="x"
        )
        self.client.force_login(outsider)

        response = self.client.post(self.url, {"receipt_image": self._image()})

        self.receipt.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertFalse(self.receipt.receipt_image)

    def test_the_learner_sees_the_open_invoice_on_their_payments_page(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("subscriptions"))

        self.assertContains(response, "Tarif farqi")
        self.assertContains(response, "Chekni yuborish")


class DifferenceOwnerPageTests(DifferenceFixture, TestCase):
    def test_the_owner_can_request_the_difference_from_the_members_page(self):
        moved = self.move_to_the_expensive_tier()
        self.client.force_login(self.owner)
        url = reverse("backoffice_cohort_members", args=[self.rich_cohort.pk])

        page = self.client.get(url)
        self.assertContains(page, "Tarif farqi uchun to'lov so'rash")
        self.assertContains(page, 'value="200000"')

        self.client.post(url, {
            "action": "difference", "enrollment_id": moved.pk, "amount": "200000",
            "change_reason": "Intensive ga o'tdi", "confirm_change": "on",
        })

        receipt = PaymentReceipt.objects.get(enrollment=moved)
        self.assertEqual(receipt.kind, PaymentReceipt.KIND_DIFFERENCE)

    def test_a_student_cannot_request_it_by_posting_directly(self):
        moved = self.move_to_the_expensive_tier()
        self.client.force_login(self.student)
        url = reverse("backoffice_cohort_members", args=[self.rich_cohort.pk])

        self.client.post(url, {
            "action": "difference", "enrollment_id": moved.pk, "amount": "1000",
            "change_reason": "o'zimga", "confirm_change": "on",
        })

        self.assertFalse(PaymentReceipt.objects.filter(enrollment=moved).exists())
