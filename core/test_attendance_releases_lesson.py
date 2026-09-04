"""Davomat yakunlangach dars guruhga ochiladi.

Loyihaning boshidagi kelishuv: 100 ta dars birdan ochilmasin — jonli dars
o'tilib, o'qituvchi davomatni yakunlagach o'sha darsning qulfi ochilsin.

Mexanizm bor edi (`courses/release_service.py` + `/teacher/release/`), ammo
u **davomat bilan ulanmagan** edi: o'qituvchi avval davomatni saqlab, keyin
boshqa sahifaga o'tib darsni ochishi kerak edi. Ikkinchi qadam unutilsa
o'quvchi darsni ko'rmasdi — ya'ni tomchilab berish amalda o'qituvchining
esidan chiqishiga bog'liq edi.

Endi ochish davomatni saqlash bilan bitta amalda. Bitta nozik joy ataylab
ko'rsatiladi: guruhdagi **birinchi** ochilish butun kursni drip rejimiga
o'tkazadi va qolgan barcha darslarni yopadi. Shuning uchun katakcha
belgilangan holda keladi, ammo uni yechish mumkin va birinchi ochilishda
ogohlantirish chiqadi.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Attendance, Cohort, Enrollment
from courses.access_service import check_lesson_access
from courses.models import CohortLessonRelease, Course, Lesson, Module
from users.models import Notification

User = get_user_model()


class AttendanceReleaseFixture:
    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        self.teacher = User.objects.create_user(
            username="davomat-teacher", email="t@example.test", password="x", is_staff=True
        )
        self.student = User.objects.create_user(
            username="davomat-student", email="s@example.test", password="x"
        )
        self.course = Course.objects.create(
            title="Kurs", description="d", level="beginner", instructor=self.teacher
        )
        self.module = Module.objects.create(course=self.course, title="M", order=1)
        self.first = Lesson.objects.create(module=self.module, title="Birinchi", order=1)
        self.second = Lesson.objects.create(module=self.module, title="Ikkinchi", order=2)
        self.cohort = Cohort.objects.create(
            name="G", course=self.course, start_date=self.today
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=self.today + datetime.timedelta(days=30),
        )
        self.url = reverse("teacher_attendance")

    def save_attendance(self, lesson, *, release=True, status="present"):
        payload = {
            "cohort": self.cohort.id,
            "lesson": lesson.id,
            f"att_{self.enrollment.id}": status,
        }
        if release:
            payload["release_lesson"] = "on"
        return self.client.post(self.url, payload)

    def is_open(self, lesson):
        return check_lesson_access(
            user=self.student, lesson=lesson, enrollment=self.enrollment
        ).is_allowed


class AttendanceOpensTheLessonTests(AttendanceReleaseFixture, TestCase):
    def test_saving_attendance_opens_that_lesson(self):
        self.client.force_login(self.teacher)

        self.save_attendance(self.first)

        self.assertTrue(
            CohortLessonRelease.objects.filter(
                cohort=self.cohort, lesson=self.first, is_released=True
            ).exists()
        )
        self.assertTrue(self.is_open(self.first))

    def test_the_attendance_itself_is_still_saved(self):
        self.client.force_login(self.teacher)

        self.save_attendance(self.first)

        self.assertTrue(
            Attendance.objects.filter(enrollment=self.enrollment, lesson=self.first).exists()
        )

    def test_the_first_release_closes_every_other_lesson(self):
        """Aynan shuni owner xohlagan: 100 ta dars birdan ochilmasin."""
        self.client.force_login(self.teacher)
        self.assertTrue(self.is_open(self.second))

        self.save_attendance(self.first)

        self.assertFalse(self.is_open(self.second))

    def test_the_learners_are_told(self):
        self.client.force_login(self.teacher)

        self.save_attendance(self.first)

        self.assertTrue(
            Notification.objects.filter(recipient=self.student, title="Yangi dars ochildi").exists()
        )

    def test_the_teacher_can_save_attendance_without_opening(self):
        """Katakcha yechilsa faqat davomat saqlanadi."""
        self.client.force_login(self.teacher)

        self.save_attendance(self.first, release=False)

        self.assertFalse(CohortLessonRelease.objects.filter(cohort=self.cohort).exists())
        self.assertTrue(
            Attendance.objects.filter(enrollment=self.enrollment, lesson=self.first).exists()
        )

    def test_an_incomplete_attendance_does_not_open_the_lesson(self):
        """Kelishuv «davomat yakunlangach» edi.

        Yarim to'ldirilgan forma darsni ochib yuborsa, birinchi ochilish
        qolgan barcha darslarni yopardi — ya'ni bitta e'tiborsizlik butun
        guruhning kursini yopib qo'yardi.
        """
        second_student = User.objects.create_user(
            username="ikkinchi", email="i@example.test", password="x"
        )
        Enrollment.objects.create(
            student=second_student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=self.today + datetime.timedelta(days=30),
        )
        self.client.force_login(self.teacher)

        # Faqat birinchi o'quvchi belgilandi.
        self.save_attendance(self.first)

        self.assertFalse(CohortLessonRelease.objects.filter(cohort=self.cohort).exists())
        self.assertTrue(self.is_open(self.second))

    def test_an_empty_submission_does_not_open_the_lesson(self):
        self.client.force_login(self.teacher)

        self.client.post(self.url, {
            "cohort": self.cohort.id, "lesson": self.first.id, "release_lesson": "on",
        })

        self.assertFalse(CohortLessonRelease.objects.filter(cohort=self.cohort).exists())

    def test_it_opens_once_every_learner_has_a_status(self):
        second_student = User.objects.create_user(
            username="ikkinchi", email="i@example.test", password="x"
        )
        second = Enrollment.objects.create(
            student=second_student, cohort=self.cohort, status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=self.today + datetime.timedelta(days=30),
        )
        self.client.force_login(self.teacher)

        self.client.post(self.url, {
            "cohort": self.cohort.id, "lesson": self.first.id, "release_lesson": "on",
            f"att_{self.enrollment.id}": "present",
            f"att_{second.id}": "absent",
        })

        self.assertTrue(
            CohortLessonRelease.objects.filter(
                cohort=self.cohort, lesson=self.first, is_released=True
            ).exists()
        )

    def test_saving_twice_does_not_write_a_second_release(self):
        self.client.force_login(self.teacher)
        self.save_attendance(self.first)

        self.save_attendance(self.first)

        self.assertEqual(
            CohortLessonRelease.objects.filter(cohort=self.cohort, lesson=self.first).count(), 1
        )


class TheTeacherIsWarnedBeforeTheFirstReleaseTests(AttendanceReleaseFixture, TestCase):
    def test_the_first_time_the_page_warns_that_the_rest_will_close(self):
        self.client.force_login(self.teacher)

        response = self.client.get(f"{self.url}?cohort={self.cohort.id}&lesson={self.first.id}")

        self.assertContains(response, "Shu darsni guruhga ochish")
        self.assertContains(response, "qolgan hammasi yopiladi")

    def test_the_warning_disappears_once_drip_is_on(self):
        self.client.force_login(self.teacher)
        self.save_attendance(self.first)

        response = self.client.get(f"{self.url}?cohort={self.cohort.id}&lesson={self.second.id}")

        self.assertContains(response, "Shu darsni guruhga ochish")
        self.assertNotContains(response, "qolgan hammasi yopiladi")

    def test_an_already_open_lesson_is_not_offered_again(self):
        self.client.force_login(self.teacher)
        self.save_attendance(self.first)

        response = self.client.get(f"{self.url}?cohort={self.cohort.id}&lesson={self.first.id}")

        self.assertNotContains(response, "Shu darsni guruhga ochish")


class OnlyTheTeacherCanDoThisTests(AttendanceReleaseFixture, TestCase):
    def test_a_student_cannot_open_a_lesson_through_this_page(self):
        self.client.force_login(self.student)

        self.save_attendance(self.first)

        self.assertFalse(CohortLessonRelease.objects.filter(cohort=self.cohort).exists())
