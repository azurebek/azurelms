"""A4 — Telegram'dan kelgan chek aynan tanlangan enrollmentga tushishi kerak.

Backlog A4: "receipt ayni tanlangan enrollmentga". Web'da bu bajarilgan —
forma `course_id` bilan keladi, ya'ni qaysi kurs uchun to'layotgani aniq.
Telegram'da esa aloqa uzilgan: `/yozilish` da tanlangan kurs hech qayerda
saqlanmaydi, chek rasmi kelganda esa nishon **taxmin qilinadi** —
"tarifi bor, tasdiqlanmagan cheki yo'q, eng oxirgi qo'shilgan enrollment".

Taxmin ikkita enrollmentli o'quvchida buziladi: eski kursga qayta to'lamoqchi
bo'lgan odamning puli yangiroq kursga yoziladi.
"""

import base64
import datetime

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from bot.services import begin_course_enrollment, submit_payment_receipt
from cohorts.models import Cohort, Enrollment, PaymentReceipt
from courses.models import Course
from subscriptions.models import Plan

User = get_user_model()

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def receipt_file(name="bot-receipt.png"):
    return SimpleUploadedFile(name, PNG_1X1, content_type="image/png")


class BotReceiptLandsOnTheChosenCourseTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="two-course-student",
            email="two-course@example.com",
            password="testpass123",
        )
        self.teacher = User.objects.create_user(
            username="two-course-teacher",
            email="two-course-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.plan = Plan.objects.create(name="Bot Plan", price=100000, order=1)

        self.old_course, self.old_cohort = self._course("Eski kurs")
        self.new_course, self.new_cohort = self._course("Yangi kurs")

        # Eski kursdagi enrollment — muddati tugagan, qayta to'lash kerak.
        self.old_enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.old_cohort,
            plan=self.plan,
            status=Enrollment.STATUS_EXPIRED,
        )
        # Yangi kursdagi enrollment keyinroq ochilgan.
        self.new_enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.new_cohort,
            plan=self.plan,
            status=Enrollment.STATUS_PENDING,
        )
        # `joined_at` — `auto_now_add`, shuning uchun sanani qo'lda suramiz.
        Enrollment.objects.filter(pk=self.old_enrollment.pk).update(
            joined_at=timezone.now() - datetime.timedelta(days=90)
        )
        Enrollment.objects.filter(pk=self.new_enrollment.pk).update(
            joined_at=timezone.now() - datetime.timedelta(days=1)
        )

    def _course(self, title):
        course = Course.objects.create(
            title=title,
            description=title,
            instructor=self.teacher,
            level="beginner",
        )
        cohort = Cohort.objects.create(
            name=f"{title} guruhi",
            course=course,
            start_date="2026-12-01",
            is_active=True,
            is_checkout_default=True,
        )
        return course, cohort

    def test_the_receipt_follows_the_course_the_learner_just_chose(self):
        """`/yozilish` da eski kurs tanlandi — chek o'sha kursga tushishi kerak."""
        started = begin_course_enrollment(self.student, self.old_course.id, self.plan.id)
        self.assertTrue(started.ok, getattr(started, "message", started))

        result = submit_payment_receipt(self.student, receipt_file())
        self.assertTrue(result.ok, getattr(result, "message", result))

        receipt = PaymentReceipt.objects.get(pk=result.receipt_id)
        self.assertEqual(
            receipt.enrollment_id,
            self.old_enrollment.id,
            "Chek foydalanuvchi tanlagan kursga emas, boshqasiga yozildi",
        )
        self.assertEqual(result.course_title, self.old_course.title)

    def test_the_receipt_follows_a_newly_chosen_course_too(self):
        """Teskari tomon: yangi kurs tanlansa ham nishon o'sha bo'lsin."""
        started = begin_course_enrollment(self.student, self.new_course.id, self.plan.id)
        self.assertTrue(started.ok, getattr(started, "message", started))

        result = submit_payment_receipt(self.student, receipt_file())
        self.assertTrue(result.ok, getattr(result, "message", result))

        receipt = PaymentReceipt.objects.get(pk=result.receipt_id)
        self.assertEqual(receipt.enrollment_id, self.new_enrollment.id)

    def test_a_learner_who_chose_nothing_is_told_to_choose(self):
        """Hech narsa tanlamagan odamning cheki taxmin bilan joylashtirilmaydi."""
        result = submit_payment_receipt(self.student, receipt_file())

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "no_target")
        self.assertEqual(PaymentReceipt.objects.count(), 0)
