"""Typed entitlement (A4).

Ilgari kirish huquqi ikki xil savolga bo'lingan edi: "enrollment faolmi?"
(`Enrollment.has_active_access`) va AI token limiti (`aicontrol`). Bulardan
tashqari **plan hech narsani belgilamasdi** — Premium to'lagan o'quvchi
Starter bilan bir xil kirish olardi va buni so'raydigan yagona joy yo'q edi.

Typed entitlement shu savolni bitta joyga yig'adi: "bu o'quvchi nimaga
haqli?" Javob enrollment holati **va** plan kodidan kelib chiqadi.

Ikki qaror bu testlarda majburlanadi:

1. **Plan kodi bo'yicha, nomi bo'yicha emas.** Ko'rsatiladigan nomni
   o'zgartirish kirish huquqini jimgina buzmasligi kerak.
2. **Faol bo'lmagan enrollment hech qanday huquq bermaydi** — va bu qoida
   `has_active_access()` dan olinadi, qayta yozilmaydi.
"""

import datetime

from django.test import TestCase
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from core.entitlements import (
    Capability,
    UnknownCapability,
    entitlements_for,
    has_entitlement,
    plan_entitlements,
)
from courses.models import Course
from subscriptions.models import Plan
from users.models import CustomUser as User


class CapabilityRegistryTests(TestCase):
    def test_every_capability_is_documented(self):
        for capability in Capability:
            self.assertTrue(capability.label, f"{capability.name}: yorliq yo'q")
            self.assertTrue(capability.description, f"{capability.name}: izoh yo'q")

    def test_asking_for_an_unknown_capability_raises(self):
        """Xato yozilgan nom jim `False` qaytarsa, huquq jimgina yo'qoladi."""
        user = User.objects.create_user(username="u", email="u@e.com", password="p-12345")
        with self.assertRaises(UnknownCapability):
            has_entitlement(user, "mavjud-emas-qobiliyat")


class PlanEntitlementTests(TestCase):
    def test_plan_is_matched_by_code_not_display_name(self):
        """Nomni o'zgartirish huquqni buzmasligi kerak.

        `PLAN_MATRIX` vaqtincha to'ldiriladi: u bo'sh bo'lganda hamma narsa
        `BASELINE` ga tushadi va kod bilan nom bir xil natija beradi, ya'ni
        test hech nimani isbotlamasdi — nazorat yugurishi shuni ko'rsatdi.
        """
        from unittest.mock import patch

        from core.entitlements import Capability

        plan = Plan.objects.create(name="Starter", price=99000, description="x", code="test-starter")
        limited = frozenset({Capability.COURSE_CONTENT})

        with patch.dict("core.entitlements.PLAN_MATRIX", {"test-starter": limited}, clear=False):
            before = plan_entitlements(plan)
            self.assertEqual(before, limited, "xarita ishlatilmayapti — test ma'nosiz bo'lardi")

            plan.name = "Boshlang'ich (yangi nom)"
            plan.save(update_fields=["name"])

            self.assertEqual(plan_entitlements(plan), limited)

    def test_an_unmapped_plan_falls_back_to_the_documented_baseline(self):
        """Yangi plan qo'shilganda kirish jimgina yopilib qolmasin."""
        plan = Plan.objects.create(name="Yangi", price=1, description="x", code="hali-xaritada-yoq")
        self.assertTrue(plan_entitlements(plan), "noma'lum plan bo'sh huquq bermasligi kerak")

    def test_no_plan_at_all_still_returns_the_baseline(self):
        self.assertTrue(plan_entitlements(None))


class LearnerEntitlementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="o", email="o@e.com", password="p-12345")
        self.plan = Plan.objects.create(name="Starter", price=99000, description="x", code="test-starter")
        teacher = User.objects.create_user(username="t", email="t@e.com", password="p-12345", is_staff=True)
        self.course = Course.objects.create(title="Kurs", description="d", instructor=teacher, level="beginner")
        self.cohort = Cohort.objects.create(
            name="Guruh", course=self.course, start_date=timezone.localdate(), is_active=True
        )

    def _enroll(self, *, status=Enrollment.STATUS_ACTIVE, deadline=None):
        return Enrollment.objects.create(
            student=self.user, cohort=self.cohort, plan=self.plan,
            status=status,
            next_payment_deadline=deadline if deadline is not None else timezone.localdate() + datetime.timedelta(days=30),
        )

    def test_a_learner_without_any_enrollment_has_nothing(self):
        self.assertEqual(entitlements_for(self.user), frozenset())

    def test_an_active_enrollment_grants_its_plan_entitlements(self):
        self._enroll()
        self.assertEqual(entitlements_for(self.user), plan_entitlements(self.plan))

    def test_an_expired_enrollment_grants_nothing(self):
        self._enroll(status=Enrollment.STATUS_EXPIRED)
        self.assertEqual(entitlements_for(self.user), frozenset())

    def test_an_overdue_deadline_grants_nothing_even_while_status_says_active(self):
        """Muddati o'tgan to'lov `has_active_access()` da hal qilinadi — bu yerda takrorlanmaydi."""
        self._enroll(deadline=timezone.localdate() - datetime.timedelta(days=365))
        self.assertEqual(entitlements_for(self.user), frozenset())

    def test_entitlements_can_be_scoped_to_one_course(self):
        self._enroll()
        other_teacher = User.objects.create_user(username="t2", email="t2@e.com", password="p-12345", is_staff=True)
        other = Course.objects.create(title="Boshqa", description="d", instructor=other_teacher, level="beginner")

        self.assertTrue(entitlements_for(self.user, course=self.course))
        self.assertEqual(entitlements_for(self.user, course=other), frozenset())

    def test_has_entitlement_matches_the_set(self):
        self._enroll()
        granted = next(iter(entitlements_for(self.user)))
        self.assertTrue(has_entitlement(self.user, granted))

    def test_anonymous_user_has_nothing(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertEqual(entitlements_for(AnonymousUser()), frozenset())


class BehaviourIsUnchangedTests(TestCase):
    """Bu slice **narx qarorini qabul qilmaydi**.

    Qaysi plan nimaga haqli ekani owner qarori. Shu sabab hozircha barcha
    planlar bir xil to'plamni oladi va mavjud xulq aynan saqlanadi;
    mexanizm tayyor, matritsa esa ownerdan kutiladi.
    """

    def test_all_seeded_plans_currently_grant_the_same_set(self):
        # `0004` migratsiyasi haqiqiy planlarni ekadi — test o'z kodlarini ishlatadi.
        codes = ("t-starter", "t-pro", "t-premium")
        plans = [
            Plan.objects.create(name=code.title(), price=1, description="x", code=code)
            for code in codes
        ]
        sets = {frozenset(plan_entitlements(plan)) for plan in plans}
        self.assertEqual(
            len(sets), 1,
            "planlar farqlanishi narx qarori — u ownerdan kelmaguncha kiritilmaydi",
        )
