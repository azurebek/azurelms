"""Telegram adapteri guruh scope'ida web bilan bir xil javob beradi (A3/A0b).

`core/access.py` 2026-08-15 da default-deny qoidasini o'rnatgan: superuser
hammasini, qolgan har kim faqat o'ziga instructor sifatida biriktirilgan
kursni. Web teacher paneli, `/guruhlarim` va `/baholash` o'sha ko'chishda
tuzatilgan edi.

`bot/services.py::can_manage_cohort` esa ko'chirilmay qolgan va eski
qoidada — `is_active_staff(user)` yetarli — turgan edi. Ya'ni har qanday
faol staff **boshqa o'qituvchining** guruhini boshqara olardi: davomat
sessiyasini ocha, yopa va guruhni chatga bog'lay olardi.

Bu yerdagi testlar shu yordamchining canonical scope bilan bir xil javob
berishini qulflaydi. "Servis to'g'ri qaror qildi" va "adapter o'sha qarorni
qo'lladi" bir xil narsa emas, shuning uchun oxirgi ikki test servis emas,
bot buyruq oqimlari orqali o'tadi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bot.services import (
    bind_chat_to_cohort, can_manage_cohort, close_lesson_session,
    start_lesson_session,
)
from cohorts.models import Cohort
from core.access import teacher_cohort_queryset
from courses.models import Course, Lesson, Module

User = get_user_model()


class CohortScopeParityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="scope-owner", email="scope-owner@example.test",
            password="x", telegram_id=201,
        )
        self.teacher = User.objects.create_user(
            username="scope-teacher", email="scope-teacher@example.test",
            password="x", is_staff=True, telegram_id=202,
        )
        self.other_staff = User.objects.create_user(
            username="scope-other-staff", email="scope-other@example.test",
            password="x", is_staff=True, telegram_id=203,
        )
        self.student = User.objects.create_user(
            username="scope-student", email="scope-student@example.test",
            password="x", telegram_id=204,
        )

        self.course = Course.objects.create(
            title="Scope kursi", description="d", level="beginner",
            instructor=self.teacher,
        )
        module = Module.objects.create(course=self.course, title="M1", order=1)
        Lesson.objects.create(
            module=module, title="Dars 1", content="<p>x</p>", order=1, xp_reward=10
        )
        self.cohort = Cohort.objects.create(
            name="Scope guruhi", course=self.course,
            start_date=timezone.now().date(), telegram_chat_id=-100777001,
        )

    def test_the_instructor_and_the_owner_can_manage(self):
        self.assertTrue(can_manage_cohort(self.teacher, self.cohort))
        self.assertTrue(can_manage_cohort(self.owner, self.cohort))

    def test_unrelated_staff_cannot_manage_another_teachers_cohort(self):
        """Asosiy nuqson: "staff" bo'lish o'zi huquq bermaydi."""
        self.assertFalse(can_manage_cohort(self.other_staff, self.cohort))

    def test_student_and_anonymous_cannot_manage(self):
        self.assertFalse(can_manage_cohort(self.student, self.cohort))
        self.assertFalse(can_manage_cohort(None, self.cohort))

    def test_the_helper_agrees_with_the_canonical_scope(self):
        """Parity shartnomasi: ikki manba bir xil javob berishi kerak."""
        for user in (self.owner, self.teacher, self.other_staff, self.student):
            in_scope = teacher_cohort_queryset(user).filter(pk=self.cohort.pk).exists()
            self.assertEqual(
                can_manage_cohort(user, self.cohort), in_scope, user.username
            )

    def test_unrelated_staff_cannot_open_a_session_through_the_bot(self):
        result = start_lesson_session(
            chat_id=self.cohort.telegram_chat_id,
            chat_title="Scope guruhi",
            actor_telegram_id=self.other_staff.telegram_id,
            lesson_ref="1",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "permission_denied")

    def test_unrelated_staff_cannot_bind_a_chat_to_a_cohort(self):
        result = bind_chat_to_cohort(
            cohort_id=self.cohort.id,
            chat_id=-100777002,
            chat_title="Begona chat",
            actor_telegram_id=self.other_staff.telegram_id,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "permission_denied")

    def test_unrelated_staff_cannot_close_someone_elses_session(self):
        opened = start_lesson_session(
            chat_id=self.cohort.telegram_chat_id,
            chat_title="Scope guruhi",
            actor_telegram_id=self.teacher.telegram_id,
            lesson_ref="1",
        )
        self.assertTrue(opened.ok, opened.message)

        result = close_lesson_session(
            chat_id=self.cohort.telegram_chat_id,
            actor_telegram_id=self.other_staff.telegram_id,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "permission_denied")
