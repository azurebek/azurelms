"""Paid plan != checkout intent; invoice history is not a live plan label."""

import datetime
import tempfile
import threading
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection
from django.test import RequestFactory, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import AIPlanPolicy, SystemAuditEvent
from aicontrol.service import resolve_limits
from bot.services import begin_course_enrollment, submit_payment_receipt, pending_receipts
from cohorts.checkout_service import checkout_period, mark_checkout_started
from cohorts.enrollment_service import promote_due_plans
from cohorts.models import Cohort, Enrollment, PaymentReceipt, PendingReceiptExists
from cohorts.receipt_service import reject_receipt, verify_receipt
from cohorts.test_single_pending_receipt import build_receipt_file
from core.entitlements import Capability, entitlements_for
from core.qa_support import skip_unless_file_backed_db
from courses.models import Course
from subscriptions.models import Plan
from subscriptions.promo_service import create_checkout_receipt_with_promo, PromoValidationError
from users.models import CustomUser, Notification


class PaymentFixture:
    def setUp(self):
        super().setUp()
        media = tempfile.TemporaryDirectory(prefix="azurelms-payment-test-")
        self.addCleanup(media.cleanup)
        override = override_settings(PRIVATE_MEDIA_ROOT=media.name)
        override.enable()
        self.addCleanup(override.disable)
        self.student = CustomUser.objects.create_user(username="paid-user", email="paid@example.test")
        self.owner = CustomUser.objects.create_superuser(username="paid-owner", email="owner@example.test", password="test")
        self.course = Course.objects.create(title="Paid course", description="d", level="beginner", instructor=self.owner)
        self.cohort = Cohort.objects.create(name="Paid group", course=self.course, start_date=timezone.localdate(), is_checkout_default=True)
        self.old = Plan.objects.create(name="Original plan", code="paid-original", price=89000)
        self.new = Plan.objects.create(name="Purchased plan", code="paid-new", price=399000)
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, plan=self.old, status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=timezone.localdate() + datetime.timedelta(days=10),
        )
        AIPlanPolicy.objects.create(plan=self.old, token_limit_5h=50000, token_limit_weekly=300000)
        AIPlanPolicy.objects.create(plan=self.new, token_limit_5h=200000, token_limit_weekly=1500000)

    def submit(self, *, plan=None, raw_code=""):
        start, end = checkout_period(self.enrollment)
        return create_checkout_receipt_with_promo(
            enrollment=self.enrollment, plan=plan or self.new,
            receipt_image=build_receipt_file(), period_start=start, period_end=end, raw_code=raw_code,
        )[0]

    def assert_original_access(self):
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.plan_id, self.old.id)
        self.assertEqual(resolve_limits(self.student), (50000, 300000))


class PendingPlanTests(PaymentFixture, TestCase):
    def test_intent_changes_neither_paid_plan_nor_ai_allowance(self):
        mark_checkout_started(self.enrollment, plan=self.new)
        self.assert_original_access()
        self.assertEqual(self.enrollment.pending_plan_id, self.new.id)

    def test_intent_does_not_grant_capabilities(self):
        matrix = {self.old.code: frozenset({Capability.COURSE_CONTENT}), self.new.code: frozenset(Capability)}
        with patch.dict("core.entitlements.PLAN_MATRIX", matrix):
            before = entitlements_for(self.student, course=self.course)
            mark_checkout_started(self.enrollment, plan=self.new)
            self.assertEqual(entitlements_for(self.student, course=self.course), before)
            receipt = self.submit()
            self.assertEqual(entitlements_for(self.student, course=self.course), before)
            verify_receipt(receipt.id, self.owner)
            # Fixture'dagi obunaning muddatiga 10 kun qolgan, ya'ni to'lov
            # kelasi davr uchun. Huquq o'sha davr boshlanganda beriladi —
            # aks holda o'quvchi to'lamagan 10 kunni ham olardi
            # (`cohorts/test_plan_effective_date.py`).
            self.assertEqual(entitlements_for(self.student, course=self.course), before)
            self.assertIn(
                Capability.AI_TUTOR,
                entitlements_for(self.student, course=self.course, today=receipt.period_start),
            )

    def test_submitted_receipt_still_does_not_raise_ai_allowance(self):
        receipt = self.submit()
        self.assertFalse(receipt.is_verified)
        self.assert_original_access()
        self.assertEqual(self.enrollment.pending_plan_id, self.new.id)

    def test_approval_activates_the_receipt_plan_and_clears_intent(self):
        receipt = self.submit()
        self.assertTrue(verify_receipt(receipt.id, self.owner).ok)
        self.enrollment.refresh_from_db()
        self.assertIsNone(self.enrollment.pending_plan_id)
        self.assertIsNone(self.enrollment.checkout_started_at)
        # To'lov kelasi davr uchun (fixture muddatiga 10 kun bor), shuning
        # uchun tarif o'sha davr boshlanganda kuchga kiradi. Kunlik xizmat
        # ustunni o'sha kuni ko'chiradi va AI limiti o'shanda ko'tariladi.
        self.assertEqual(self.enrollment.active_plan().id, self.old.id)
        self.assertEqual(self.enrollment.active_plan(today=receipt.period_start).id, self.new.id)
        self.assertEqual(promote_due_plans(today=receipt.period_start), 1)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.plan_id, self.new.id)
        self.assertEqual(resolve_limits(self.student), (200000, 1500000))

    def test_rejection_preserves_paid_access_and_clears_intent(self):
        receipt = self.submit()
        self.assertTrue(reject_receipt(receipt.id, self.owner).ok)
        self.assert_original_access()
        self.assertIsNone(self.enrollment.pending_plan_id)
        self.assertIsNone(self.enrollment.checkout_started_at)

    def test_invalid_promo_does_not_change_existing_intent(self):
        mark_checkout_started(self.enrollment, plan=self.old)
        with self.assertRaises(PromoValidationError):
            self.submit(raw_code="DOES-NOT-EXIST")
        self.assert_original_access()
        self.assertEqual(self.enrollment.pending_plan_id, self.old.id)
        self.assertFalse(PaymentReceipt.objects.exists())

    def test_pending_invoice_cannot_be_retargeted_by_another_checkout(self):
        receipt = self.submit()
        with self.assertRaises(PendingReceiptExists):
            mark_checkout_started(self.enrollment, plan=self.old)
        with self.assertRaises(PendingReceiptExists):
            self.submit(plan=self.old)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.pending_plan_id, self.new.id)
        self.assertEqual(PaymentReceipt.objects.get(pk=receipt.id).plan_id, self.new.id)

    def test_web_submission_does_not_activate_the_selected_plan(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse("cohorts:checkout", args=[self.course.pk]), {
            "plan_id": self.new.pk, "receipt_image": build_receipt_file(),
        })
        self.assertEqual(response.status_code, 302)
        self.assert_original_access()
        self.assertEqual(PaymentReceipt.objects.get().plan_id, self.new.id)

    def test_missing_upload_does_not_change_paid_plan(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse("cohorts:checkout", args=[self.course.pk]), {"plan_id": self.new.pk})
        self.assertEqual(response.status_code, 200)
        self.assert_original_access()
        self.assertFalse(PaymentReceipt.objects.exists())

    def test_bot_uses_pending_plan_and_requires_a_fresh_intent_after_approval(self):
        self.assertTrue(begin_course_enrollment(self.student, self.course.pk, self.new.pk).ok)
        self.assert_original_access()
        submitted = submit_payment_receipt(self.student, build_receipt_file())
        self.assertTrue(submitted.ok, submitted.message)
        receipt = PaymentReceipt.objects.get(pk=submitted.receipt_id)
        self.assertEqual(receipt.plan_id, self.new.pk)
        self.assertEqual(pending_receipts()[0]["plan"], self.new.name)
        self.assert_original_access()
        verify_receipt(receipt.pk, self.owner)
        self.assertEqual(submit_payment_receipt(self.student, build_receipt_file()).code, "no_target")


class InvoiceSnapshotTests(PaymentFixture, TestCase):
    def test_invoice_keeps_original_name_price_and_period_after_catalog_changes(self):
        receipt = self.submit()
        expected_period = (receipt.period_start, receipt.period_end)
        self.new.name, self.new.price = "Renamed plan", 499000
        self.new.save(update_fields=["name", "price"])
        receipt.refresh_from_db()
        self.assertEqual(receipt.plan_code_snapshot, "paid-new")
        self.assertEqual(receipt.plan_name_snapshot, "Purchased plan")
        self.assertEqual(receipt.plan_price_snapshot, Decimal("399000"))
        self.assertEqual(receipt.amount, Decimal("399000"))
        self.assertEqual((receipt.period_start, receipt.period_end), expected_period)
        verify_receipt(receipt.id, self.owner)
        self.assertEqual(pending_receipts(), [])

    def test_approved_history_does_not_follow_the_current_enrollment(self):
        receipt = self.submit()
        verify_receipt(receipt.id, self.owner)
        Enrollment.objects.filter(pk=self.enrollment.pk).update(plan=self.old)
        self.client.force_login(self.student)
        response = self.client.get(reverse("cohorts:checkout_success", args=[receipt.pk]))
        self.assertContains(response, "Purchased plan")
        self.assertNotContains(response, "Original plan")

    def test_pending_page_and_owner_review_show_purchased_not_active_plan(self):
        receipt = self.submit()
        self.client.force_login(self.student)
        response = self.client.get(reverse("cohorts:checkout_pending", args=[receipt.pk]))
        self.assertContains(response, "Purchased plan")
        self.assertNotContains(response, "Original plan")
        self.client.force_login(self.owner)
        response = self.client.get(reverse("backoffice_receipts"))
        self.assertContains(response, "Purchased plan")
        self.assertNotContains(response, "Original plan")

    def test_invoice_fields_cannot_be_rewritten_by_a_normal_save(self):
        receipt = self.submit()
        for name, value in (
            ("plan_id", self.old.id), ("plan_name_snapshot", "Forged"),
            ("plan_price_snapshot", 1), ("amount", 1),
            ("period_end", timezone.localdate()),
        ):
            with self.subTest(field=name):
                receipt.refresh_from_db()
                setattr(receipt, name, value)
                with self.assertRaises(ValidationError):
                    receipt.save()

    def test_legacy_history_is_not_guessed_from_current_enrollment(self):
        receipt = self.submit()
        PaymentReceipt.objects.filter(pk=receipt.pk).update(
            plan=None, plan_name_snapshot="", plan_code_snapshot="", plan_price_snapshot=None,
            plan_snapshot_source="legacy",
        )
        receipt.refresh_from_db()
        self.assertEqual(receipt.plan_label, "Tarif qayd etilmagan")

    def test_repeated_stale_verification_does_not_overwrite_a_later_paid_plan(self):
        receipt = self.submit()
        stale = PaymentReceipt.objects.get(pk=receipt.pk)
        verify_receipt(receipt.id, self.owner)
        next_receipt = self.submit(plan=self.old)
        verify_receipt(next_receipt.id, self.owner)
        stale.is_verified = True
        stale.save()
        self.assert_original_access()

    def test_update_fields_without_verification_has_no_activation_side_effect(self):
        receipt = self.submit()
        receipt.is_verified = True
        receipt.save(update_fields=["receipt_image"])
        receipt.refresh_from_db()
        self.assertFalse(receipt.is_verified)
        self.assert_original_access()

    def test_repeated_decision_sends_one_notification_and_audit(self):
        receipt = self.submit()
        self.assertEqual(verify_receipt(receipt.pk, self.owner).code, "verified")
        self.assertEqual(verify_receipt(receipt.pk, self.owner).code, "already")
        self.assertEqual(Notification.objects.filter(title="To'lov tasdiqlandi ✅").count(), 1)
        self.assertEqual(SystemAuditEvent.objects.filter(action="receipt.verify").count(), 1)

    def test_verified_receipt_cannot_be_unverified_or_deleted(self):
        receipt = self.submit()
        verify_receipt(receipt.id, self.owner)
        receipt.refresh_from_db()
        receipt.is_verified = False
        with self.assertRaises(ValidationError):
            receipt.save()
        with self.assertRaises(ValidationError):
            receipt.delete()


class LegacyReceiptAdminTests(PaymentFixture, TestCase):
    def test_inline_does_not_offer_or_accept_invoice_edits(self):
        from django.contrib import admin
        from cohorts.admin import PaymentReceiptInline

        receipt = self.submit()
        request = RequestFactory().get("/")
        request.user = self.owner
        inline = PaymentReceiptInline(Enrollment, admin.site)
        formset_class = inline.get_formset(request, self.enrollment)
        protected = set(PaymentReceipt.BILLING_FIELDS) - {"enrollment"}
        self.assertFalse(protected.intersection(formset_class.form.base_fields))
        self.assertNotIn("is_verified", formset_class.form.base_fields)
        self.assertNotIn("receipt_image", formset_class.form.base_fields)
        self.assertFalse(inline.has_add_permission(request, self.enrollment))
        self.assertFalse(formset_class.can_delete)
        self.assertIn(reverse("cohorts:receipt_file", args=[receipt.pk]), inline.receipt_file_link(receipt))
        prefix = formset_class.get_default_prefix()
        formset = formset_class(instance=self.enrollment, data={
            f"{prefix}-TOTAL_FORMS": "1", f"{prefix}-INITIAL_FORMS": "1",
            f"{prefix}-0-id": str(receipt.pk), f"{prefix}-0-enrollment": str(self.enrollment.pk),
            f"{prefix}-0-amount": "1", f"{prefix}-0-is_verified": "on",
        })
        self.assertTrue(formset.is_valid(), formset.errors)
        formset.save()
        receipt.refresh_from_db()
        self.assertEqual(receipt.amount, Decimal("399000"))
        self.assertFalse(receipt.is_verified)

    def test_standalone_admin_cannot_bypass_the_audited_decision_service(self):
        from django.contrib import admin
        from cohorts.admin import PaymentReceiptAdmin

        receipt = self.submit()
        request = RequestFactory().get("/")
        request.user = self.owner
        model_admin = PaymentReceiptAdmin(PaymentReceipt, admin.site)
        self.assertNotIn("is_verified", model_admin.list_editable)
        for verified in (False, True):
            receipt.is_verified = verified
            fields = model_admin.get_form(request, receipt).base_fields
            self.assertNotIn("is_verified", fields)
            self.assertFalse(set(PaymentReceipt.BILLING_FIELDS).intersection(fields))
            self.assertFalse(model_admin.has_delete_permission(request, receipt))


class ConcurrentPaymentDecisionTests(PaymentFixture, TransactionTestCase):
    def setUp(self):
        skip_unless_file_backed_db(self)
        super().setUp()

    def race(self, actions):
        receipt = self.submit()
        barrier = threading.Barrier(len(actions), timeout=15)
        results = []
        guard = threading.Lock()

        def run(action):
            try:
                actor = CustomUser.objects.get(pk=self.owner.pk)
                barrier.wait()
                result = action(receipt.pk, actor).code
            except Exception as exc:
                result = f"{type(exc).__name__}: {exc}"
            finally:
                connection.close()
            with guard:
                results.append(result)

        threads = [threading.Thread(target=run, args=(action,)) for action in actions]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=25)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        return receipt, results

    def test_two_approvals_produce_one_activation_notification_and_audit(self):
        _, results = self.race([verify_receipt, verify_receipt])
        self.assertCountEqual(results, ["verified", "already"])
        self.assertEqual(Notification.objects.filter(title="To'lov tasdiqlandi ✅").count(), 1)
        self.assertEqual(SystemAuditEvent.objects.filter(action="receipt.verify").count(), 1)

    def test_approval_vs_rejection_has_one_winner(self):
        receipt, results = self.race([verify_receipt, reject_receipt])
        self.assertEqual(results.count("missing"), 1, results)
        self.assertEqual(len(set(results) & {"verified", "rejected"}), 1, results)
        self.assertEqual(Notification.objects.filter(category=Notification.CATEGORY_SUBSCRIPTION).count(), 1)
        self.assertEqual(SystemAuditEvent.objects.filter(action__in=["receipt.verify", "receipt.reject"]).count(), 1)
        self.enrollment.refresh_from_db()
        if "verified" in results:
            self.assertTrue(PaymentReceipt.objects.get(pk=receipt.pk).is_verified)
            self.assertEqual(self.enrollment.plan_id, self.new.id)
        else:
            self.assertFalse(PaymentReceipt.objects.filter(pk=receipt.pk).exists())
            self.assertEqual(self.enrollment.plan_id, self.old.id)
