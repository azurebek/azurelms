"""PUB1.6a — ochiq sahifada odam nomi: hisobdagi ism yoki umumiy nom, login hech qachon.

Blog sahifalari `blog/test_public_contract.py`da; bu yerda kurs o'qituvchisi
(katalog kartasi va kurs sahifasi, ikkala renderer) va qoidaning o'zi.
"""

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from aicontrol.models import FeatureFlag
from courses.models import Course
from frontend.public_people import public_person_name
from frontend.templatetags.public_content import public_initials
from users.models import CustomUser


class _User:
    def __init__(self, first="", last="", username="login_nomi"):
        self.first, self.last, self.username = first, last, username

    def get_full_name(self):
        return f"{self.first} {self.last}".strip()

    def get_username(self):
        return self.username


class RuleTests(SimpleTestCase):
    def test_real_name_or_a_generic_label_never_the_login(self):
        self.assertEqual(public_person_name(_User("Ali", "Valiyev")), "Ali Valiyev")
        self.assertEqual(public_person_name(_User(), "author"), "Platforma muallifi")
        self.assertEqual(public_person_name(_User(), "teacher"), "Platforma o‘qituvchisi")
        self.assertEqual(public_person_name(_User()), "Foydalanuvchi")
        self.assertEqual(public_person_name(None), "Foydalanuvchi")
        self.assertEqual(public_initials(_User("Ali", "Valiyev")), "AV")
        self.assertNotIn("L", public_initials(_User(username="Login")))


class CourseTeacherTests(TestCase):
    def setUp(self):
        self.teacher = CustomUser.objects.create_user(username="ustoz_login", email="u@example.test", password="x")
        self.course = Course.objects.create(title="Turk tili A1", description="d", level="beginner", instructor=self.teacher)

    def test_course_pages_show_no_teacher_login(self):
        for v1 in (False, True):
            FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": v1})
            for url in (reverse("courses"), reverse("course_detail", args=[self.course.pk])):
                with self.subTest(v1=v1, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotContains(response, "ustoz_login")
            self.assertContains(self.client.get(reverse("course_detail", args=[self.course.pk])), "Platforma o‘qituvchisi")
