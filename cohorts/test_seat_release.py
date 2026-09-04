"""Owner joyni o'zi bo'shata oladi.

Audit paytida topilgan bo'shliq: joyni band qiladigan a'zolik faqat
**avtomatik** o'zgarardi — to'lov tasdiqlansa `active`, muddati o'tsa
`expired`. Odam qaror qiladigan yagona yo'l eski Django admin edi, u esa
default o'chiq (`ENABLE_LEGACY_ADMIN=False`, `/admin/` → 404), va `frozen`
holati faqat guruhdan guruhga ko'chirishning yon ta'siri sifatida
qo'yilardi.

Ya'ni muddati o'tgan a'zolik joyni saqlab qolardi (bu ataylab — bir kun
kechikkan o'quvchi o'rnini yo'qotmasligi kerak), ammo qaytmaydigan
o'quvchining joyini **hech kim bo'shata olmasdi**. Guruh to'lib qolib
sotuvni jimgina to'xtatardi.

Ikkita himoya ataylab tekshiriladi: to'lovi amal qiladigan o'quvchining
joyi bo'shatilmaydi, va bo'shagan joy sotilgan bo'lsa a'zolik jimgina
qaytarilmaydi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from cohorts.membership_service import release_seat, restore_seat
from cohorts.models import Cohort, Enrollment
from courses.models import Course
from subscriptions.models import Plan
from users.models import Notification

User = get_user_model()


class SeatReleaseTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.owner = User.objects.create_superuser(
            username="joy-owner", email="owner@example.test", password="x"
        )
        self.course = Course.objects.create(title="Kurs", description="d", level="beginner")
        self.plan = Plan.objects.create(
            code="seat-intensive", name="Intensive", price=399000,
            description="d", cohort_capacity_limit=3,
        )
        self.cohort = Cohort.objects.create(
            name="Guruh", course=self.course, start_date=self.today,
            plan=self.plan, capacity=1,
        )

    def _member(self, username, *, status, lapsed_days):
        student = User.objects.create_user(
            username=username, email=f"{username}@example.test", password="x"
        )
        return Enrollment.objects.create(
            student=student, cohort=self.cohort, plan=self.plan, status=status,
            next_payment_deadline=self.today - datetime.timedelta(days=lapsed_days),
        )

    # ---------------------------------------------------------- bo'shatish

    def test_releasing_a_lapsed_membership_frees_the_seat(self):
        member = self._member("ketgan", status=Enrollment.STATUS_EXPIRED, lapsed_days=200)
        self.assertTrue(self.cohort.is_full)

        decision = release_seat(member.id, self.owner, reason="yarim yil to'lamadi")

        member.refresh_from_db()
        self.assertTrue(decision.ok, decision.message)
        self.assertEqual(member.status, Enrollment.STATUS_FROZEN)
        self.assertEqual(Cohort.objects.get(pk=self.cohort.pk).occupied_seats, 0)

    def test_a_paying_member_keeps_the_seat(self):
        """Eng muhim himoya: to'lagan o'quvchining kirishi tasodifan uzilmasin."""
        member = self._member("tolayotgan", status=Enrollment.STATUS_ACTIVE, lapsed_days=-10)

        decision = release_seat(member.id, self.owner, reason="xato bosildi")

        member.refresh_from_db()
        self.assertFalse(decision.ok)
        self.assertEqual(decision.code, "access_open")
        self.assertEqual(member.status, Enrollment.STATUS_ACTIVE)

    def test_a_member_inside_the_grace_period_keeps_the_seat(self):
        member = self._member("kechikkan", status=Enrollment.STATUS_ACTIVE, lapsed_days=1)

        self.assertFalse(release_seat(member.id, self.owner, reason="hali erta").ok)
        member.refresh_from_db()
        self.assertEqual(member.status, Enrollment.STATUS_ACTIVE)

    def test_releasing_twice_is_harmless(self):
        member = self._member("ketgan", status=Enrollment.STATUS_EXPIRED, lapsed_days=200)
        release_seat(member.id, self.owner, reason="birinchi")

        decision = release_seat(member.id, self.owner, reason="ikkinchi")

        self.assertTrue(decision.ok)
        self.assertEqual(decision.code, "already")

    def test_the_decision_is_audited_with_its_reason(self):
        member = self._member("ketgan", status=Enrollment.STATUS_EXPIRED, lapsed_days=200)

        release_seat(member.id, self.owner, reason="yarim yil to'lamadi")

        event = SystemAuditEvent.objects.filter(action="membership.release").latest("id")
        self.assertEqual(event.actor, self.owner)
        self.assertIn("yarim yil to'lamadi", event.reason)

    def test_the_learner_is_told(self):
        member = self._member("ketgan", status=Enrollment.STATUS_EXPIRED, lapsed_days=200)

        release_seat(member.id, self.owner, reason="yarim yil to'lamadi")

        self.assertTrue(
            Notification.objects.filter(
                recipient=member.student, category=Notification.CATEGORY_SUBSCRIPTION
            ).exists()
        )

    # ------------------------------------------------------------ ruxsat

    def test_a_student_cannot_free_a_seat(self):
        member = self._member("ketgan", status=Enrollment.STATUS_EXPIRED, lapsed_days=200)
        outsider = User.objects.create_user(
            username="chetdagi", email="chetdagi@example.test", password="x"
        )

        decision = release_seat(member.id, outsider, reason="men xohladim")

        member.refresh_from_db()
        self.assertFalse(decision.ok)
        self.assertEqual(member.status, Enrollment.STATUS_EXPIRED)

    def test_a_denied_attempt_is_audited(self):
        member = self._member("ketgan", status=Enrollment.STATUS_EXPIRED, lapsed_days=200)
        outsider = User.objects.create_user(
            username="chetdagi", email="chetdagi@example.test", password="x"
        )

        release_seat(member.id, outsider, reason="men xohladim")

        event = SystemAuditEvent.objects.filter(action="membership.release").latest("id")
        self.assertEqual(event.outcome, SystemAuditEvent.OUTCOME_DENIED)

    # ---------------------------------------------------------- qaytarish

    def test_a_released_membership_can_be_restored_while_the_seat_is_free(self):
        member = self._member("ketgan", status=Enrollment.STATUS_EXPIRED, lapsed_days=200)
        release_seat(member.id, self.owner, reason="to'lamadi")

        decision = restore_seat(member.id, self.owner, reason="xato muzlatilgan edi")

        member.refresh_from_db()
        self.assertTrue(decision.ok, decision.message)
        self.assertEqual(member.status, Enrollment.STATUS_EXPIRED)

    def test_restoring_is_refused_once_the_freed_seat_was_sold(self):
        """Bo'shatilgan joy sotilgan bo'lsa, a'zolik jimgina sig'imdan oshmaydi."""
        member = self._member("ketgan", status=Enrollment.STATUS_EXPIRED, lapsed_days=200)
        release_seat(member.id, self.owner, reason="to'lamadi")
        self._member("yangi", status=Enrollment.STATUS_ACTIVE, lapsed_days=-30)

        decision = restore_seat(member.id, self.owner, reason="qaytaramiz")

        member.refresh_from_db()
        self.assertFalse(decision.ok)
        self.assertEqual(member.status, Enrollment.STATUS_FROZEN)


class SeatReleasePageTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.owner = User.objects.create_superuser(
            username="sahifa-owner", email="owner@example.test", password="x"
        )
        self.student = User.objects.create_user(
            username="ketgan", email="ketgan@example.test", password="x"
        )
        course = Course.objects.create(title="Kurs", description="d", level="beginner")
        self.cohort = Cohort.objects.create(
            name="Guruh", course=course, start_date=self.today
        )
        self.member = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_EXPIRED,
            next_payment_deadline=self.today - datetime.timedelta(days=200),
        )
        self.url = reverse("backoffice_cohort_members", args=[self.cohort.pk])

    def _post(self, action="release", *, reason="to'lamayapti", confirm=True):
        payload = {"enrollment_id": self.member.pk, "action": action, "change_reason": reason}
        if confirm:
            payload["confirm_change"] = "on"
        return self.client.post(self.url, payload)

    def test_a_student_cannot_open_the_page(self):
        self.client.force_login(self.student)

        self.assertNotEqual(self.client.get(self.url).status_code, 200)

    def test_a_student_cannot_free_a_seat_by_posting_directly(self):
        self.client.force_login(self.student)

        self._post()

        self.member.refresh_from_db()
        self.assertEqual(self.member.status, Enrollment.STATUS_EXPIRED)

    def test_the_owner_sees_the_members_and_can_free_the_seat(self):
        self.client.force_login(self.owner)

        response = self.client.get(self.url)
        self.assertContains(response, "Joyni bo'shatish")

        self._post()

        self.member.refresh_from_db()
        self.assertEqual(self.member.status, Enrollment.STATUS_FROZEN)

    def test_a_decision_without_a_reason_is_not_applied(self):
        self.client.force_login(self.owner)

        self._post(reason="")

        self.member.refresh_from_db()
        self.assertEqual(self.member.status, Enrollment.STATUS_EXPIRED)

    def test_a_decision_without_confirmation_is_not_applied(self):
        self.client.force_login(self.owner)

        self._post(confirm=False)

        self.member.refresh_from_db()
        self.assertEqual(self.member.status, Enrollment.STATUS_EXPIRED)
