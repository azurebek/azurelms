"""Dars tugagach o'quvchi qayerga borishni biladi.

UX auditning 3-topilmasi. Dars sahifasining pastida faqat «Kurs sahifasi»,
«Bajarildi» va (agar bo'lsa) «Imtihon» turardi — keyingi darsga havola
yo'q edi. Darslar ro'yxati esa faqat yon mundarijada, u 375px da yopiladi:
telefonda sahifada **birorta ham** dars havolasi qolmasdi.

View allaqachon `prev_lesson`, `next_lesson`, `next_lesson_locked` va
`next_lesson_lock_reason` ni hisoblab qo'yardi (`courses/views.py`) —
shablon ulardan foydalanmasdi. Ya'ni bu yo'qolgan ma'lumot emas, ishlatilmagan
ma'lumot edi.

Yopiq keyingi dars uchun alohida qoida: sabab **ko'rinadigan matn**. Ilgari
qulf sababi faqat yon ro'yxatdagi `title=` atributida edi — sichqonchani
ustida ushlab turmagan odam uni umuman ko'rmasdi, telefonda esa `title`
umuman yo'q.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from courses.models import (
    Assignment, CohortLessonRelease, Course, Lesson, Module,
)

User = get_user_model()


class LessonFooterFixture:
    def setUp(self):
        super().setUp()
        today = timezone.localdate()
        self.teacher = User.objects.create_user(
            username="oyoq-teacher", email="t@example.test", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="oyoq-student", email="s@example.test", password="x"
        )
        self.course = Course.objects.create(
            title="Kurs", description="d", level="beginner", instructor=self.teacher
        )
        module = Module.objects.create(course=self.course, title="M", order=1)
        self.first = Lesson.objects.create(module=module, title="Birinchi dars", order=1)
        self.second = Lesson.objects.create(module=module, title="Ikkinchi dars", order=2)
        self.third = Lesson.objects.create(module=module, title="Uchinchi dars", order=3)
        self.cohort = Cohort.objects.create(
            name="G", course=self.course, start_date=today
        )
        Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=today + datetime.timedelta(days=30),
        )

    def visit(self, lesson):
        self.client.force_login(self.student)
        return self.client.get(reverse("lesson_detail", kwargs={
            "course_id": self.course.id, "lesson_id": lesson.id,
        }))

    def link_to(self, lesson):
        return reverse("lesson_detail", kwargs={
            "course_id": self.course.id, "lesson_id": lesson.id,
        })

    def footer(self, response):
        """Faqat pastki panel.

        Yon mundarija ham xuddi shu havolalarni saqlaydi, ya'ni butun
        sahifa bo'yicha qidiruv hech narsani isbotlamaydi — aynan
        375px da yopiladigan mundarijadan tashqarida borligi kerak.
        """
        html = response.content.decode(response.charset)
        return html[html.index("<!-- Footer -->"):]


class TheFooterCarriesTheNextLessonTests(LessonFooterFixture, TestCase):
    def test_an_open_next_lesson_is_one_click_away(self):
        response = self.visit(self.first)

        footer = self.footer(response)
        self.assertIn("Keyingi dars", footer)
        self.assertIn(f'href="{self.link_to(self.second)}', footer)

    def test_the_previous_lesson_is_reachable_too(self):
        response = self.visit(self.second)

        self.assertIn(f'href="{self.link_to(self.first)}', self.footer(response))

    def test_the_first_lesson_offers_no_previous(self):
        """Yo'q joyga havola qo'yilmaydi."""
        response = self.visit(self.first)

        self.assertNotContains(response, "> Oldingi")

    def test_the_last_lesson_offers_no_next(self):
        response = self.visit(self.third)

        self.assertNotIn("Keyingi dars", self.footer(response))

    def test_the_first_lesson_still_offers_the_course_page(self):
        """Yangi tugmalar eskisini siqib chiqarmasin."""
        response = self.visit(self.first)

        self.assertIn("Kurs sahifasi", self.footer(response))


class ALockedNextLessonSaysWhyTests(LessonFooterFixture, TestCase):
    def test_the_reason_is_readable_text_not_a_tooltip(self):
        Assignment.objects.create(lesson=self.first, title="Vazifa", description="d")

        response = self.visit(self.first)

        self.assertIn("tasdiqlanmaguncha", self.footer(response))

    def test_a_locked_next_lesson_is_not_a_link(self):
        Assignment.objects.create(lesson=self.first, title="Vazifa", description="d")

        response = self.visit(self.first)

        self.assertNotIn(f'href="{self.link_to(self.second)}', self.footer(response))

    def test_the_drip_reason_is_shown_when_the_teacher_has_not_opened_it(self):
        """Tomchilab berish: sabab boshqa, ammo u ham ko'rinishi kerak."""
        CohortLessonRelease.objects.create(
            cohort=self.cohort, lesson=self.first, is_released=True
        )
        CohortLessonRelease.objects.create(
            cohort=self.cohort, lesson=self.second, is_released=False
        )

        response = self.visit(self.first)

        self.assertIn("o&#x27;qituvchi tomonidan ochilmagan", self.footer(response))


class TheExamDoesNotCompeteWithTheNextLessonTests(LessonFooterFixture, TestCase):
    """Ikkita ko'k tugma yonma-yon tursa o'quvchi qaysi biri asosiyligini bilmaydi."""

    def _add_exam(self):
        from courses.models import Exam

        return Exam.objects.create(
            course=self.course, title="Yakuniy", exam_type="final", weight_percentage=60,
        )

    def _exam_link(self, response):
        footer = self.footer(response)
        start = footer.index("exam_detail" if "exam_detail" in footer else "/exam")
        return footer[start:footer.index("Imtihon", start)]

    def test_the_exam_is_secondary_while_lessons_remain(self):
        self._add_exam()

        response = self.visit(self.first)

        self.assertIn("border:1px solid var(--line)", self._exam_link(response))

    def test_the_exam_becomes_the_main_action_on_the_last_lesson(self):
        self._add_exam()

        response = self.visit(self.third)

        self.assertIn("background:var(--azure)", self._exam_link(response))
