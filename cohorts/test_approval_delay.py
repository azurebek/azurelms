"""Tasdiqlash kechikkani uchun to'langan kunlar yo'qolmaydi.

To'lov davri chek yuborilgan kuni hisoblanadi, tasdiqlash esa qo'lda:
owner bank o'tkazmasini bir necha soatdan bir necha kungacha keyin
ko'radi. Ilgari muddat to'g'ridan-to'g'ri chekdagi davr oxiriga
qo'yilardi, ya'ni kirishi yopiq turgan o'quvchi kutgan kunlarini
yo'qotardi: 3 kun kutgan bo'lsa, 30 kunlik pulga 27 kun olardi.

Bu `test_plan_effective_date.py` dagi nuqsonning ko'zgudagi aksi. U yerda
tizim o'quvchiga to'lanmagan kunlarni **berardi**, bu yerda esa to'langan
kunlarni **olib qolardi**. Ikkalasining sababi bitta: qaror vaqti bilan
xizmat vaqti bir narsa deb qaralgan edi.

Kirishi ochiq turgan o'quvchi hech narsa yo'qotmaydi — unga kechikish
uchun qo'shimcha kun berilmaydi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from cohorts.models import Cohort, Enrollment, PaymentReceipt
from cohorts.receipt_service import verify_receipt
from courses.models import Course
from subscriptions.models import Plan
from subscriptions.promo_service import create_checkout_receipt_with_promo

User = get_user_model()


class ApprovalDelayTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.owner = User.objects.create_superuser(
            username="kechikish-owner", email="owner@example.test", password="x"
        )
        self.student = User.objects.create_user(
            username="kechikish-student", email="student@example.test", password="x"
        )
        course = Course.objects.create(title="Kurs", description="d", level="beginner")
        self.cohort = Cohort.objects.create(
            name="Guruh", course=course, start_date=self.today
        )
        self.plan = Plan.objects.create(
            code="standard", name="Standard", price=259000, description="d"
        )

    def _submit(self, enrollment, *, days_ago=0, days=30):
        """Chek `days_ago` kun oldin yuborilgan deb hisoblanadi."""
        start = self.today - datetime.timedelta(days=days_ago)
        receipt, _, _ = create_checkout_receipt_with_promo(
            enrollment=enrollment, plan=self.plan, receipt_image=None,
            period_start=start, period_end=start + datetime.timedelta(days=days),
        )
        return receipt

    # ------------------------------------------------- kirishi yopiq bo'lgan

    def test_a_first_purchase_gets_the_full_period_from_the_day_access_opens(self):
        enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_PENDING
        )
        receipt = self._submit(enrollment, days_ago=3)
        self.assertFalse(enrollment.has_active_access())

        verify_receipt(receipt.id, self.owner)

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.next_payment_deadline, self.today + datetime.timedelta(days=30))

    def test_a_lapsed_subscription_also_gets_its_full_period(self):
        enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_EXPIRED,
            plan=self.plan, next_payment_deadline=self.today - datetime.timedelta(days=20),
        )
        receipt = self._submit(enrollment, days_ago=2)

        verify_receipt(receipt.id, self.owner)

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.next_payment_deadline, self.today + datetime.timedelta(days=30))

    def test_same_day_approval_is_unchanged(self):
        enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_PENDING
        )
        receipt = self._submit(enrollment, days_ago=0)

        verify_receipt(receipt.id, self.owner)

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.next_payment_deadline, receipt.period_end)

    # -------------------------------------------------- kirishi ochiq bo'lgan

    def test_a_delay_is_not_a_gift_while_access_stayed_open(self):
        """Grace ichida tasdiqlangan yangilash qo'shimcha kun bermaydi."""
        enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
            plan=self.plan, next_payment_deadline=self.today - datetime.timedelta(days=1),
        )
        self.assertTrue(enrollment.has_active_access())
        receipt = self._submit(enrollment, days_ago=4)

        verify_receipt(receipt.id, self.owner)

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.next_payment_deadline, receipt.period_end)

    def test_a_renewal_paid_in_advance_still_stacks_on_the_current_period(self):
        enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
            plan=self.plan, next_payment_deadline=self.today + datetime.timedelta(days=10),
        )
        start = self.today + datetime.timedelta(days=10)
        receipt, _, _ = create_checkout_receipt_with_promo(
            enrollment=enrollment, plan=self.plan, receipt_image=None,
            period_start=start, period_end=start + datetime.timedelta(days=30),
        )

        verify_receipt(receipt.id, self.owner)

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.next_payment_deadline, receipt.period_end)

    # ------------------------------------------------------------ eski yozuv

    def test_a_receipt_without_a_period_keeps_the_thirty_day_default(self):
        enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_PENDING
        )
        receipt = PaymentReceipt.objects.create(enrollment=enrollment, amount=259000)

        verify_receipt(receipt.id, self.owner)

        enrollment.refresh_from_db()
        self.assertEqual(enrollment.next_payment_deadline, self.today + datetime.timedelta(days=30))
