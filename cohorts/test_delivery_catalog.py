"""Delivery invariants through supported web, bot, model and payment writes."""

import datetime
import threading
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import AIPlanPolicy, SystemAuditEvent
from aicontrol.service import resolve_limits
from bot.services import begin_course_enrollment, submit_payment_receipt
from cohorts.checkout_service import CheckoutUnavailable, checkout_period, find_checkout_enrollment, resolve_checkout_enrollment
from cohorts.delivery_service import occupied_seats
from cohorts.enrollment_service import expire_overdue_enrollments
from cohorts.models import Cohort, Enrollment, EnrollmentTransition, PaymentReceipt
from cohorts.receipt_service import reject_receipt, verify_receipt
from cohorts.test_single_pending_receipt import build_receipt_file
from cohorts.transition_service import EnrollmentTransitionError, transfer_enrollment_to_cohort
from core.entitlements import BASELINE, plan_entitlements
from core.qa_support import skip_unless_file_backed_db
from courses.models import Course
from subscriptions.models import Plan
from subscriptions.promo_service import create_checkout_receipt_with_promo
from users.models import CustomUser, Notification


class DeliveryFixture:
    def setUp(self):
        super().setUp()
        self.owner = CustomUser.objects.create_superuser(username="delivery-owner", email="owner@example.test", password="test")
        self.student = CustomUser.objects.create_user(username="delivery-user", email="user@example.test")
        self.course = Course.objects.create(title="Delivery", description="d", level="beginner", instructor=self.owner)
        self.plan = Plan.objects.create(code="delivery-plan", name="Delivery plan", price=259000, cohort_capacity_limit=8)
        self.other = Plan.objects.create(code="other-delivery", name="Other delivery", price=399000, cohort_capacity_limit=3)
        self.cohort = Cohort.objects.create(name="Delivery group", course=self.course, plan=self.plan, capacity=1, start_date=timezone.localdate(), is_checkout_default=True)

    def enrollment(self, student=None, cohort=None, **kwargs):
        return Enrollment.objects.create(student=student or self.student, cohort=cohort or self.cohort, **kwargs)

    def receipt(self, enrollment=None, plan=None):
        enrollment = enrollment or self.enrollment()
        start, end = checkout_period(enrollment)
        return create_checkout_receipt_with_promo(
            enrollment=enrollment, plan=plan or self.plan, receipt_image=None,
            period_start=start, period_end=end,
        )[0]

    def second_student(self):
        return CustomUser.objects.create_user(username="delivery-second", email="second@example.test")


class DeliveryTests(DeliveryFixture, TestCase):
    def test_seeded_tiers_have_capacity_defaults_and_equal_core_capabilities(self):
        for code, capacity in (("economic", 60), ("standard", 8), ("intensive", 3)):
            plan = Plan.objects.get(code=code)
            group = Cohort.objects.create(name=code, course=self.course, plan=plan, start_date=timezone.localdate(), is_checkout_default=True)
            self.assertEqual(group.capacity, capacity)
            self.assertEqual(plan_entitlements(plan), BASELINE)

    def test_capacity_cannot_be_zero(self):
        self.cohort.capacity = 0
        with self.assertRaises(ValidationError):
            self.cohort.save()
        self.cohort.refresh_from_db()
        self.assertEqual(self.cohort.capacity, 1)

    def test_the_owner_may_seat_more_than_the_tier_standard(self):
        """Tarifdagi son — standart, qattiq shift emas.

        Egasi bitta guruhga istisno qila olishi kerak (masalan oxirgi bitta
        o'quvchini qabul qilish). Tasodif emasligini forma ta'minlaydi:
        sabab, tasdiq va audit; katalogda esa istisno ko'rinib turadi.
        """
        self.cohort.capacity = 9

        self.cohort.save()

        self.cohort.refresh_from_db()
        self.assertEqual(self.cohort.capacity, 9)

    def test_cannot_shrink_below_members_or_relabel_populated_cohort(self):
        self.cohort.capacity = 2
        self.cohort.save()
        self.enrollment(status="active", plan=self.plan)
        self.enrollment(self.second_student(), status="expired", plan=self.plan)
        self.cohort.capacity = 1
        with self.assertRaises(ValidationError):
            self.cohort.save()
        self.cohort.refresh_from_db()
        self.cohort.plan = self.other
        with self.assertRaises(ValidationError):
            self.cohort.save()

    def test_untyped_legacy_cohort_cannot_receive_delivery_tier(self):
        legacy = Cohort.objects.create(name="Legacy", course=self.course, start_date=timezone.localdate())
        enrollment = self.enrollment(cohort=legacy)
        with self.assertRaises(ValidationError):
            self.receipt(enrollment)
        self.assertFalse(PaymentReceipt.objects.exists())

    def test_pending_and_active_plan_must_match_cohort(self):
        for kwargs in ({"plan": self.other}, {"pending_plan": self.other}, {"status": "active"}):
            with self.assertRaises(ValidationError):
                self.enrollment(**kwargs)
        self.assertEqual(Enrollment.objects.count(), 0)

    def test_get_and_preview_do_not_create_or_reserve_membership(self):
        self.client.force_login(self.student)
        url = reverse("cohorts:checkout", args=[self.course.pk])
        response = self.client.get(url, {"plan_id": self.plan.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Guruh sig'imi: 1")
        self.assertContains(response, '<script defer src="/static/js/checkout-plan.js"></script>')
        self.client.get(reverse("cohorts:checkout_promo_preview", args=[self.course.pk]), {"plan_id": self.plan.pk})
        self.assertEqual(Enrollment.objects.count(), 0)
        self.assertEqual(occupied_seats(self.cohort), 0)

    def test_unqualified_course_cta_finds_an_offered_plan(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("cohorts:checkout", args=[self.course.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_plan"].pk, self.plan.pk)
        self.assertEqual(response.context["checkout_cohort"].pk, self.cohort.pk)

    def test_two_pending_receipts_hold_no_seat_only_first_approval_wins(self):
        first = self.receipt()
        second = self.receipt(self.enrollment(self.second_student()))
        self.assertEqual(occupied_seats(self.cohort), 0)
        self.assertTrue(verify_receipt(first.pk, self.owner).ok)
        result = verify_receipt(second.pk, self.owner)
        self.assertEqual(result.code, "cohort_full")
        second.refresh_from_db()
        self.assertFalse(second.is_verified)
        self.assertEqual(second.enrollment.status, "pending")
        self.assertIsNone(second.enrollment.plan_id)
        self.assertEqual(occupied_seats(self.cohort), 1)
        self.assertEqual(Notification.objects.filter(title="To'lov tasdiqlandi ✅").count(), 1)
        self.assertTrue(SystemAuditEvent.objects.filter(action="receipt.verify", outcome="denied").exists())

    def test_full_cohort_rejects_new_web_bot_and_model_admissions_but_allows_renewal(self):
        first = self.receipt()
        verify_receipt(first.pk, self.owner)
        newcomer = self.second_student()
        self.assertFalse(begin_course_enrollment(newcomer, self.course.pk, self.plan.pk).ok)
        self.client.force_login(newcomer)
        self.assertEqual(self.client.get(reverse("cohorts:checkout", args=[self.course.pk]), {"plan_id": self.plan.pk}).status_code, 302)
        with self.assertRaises(ValidationError):
            self.enrollment(newcomer)
        renewal = self.receipt(Enrollment.objects.get(pk=first.enrollment_id))
        self.assertTrue(verify_receipt(renewal.pk, self.owner).ok)
        self.assertEqual(occupied_seats(self.cohort), 1)

    def test_expiry_does_not_release_seat_but_freezing_does(self):
        active = self.enrollment(plan=self.plan, status="active", next_payment_deadline=timezone.localdate() - datetime.timedelta(days=10))
        expire_overdue_enrollments()
        active.refresh_from_db()
        self.assertEqual(active.status, "expired")
        self.assertEqual(occupied_seats(self.cohort), 1)
        active.status = "frozen"
        active.save(update_fields=["status"])
        self.assertEqual(occupied_seats(self.cohort), 0)

    def test_tier_specific_default_does_not_move_student_to_another_plan(self):
        other = Cohort.objects.create(name="Other tier", course=self.course, plan=self.other, start_date=timezone.localdate(), is_checkout_default=True)
        enrollment, _created, target = resolve_checkout_enrollment(student=self.student, course=self.course, plan=self.other)
        self.assertEqual(target.pk, other.pk)
        self.assertEqual(enrollment.cohort_id, other.pk)
        self.assertIsNone(enrollment.plan_id)

    def test_auto_tier_change_for_paid_membership_is_rejected(self):
        self.enrollment(plan=self.plan, status="active")
        Cohort.objects.create(name="Other tier", course=self.course, plan=self.other, start_date=timezone.localdate())
        with self.assertRaises(CheckoutUnavailable):
            find_checkout_enrollment(student=self.student, course=self.course, plan=self.other)

    def test_full_default_falls_back_without_changing_default_flag(self):
        self.enrollment(plan=self.plan, status="active")
        fallback = Cohort.objects.create(name="Fallback", course=self.course, plan=self.plan, start_date=timezone.localdate())
        enrollment, _created, group = resolve_checkout_enrollment(student=self.second_student(), course=self.course, plan=self.plan)
        self.assertEqual(group.pk, fallback.pk)
        fallback.refresh_from_db()
        self.assertFalse(fallback.is_checkout_default)
        self.assertEqual(enrollment.cohort_id, fallback.pk)

    def stranded_checkout(self, *, keep_receipt=False):
        self.assertTrue(begin_course_enrollment(self.student, self.course.pk, self.plan.pk).ok)
        pending = Enrollment.objects.get(student=self.student)
        receipt = self.receipt(pending)
        self.enrollment(self.second_student(), plan=self.plan, status="active")
        self.assertEqual(verify_receipt(receipt.pk, self.owner).code, "cohort_full")
        if not keep_receipt:
            self.assertTrue(reject_receipt(receipt.pk, self.owner).ok)
        fallback = Cohort.objects.create(name="Fallback", course=self.course, plan=self.plan, capacity=1, start_date=timezone.localdate())
        return pending, fallback, receipt

    def test_stranded_pending_preview_uses_fallback_without_writes(self):
        pending, fallback, _ = self.stranded_checkout()
        self.client.force_login(self.student)
        before = list(Enrollment.objects.values())
        response = self.client.get(reverse("cohorts:checkout", args=[self.course.pk]), {"plan_id": self.plan.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["checkout_cohort"].pk, fallback.pk)
        self.client.get(reverse("cohorts:checkout_promo_preview", args=[self.course.pk]), {"plan_id": self.plan.pk})
        self.assertEqual(list(Enrollment.objects.values()), before)
        self.assertFalse(EnrollmentTransition.objects.exists())
        self.assertEqual(occupied_seats(fallback), 0)

    def test_web_retry_after_rejection_reassigns_and_can_be_approved(self):
        pending, fallback, _ = self.stranded_checkout()
        self.client.force_login(self.student)
        response = self.client.post(reverse("cohorts:checkout", args=[self.course.pk]), {
            "plan_id": self.plan.pk, "receipt_image": build_receipt_file(),
        })
        self.assertEqual(response.status_code, 302)
        replacement = Enrollment.objects.get(student=self.student, cohort=fallback)
        pending.refresh_from_db()
        self.assertEqual(pending.status, "frozen")
        self.assertIsNone(pending.pending_plan_id)
        self.assertIsNone(pending.checkout_started_at)
        self.assertEqual(replacement.status, "pending")
        self.assertEqual(occupied_seats(fallback), 0)
        transition = EnrollmentTransition.objects.get()
        self.assertEqual(transition.source_enrollment_id, pending.pk)
        self.assertEqual(transition.target_enrollment_id, replacement.pk)
        self.assertTrue(SystemAuditEvent.objects.filter(action="enrollment.checkout_reassign", actor=self.student).exists())
        receipt = replacement.receipts.get()
        self.assertEqual(receipt.plan_id, self.plan.pk)
        self.assertTrue(verify_receipt(receipt.pk, self.owner).ok)
        self.assertEqual(occupied_seats(fallback), 1)
        self.assertEqual(occupied_seats(self.cohort), 1)

    def test_bot_retry_reassigns_once_and_routes_image_to_new_group(self):
        pending, fallback, _ = self.stranded_checkout()
        for _ in range(2):
            result = begin_course_enrollment(self.student, self.course.pk, self.plan.pk)
            self.assertTrue(result.ok, result.message)
        self.assertEqual(EnrollmentTransition.objects.count(), 1)
        receipt_result = submit_payment_receipt(self.student, build_receipt_file())
        self.assertTrue(receipt_result.ok, receipt_result.message)
        receipt = PaymentReceipt.objects.get(pk=receipt_result.receipt_id)
        self.assertEqual(receipt.enrollment.cohort_id, fallback.pk)
        self.assertNotEqual(receipt.enrollment_id, pending.pk)
        self.assertTrue(verify_receipt(receipt.pk, self.owner).ok)

    def test_unresolved_receipt_stays_in_original_group_and_blocks_reassignment(self):
        pending, fallback, receipt = self.stranded_checkout(keep_receipt=True)
        result = begin_course_enrollment(self.student, self.course.pk, self.plan.pk)
        self.assertEqual(result.code, "pending_receipt")
        self.client.force_login(self.student)
        response = self.client.get(reverse("cohorts:checkout", args=[self.course.pk]), {"plan_id": self.plan.pk})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["has_pending_receipt"])
        self.assertEqual(response.context["checkout_cohort"].pk, self.cohort.pk)
        receipt.refresh_from_db()
        self.assertEqual(receipt.enrollment_id, pending.pk)
        self.assertFalse(receipt.is_verified)
        self.assertFalse(EnrollmentTransition.objects.exists())
        self.assertFalse(fallback.members.exists())

    def test_reassignment_audit_failure_rolls_back_membership_and_intent(self):
        pending, fallback, _ = self.stranded_checkout()
        before = list(Enrollment.objects.values())
        with patch("cohorts.transition_service._audit_transition", side_effect=RuntimeError("audit offline")):
            with self.assertRaises(RuntimeError):
                resolve_checkout_enrollment(student=self.student, course=self.course, plan=self.plan)
        self.assertEqual(list(Enrollment.objects.values()), before)
        self.assertFalse(fallback.members.exists())
        self.assertFalse(EnrollmentTransition.objects.exists())

    def test_closed_unpaid_group_can_fall_back_but_never_to_another_tier(self):
        pending = self.enrollment(pending_plan=self.plan)
        self.cohort.is_active = False
        self.cohort.save(update_fields=["is_active"])
        Cohort.objects.create(name="Wrong tier", course=self.course, plan=self.other, start_date=timezone.localdate())
        with self.assertRaises(CheckoutUnavailable):
            resolve_checkout_enrollment(student=self.student, course=self.course, plan=self.plan)
        pending.refresh_from_db()
        self.assertEqual(pending.status, "pending")
        fallback = Cohort.objects.create(name="Fallback", course=self.course, plan=self.plan, start_date=timezone.localdate())
        replacement, created, target = resolve_checkout_enrollment(student=self.student, course=self.course, plan=self.plan)
        self.assertTrue(created)
        self.assertEqual(replacement.cohort_id, fallback.pk)
        self.assertEqual(target.pk, fallback.pk)

    def test_bot_submission_uses_same_tier_capacity_and_approval(self):
        self.assertTrue(begin_course_enrollment(self.student, self.course.pk, self.plan.pk).ok)
        result = submit_payment_receipt(self.student, build_receipt_file())
        self.assertTrue(result.ok, result.message)
        self.assertEqual(occupied_seats(self.cohort), 0)
        self.assertTrue(verify_receipt(result.receipt_id, self.owner).ok)
        self.assertEqual(occupied_seats(self.cohort), 1)

    def test_receipt_survives_archiving_but_new_sale_does_not(self):
        receipt = self.receipt()
        self.plan.is_available_for_purchase = False
        self.plan.save(update_fields=["is_available_for_purchase"])
        self.assertTrue(verify_receipt(receipt.pk, self.owner).ok)
        self.assertTrue(begin_course_enrollment(self.student, self.course.pk, self.plan.pk).ok)
        self.assertFalse(begin_course_enrollment(self.second_student(), self.course.pk, self.plan.pk).ok)

    def test_rejection_does_not_change_existing_paid_seat(self):
        receipt = self.receipt()
        verify_receipt(receipt.pk, self.owner)
        renewal = self.receipt(Enrollment.objects.get(pk=receipt.enrollment_id))
        reject_receipt(renewal.pk, self.owner)
        self.assertEqual(occupied_seats(self.cohort), 1)

    def test_transfer_is_atomic_when_target_full_or_wrong_tier(self):
        source = self.enrollment(plan=self.plan, status="active")
        target = Cohort.objects.create(name="Full target", course=self.course, plan=self.plan, capacity=1, start_date=timezone.localdate())
        self.enrollment(self.second_student(), target, plan=self.plan, status="active")
        with self.assertRaises(EnrollmentTransitionError):
            transfer_enrollment_to_cohort(source_enrollment=source, target_cohort=target, created_by=self.owner)
        source.refresh_from_db()
        self.assertEqual(source.status, "active")
        wrong = Cohort.objects.create(name="Wrong tier", course=self.course, plan=self.other, start_date=timezone.localdate())
        with self.assertRaises(EnrollmentTransitionError):
            transfer_enrollment_to_cohort(source_enrollment=source, target_cohort=wrong, created_by=self.owner)

    def test_latest_active_enrollment_sets_ai_limit_not_max_or_sum(self):
        AIPlanPolicy.objects.create(plan=self.plan, token_limit_5h=200000, token_limit_weekly=1500000)
        AIPlanPolicy.objects.create(plan=self.other, token_limit_5h=50000, token_limit_weekly=300000)
        self.enrollment(plan=self.plan, status="active")
        second_course = Course.objects.create(title="Another", description="d", level="beginner")
        second = Cohort.objects.create(name="Latest", course=second_course, plan=self.other, start_date=timezone.localdate())
        latest = self.enrollment(cohort=second, plan=self.other, status="pending")
        self.assertEqual(resolve_limits(self.student), (200000, 1500000))
        receipt = self.receipt(latest, plan=self.other)
        verify_receipt(receipt.pk, self.owner)
        self.assertEqual(resolve_limits(self.student), (50000, 300000))
        self.other.is_available_for_purchase = False
        self.other.save(update_fields=["is_available_for_purchase"])
        self.assertEqual(resolve_limits(self.student), (50000, 300000))


class DeliveryContentionTests(DeliveryFixture, TransactionTestCase):
    def setUp(self):
        skip_unless_file_backed_db(self)
        super().setUp()

    def test_last_seat_has_exactly_one_winner(self):
        receipts = [self.receipt(), self.receipt(self.enrollment(self.second_student()))]
        gate = threading.Barrier(2, timeout=15)
        results = []

        def approve(receipt_id):
            try:
                actor = CustomUser.objects.get(pk=self.owner.pk)
                gate.wait()
                results.append(verify_receipt(receipt_id, actor).code)
            except Exception as exc:
                results.append(repr(exc))
            finally:
                connection.close()

        threads = [threading.Thread(target=approve, args=(receipt.pk,)) for receipt in receipts]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=25)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertCountEqual(results, ["verified", "cohort_full"])
        self.assertEqual(occupied_seats(self.cohort), 1)
        self.assertEqual(PaymentReceipt.objects.filter(is_verified=True).count(), 1)
        self.assertEqual(Notification.objects.filter(title="To'lov tasdiqlandi ✅").count(), 1)
