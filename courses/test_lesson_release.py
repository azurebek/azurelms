"""A3 — guruhga dars ochish owner uchun amaldagi yo'lga ega bo'lishi kerak.

Drip-release o'qish tomonida ishlab turardi: `courses/views.py` bironta
`CohortLessonRelease` qatori bo'lsa darslarni yopadi va faqat ochilganlarini
ko'rsatadi. Yozish tomoni esa faqat Django adminda edi, u esa default o'chiq
(`ENABLE_LEGACY_ADMIN=False`) — ya'ni A3 sanagan uchta asosiy amaldan biri
("release") owner uchun umuman mavjud emas edi.

Bu yerdagi da'volar: yuza mavjud va **topiladi**, amal idempotent, ruxsat
o'qituvchi scope'iga bo'ysunadi, audit ledgeriga yoziladi va o'quvchilar
xabar oladi.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from aicontrol.models import SystemAuditEvent
from cohorts.models import Cohort, Enrollment
from courses.models import CohortLessonRelease, Course, Lesson, Module
from courses.release_service import set_lesson_release
from users.models import Notification

User = get_user_model()


class LessonReleaseFixture(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="rel-teacher",
            email="rel-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.course = Course.objects.create(
            title="Release Course",
            description="A3 release",
            instructor=self.teacher,
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="M1", order=1)
        self.lesson_1 = Lesson.objects.create(
            module=self.module, title="Dars 1", content="<p>a</p>", order=1
        )
        self.lesson_2 = Lesson.objects.create(
            module=self.module, title="Dars 2", content="<p>b</p>", order=2
        )
        self.cohort = Cohort.objects.create(
            name="Release Cohort",
            course=self.course,
            start_date="2026-01-01",
            is_active=True,
        )
        self.student = User.objects.create_user(
            username="rel-student", email="rel-student@example.com", password="testpass123"
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status=Enrollment.STATUS_ACTIVE,
        )


class ReleaseServiceTests(LessonReleaseFixture):
    def test_releasing_a_lesson_creates_an_open_record(self):
        release, changed = set_lesson_release(
            cohort=self.cohort, lesson=self.lesson_1, released=True, actor=self.teacher
        )

        self.assertTrue(changed)
        self.assertTrue(release.is_released)
        self.assertEqual(release.released_by, self.teacher)

    def test_releasing_twice_changes_nothing_the_second_time(self):
        set_lesson_release(cohort=self.cohort, lesson=self.lesson_1, released=True, actor=self.teacher)
        _release, changed = set_lesson_release(
            cohort=self.cohort, lesson=self.lesson_1, released=True, actor=self.teacher
        )

        self.assertFalse(changed)
        self.assertEqual(CohortLessonRelease.objects.count(), 1)

    def test_locking_a_released_lesson_flips_it_back(self):
        set_lesson_release(cohort=self.cohort, lesson=self.lesson_1, released=True, actor=self.teacher)
        release, changed = set_lesson_release(
            cohort=self.cohort, lesson=self.lesson_1, released=False, actor=self.teacher
        )

        self.assertTrue(changed)
        self.assertFalse(release.is_released)

    def test_students_are_notified_when_a_lesson_opens(self):
        set_lesson_release(cohort=self.cohort, lesson=self.lesson_1, released=True, actor=self.teacher)

        notification = Notification.objects.filter(recipient=self.student).first()
        self.assertIsNotNone(notification, "O'quvchiga xabar bormadi")
        self.assertIn("Dars 1", notification.message)

    def test_a_lock_does_not_notify(self):
        set_lesson_release(cohort=self.cohort, lesson=self.lesson_1, released=False, actor=self.teacher)

        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 0)

    def test_the_release_is_written_to_the_audit_ledger(self):
        """`05-launch-ops.md` §3 minimal audit ro'yxatida "lesson release" bor."""
        set_lesson_release(
            cohort=self.cohort,
            lesson=self.lesson_1,
            released=True,
            actor=self.teacher,
            note="birinchi hafta",
        )

        event = SystemAuditEvent.objects.get(action="lesson.release")
        self.assertEqual(event.actor_label, "rel-teacher")
        self.assertEqual(event.reason, "birinchi hafta")
        self.assertEqual(event.after["is_released"], True)

    def test_a_no_op_writes_no_audit_event(self):
        set_lesson_release(cohort=self.cohort, lesson=self.lesson_1, released=True, actor=self.teacher)
        SystemAuditEvent.objects.all().delete()

        set_lesson_release(cohort=self.cohort, lesson=self.lesson_1, released=True, actor=self.teacher)

        self.assertEqual(SystemAuditEvent.objects.count(), 0)


class ReleasePageTests(LessonReleaseFixture):
    def test_the_page_renders_with_the_cohort_lessons(self):
        self.client.force_login(self.teacher)

        response = self.client.get(reverse("teacher_release"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dars 1")
        self.assertContains(response, "Dars 2")

    def test_the_page_warns_before_drip_mode_switches_on(self):
        """Birinchi ochish qolgan darslarni yopadi — buni oldindan aytish kerak."""
        self.client.force_login(self.teacher)

        response = self.client.get(reverse("teacher_release"))

        self.assertContains(response, "drip")

    def test_the_warning_disappears_once_drip_is_active(self):
        set_lesson_release(cohort=self.cohort, lesson=self.lesson_1, released=True, actor=self.teacher)
        self.client.force_login(self.teacher)

        response = self.client.get(reverse("teacher_release"))

        self.assertNotContains(response, "drip")

    def test_the_teacher_can_open_a_lesson_from_the_page(self):
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse("teacher_release"),
            {"cohort": self.cohort.id, "lesson": self.lesson_1.id, "action": "release"},
        )

        self.assertEqual(response.status_code, 302)
        release = CohortLessonRelease.objects.get(cohort=self.cohort, lesson=self.lesson_1)
        self.assertTrue(release.is_released)

    def test_the_page_is_reachable_from_the_teacher_navigation(self):
        """Sahifa mavjud bo'lishining o'zi yetarli emas — u topilishi kerak."""
        self.client.force_login(self.teacher)

        response = self.client.get(reverse("teacher_attendance"))

        self.assertContains(response, reverse("teacher_release"))

    def test_a_student_cannot_reach_the_page(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse("teacher_release"))

        self.assertNotEqual(response.status_code, 200)

    def test_a_teacher_cannot_release_another_teachers_course(self):
        """Begona o'qituvchining o'z guruhi bor, ammo bu cohort ID begona."""
        other_teacher = User.objects.create_user(
            username="other-teacher",
            email="other-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        other_course = Course.objects.create(
            title="Other Course",
            description="boshqa",
            instructor=other_teacher,
            level="beginner",
        )
        Cohort.objects.create(
            name="Other Cohort",
            course=other_course,
            start_date="2026-01-01",
            is_active=True,
        )
        self.client.force_login(other_teacher)

        self.client.post(
            reverse("teacher_release"),
            {"cohort": self.cohort.id, "lesson": self.lesson_1.id, "action": "release"},
        )

        self.assertFalse(
            CohortLessonRelease.objects.filter(cohort=self.cohort, lesson=self.lesson_1).exists(),
            "Begona o'qituvchi boshqa kursning darsini ochdi",
        )
