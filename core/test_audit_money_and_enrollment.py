"""A2 — pul va enrollment qarorlari audit ledgeriga tushishi kerak.

`05-launch-ops.md` §3 minimal audit ro'yxatida "receipt qarori" va "enrollment
transition" bor. Ikkalasi ham bugungacha ledgerdan tashqarida edi.

**Chek tasdiqlash** — pulga tegadigan yagona qaror. U enrollmentni faollashtiradi
va promo chegirmasini "ishlatilgan" holatiga o'tkazadi, ammo kim tasdiqlagani
faqat `reviewed_by` maydonida qolardi: qaysi qurilmadan, qachon, qaysi release'da
va qanday holatdan qanday holatga o'tgani yozilmasdi.

**Enrollment transfer/promotion** o'z `EnrollmentTransition` yozuvini qoldiradi
va bu domen uchun yetarli, ammo u operatsion ledger emas — `source`, IP va
release SHA yo'q, ya'ni "kim, qayerdan" savoliga javob bermaydi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from bot.services import verify_receipt
from cohorts.models import Cohort, Enrollment, PaymentReceipt
from cohorts.transition_service import promote_enrollment_to_cohort, transfer_enrollment_to_cohort
from courses.models import Course
from subscriptions.models import Plan

User = get_user_model()


class ReceiptDecisionIsAuditedTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="receipt-owner",
            email="receipt-owner@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.owner.telegram_id = 880000001
        self.owner.save(update_fields=["telegram_id"])
        self.student = User.objects.create_user(
            username="receipt-student", email="receipt-student@example.com", password="x"
        )
        self.course = Course.objects.create(
            title="Receipt Course", description="A2", instructor=self.owner, level="beginner"
        )
        self.cohort = Cohort.objects.create(
            name="Receipt Cohort", course=self.course, start_date="2026-01-01", is_active=True
        )
        self.plan = Plan.objects.create(name="Receipt Plan", price=100000, order=1)
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            plan=self.plan,
            status=Enrollment.STATUS_PENDING,
        )
        self.receipt = PaymentReceipt.objects.create(
            enrollment=self.enrollment,
            amount=100000,
            period_start=timezone.localdate(),
            period_end=timezone.localdate() + datetime.timedelta(days=30),
        )

    def test_verifying_a_receipt_writes_an_audit_event(self):
        verify_receipt(receipt_id=self.receipt.id, actor=self.owner)

        event = SystemAuditEvent.objects.get(action="receipt.verify")
        self.assertEqual(event.actor_label, "receipt-owner")
        self.assertEqual(event.source, SystemAuditEvent.SOURCE_BOT)

    def test_the_event_records_the_enrollment_state_change(self):
        verify_receipt(receipt_id=self.receipt.id, actor=self.owner)

        event = SystemAuditEvent.objects.get(action="receipt.verify")
        self.assertEqual(event.before["enrollment_status"], Enrollment.STATUS_PENDING)
        self.assertEqual(event.after["enrollment_status"], Enrollment.STATUS_ACTIVE)
        self.assertEqual(event.after["amount"], "100000.00")

    def test_verifying_an_already_verified_receipt_writes_nothing(self):
        verify_receipt(receipt_id=self.receipt.id, actor=self.owner)
        SystemAuditEvent.objects.all().delete()

        result = verify_receipt(receipt_id=self.receipt.id, actor=self.owner)

        self.assertEqual(result.code, "already")
        self.assertEqual(SystemAuditEvent.objects.count(), 0)

    def test_a_denied_attempt_is_recorded_as_denied(self):
        """Ruxsatsiz urinish ham izsiz qolmasligi kerak."""
        outsider = User.objects.create_user(
            username="outsider", email="outsider@example.com", password="x"
        )

        result = verify_receipt(receipt_id=self.receipt.id, actor=outsider)

        self.assertFalse(result.ok)
        event = SystemAuditEvent.objects.get(action="receipt.verify")
        self.assertEqual(event.outcome, SystemAuditEvent.OUTCOME_DENIED)
        self.receipt.refresh_from_db()
        self.assertFalse(self.receipt.is_verified)


class EnrollmentTransitionIsAuditedTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="tr-owner", email="tr-owner@example.com", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="tr-student", email="tr-student@example.com", password="x"
        )
        self.course = Course.objects.create(
            title="Transition Course", description="A2", instructor=self.owner, level="beginner"
        )
        self.source_cohort = Cohort.objects.create(
            name="Manba guruh", course=self.course, start_date="2026-01-01", is_active=True
        )
        self.target_cohort = Cohort.objects.create(
            name="Maqsad guruh", course=self.course, start_date="2026-02-01", is_active=True
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.source_cohort, status=Enrollment.STATUS_ACTIVE
        )

    def test_a_transfer_is_written_to_the_ledger(self):
        transfer_enrollment_to_cohort(
            source_enrollment=self.enrollment,
            target_cohort=self.target_cohort,
            created_by=self.owner,
            note="jadval mos kelmadi",
        )

        event = SystemAuditEvent.objects.get(action="enrollment.transfer")
        self.assertEqual(event.actor_label, "tr-owner")
        self.assertEqual(event.reason, "jadval mos kelmadi")
        self.assertEqual(event.before["cohort"], "Manba guruh")
        self.assertEqual(event.after["cohort"], "Maqsad guruh")

    def test_a_promotion_is_written_to_the_ledger(self):
        next_course = Course.objects.create(
            title="Keyingi kurs", description="A2", instructor=self.owner, level="beginner"
        )
        next_cohort = Cohort.objects.create(
            name="Keyingi guruh", course=next_course, start_date="2026-03-01", is_active=True
        )
        self.enrollment.completion_state = Enrollment.COMPLETION_STATE_PROMOTION_READY
        self.enrollment.save(update_fields=["completion_state"])

        promote_enrollment_to_cohort(
            source_enrollment=self.enrollment,
            target_cohort=next_cohort,
            created_by=self.owner,
        )

        event = SystemAuditEvent.objects.get(action="enrollment.promote")
        self.assertEqual(event.after["cohort"], "Keyingi guruh")

    def test_a_refused_transition_leaves_no_event(self):
        """Xato bilan to'xtagan amal ledgerni ifloslantirmaydi."""
        from cohorts.transition_service import EnrollmentTransitionError

        with self.assertRaises(EnrollmentTransitionError):
            transfer_enrollment_to_cohort(
                source_enrollment=self.enrollment,
                target_cohort=self.source_cohort,
                created_by=self.owner,
            )

        self.assertEqual(SystemAuditEvent.objects.count(), 0)
