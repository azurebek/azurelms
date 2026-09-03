"""Blur hisoblagichi imtihon holatini bosib ketmaydi.

`LogBlurWarningView` hisoblagichni Pythonda oshirib, `attempt.save()` ni
**`update_fields`siz** chaqirardi. Ya'ni u bitta ustunni emas, `ExamAttempt`
ning **butun qatorini** o'zidagi (ehtimol eskirgan) qiymatlar bilan qayta
yozardi.

Nima uchun bu real: blur hodisasi oynadan chiqishda otiladi, ya'ni u
imtihonni topshirish bilan deyarli bir vaqtda keladi. Topshiruv
`is_completed`, `completed_time` va `score` ni yozib bo'lgach, yo'lda qolgan
blur so'rovi o'sha qatorni eski qiymatlar bilan bosib ketardi —
**tugallangan imtihon `in progress` ga qaytib, ball nolga tushardi.**

`ExamAttempt` da yo'qotish mumkin bo'lgan maydonlar oz emas:
`is_completed`, `completed_time`, `score`, `passed`, `is_reviewed`,
`reviewed_at`, `reviewed_by`, `review_notes`.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from courses.models import Course, Exam, ExamAttempt, Lesson, Module

User = get_user_model()


class BlurWarningIsolationTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="blur-teacher", email="blur-teacher@example.test",
            password="x", is_staff=True,
        )
        self.student = User.objects.create_user(
            username="blur-student", email="blur-student@example.test", password="x"
        )
        self.course = Course.objects.create(
            title="Blur kursi", description="d", level="beginner",
            instructor=self.teacher,
        )
        module = Module.objects.create(course=self.course, title="M1", order=1)
        Lesson.objects.create(
            module=module, title="Dars 1", content="<p>x</p>", order=1, xp_reward=10
        )
        cohort = Cohort.objects.create(
            name="Blur guruhi", course=self.course, start_date=timezone.now().date()
        )
        Enrollment.objects.create(
            student=self.student, cohort=cohort, status=Enrollment.STATUS_ACTIVE
        )
        self.exam = Exam.objects.create(
            course=self.course, title="Imtihon", exam_type="final",
            weight_percentage=40, passing_score=60, max_attempts=3,
        )
        self.attempt = ExamAttempt.objects.create(
            student=self.student, exam=self.exam, attempt_number=1
        )
        self.url = reverse(
            "api_exam_blur",
            kwargs={"course_id": self.course.id, "exam_id": self.exam.id},
        )
        self.client.force_login(self.student)

    def test_the_counter_still_increments(self):
        first = self.client.post(self.url)
        second = self.client.post(self.url)

        self.assertEqual(first.json()["warnings"], 1)
        self.assertEqual(second.json()["warnings"], 2)
        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.blur_warnings, 2)

    def test_the_write_touches_only_the_counter_column(self):
        """Asosiy da'vo — va uni **SQL darajasida** tekshirish kerak.

        Birinchi urinishimda men poygani "eskirgan nusxa" bilan
        modellashtirgandim va test tuzatishsiz ham o'tib ketdi: view har
        so'rovda attemptni yangidan o'qiydi, ya'ni bitta so'rov ichida
        eskirish yo'q. Haqiqiy poyga ikkita **parallel** so'rovni talab
        qiladi va uni bitta oqimli test klienti ko'rsata olmaydi.

        Tuzatish nimani o'zgartirgan bo'lsa, o'shani tekshiramiz:
        yuboriladigan `UPDATE` faqat hisoblagich ustuniga tegadi.
        Ilgari `attempt.save()` butun qatorni yozardi, ya'ni parallel
        yozuvchining natijasi ustidan o'tish uchun oyna ochiq edi.
        """
        with CaptureQueriesContext(connection) as queries:
            response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        updates = [
            q["sql"] for q in queries.captured_queries
            if q["sql"].lstrip().upper().startswith("UPDATE")
            and "courses_examattempt" in q["sql"]
        ]
        self.assertEqual(len(updates), 1, updates)
        sql = updates[0]
        self.assertIn("blur_warnings", sql)
        for column in ("score", "is_completed", "passed", "is_reviewed", "review_notes"):
            self.assertNotIn(column, sql, f"{column} ustuni ham qayta yozilyapti")

    def test_the_counter_is_incremented_in_the_database(self):
        """Oshirish Pythonda emas, bazada bajariladi (`F()`)."""
        with CaptureQueriesContext(connection) as queries:
            self.client.post(self.url)

        sql = next(
            q["sql"] for q in queries.captured_queries
            if q["sql"].lstrip().upper().startswith("UPDATE")
            and "courses_examattempt" in q["sql"]
        )
        # `F()` ifodasi SQL da ustun nomining o'zini qo'shish sifatida
        # ko'rinadi; oddiy Python oshirishi esa tayyor raqam yuboradi.
        self.assertIn("blur_warnings", sql.split("SET", 1)[1])
        self.assertRegex(sql, r'blur_warnings["`\]]?\s*=\s*\(?\s*["`\[]?\w*["`\]]?\.?["`\[]?blur_warnings')

    def test_a_finished_attempt_is_not_reopened(self):
        """Eng og'ir oqibat: tugallangan imtihon `in progress` ga qaytishi."""
        ExamAttempt.objects.filter(pk=self.attempt.pk).update(
            is_completed=True, completed_time=timezone.now(), score=Decimal("70.00")
        )

        response = self.client.post(self.url)

        # Tugallangan urinish uchun blur endpointi umuman ish ko'rmaydi.
        self.assertEqual(response.status_code, 404)
        self.attempt.refresh_from_db()
        self.assertTrue(self.attempt.is_completed)
        self.assertEqual(self.attempt.score, Decimal("70.00"))
