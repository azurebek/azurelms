"""To'lamayotgan a'zo joyni ushlab turishi ko'rinib turadi.

Muddati o'tgan a'zolik ataylab guruhda qoladi: bir kun kechikkan o'quvchi
o'z o'rnini boshqa odamga berib qo'ymasligi kerak. Ammo joy hech qachon
avtomatik bo'shamaydi, ya'ni qaytmaydigan o'quvchi uni **abadiy** ushlab
turadi va guruh jimgina sotuvni to'xtatadi.

O'lchov: sig'imi 2 bo'lgan Intensive guruhda 200 kun oldin to'lashni
to'xtatgan ikki o'quvchi bor bo'lsa, yangi mijoz "Guruh to'ldi" javobini
oladi. Owner backoffice'da 2 / 2 raqamini ko'radi va bu joylarni kim
egallab turganini bilmaydi — sotuv yo'qolgani sezilmaydi.

Bu yerda siyosat o'zgarmaydi: joy avtomatik bo'shatilmaydi. Faqat fakt
ko'rsatiladi, qaror ownerda qoladi (a'zolikni muzlatish joyni bo'shatadi).
"""

import datetime

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from cohorts.checkout_service import CheckoutUnavailable, find_checkout_enrollment
from cohorts.models import Cohort, Enrollment
from courses.models import Course
from subscriptions.models import Plan

User = get_user_model()


class StaleSeatTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.course = Course.objects.create(title="Kurs", description="d", level="beginner")
        self.plan = Plan.objects.create(
            code="stale-intensive", name="Intensive", price=399000, description="d",
        )
        self.cohort = Cohort.objects.create(
            name="Guruh", course=self.course, start_date=self.today, capacity=None,
        )

    def _member(self, username, *, status, deadline, plan=None):
        student = User.objects.create_user(
            username=username, email=f"{username}@example.test", password="x"
        )
        return Enrollment.objects.create(
            student=student, cohort=self.cohort, plan=plan or self.plan,
            status=status, next_payment_deadline=deadline,
        )

    # ------------------------------------------------------------ hisoblash

    def test_a_paying_member_is_not_stale(self):
        self._member(
            "tolayotgan", status=Enrollment.STATUS_ACTIVE,
            deadline=self.today + datetime.timedelta(days=10),
        )

        self.assertEqual(self.cohort.occupied_seats, 1)
        self.assertEqual(self.cohort.stale_seats, 0)

    def test_an_expired_member_still_holds_a_seat_and_is_reported(self):
        self._member(
            "ketgan", status=Enrollment.STATUS_EXPIRED,
            deadline=self.today - datetime.timedelta(days=200),
        )

        self.assertEqual(self.cohort.occupied_seats, 1)
        self.assertEqual(self.cohort.stale_seats, 1)
        self.assertEqual(self.cohort.longest_lapse_days, 200)

    def test_a_member_inside_the_grace_period_is_not_stale_yet(self):
        """Bir kun kechikkan o'quvchi hali kirishi ochiq — u \"ketgan\" emas."""
        self._member(
            "kechikkan", status=Enrollment.STATUS_ACTIVE,
            deadline=self.today - datetime.timedelta(days=1),
        )

        self.assertEqual(self.cohort.stale_seats, 0)

    def test_a_member_past_the_grace_period_is_stale_even_while_still_marked_active(self):
        """Kunlik xizmat hali yugurmagan bo'lsa ham holat to'g'ri ko'rinadi."""
        self._member(
            "yugurmagan", status=Enrollment.STATUS_ACTIVE,
            deadline=self.today - datetime.timedelta(days=30),
        )

        self.assertEqual(self.cohort.stale_seats, 1)

    def test_a_frozen_member_holds_no_seat_at_all(self):
        self._member(
            "muzlatilgan", status=Enrollment.STATUS_FROZEN,
            deadline=self.today - datetime.timedelta(days=200),
        )

        self.assertEqual(self.cohort.occupied_seats, 0)
        self.assertEqual(self.cohort.stale_seats, 0)

    def test_no_stale_member_means_no_lapse_figure(self):
        self._member(
            "tolayotgan", status=Enrollment.STATUS_ACTIVE,
            deadline=self.today + datetime.timedelta(days=10),
        )

        self.assertIsNone(self.cohort.longest_lapse_days)

    # ------------------------------------------------------------- oqibati

    def test_stale_members_can_fill_a_cohort_and_stop_new_sales(self):
        """Nega bu ko'rsatiladi: yo'qolgan sotuv boshqa hech qayerda ko'rinmaydi."""
        # `Plan.cohort_capacity_limit` yaratilgandan keyin o'zgarmaydi,
        # shuning uchun delivery tarifi va guruhi darhol shunday yaratiladi.
        tiered_plan = Plan.objects.create(
            code="stale-delivery", name="Intensive delivery", price=399000,
            description="d", cohort_capacity_limit=3,
        )
        self.cohort = Cohort.objects.create(
            name="Delivery guruh", course=self.course, start_date=self.today,
            plan=tiered_plan, capacity=2,
        )
        for index in range(2):
            self._member(
                f"ketgan{index}", status=Enrollment.STATUS_EXPIRED,
                deadline=self.today - datetime.timedelta(days=200),
                plan=tiered_plan,
            )
        newcomer = User.objects.create_user(
            username="yangi", email="yangi@example.test", password="x"
        )

        with self.assertRaises(CheckoutUnavailable):
            find_checkout_enrollment(student=newcomer, course=self.course, plan=tiered_plan)

        self.assertTrue(self.cohort.is_full)
        self.assertEqual(self.cohort.stale_seats, 2)


class CatalogPageShowsStaleSeatsTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.owner = User.objects.create_superuser(
            username="katalog-owner", email="owner@example.test", password="x"
        )
        course = Course.objects.create(title="Kurs", description="d", level="beginner")
        self.cohort = Cohort.objects.create(
            name="Guruh", course=course, start_date=self.today
        )
        student = User.objects.create_user(
            username="ketgan", email="ketgan@example.test", password="x"
        )
        Enrollment.objects.create(
            student=student, cohort=self.cohort, status=Enrollment.STATUS_EXPIRED,
            next_payment_deadline=self.today - datetime.timedelta(days=214),
        )

    def _another_stale_cohort(self, index):
        course = Course.objects.create(
            title=f"Kurs {index}", description="d", level="beginner"
        )
        cohort = Cohort.objects.create(
            name=f"Guruh {index}", course=course, start_date=self.today
        )
        student = User.objects.create_user(
            username=f"ketgan{index}", email=f"ketgan{index}@example.test", password="x"
        )
        Enrollment.objects.create(
            student=student, cohort=cohort, status=Enrollment.STATUS_EXPIRED,
            next_payment_deadline=self.today - datetime.timedelta(days=100 + index),
        )

    def test_the_owner_sees_who_is_holding_the_seat(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("backoffice_catalog"))

        self.assertContains(response, "tasi to'lamayapti")
        self.assertContains(response, "214 kun")

    def test_the_page_cost_does_not_grow_with_the_number_of_cohorts(self):
        """Ko'rsatkichlar xossa bo'lgani uchun har qator o'z so'rovini yugurtirardi.

        Sahifa ownerga ochiq va guruhlar vaqt o'tishi bilan yig'iladi, ya'ni
        qator boshiga so'rov sekin-asta sezilarli bo'lardi. Shuning uchun
        o'lchov: guruhlar soni ortganda so'rovlar soni **o'zgarmasligi** kerak.
        """
        self.client.force_login(self.owner)
        url = reverse("backoffice_catalog")
        self.client.get(url)  # sessiya/auth so'rovlarini isitib qo'yish
        with CaptureQueriesContext(connection) as single:
            self.client.get(url)

        for index in range(4):
            self._another_stale_cohort(index)

        with CaptureQueriesContext(connection) as many:
            response = self.client.get(url)

        self.assertContains(response, "tasi to'lamayapti")
        self.assertEqual(len(many.captured_queries), len(single.captured_queries))
