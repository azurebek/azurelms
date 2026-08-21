"""Telegram checkout web bilan bir xil qoidaga bo'ysunadi (A4).

`begin_course_enrollment` sayt bilan **bitta** servisni chaqiradi
(`resolve_checkout_enrollment`) — bu to'g'ri tuzilma va dublikat mantiq yo'q.
Ammo adapterning o'zi sinalmagan edi: servis to'g'ri qaror qabul qilishi bilan
adapter o'sha qarorni foydalanuvchiga to'g'ri yetkazishi bir xil narsa emas.

A4 ning acceptance talabi shu: "web/Telegram parity". Bu testlar aynan
adapter chegarasini tekshiradi.
"""

from django.test import TestCase
from django.utils import timezone

from bot.services import begin_course_enrollment
from cohorts.models import Cohort, Enrollment
from courses.models import Course
from subscriptions.models import Plan
from users.models import CustomUser as User


class TelegramCheckoutParityTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="tg-oquvchi", email="tg@example.com", password="testpass123"
        )
        teacher = User.objects.create_user(
            username="tg-teacher", email="tgt@example.com", password="testpass123", is_staff=True
        )
        self.course = Course.objects.create(
            title="Kurs", description="d", instructor=teacher, level="beginner", is_active=True
        )
        self.cohort = Cohort.objects.create(
            name="Guruh", course=self.course, start_date=timezone.localdate(),
            is_active=True, is_checkout_default=True,
        )
        self.plan = Plan.objects.create(
            name="Tarif", price=99000, description="x", code="tg-tarif"
        )

    def test_open_admissions_create_a_pending_enrollment(self):
        result = begin_course_enrollment(self.student, self.course.id, self.plan.id)

        self.assertTrue(result.ok, getattr(result, "message", ""))
        self.assertTrue(Enrollment.objects.filter(student=self.student, cohort=self.cohort).exists())

    def test_closed_admissions_are_refused_through_telegram_too(self):
        """Sayt yopiq desa, Telegram ham yopiq deyishi kerak."""
        Cohort.objects.filter(course=self.course).update(is_active=False)

        result = begin_course_enrollment(self.student, self.course.id, self.plan.id)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "unavailable")
        self.assertFalse(
            Enrollment.objects.filter(student=self.student).exists(),
            "yopiq qabulda enrollment yaratilmasligi kerak",
        )

    def test_telegram_checkout_does_not_reopen_a_closed_cohort(self):
        """Adapter orqali kelgan o'quvchi ham qabulni qayta ocholmaydi."""
        Cohort.objects.filter(course=self.course).update(is_active=False)

        begin_course_enrollment(self.student, self.course.id, self.plan.id)

        self.cohort.refresh_from_db()
        self.assertFalse(self.cohort.is_active, "yopilgan cohort Telegram orqali qayta ochildi")

    def test_an_inactive_course_is_refused_before_any_cohort_lookup(self):
        self.course.is_active = False
        self.course.save(update_fields=["is_active"])

        result = begin_course_enrollment(self.student, self.course.id, self.plan.id)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "course_missing")

    def test_a_second_attempt_reuses_the_same_enrollment(self):
        """Dublikat enrollment ochilmasligi — web tomonida ham shunday."""
        begin_course_enrollment(self.student, self.course.id, self.plan.id)
        begin_course_enrollment(self.student, self.course.id, self.plan.id)

        self.assertEqual(Enrollment.objects.filter(student=self.student).count(), 1)
