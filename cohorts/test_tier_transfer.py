"""O'quvchini boshqa tarifdagi guruhga ko'chirish.

Audit paytida topilgan bo'shliq. Checkout to'lagan o'quvchiga «Tarifni
almashtirish uchun administrator orqali mos guruhga o'ting» deb yozardi,
ammo administratorda hech qanday yo'l yo'q edi:

* `transfer_enrollment_to_cohort` faqat eski Django admindan chaqirilardi,
  u esa default o'chiq (`ENABLE_LEGACY_ADMIN=False`, `/admin/` → 404);
* funksiyaning o'zi ham tarif almashishini rad etardi —
  `validate_plan_cohort` mavjud tarifni maqsad guruhga solishtirardi;
* butun guruhning tarifini o'zgartirish ham taqiqlangan
  (`A'zolari bor guruhning kursi/tarifi o'zgarmaydi`).

Ya'ni arzondan qimmatga ham, qimmatdan arzonga ham o'tish **hech kim
uchun** mumkin emas edi.

Endi ko'chirish owner qo'lida. Tarif almashishi alohida tasdiq so'raydi,
chunki pulga tegadi: tizim narx farqini hisoblamaydi — yangi tarif joriy
davr oxirigacha ishlaydi va farqni owner odatdagi to'lov oqimi orqali
oladi. Bu ataylab: proration hali qabul qilinmagan product qarori.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import AIPlanPolicy, SystemAuditEvent
from aicontrol.service import resolve_limits
from cohorts.membership_service import transfer_member
from cohorts.models import Cohort, Enrollment
from cohorts.transition_service import (
    EnrollmentTransitionError,
    transfer_enrollment_to_cohort,
)
from courses.models import Course
from subscriptions.models import Plan

User = get_user_model()


class TierTransferFixture:
    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        self.owner = User.objects.create_superuser(
            username="kochirish-owner", email="owner@example.test", password="x"
        )
        self.student = User.objects.create_user(
            username="talaba", email="talaba@example.test", password="x",
            first_name="Aziz", last_name="Aliyev",
        )
        self.course = Course.objects.create(
            title="Kurs", description="d", level="beginner", instructor=self.owner
        )
        self.cheap = Plan.objects.create(
            code="kochirish-economic", name="Economic", price=89000,
            description="d", cohort_capacity_limit=60,
        )
        self.rich = Plan.objects.create(
            code="kochirish-intensive", name="Intensive", price=399000,
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


class TierTransferServiceTests(TierTransferFixture, TestCase):
    def test_a_tier_change_is_refused_unless_it_is_deliberate(self):
        """Sukut bo'yicha rad etiladi: bu qadam pulga tegadi."""
        with self.assertRaises(EnrollmentTransitionError):
            transfer_enrollment_to_cohort(
                source_enrollment=self.enrollment,
                target_cohort=self.rich_cohort,
                created_by=self.owner,
            )

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.STATUS_ACTIVE)
        self.assertEqual(self.enrollment.cohort_id, self.cheap_cohort.pk)

    def test_moving_up_a_tier_carries_the_membership_and_the_deadline(self):
        result = transfer_enrollment_to_cohort(
            source_enrollment=self.enrollment,
            target_cohort=self.rich_cohort,
            created_by=self.owner,
            allow_tier_change=True,
        )

        target = result.target_enrollment
        self.assertEqual(target.cohort_id, self.rich_cohort.pk)
        self.assertEqual(target.plan_id, self.rich.pk)
        self.assertEqual(target.status, Enrollment.STATUS_ACTIVE)
        self.assertEqual(target.next_payment_deadline, self.enrollment.next_payment_deadline)

    def test_moving_down_a_tier_works_the_same_way(self):
        """Qimmatdan arzonga o'tish ham xuddi shu yo'l bilan."""
        rich_member = Enrollment.objects.create(
            student=User.objects.create_user(
                username="qimmat", email="qimmat@example.test", password="x"
            ),
            cohort=self.rich_cohort, plan=self.rich, status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=self.today + datetime.timedelta(days=20),
        )

        result = transfer_enrollment_to_cohort(
            source_enrollment=rich_member, target_cohort=self.cheap_cohort,
            created_by=self.owner, allow_tier_change=True,
        )

        self.assertEqual(result.target_enrollment.plan_id, self.cheap.pk)

    def test_the_old_membership_is_frozen_and_releases_its_seat(self):
        transfer_enrollment_to_cohort(
            source_enrollment=self.enrollment, target_cohort=self.rich_cohort,
            created_by=self.owner, allow_tier_change=True,
        )

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.STATUS_FROZEN)
        self.assertEqual(Cohort.objects.get(pk=self.cheap_cohort.pk).occupied_seats, 0)

    def test_the_ai_quota_follows_the_new_tier(self):
        """Nima uchun bu qadam pulga tegadi — o'lchov."""
        AIPlanPolicy.objects.create(
            plan=self.cheap, token_limit_5h=50_000, token_limit_weekly=300_000, is_active=True
        )
        AIPlanPolicy.objects.create(
            plan=self.rich, token_limit_5h=200_000, token_limit_weekly=1_500_000, is_active=True
        )
        self.assertEqual(resolve_limits(self.student), (50_000, 300_000))

        transfer_enrollment_to_cohort(
            source_enrollment=self.enrollment, target_cohort=self.rich_cohort,
            created_by=self.owner, allow_tier_change=True,
        )

        self.assertEqual(resolve_limits(self.student), (200_000, 1_500_000))

    def test_a_full_target_group_refuses_the_move(self):
        for index in range(3):
            Enrollment.objects.create(
                student=User.objects.create_user(
                    username=f"band{index}", email=f"band{index}@example.test", password="x"
                ),
                cohort=self.rich_cohort, plan=self.rich, status=Enrollment.STATUS_ACTIVE,
                next_payment_deadline=self.today + datetime.timedelta(days=20),
            )

        with self.assertRaises(EnrollmentTransitionError):
            transfer_enrollment_to_cohort(
                source_enrollment=self.enrollment, target_cohort=self.rich_cohort,
                created_by=self.owner, allow_tier_change=True,
            )

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.cohort_id, self.cheap_cohort.pk)


class TierTransferOwnerSurfaceTests(TierTransferFixture, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("backoffice_cohort_members", args=[self.cheap_cohort.pk])

    def _post(self, **changes):
        payload = {
            "action": "transfer",
            "enrollment_id": self.enrollment.pk,
            "target_cohort": self.rich_cohort.pk,
            "change_reason": "o'quvchi qimmatroq tarifga o'tmoqchi",
            "confirm_change": "on",
            "allow_tier_change": "on",
        }
        payload.update(changes)
        payload = {key: value for key, value in payload.items() if value is not None}
        return self.client.post(self.url, payload)

    def test_a_student_cannot_move_anyone(self):
        self.client.force_login(self.student)

        self._post()

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.cohort_id, self.cheap_cohort.pk)

    def test_the_owner_can_move_a_student_to_another_tier(self):
        self.client.force_login(self.owner)

        response = self.client.get(self.url)
        self.assertContains(response, "Boshqa guruhga ko'chirish")

        self._post()

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.STATUS_FROZEN)
        self.assertTrue(
            Enrollment.objects.filter(
                student=self.student, cohort=self.rich_cohort, plan=self.rich
            ).exists()
        )

    def test_without_the_tier_acknowledgement_nothing_moves(self):
        self.client.force_login(self.owner)

        self._post(allow_tier_change=None)

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.cohort_id, self.cheap_cohort.pk)

    def test_without_a_reason_nothing_moves(self):
        self.client.force_login(self.owner)

        self._post(change_reason="")

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.cohort_id, self.cheap_cohort.pk)

    def test_the_move_is_audited_with_its_reason(self):
        self.client.force_login(self.owner)

        self._post()

        event = SystemAuditEvent.objects.filter(action="enrollment.transfer").latest("id")
        self.assertEqual(event.actor, self.owner)
        self.assertIn("qimmatroq tarifga", event.reason)

    def test_a_refused_move_is_audited_too(self):
        self.client.force_login(self.owner)
        transfer_member(
            self.enrollment.pk, self.rich_cohort.pk, self.owner,
            reason="tasdiqsiz urinish",
        )

        event = SystemAuditEvent.objects.filter(action="enrollment.transfer").latest("id")
        self.assertEqual(event.outcome, SystemAuditEvent.OUTCOME_FAILURE)
