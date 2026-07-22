from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class ProfileInlineEditTests(TestCase):
    """Profilda tahrirlash boshqa sahifaga olib o'tmasligi kerak.

    Ilgari "Tahrirlash" Sozlamalar > Hisobga sakrardi va butun sidebar
    almashardi — foydalanuvchi kontekstni yo'qotardi.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="profile-editor",
            email="profile-editor@example.test",
            password="pass-12345",
            first_name="Eski",
        )
        self.client.force_login(self.user)

    def test_profile_renders_the_inline_form_instead_of_a_settings_link(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "components/profile_fields_form.html")
        html = response.content.decode()
        # Forma profilning o'ziga POST qiladi — sozlamalarga emas.
        self.assertIn(f'action="{reverse("profile")}"', html)
        self.assertIn("data-profile-edit-open", html)
        self.assertIn("data-profile-edit-cancel", html)

    def test_saving_from_profile_stays_on_profile(self):
        response = self.client.post(
            reverse("profile"),
            {"first_name": "Yangi", "last_name": "Ism", "phone_number": "", "bio": "Salom"},
        )
        self.assertRedirects(response, reverse("profile"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Yangi")
        self.assertEqual(self.user.bio, "Salom")

    def test_profile_post_cannot_change_username_or_email(self):
        """Eski qo'lda yozilgan handler bularni tekshiruvsiz qabul qilardi."""
        original_username = self.user.username
        original_email = self.user.email

        self.client.post(
            reverse("profile"),
            {
                "first_name": "Yangi",
                "last_name": "",
                "phone_number": "",
                "bio": "",
                "username": "boshqa-username",
                "email": "boshqa@example.test",
            },
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.username, original_username)
        self.assertEqual(self.user.email, original_email)

    def test_both_surfaces_share_one_form_component(self):
        # Ikki joyda ikki xil forma bo'lsa validatsiya ham ajralib ketadi.
        for url_name in ("profile", "settings_account"):
            with self.subTest(surface=url_name):
                response = self.client.get(reverse(url_name))
                self.assertTemplateUsed(response, "components/profile_fields_form.html")


class SettingsNextRedirectTests(TestCase):
    """`next` faqat ichki manzil bo'lsa qabul qilinadi."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="next-user",
            email="next-user@example.test",
            password="pass-12345",
        )
        self.client.force_login(self.user)

    def test_internal_next_is_honoured(self):
        response = self.client.post(
            reverse("settings_account"),
            {"first_name": "A", "last_name": "", "phone_number": "", "bio": "", "next": reverse("profile")},
        )
        self.assertRedirects(response, reverse("profile"))

    def test_external_next_is_rejected(self):
        response = self.client.post(
            reverse("settings_account"),
            {
                "first_name": "A",
                "last_name": "",
                "phone_number": "",
                "bio": "",
                "next": "https://evil.example.com/steal",
            },
        )
        self.assertRedirects(response, reverse("settings_account"))

    def test_avatar_upload_can_return_to_profile(self):
        response = self.client.post(reverse("update_avatar"), {"next": reverse("profile")})
        self.assertRedirects(response, reverse("profile"))

    def test_avatar_upload_rejects_external_next(self):
        response = self.client.post(
            reverse("update_avatar"), {"next": "https://evil.example.com/steal"}
        )
        self.assertRedirects(response, reverse("settings_account"))
