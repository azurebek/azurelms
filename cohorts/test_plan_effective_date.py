"""Tarif o'zi to'langan davr boshlanganda kuchga kiradi.

Audit paytida topilgan pul teshigi. Yangilash to'lovi joriy muddat
tugaganidan boshlanadi (`checkout_service.checkout_period`), ammo chek
tasdiqlanishi bilanoq `Enrollment.plan` almashardi. Natija:

* **qimmatroqqa o'tish** — kelasi oy uchun to'langan tarif bugundan ishlay
  boshlardi. Muddatiga 10 kun qolgan o'quvchi 30 kunlik pulga 40 kunlik AI
  kvotasi va o'qituvchi vaqtini olardi. Buni ataylab ham qilish mumkin edi:
  muddat boshida yangilab, eng qimmat tarifni deyarli ikki barobar uzoq
  ishlatish;
* **arzonroqqa o'tish** — aksincha, o'quvchi allaqachon to'lagan kunlarini
  yo'qotardi.

Ikkalasi ham bitta sababdan: qaror vaqti (tasdiqlash) bilan xizmat vaqti
(to'langan davr) aralashib ketgan edi. Endi ular ajratilgan.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from aicontrol.models import AIPlanPolicy, AISettings
from aicontrol.service import resolve_limits
from cohorts.checkout_service import checkout_period
from cohorts.enrollment_service import promote_due_plans
from cohorts.models import Cohort, Enrollment, PaymentReceipt
from cohorts.receipt_service import verify_receipt
from courses.models import Course
from subscriptions.models import Plan
from subscriptions.promo_service import create_checkout_receipt_with_promo

User = get_user_model()


class PlanEffectiveDateTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.owner = User.objects.create_superuser(
            username="tarif-owner", email="owner@example.test", password="x"
        )
        self.student = User.objects.create_user(
            username="tarif-student", email="student@example.test", password="x"
        )
        course = Course.objects.create(title="Kurs", description="d", level="beginner")
        self.cohort = Cohort.objects.create(
            name="Guruh", course=course, start_date=self.today
        )
        # This is the pre-catalog legacy renewal contract (same cohort may
        # change price tier). New delivery cohorts have an explicit tier.
        self.cheap = Plan.objects.create(code="legacy-economic", name="Economic", price=89000, description="d")
        self.rich = Plan.objects.create(code="legacy-intensive", name="Intensive", price=399000, description="d")

    def _renewing_enrollment(self, *, plan, days_left=10):
        """Faol obuna: muddati tugashiga `days_left` kun qolgan."""
        return Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
            plan=plan,
            next_payment_deadline=self.today + datetime.timedelta(days=days_left),
        )

    def _buy(self, enrollment, plan):
        start, end = checkout_period(enrollment)
        receipt, _, _ = create_checkout_receipt_with_promo(
            enrollment=enrollment, plan=plan, receipt_image=None,
            period_start=start, period_end=end,
        )
        decision = verify_receipt(receipt.id, self.owner)
        self.assertTrue(decision.ok, decision.message)
        enrollment.refresh_from_db()
        return receipt

    # ------------------------------------------------- oldindan to'lash

    def test_paying_for_the_next_period_does_not_upgrade_access_today(self):
        enrollment = self._renewing_enrollment(plan=self.cheap)

        self._buy(enrollment, self.rich)

        self.assertEqual(enrollment.active_plan().code, "legacy-economic")
        self.assertEqual(enrollment.plan_id, self.cheap.id)

    def test_the_paid_plan_takes_effect_when_its_period_starts(self):
        """Cron ishlamasa ham o'quvchi to'lagan narsasini oladi."""
        enrollment = self._renewing_enrollment(plan=self.cheap, days_left=10)

        receipt = self._buy(enrollment, self.rich)

        self.assertEqual(enrollment.active_plan(today=receipt.period_start).code, "legacy-intensive")

    def test_the_payment_still_extends_the_deadline_right_away(self):
        """Tarif kutadi, pul emas: to'lov muddatni darhol uzaytiradi."""
        enrollment = self._renewing_enrollment(plan=self.cheap)

        receipt = self._buy(enrollment, self.rich)

        self.assertEqual(enrollment.next_payment_deadline, receipt.period_end)
        self.assertEqual(enrollment.status, Enrollment.STATUS_ACTIVE)

    def test_moving_to_a_cheaper_plan_does_not_cut_the_days_already_paid_for(self):
        enrollment = self._renewing_enrollment(plan=self.rich)

        self._buy(enrollment, self.cheap)

        self.assertEqual(enrollment.active_plan().code, "legacy-intensive")

    # ------------------------------------------------------ birinchi xarid

    def test_a_first_purchase_takes_effect_immediately(self):
        """Muddati yo'q obunada davr bugundan boshlanadi — kutish yo'q."""
        enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_PENDING
        )

        self._buy(enrollment, self.rich)

        self.assertEqual(enrollment.plan_id, self.rich.id)
        self.assertEqual(enrollment.active_plan().code, "legacy-intensive")

    # --------------------------------------------------------- AI kvotasi

    def test_ai_limits_follow_the_effective_plan_not_the_prepaid_one(self):
        """Teshikning aslida qimmatga tushadigan joyi."""
        AISettings.load()
        AIPlanPolicy.objects.create(
            plan=self.cheap, token_limit_5h=50_000, token_limit_weekly=300_000, is_active=True
        )
        AIPlanPolicy.objects.create(
            plan=self.rich, token_limit_5h=200_000, token_limit_weekly=1_500_000, is_active=True
        )
        enrollment = self._renewing_enrollment(plan=self.cheap)

        self._buy(enrollment, self.rich)

        self.assertEqual(resolve_limits(self.student), (50_000, 300_000))

    # ----------------------------------------------------- denormalizatsiya

    def test_the_daily_service_materialises_the_plan_once_its_period_starts(self):
        enrollment = self._renewing_enrollment(plan=self.cheap)
        receipt = self._buy(enrollment, self.rich)

        promoted = promote_due_plans(today=receipt.period_start)

        enrollment.refresh_from_db()
        self.assertEqual(promoted, 1)
        self.assertEqual(enrollment.plan_id, self.rich.id)

    def test_the_daily_service_does_not_promote_a_period_that_has_not_started(self):
        enrollment = self._renewing_enrollment(plan=self.cheap)
        self._buy(enrollment, self.rich)

        self.assertEqual(promote_due_plans(today=self.today), 0)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.plan_id, self.cheap.id)

    # ---------------------------------------------------------- eski yozuv

    def test_a_legacy_receipt_without_a_plan_falls_back_to_the_enrollment_plan(self):
        """`cohorts.0016`dan oldingi cheklarda tarif snapshoti yo'q."""
        enrollment = self._renewing_enrollment(plan=self.cheap)
        PaymentReceipt.objects.create(
            enrollment=enrollment, amount=89000, is_verified=True,
            period_start=self.today - datetime.timedelta(days=5),
            period_end=self.today + datetime.timedelta(days=25),
        )

        self.assertEqual(enrollment.active_plan().code, "legacy-economic")
