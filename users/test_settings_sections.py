from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


User = get_user_model()

SECTIONS = {
    "settings_account": ("account", "users/settings/account.html", "Hisob"),
    "settings_privacy": ("privacy", "users/settings/privacy.html", "Maxfiylik"),
    "settings_billing": ("billing", "users/settings/billing.html", "To'lov"),
    "settings_capabilities": ("capabilities", "users/settings/capabilities.html", "Imkoniyatlar"),
}


class SettingsSectionRoutingTests(TestCase):
    """Sozlamalar 4 alohida sahifaga ajratildi.

    Eski `settings` va `ai_memory` nomlari ko'p shablonda ishlatiladi —
    ular sinmasligi shart, aks holda profil menyusi, Mini App va
    messenger havolalari 404 beradi.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="settings-user",
            email="settings-user@example.test",
            password="pass-12345",
        )
        self.client.force_login(self.user)

    def test_each_section_renders_with_its_own_template(self):
        for url_name, (section, template, heading) in SECTIONS.items():
            with self.subTest(section=section):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)
                self.assertTemplateUsed(response, "components/settings_nav.html")
                self.assertEqual(response.context["settings_section"], section)
                self.assertContains(response, heading)

    def test_settings_entry_point_redirects_to_account(self):
        response = self.client.get(reverse("settings"))
        self.assertRedirects(response, reverse("settings_account"))

    def test_legacy_ai_memory_url_redirects_to_privacy(self):
        response = self.client.get(reverse("ai_memory"))
        self.assertRedirects(response, reverse("settings_privacy"))

    def test_every_section_links_to_all_the_others(self):
        # Nav yagona manba — bittasi tushib qolsa bo'lim yetib bo'lmas holga keladi.
        targets = [reverse(name) for name in SECTIONS]
        for url_name in SECTIONS:
            with self.subTest(section=url_name):
                html = self.client.get(reverse(url_name)).content.decode()
                for target in targets:
                    self.assertIn(f'href="{target}"', html)

    def test_settings_replaces_the_dashboard_sidebar_nav(self):
        """Sozlamalarda bitta sidebar bo'ladi.

        Dashboard elementlari o'rnini bo'limlar egallaydi — aks holda
        sahifada ikkita parallel navigatsiya paydo bo'ladi.
        """
        html = self.client.get(reverse("settings_account")).content.decode()

        for url_name in (
            "my_courses",
            "exam_center",
            "certificates",
            "leaderboard",
            "attendance_calendar",
            "help_center",
        ):
            with self.subTest(dashboard_item=url_name):
                self.assertNotIn(f'href="{reverse(url_name)}"', html)

        # Chiqish yo'li qolishi kerak.
        self.assertIn(f'href="{reverse("dashboard")}"', html)

    def test_sections_require_login(self):
        self.client.logout()
        for url_name in SECTIONS:
            with self.subTest(section=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 302)
                self.assertIn("/users/login/", response["Location"])


class SettingsSectionContentTests(TestCase):
    """Har bo'lim o'ziga tegishli boshqaruvni ko'rsatishi kerak."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="settings-content",
            email="settings-content@example.test",
            password="pass-12345",
        )
        self.client.force_login(self.user)

    def test_account_holds_profile_password_and_theme(self):
        html = self.client.get(reverse("settings_account")).content.decode()
        self.assertIn(f'action="{reverse("settings_account")}"', html)
        self.assertIn(f'action="{reverse("update_password")}"', html)
        self.assertIn(f'action="{reverse("update_avatar")}"', html)
        self.assertIn("data-theme-set", html)

    def test_capabilities_holds_the_ai_preference_controls(self):
        html = self.client.get(reverse("settings_capabilities")).content.decode()
        self.assertIn(f'action="{reverse("update_ai_tone")}"', html)
        self.assertIn(f'action="{reverse("update_ai_model")}"', html)
        # Web qidiruv endpointi bor edi, lekin UI'da hech qayerda yo'q edi.
        self.assertIn(f'action="{reverse("update_ai_web_search_effort")}"', html)

    @override_settings(
        AI_FREE_TIER_MODE=True,
        GEMINI_FREE_MODEL_ALLOWLIST=(
            User.AI_MODEL_25_FLASH,
            User.AI_MODEL_25_FLASH_LITE,
        ),
    )
    def test_capabilities_only_shows_effective_free_tier_choices(self):
        self.user.ai_model = User.AI_MODEL_31_PRO
        self.user.ai_web_search_effort = User.AI_WEB_SEARCH_HEAVY
        self.user.save(update_fields=["ai_model", "ai_web_search_effort"])

        response = self.client.get(reverse("settings_capabilities"))
        html = response.content.decode()

        self.assertEqual(
            response.context["model_choices"],
            [
                (User.AI_MODEL_25_FLASH, "Gemini 2.5 Flash"),
                (User.AI_MODEL_25_FLASH_LITE, "Gemini 2.5 Flash-Lite"),
            ],
        )
        self.assertEqual(
            [value for value, _label in response.context["web_search_choices"]],
            [User.AI_WEB_SEARCH_LIGHT, User.AI_WEB_SEARCH_MEDIUM],
        )
        self.assertIn(f'value="{User.AI_MODEL_25_FLASH}"', html)
        self.assertIn(f'value="{User.AI_MODEL_25_FLASH_LITE}"', html)
        self.assertNotIn(f'value="{User.AI_MODEL_31_PRO}"', html)
        self.assertNotIn(f'value="{User.AI_WEB_SEARCH_HEAVY}"', html)

    @override_settings(AI_FREE_TIER_MODE=False)
    def test_non_free_mode_restores_heavy_effort_choice(self):
        response = self.client.get(reverse("settings_capabilities"))

        self.assertIn(
            User.AI_WEB_SEARCH_HEAVY,
            [value for value, _label in response.context["web_search_choices"]],
        )

    def test_privacy_holds_the_memory_controls(self):
        response = self.client.get(reverse("settings_privacy"))
        self.assertIn(f'action="{reverse("ai_memory_toggle")}"', response.content.decode())
        self.assertIn("memory_total", response.context)

    def test_billing_holds_usage_and_subscription_link(self):
        response = self.client.get(reverse("settings_billing"))
        html = response.content.decode()
        self.assertIn("ai_usage", response.context)
        self.assertIn(f'href="{reverse("subscriptions")}"', html)


class SettingsMutationRedirectTests(TestCase):
    """Har POST o'zi tegishli bo'limga qaytishi kerak.

    Bo'limlarga ajratilgach `redirect('settings')` bilan qoldirilsa,
    foydalanuvchi AI sozlamasini o'zgartirgach Hisob sahifasiga tushib
    qolardi.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="settings-redirect",
            email="settings-redirect@example.test",
            password="pass-12345",
        )
        self.client.force_login(self.user)

    def test_ai_preference_posts_return_to_capabilities(self):
        cases = [
            ("update_ai_tone", {"ai_tone": "formal"}),
            ("update_ai_model", {"ai_model": User.effective_ai_model_choices()[0][0]}),
            ("update_ai_web_search_effort", {"ai_web_search_effort": "medium"}),
        ]
        for url_name, payload in cases:
            with self.subTest(endpoint=url_name):
                response = self.client.post(reverse(url_name), payload)
                self.assertRedirects(response, reverse("settings_capabilities"))

    def test_memory_toggle_returns_to_privacy(self):
        response = self.client.post(reverse("ai_memory_toggle"), {"ai_memory_enabled": "0"})
        self.assertRedirects(response, reverse("settings_privacy"))

    def test_avatar_post_returns_to_account(self):
        response = self.client.post(reverse("update_avatar"), {})
        self.assertRedirects(response, reverse("settings_account"))
