"""QA uchun demo ma'lumot generatori (A5 / R4).

Lokal bazada bitta foydalanuvchi bor, kurs/dars/imtihon esa yo'q. Ya'ni
mobil QA faqat bo'sh ekranlarni ko'ra oladi, A5 esa dars sarlavhasi, imtihon
landscape, checkout va davomat sahifalarini talab qiladi. R4 ham "fresh demo
account" so'raydi.

Ikkita da'vo eng muhim: buyruq **lokaldan tashqarida ishlamaydi** va
**qaytarib olinadi** — QA ma'lumoti haqiqiy ma'lumot bilan aralashib
qolmasligi kerak.
"""

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings

from cohorts.models import Cohort, Enrollment
from core.demo_seed import DEMO_MARK, seed_demo_data, wipe_demo_data
from courses.models import Assignment, Course, Lesson, Module

User = get_user_model()


class SeedGuardTests(TestCase):
    @override_settings(IS_LOCAL=False)
    def test_seeding_is_refused_outside_local(self):
        """Fail-closed: demo ma'lumot production bazasiga hech qachon tushmasin."""
        with self.assertRaises(CommandError):
            call_command("seed_demo")

    @override_settings(IS_LOCAL=False)
    def test_wiping_is_refused_outside_local_too(self):
        with self.assertRaises(CommandError):
            call_command("seed_demo", "--wipe")


class SeedContentTests(TestCase):
    def test_the_seed_builds_a_walkable_course(self):
        seed_demo_data()

        course = Course.objects.get(title__startswith=DEMO_MARK)
        self.assertGreaterEqual(Module.objects.filter(course=course).count(), 2)
        self.assertGreaterEqual(Lesson.objects.filter(module__course=course).count(), 4)
        self.assertTrue(Assignment.objects.filter(lesson__module__course=course).exists())

    def test_the_seed_creates_an_enrolled_student_with_access(self):
        seed_demo_data()

        student = User.objects.get(username="demo-student")
        enrollment = Enrollment.objects.get(student=student)
        self.assertTrue(enrollment.has_active_access())

    def test_lessons_carry_enough_text_to_expose_layout_problems(self):
        """Bir qatorlik dars mobil layoutni sinamaydi."""
        seed_demo_data()

        lesson = Lesson.objects.filter(module__course__title__startswith=DEMO_MARK).first()
        self.assertGreater(len(lesson.content), 400)

    def test_running_twice_changes_nothing(self):
        seed_demo_data()
        counts = (Course.objects.count(), Lesson.objects.count(), User.objects.count())

        seed_demo_data()

        self.assertEqual(
            (Course.objects.count(), Lesson.objects.count(), User.objects.count()), counts
        )


class WipeTests(TestCase):
    def test_wipe_removes_what_the_seed_created(self):
        seed_demo_data()

        wipe_demo_data()

        self.assertFalse(Course.objects.filter(title__startswith=DEMO_MARK).exists())
        self.assertFalse(User.objects.filter(username__startswith="demo-").exists())
        self.assertFalse(Cohort.objects.filter(name__startswith=DEMO_MARK).exists())

    def test_wipe_leaves_real_data_alone(self):
        """Eng muhim da'vo: tozalash faqat o'zi yaratganini oladi."""
        real_user = User.objects.create_user(
            username="haqiqiy-oquvchi", email="real@example.com", password="x")
        real_course = Course.objects.create(
            title="Haqiqiy kurs", description="tegilmasin", level="beginner")
        seed_demo_data()

        wipe_demo_data()

        self.assertTrue(User.objects.filter(pk=real_user.pk).exists())
        self.assertTrue(Course.objects.filter(pk=real_course.pk).exists())
