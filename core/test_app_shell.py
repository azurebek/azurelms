from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AppShellUserMenuTests(TestCase):
    """Sidebar profil menyusi kontrakti — uchala app shell uchun.

    Hisob amallari (profil, sozlamalar, chiqish) va rol almashtirish shu
    menyuda yashaydi. Ular yana sidebar tanasiga qaytib chiqsa, scroller
    yana siqiladi — shuning uchun joylashuv test bilan qulflanadi.
    """

    def setUp(self):
        self.owner = get_user_model().objects.create_superuser(
            username="shell-owner",
            email="shell-owner@example.test",
            password="pass-12345",
        )
        self.client.force_login(self.owner)

    def _shell_urls(self):
        return {
            "app": reverse("dashboard"),
            "teacher": reverse("teacher_dashboard"),
            "backoffice": reverse("backoffice_dashboard"),
        }

    def test_every_shell_renders_the_shared_user_menu(self):
        for shell, url in self._shell_urls().items():
            with self.subTest(shell=shell):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, "components/app_user_menu.html")
                self.assertContains(response, "data-app-user-trigger")
                self.assertContains(response, "data-app-user-pop")

    def test_logout_stays_a_post_form_inside_the_menu(self):
        # Django 6 LogoutView faqat POST qabul qiladi — menyuga ko'chirishda
        # uni oddiy linkka aylantirib yuborish oson xato bo'lardi.
        for shell, url in self._shell_urls().items():
            with self.subTest(shell=shell):
                response = self.client.get(url)
                self.assertContains(response, f'action="{reverse("logout")}"')
                self.assertContains(response, "csrfmiddlewaretoken")

    def test_collapse_control_sits_in_the_sidebar_head_not_the_menu(self):
        # Yig'ish — ko'rinish boshqaruvi, hisob amali emas.
        for shell, url in self._shell_urls().items():
            with self.subTest(shell=shell):
                response = self.client.get(url)
                self.assertContains(response, "app-side-head")
                self.assertContains(response, "app-collapse-btn")
                self.assertContains(response, "data-app-collapse")

    def test_staff_role_links_are_scoped_per_shell(self):
        app_html = self.client.get(reverse("dashboard")).content.decode()
        self.assertIn(reverse("teacher_dashboard"), app_html)
        self.assertIn(reverse("backoffice_dashboard"), app_html)

        # Shablon matni o'zgaruvchi emas — Django uni escape qilmaydi.
        teacher_html = self.client.get(reverse("teacher_dashboard")).content.decode()
        self.assertIn("O'quvchi rejimi", teacher_html)
        self.assertNotIn(reverse("backoffice_dashboard"), teacher_html)

    def test_non_staff_student_sees_no_staff_links(self):
        student = get_user_model().objects.create_user(
            username="shell-student",
            email="shell-student@example.test",
            password="pass-12345",
        )
        self.client.force_login(student)
        html = self.client.get(reverse("dashboard")).content.decode()
        self.assertNotIn(reverse("teacher_dashboard"), html)
        self.assertNotIn(reverse("backoffice_dashboard"), html)
