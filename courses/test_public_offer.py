"""PUB1.3b — ochiq kurs taklifi checkout bilan bir manbadan.

Sahifa “qabul ochiq” desa, checkout aynan shu tarif uchun aynan shu guruhni
tanlaydi va aynan shu narx/davrni ko'rsatadi; “yopiq” desa, checkout ham
qabul qilmaydi. Taklifni ko'rsatish hech narsa yozmaydi va so'rovlar soni
guruh/tarif/kurs soniga bog'liq emas.
"""

import datetime
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag
from cohorts.checkout_service import pick_checkout_cohort
from cohorts.models import Cohort, Enrollment
from courses import public_offer
from courses.models import Course
from subscriptions.models import Plan, PlanFeature


def set_flag(slug, enabled):
    FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": enabled})


def renderers():
    for enabled, name in ((False, "legacy"), (True, "v1")):
        set_flag("frontend_v1_public", enabled)
        yield name


def writes(queries):
    return [q["sql"] for q in queries.captured_queries
            if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))]


class OfferWorld(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.legacy = Plan.objects.create(name="Oddiy", price=Decimal("200000"), order=1)
        PlanFeature.objects.create(plan=self.legacy, name="Darslar", is_included=True, order=1)
        PlanFeature.objects.create(plan=self.legacy, name="Shaxsiy ustoz", is_included=False, order=2)
        self.delivery = Plan.objects.create(name="Guruh", price=Decimal("300000"), order=2, cohort_capacity_limit=10)
        self.archived = Plan.objects.create(name="Arxiv", price=Decimal("1"), order=3, is_available_for_purchase=False)
        self.course = Course.objects.create(title="Kurs", description="<p>d</p>", level="beginner")
        self.User = get_user_model()

    def cohort(self, course=None, **fields):
        fields.setdefault("start_date", self.today)
        fields.setdefault("name", f"Guruh {Cohort.objects.count() + 1}")
        return Cohort.objects.create(course=course or self.course, **fields)

    def member(self, cohort, status=Enrollment.STATUS_ACTIVE, username=None):
        user = self.User.objects.create_user(username or f"a{Enrollment.objects.count()}", email=f"{username or Enrollment.objects.count()}@x.test")
        Enrollment.objects.create(student=user, cohort=cohort, status=status, plan=cohort.plan,
                                  next_payment_deadline=self.today + timedelta(days=10))
        return user

    def offer(self, course=None):
        return public_offer.build_offer(course or self.course)


class ReasonTaxonomyTests(OfferWorld):
    def test_no_cohort_means_not_open_and_no_guessed_date(self):
        offer = self.offer()
        self.assertEqual(offer.reason, public_offer.NOT_OPEN)
        self.assertIsNone(offer.next_start)
        self.assertEqual(offer.active_cohort_count, 0)
        self.assertEqual({plan.reason for plan in offer.plans}, {public_offer.NOT_OPEN})

    def test_open_full_inactive_and_delivery_cohorts(self):
        future = self.cohort(start_date=self.today + timedelta(days=10))
        offer = self.offer()
        self.assertTrue(offer.available)
        self.assertEqual(offer.plan(self.legacy.pk).cohort_id, future.pk)
        self.assertTrue(offer.starts_later)
        self.assertEqual(offer.plan(self.delivery.pk).reason, public_offer.NOT_OPEN)  # delivery legacy guruhga tushmaydi

        future.is_active = False
        future.save()
        closed = self.offer()
        self.assertEqual((closed.reason, closed.active_cohort_count), (public_offer.NOT_OPEN, 0))

        # Sig'im faqat delivery guruhda bo'ladi: to'lsa — FULL, joy bo'lsa — davom etayotgan guruh.
        group = self.cohort(plan=self.delivery, capacity=1, start_date=self.today - timedelta(days=20))
        self.member(group)
        self.assertEqual(self.offer().reason, public_offer.FULL)
        group.capacity = 10
        group.save()
        delivery = self.offer()
        self.assertTrue(delivery.available)
        self.assertTrue(delivery.plan(self.delivery.pk).available)
        self.assertFalse(delivery.starts_later)  # davom etayotgan guruh

    def test_archived_plans_are_not_offered_and_no_sale_plan_means_no_plans(self):
        self.cohort()
        self.assertNotIn(self.archived.pk, [plan.plan_id for plan in self.offer().plans])
        Plan.objects.update(is_available_for_purchase=False)
        self.assertEqual(self.offer().reason, public_offer.NO_PLANS)

    def test_plan_facts_come_from_the_plan_not_the_course_price_field(self):
        self.course.price = Decimal("999")
        self.course.save()
        self.cohort()
        plan = self.offer().plan(self.legacy.pk)
        self.assertEqual(plan.price, Decimal("200000"))
        self.assertEqual(plan.period_days, 30)
        self.assertEqual((plan.included, plan.excluded), (("Darslar",), ("Shaxsiy ustoz",)))
        self.assertEqual(self.offer().plan(self.delivery.pk).group_size_claim, "Maksimum 10 kishilik guruh")

    def test_source_revision_is_stable_and_tracks_inputs(self):
        self.cohort()
        first, again = self.offer(), self.offer()
        self.assertEqual(first.source_revision, again.source_revision)
        Plan.objects.filter(pk=self.legacy.pk).update(price=Decimal("210000"))
        self.assertNotEqual(self.offer().source_revision, first.source_revision)

    def test_local_calendar_day_decides_upcoming(self):
        # 20:30 UTC Toshkentda ertasi kun (UTC+5): o'sha kungi guruh "keyinroq" emas.
        moment = datetime.datetime(2026, 10, 18, 20, 30, tzinfo=datetime.timezone.utc)
        local_day = timezone.localtime(moment).date()
        self.assertEqual(local_day, datetime.date(2026, 10, 19))
        self.cohort(start_date=local_day)
        with mock.patch("django.utils.timezone.now", return_value=moment):
            offer = self.offer()
        self.assertEqual(offer.today, local_day)
        self.assertTrue(offer.available)
        self.assertFalse(offer.starts_later)


class CheckoutEqualityTests(OfferWorld):
    """Har holatda: taklif qarori = checkout qarori (guruh, narx, davr, imkoniyatlar)."""

    def scenarios(self):
        yield "no cohort", lambda: None
        yield "upcoming legacy", lambda: self.cohort(start_date=self.today + timedelta(days=5))
        yield "default and ongoing", lambda: (self.cohort(start_date=self.today - timedelta(days=30)),
                                              self.cohort(start_date=self.today - timedelta(days=60), is_checkout_default=True))
        yield "full delivery", lambda: self.member(self.cohort(plan=self.delivery, capacity=1))
        yield "delivery only", lambda: self.cohort(plan=self.delivery, capacity=3)
        yield "inactive", lambda: self.cohort(is_active=False)

    def test_offer_matches_checkout_selection_and_quote(self):
        buyer = self.User.objects.create_user("xaridor", email="x@x.test")
        compared = refused = 0
        for name, build in self.scenarios():
            Enrollment.objects.all().delete()
            Cohort.objects.all().delete()
            build()
            offer = self.offer()
            for plan in (self.legacy, self.delivery):
                plan_offer = offer.plan(plan.pk)
                expected = pick_checkout_cohort(course=self.course, plan=plan)
                with self.subTest(scenario=name, plan=plan.name):
                    self.assertEqual(plan_offer.cohort_id, expected.pk if expected else None)
                    self.assertEqual(plan_offer.available, expected is not None)
                    for checkout_flag in (True, False):
                        set_flag("frontend_v1_checkout", checkout_flag)
                        self.client.force_login(buyer)
                        url = reverse("cohorts:checkout", kwargs={"course_id": self.course.pk})
                        with CaptureQueriesContext(connection) as queries:
                            response = self.client.get(url, {"plan_id": plan.pk})
                        self.assertEqual(writes(queries), [])
                        if not plan_offer.available:
                            self.assertIn(response.status_code, (302, 400), (checkout_flag, response.status_code))
                            refused += 1
                            continue
                        self.assertEqual(response.status_code, 200)
                        context = response.context
                        self.assertEqual(context["selected_plan"].pk, plan.pk)
                        self.assertEqual(context["checkout_cohort"].pk, plan_offer.cohort_id)
                        self.assertEqual((context["period_end"] - context["period_start"]).days, plan_offer.period_days)
                        shown = Decimal(context["promo_quote"].base_amount) if checkout_flag else context["selected_plan"].price
                        self.assertEqual(shown, plan_offer.price)
                        included = tuple(f.name for f in context["selected_plan"].features.all() if f.is_included)
                        self.assertEqual(sorted(included), sorted(plan_offer.included))
                        compared += 1
        # Ikkala yo'l ham haqiqatan sinaldi: ochiq holatlar narx/davr bilan, yopiqlar rad bilan.
        self.assertGreaterEqual(compared, 6)
        self.assertGreaterEqual(refused, 10)


class CallToActionTests(OfferWorld):
    def detail(self):
        return self.client.get(reverse("course_detail", args=[self.course.pk]))

    def test_unavailable_course_explains_instead_of_bouncing_through_checkout(self):
        checkout = reverse("cohorts:checkout", kwargs={"course_id": self.course.pk})
        stranger = self.User.objects.create_user("begona", email="b@x.test")
        for viewer in (None, stranger):
            if viewer:
                self.client.force_login(viewer)
            for name in renderers():
                response = self.detail()
                with self.subTest(renderer=name, viewer=viewer):
                    self.assertEqual(response.context["offer_cta"].destination, public_offer.CATALOG)
                    self.assertContains(response, "Bu kursga qabul hozircha ochilmagan.")
                    self.assertNotContains(response, checkout)
                    self.assertContains(response, f'href="{reverse("courses")}"')

    def test_open_course_offers_checkout_or_login_and_the_next_start(self):
        start = self.today + timedelta(days=7)
        self.cohort(start_date=start)
        checkout = reverse("cohorts:checkout", kwargs={"course_id": self.course.pk})
        for name in renderers():
            response = self.detail()
            with self.subTest(renderer=name, viewer="guest"):
                cta = response.context["offer_cta"]
                self.assertEqual((cta.destination, cta.auth_required), (public_offer.CHECKOUT, True))
                self.assertContains(response, reverse("login"))
                self.assertContains(response, f"Keyingi guruh: {start:%d.%m.%Y}.")
        self.client.force_login(self.User.objects.create_user("yangi", email="y@x.test"))
        for name in renderers():
            with self.subTest(renderer=name, viewer="member-to-be"):
                self.assertContains(self.detail(), checkout)

    def test_continuing_member_keeps_checkout_when_admission_closes(self):
        cohort = self.cohort()
        member = self.member(cohort, status=Enrollment.STATUS_EXPIRED, username="davomchi")
        cohort.is_active = False
        cohort.save()
        self.client.force_login(member)
        response = self.detail()
        self.assertEqual(response.context["offer_cta"].destination, public_offer.CHECKOUT)
        self.assertEqual(self.client.get(reverse("cohorts:checkout", kwargs={"course_id": self.course.pk})).status_code, 200)

    def test_enrolled_learner_goes_to_study(self):
        member = self.member(self.cohort(), username="oquvchi")
        self.client.force_login(member)
        self.assertEqual(self.detail().context["offer_cta"].destination, public_offer.STUDY)


class OfferCostTests(OfferWorld):
    def queries(self, url):
        self.client.get(url)
        with CaptureQueriesContext(connection) as captured:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(writes(captured), [])
        return len(captured.captured_queries)

    def test_builder_cost_is_constant_for_0_1_8_and_100_courses(self):
        self.assertEqual(public_offer.build_offers([]), {})
        for count in (1, 8, 100):
            Cohort.objects.all().delete()
            Course.objects.exclude(pk=self.course.pk).delete()
            courses = [self.course] + [Course(title=f"K{index}", description="<p>d</p>") for index in range(count - 1)]
            Course.objects.bulk_create(courses[1:])
            courses = list(Course.objects.all())
            for course in courses[:5]:
                self.cohort(course=course)
                self.cohort(course=course, plan=self.delivery, capacity=2)
            with CaptureQueriesContext(connection) as captured:
                offers = public_offer.build_offers(courses)
            with self.subTest(courses=count):
                self.assertEqual(len(offers), count)
                self.assertEqual(len(captured.captured_queries), 3)

    def test_pages_do_not_grow_with_cohorts_or_plans(self):
        detail = reverse("course_detail", args=[self.course.pk])
        for name in renderers():
            self.cohort()
            base = {"detail": self.queries(detail), "catalog": self.queries(reverse("courses"))}
            for index in range(5):
                self.cohort(start_date=self.today + timedelta(days=index + 1))
                Plan.objects.create(name=f"Qo‘shimcha {name} {index}", price=Decimal("100"), order=10 + index)
            with self.subTest(renderer=name):
                self.assertEqual(self.queries(detail), base["detail"])
                self.assertEqual(self.queries(reverse("courses")), base["catalog"])

    def test_catalog_cards_show_the_same_availability(self):
        self.cohort(start_date=self.today + timedelta(days=3))
        closed = Course.objects.create(title="Yopiq kurs", description="<p>d</p>")
        for name in renderers():
            response = self.client.get(reverse("courses"))
            offers = {course.pk: course.public_offer for course in response.context["courses"]}
            with self.subTest(renderer=name):
                self.assertTrue(offers[self.course.pk].available)
                self.assertEqual(offers[closed.pk].reason, public_offer.NOT_OPEN)
                self.assertContains(response, "Qabul hali ochilmagan")
                self.assertContains(response, "Qabul ochiq · keyingi guruh")
