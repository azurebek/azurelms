import base64
import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

# 1x1 PNG — upload validatsiyasi baytlarni tekshirgani uchun testlar ham
# haqiqiy fayl bilan ishlaydi.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

from courses.models import Course, Lesson, LessonProgress, Module
from subscriptions.models import Plan, PromoCampaign, PromoCode, PromoRedemption
from users.models import Notification

from .checkout_service import resolve_checkout_enrollment, CheckoutUnavailable
from .enrollment_service import expire_overdue_enrollments
from .models import Attendance, Cohort, Enrollment, EnrollmentTransition, PaymentReceipt
from .transition_service import (
    EnrollmentTransitionError,
    promote_enrollment_to_cohort,
    transfer_enrollment_to_cohort,
)


User = get_user_model()

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
                        "cohorts/checkout_success.html": "Success receipt {{ receipt.id }}",
                    },
                )
            ],
        },
    }
]


@override_settings(TEMPLATES=TEST_TEMPLATES)
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
            is_checkout_default=True,
        )
        self.future_cohort = Cohort.objects.create(
            name="Future Checkout Cohort",
            course=self.course,
            start_date="2026-04-01",
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
        self.preview_url = reverse("cohorts:checkout_promo_preview", args=[self.course.id])
        self.client.force_login(self.student)

    def _fake_receipt(self):
        # Haqiqiy PNG baytlari: upload gate'i (A0b) faylni nomiga emas,
        # baytlariga qarab tekshiradi.
        return SimpleUploadedFile("receipt.png", PNG_1X1, content_type="image/png")

    def test_checkout_uses_selected_plan_price_and_assigns_plan_to_enrollment(self):
        response = self.client.post(
            self.checkout_url,
            {
                "plan_id": str(self.plan_pro.id),
                "receipt_image": self._fake_receipt(),
            },
        )

        receipt = PaymentReceipt.objects.get(enrollment__student=self.student)
        self.assertRedirects(
            response,
            reverse("cohorts:checkout_pending", args=[receipt.id]),
            fetch_redirect_response=False,
        )

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
        messages = [message.message for message in get_messages(response.wsgi_request)]
        self.assertIn("Iltimos, mavjud tariflardan birini tanlang.", messages)
        self.assertEqual(PaymentReceipt.objects.count(), 0)

    def test_checkout_applies_percent_promo_and_verification_marks_redemption_applied(self):
        campaign = PromoCampaign.objects.create(
            name="Checkout Promo",
            status=PromoCampaign.STATUS_ACTIVE,
            discount_type=PromoCampaign.DISCOUNT_PERCENT,
            discount_value=20,
        )
        campaign.applicable_plans.add(self.plan_pro)
        promo_code = PromoCode.objects.create(
            campaign=campaign,
            code="CHECK20",
        )

        response = self.client.post(
            self.checkout_url,
            {
                "plan_id": str(self.plan_pro.id),
                "promo_code": promo_code.code,
                "receipt_image": self._fake_receipt(),
            },
        )

        receipt = PaymentReceipt.objects.get()
        self.assertRedirects(
            response,
            reverse("cohorts:checkout_pending", args=[receipt.id]),
            fetch_redirect_response=False,
        )
        redemption = PromoRedemption.objects.get(payment_receipt=receipt)

        self.assertEqual(str(receipt.base_amount), "149000.00")
        self.assertEqual(str(receipt.discount_amount), "29800.00")
        self.assertEqual(str(receipt.amount), "119200.00")
        self.assertEqual(receipt.promo_code_snapshot, promo_code.code)
        self.assertEqual(redemption.status, PromoRedemption.STATUS_RESERVED)

        receipt.is_verified = True
        receipt.save()
        redemption.refresh_from_db()

        self.assertEqual(redemption.status, PromoRedemption.STATUS_APPLIED)

    def test_checkout_receipt_status_pages_follow_verification_state(self):
        self.client.post(
            self.checkout_url,
            {
                "plan_id": str(self.plan_standard.id),
                "receipt_image": self._fake_receipt(),
            },
        )
        receipt = PaymentReceipt.objects.get()

        pending_url = reverse("cohorts:checkout_pending", args=[receipt.id])
        success_url = reverse("cohorts:checkout_success", args=[receipt.id])

        pending_response = self.client.get(pending_url)
        self.assertContains(pending_response, f"Pending receipt {receipt.id}")

        success_response = self.client.get(success_url)
        self.assertRedirects(success_response, pending_url, fetch_redirect_response=False)

        receipt.is_verified = True
        receipt.save()

        pending_response = self.client.get(pending_url)
        self.assertRedirects(pending_response, success_url, fetch_redirect_response=False)

        success_response = self.client.get(success_url)
        self.assertContains(success_response, f"Success receipt {receipt.id}")

    def test_checkout_promo_preview_endpoint_returns_discount_breakdown(self):
        campaign = PromoCampaign.objects.create(
            name="Preview Promo",
            status=PromoCampaign.STATUS_ACTIVE,
            discount_type=PromoCampaign.DISCOUNT_FIXED,
            discount_value=10000,
        )
        promo_code = PromoCode.objects.create(
            campaign=campaign,
            code="PREVIEW10",
        )

        response = self.client.get(
            self.preview_url,
            {
                "plan_id": self.plan_standard.id,
                "promo_code": promo_code.code,
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["promo_code"], promo_code.code)
        self.assertEqual(payload["base_amount"], "99000.00")
        self.assertEqual(payload["discount_amount"], "10000.00")
        self.assertEqual(payload["final_amount"], "89000.00")


class CheckoutResolutionServiceTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="checkout-service-student",
            email="checkout-service-student@example.com",
            password="testpass123",
        )
        self.teacher = User.objects.create_user(
            username="checkout-service-teacher",
            email="checkout-service-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.course = Course.objects.create(
            title="Checkout Resolution Course",
            description="Resolution test",
            instructor=self.teacher,
            level="beginner",
        )
        self.default_cohort = Cohort.objects.create(
            name="Default Cohort",
            course=self.course,
            start_date="2026-03-01",
            is_active=True,
            is_checkout_default=True,
        )
        self.other_cohort = Cohort.objects.create(
            name="Other Cohort",
            course=self.course,
            start_date="2026-04-01",
            is_active=True,
        )

    def test_checkout_resolution_uses_default_cohort_for_new_enrollment(self):
        enrollment, created, checkout_cohort = resolve_checkout_enrollment(
            student=self.student,
            course=self.course,
        )

        self.assertTrue(created)
        self.assertEqual(enrollment.cohort, self.default_cohort)
        self.assertEqual(checkout_cohort, self.default_cohort)

    def test_checkout_resolution_reuses_existing_same_course_enrollment(self):
        existing = Enrollment.objects.create(
            student=self.student,
            cohort=self.other_cohort,
            status=Enrollment.STATUS_EXPIRED,
        )

        enrollment, created, checkout_cohort = resolve_checkout_enrollment(
            student=self.student,
            course=self.course,
        )

        self.assertFalse(created)
        self.assertEqual(enrollment, existing)
        self.assertEqual(checkout_cohort, self.default_cohort)

    def test_checkout_resolution_fails_when_course_has_no_group(self):
        course_without_group = Course.objects.create(
            title="Subscription Only Course",
            description="No cohort yet",
            instructor=self.teacher,
            level="beginner",
        )

        with self.assertRaises(CheckoutUnavailable):
            resolve_checkout_enrollment(
                student=self.student,
                course=course_without_group,
            )


class EnrollmentInvariantTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="invariant-student",
            email="invariant-student@example.com",
            password="testpass123",
        )
        self.teacher = User.objects.create_user(
            username="invariant-teacher",
            email="invariant-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.course = Course.objects.create(
            title="Invariant Course",
            description="Invariant test",
            instructor=self.teacher,
            level="beginner",
        )
        self.first_cohort = Cohort.objects.create(
            name="Invariant Cohort 1",
            course=self.course,
            start_date="2026-03-01",
        )
        self.second_cohort = Cohort.objects.create(
            name="Invariant Cohort 2",
            course=self.course,
            start_date="2026-03-15",
        )

    def test_second_active_enrollment_for_same_course_is_blocked(self):
        Enrollment.objects.create(
            student=self.student,
            cohort=self.first_cohort,
            status=Enrollment.STATUS_ACTIVE,
        )

        with self.assertRaises(ValidationError):
            Enrollment.objects.create(
                student=self.student,
                cohort=self.second_cohort,
                status=Enrollment.STATUS_ACTIVE,
            )


class EnrollmentActiveAccessTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="access-student",
            email="access-student@example.com",
            password="testpass123",
        )
        self.teacher = User.objects.create_user(
            username="access-teacher",
            email="access-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.course = Course.objects.create(
            title="Lifecycle Course",
            description="Lifecycle test",
            instructor=self.teacher,
            level="beginner",
        )
        self.cohort_overdue = Cohort.objects.create(
            name="Lifecycle Overdue",
            course=self.course,
            start_date="2026-03-01",
            is_active=True,
        )
        self.cohort_grace = Cohort.objects.create(
            name="Lifecycle Grace",
            course=self.course,
            start_date="2026-03-02",
            is_active=True,
        )
        self.cohort_open = Cohort.objects.create(
            name="Lifecycle Open",
            course=self.course,
            start_date="2026-03-03",
            is_active=True,
        )

    def test_with_active_access_excludes_only_enrollments_past_grace_period(self):
        today = timezone.localdate()
        second_student = User.objects.create_user(
            username="access-student-2",
            email="access-student-2@example.com",
            password="testpass123",
        )
        third_student = User.objects.create_user(
            username="access-student-3",
            email="access-student-3@example.com",
            password="testpass123",
        )
        overdue = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort_overdue,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=today - datetime.timedelta(days=3),
        )
        within_grace = Enrollment.objects.create(
            student=second_student,
            cohort=self.cohort_grace,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=today - datetime.timedelta(days=2),
        )
        open_ended = Enrollment.objects.create(
            student=third_student,
            cohort=self.cohort_open,
            status=Enrollment.STATUS_ACTIVE,
        )

        active_ids = set(Enrollment.objects.with_active_access().values_list("id", flat=True))

        self.assertNotIn(overdue.id, active_ids)
        self.assertIn(within_grace.id, active_ids)
        self.assertIn(open_ended.id, active_ids)

    def test_expire_overdue_enrollments_persists_only_overdue_records(self):
        today = timezone.localdate()
        overdue = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort_overdue,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=today - datetime.timedelta(days=3),
        )
        within_grace = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort_grace,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=today - datetime.timedelta(days=1),
        )

        updated_count = expire_overdue_enrollments()

        overdue.refresh_from_db()
        within_grace.refresh_from_db()

        self.assertEqual(updated_count, 1)
        self.assertEqual(overdue.status, Enrollment.STATUS_EXPIRED)
        self.assertEqual(within_grace.status, Enrollment.STATUS_ACTIVE)

    def test_expire_overdue_enrollments_command_uses_same_lifecycle_service(self):
        overdue = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort_overdue,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=timezone.localdate() - datetime.timedelta(days=4),
        )

        call_command("expire_overdue_enrollments")
        overdue.refresh_from_db()

        self.assertEqual(overdue.status, Enrollment.STATUS_EXPIRED)


class EnrollmentTransitionServiceTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="transition-teacher",
            email="transition-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="transition-student",
            email="transition-student@example.com",
            password="testpass123",
        )
        self.plan = Plan.objects.create(
            name="Premium",
            price=199000,
            description="Premium tarif",
            order=1,
        )

        self.course_a1 = Course.objects.create(
            title="Turk tili A1",
            description="A1",
            instructor=self.teacher,
            level="beginner",
        )
        self.course_a2 = Course.objects.create(
            title="Turk tili A2",
            description="A2",
            instructor=self.teacher,
            level="beginner",
        )

        self.source_cohort = Cohort.objects.create(
            name="Yanvar A1",
            course=self.course_a1,
            start_date="2026-01-10",
            is_active=True,
        )
        self.transfer_target_cohort = Cohort.objects.create(
            name="Fevral A1",
            course=self.course_a1,
            start_date="2026-02-10",
            is_active=True,
        )
        self.promotion_target_cohort = Cohort.objects.create(
            name="Mart A2",
            course=self.course_a2,
            start_date="2026-03-10",
            is_active=True,
        )

        self.source_enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.source_cohort,
            plan=self.plan,
            status=Enrollment.STATUS_ACTIVE,
            completion_state=Enrollment.COMPLETION_STATE_IN_PROGRESS,
            last_payment_date=timezone.localdate() - datetime.timedelta(days=7),
            next_payment_deadline=timezone.localdate() + datetime.timedelta(days=23),
        )

        self.module = Module.objects.create(course=self.course_a1, title="1-modul", order=1)
        self.lesson = Lesson.objects.create(module=self.module, title="1-dars", order=1)
        self.lesson_progress = LessonProgress.objects.create(
            enrollment=self.source_enrollment,
            lesson=self.lesson,
            is_completed=True,
            completed_at=timezone.now(),
        )
        self.attendance = Attendance.objects.create(
            enrollment=self.source_enrollment,
            lesson=self.lesson,
            date=timezone.localdate(),
            status=Attendance.STATUS_PRESENT,
            xp_awarded=15,
        )

    def test_transfer_creates_new_enrollment_moves_progress_and_keeps_attendance_history(self):
        result = transfer_enrollment_to_cohort(
            source_enrollment=self.source_enrollment,
            target_cohort=self.transfer_target_cohort,
            created_by=self.teacher,
            note="Schedule updated",
        )

        self.source_enrollment.refresh_from_db()
        target = result.target_enrollment
        target.refresh_from_db()
        self.lesson_progress.refresh_from_db()
        self.attendance.refresh_from_db()

        self.assertEqual(self.source_enrollment.status, Enrollment.STATUS_FROZEN)
        self.assertEqual(self.source_enrollment.completion_state, Enrollment.COMPLETION_STATE_IN_PROGRESS)
        self.assertEqual(target.cohort, self.transfer_target_cohort)
        self.assertEqual(target.status, Enrollment.STATUS_ACTIVE)
        self.assertEqual(target.plan, self.plan)
        self.assertEqual(target.next_payment_deadline, self.source_enrollment.next_payment_deadline)
        self.assertEqual(self.lesson_progress.enrollment, target)
        self.assertEqual(self.attendance.enrollment, self.source_enrollment)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                external_key=f"enrollment-transition-{result.transition.id}",
            ).exists()
        )

        transition = EnrollmentTransition.objects.get(pk=result.transition.pk)
        self.assertEqual(transition.kind, EnrollmentTransition.KIND_TRANSFER)
        self.assertEqual(transition.progress_items_moved, 1)
        self.assertEqual(transition.source_enrollment, self.source_enrollment)
        self.assertEqual(transition.target_enrollment, target)

    def test_promotion_requires_ready_state_and_creates_pending_target(self):
        self.source_enrollment.completion_state = Enrollment.COMPLETION_STATE_PROMOTION_READY
        self.source_enrollment.completed_at = timezone.now()
        self.source_enrollment.promotion_ready_at = timezone.now()
        self.source_enrollment.save(
            update_fields=["completion_state", "completed_at", "promotion_ready_at"]
        )

        result = promote_enrollment_to_cohort(
            source_enrollment=self.source_enrollment,
            target_cohort=self.promotion_target_cohort,
            created_by=self.teacher,
            note="A2 ga o'tkazildi",
        )

        self.source_enrollment.refresh_from_db()
        target = result.target_enrollment
        target.refresh_from_db()
        self.lesson_progress.refresh_from_db()
        self.attendance.refresh_from_db()

        self.assertEqual(self.source_enrollment.status, Enrollment.STATUS_FROZEN)
        self.assertEqual(self.source_enrollment.completion_state, Enrollment.COMPLETION_STATE_COMPLETED)
        self.assertEqual(target.cohort, self.promotion_target_cohort)
        self.assertEqual(target.status, Enrollment.STATUS_PENDING)
        self.assertEqual(target.completion_state, Enrollment.COMPLETION_STATE_IN_PROGRESS)
        self.assertEqual(target.plan, self.plan)
        self.assertIsNone(target.next_payment_deadline)
        self.assertEqual(self.lesson_progress.enrollment, self.source_enrollment)
        self.assertEqual(self.attendance.enrollment, self.source_enrollment)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                external_key=f"enrollment-transition-{result.transition.id}",
            ).exists()
        )

        transition = EnrollmentTransition.objects.get(pk=result.transition.pk)
        self.assertEqual(transition.kind, EnrollmentTransition.KIND_PROMOTION)
        self.assertEqual(transition.progress_items_moved, 0)

    def test_transfer_rejects_target_from_another_course(self):
        with self.assertRaises(EnrollmentTransitionError):
            transfer_enrollment_to_cohort(
                source_enrollment=self.source_enrollment,
                target_cohort=self.promotion_target_cohort,
                created_by=self.teacher,
            )

    def test_promotion_rejects_non_ready_enrollment(self):
        with self.assertRaises(EnrollmentTransitionError):
            promote_enrollment_to_cohort(
                source_enrollment=self.source_enrollment,
                target_cohort=self.promotion_target_cohort,
                created_by=self.teacher,
            )

    def test_promotion_rejects_existing_active_target_course_enrollment(self):
        self.source_enrollment.completion_state = Enrollment.COMPLETION_STATE_PROMOTION_READY
        self.source_enrollment.completed_at = timezone.now()
        self.source_enrollment.promotion_ready_at = timezone.now()
        self.source_enrollment.save(
            update_fields=["completion_state", "completed_at", "promotion_ready_at"]
        )
        other_target = Cohort.objects.create(
            name="A2 Old Cohort",
            course=self.course_a2,
            start_date="2026-02-01",
            is_active=True,
        )
        Enrollment.objects.create(
            student=self.student,
            cohort=other_target,
            status=Enrollment.STATUS_ACTIVE,
        )

        with self.assertRaises(EnrollmentTransitionError):
            promote_enrollment_to_cohort(
                source_enrollment=self.source_enrollment,
                target_cohort=self.promotion_target_cohort,
                created_by=self.teacher,
            )
