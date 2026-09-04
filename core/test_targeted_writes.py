"""Yozuv faqat o'zgargan ustunga tegadi.

Blur hisoblagichi nuqsonidan (PR #59) keyin butun kod bo'ylab shu naqsh
qidirildi: `obj.save()` ni argumentsiz chaqirish **butun qatorni** obyektdagi
(ehtimol eskirgan) qiymatlar bilan qayta yozadi va parallel yozuvchining
natijasini jimgina bosib ketadi.

To'rtta joy topildi:

* **profil sozlamalarini saqlash** — eng ko'p uchraydigani. `UpdateView` +
  `ModelForm` `CustomUser` ning butun qatorini yozardi, ya'ni `total_xp`
  (`users/xp.py` beradi) va `ai_tone`/`ai_model`/`ai_skill`/`ai_memory_enabled`
  (`/users/settings/ai-*` endpointlari o'zgartiradi) formaga yuklangan eski
  qiymatlarga qaytardi;
* **to'lov cheki tasdiqlanishi** — `Enrollment` qatorini parallel
  transfer/promotion (`cohorts/transition_service.py`) ham yangilaydi;
* **parol o'zgartirish** — o'sha `CustomUser` qatori;
* **`ExamAttempt.calculate_total_score`** — u umuman chaqirilmasdi, ya'ni
  o'lik footgun edi; olib tashlandi va bu yerda yo'qligi tekshiriladi.

Tekshiruv SQL darajasida: haqiqiy poyga ikkita parallel so'rovni talab
qiladi va uni bitta oqimli test klienti ko'rsata olmaydi (bu saboq blur
testida qimmatga tushgan edi). Shuning uchun tuzatish nimani o'zgartirgan
bo'lsa, o'sha tekshiriladi — yuborilgan `UPDATE` ning ustunlari.
"""

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort, Enrollment, PaymentReceipt
from courses.models import Course, ExamAttempt

User = get_user_model()


def _update_statements(queries, table):
    return [
        query["sql"]
        for query in queries.captured_queries
        if query["sql"].lstrip().upper().startswith("UPDATE") and table in query["sql"]
    ]


class ProfileSaveWriteTests(TestCase):
    """Eng ko'p uchraydigan yo'l — profil sozlamalarini saqlash."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="profil-user", email="profil@example.test", password="ParolX123"
        )
        self.client.force_login(self.user)

    def _post_profile(self):
        return self.client.post(
            reverse("settings_account"),
            {"first_name": "Aziz", "last_name": "Rahimov", "phone_number": "", "bio": "salom"},
        )

    def test_saving_the_profile_does_not_rewrite_unrelated_columns(self):
        with CaptureQueriesContext(connection) as queries:
            response = self._post_profile()

        self.assertEqual(response.status_code, 302)
        updates = _update_statements(queries, "users_customuser")
        self.assertEqual(len(updates), 1, updates)
        sql = updates[0]
        for column in ("total_xp", "ai_tone", "ai_model", "ai_memory_enabled", "password"):
            self.assertNotIn(column, sql, f"{column} ham qayta yozilyapti")

    def test_the_profile_fields_are_actually_saved(self):
        self._post_profile()

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Aziz")
        self.assertEqual(self.user.bio, "salom")

    def test_a_stale_form_instance_does_not_roll_back_other_columns(self):
        """Poygani forma darajasida modellashtiramiz.

        HTTP klienti buni ko'rsata olmaydi: `UpdateView` obyektni so'rov
        boshida yuklaydi, ya'ni bitta so'rov ichida eskirish yo'q. Birinchi
        urinishimda aynan shu sabab ikkita test tuzatishsiz ham o'tib ketdi.

        Bu yerda esa forma **ataylab** eskirgan nusxa bilan quriladi — real
        holatda o'sha nusxa so'rov boshida yuklanadi va foydalanuvchi formani
        to'ldirguncha boshqa yo'l XP beradi yoki AI ohangini o'zgartiradi.
        """
        from users.forms import ProfileFieldsForm
        from users.xp import award_xp

        stale = User.objects.get(pk=self.user.pk)
        self.assertEqual(stale.total_xp, 0)

        award_xp(User.objects.get(pk=self.user.pk), 40)
        User.objects.filter(pk=self.user.pk).update(ai_tone="formal")

        form = ProfileFieldsForm(
            {"first_name": "Aziz", "last_name": "Rahimov", "phone_number": "", "bio": "salom"},
            instance=stale,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        fresh = User.objects.get(pk=self.user.pk)
        self.assertEqual(fresh.total_xp, 40, "XP eskirgan nusxa bilan bosib ketildi")
        self.assertEqual(fresh.ai_tone, "formal", "AI ohangi eskisiga qaytarildi")
        self.assertEqual(fresh.first_name, "Aziz")


class ReceiptVerificationWriteTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="chek-student", email="chek@example.test", password="x"
        )
        course = Course.objects.create(title="Kurs", description="d", level="beginner")
        self.cohort = Cohort.objects.create(
            name="Guruh", course=course, start_date=timezone.now().date()
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_PENDING
        )

    def test_verifying_a_receipt_touches_only_the_payment_columns(self):
        receipt = PaymentReceipt.objects.create(
            enrollment=self.enrollment, amount=100000
        )

        with CaptureQueriesContext(connection) as queries:
            receipt.is_verified = True
            receipt.save()

        updates = _update_statements(queries, "cohorts_enrollment")
        self.assertEqual(len(updates), 1, updates)
        sql = updates[0]
        for column in ("status", "last_payment_date", "next_payment_deadline"):
            self.assertIn(column, sql)
        for column in ("plan_id", "joined_at", "cohort_id"):
            # `pending_plan_id` endi payment ustuni; substring testi uni
            # faol `plan_id` bilan adashtirmasligi kerak.
            self.assertNotIn(f'"{column}"', sql, f"{column} ham qayta yozilyapti")

    def test_the_enrollment_still_becomes_active(self):
        receipt = PaymentReceipt.objects.create(
            enrollment=self.enrollment, amount=100000
        )

        receipt.is_verified = True
        receipt.save()

        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.STATUS_ACTIVE)
        self.assertIsNotNone(self.enrollment.next_payment_deadline)


class DeadScoringMethodTests(TestCase):
    def test_the_unused_full_row_scorer_is_gone(self):
        """Chaqirilmaydigan, lekin butun qatorni yozadigan metod qoldirilmadi."""
        self.assertFalse(
            hasattr(ExamAttempt, "calculate_total_score"),
            "o'lik `calculate_total_score` qaytib kelgan — u `save()` ni "
            "argumentsiz chaqiradi va butun qatorni bosib ketadi",
        )
