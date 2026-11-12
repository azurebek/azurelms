import json
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from aicontrol.models import FeatureFlag
from bot.test_miniapp_parity import TEST_TOKEN, make_init_data
from frontend.a11y_probe import missing_fragment_targets, probe


User = get_user_model()


class CalmMiniAppTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="calm-mini",
            email="calm-mini@example.test",
            password="x",
            telegram_id=770001,
            total_xp=85,
        )
        self.client.force_login(self.user)

    def set_calm(self, enabled):
        FeatureFlag.objects.update_or_create(
            slug="platform_calm_v1", defaults={"enabled": enabled}
        )

    def test_flag_off_keeps_the_existing_templates_and_bytes(self):
        FeatureFlag.objects.filter(slug="platform_calm_v1").delete()
        default_home = self.client.get(reverse("bot:miniapp_home"))
        self.set_calm(False)
        explicit_home = self.client.get(reverse("bot:miniapp_home"))

        self.assertEqual(default_home.content, explicit_home.content)
        self.assertTemplateUsed(explicit_home, "bot/miniapp_home.html")
        self.assertContains(explicit_home, "/static/css/miniapp.css?v=20260721-1")
        for name, template in (
            ("bot:miniapp_courses", "bot/miniapp_courses.html"),
            ("bot:miniapp_ai", "bot/miniapp_ai.html"),
            ("bot:miniapp_profile", "bot/miniapp_profile.html"),
        ):
            with self.subTest(name=name):
                self.assertTemplateUsed(self.client.get(reverse(name)), template)

    def test_flag_on_uses_one_quiet_shell_and_canonical_frame_targets(self):
        self.set_calm(True)
        home = self.client.get(reverse("bot:miniapp_home"))

        self.assertTemplateUsed(home, "frontend_v1/calm/bot/miniapp_home.html")
        self.assertContains(home, "frontend_v1/css/calm-miniapp.css")
        self.assertNotContains(home, "/static/css/miniapp.css")
        self.assertContains(home, 'name="tgmini"')
        self.assertContains(home, f'href="{reverse("my_courses")}"')
        self.assertContains(home, f'href="{reverse("messenger:ai")}"')
        self.assertContains(home, ">Menyu</span>")
        self.assertContains(home, "85")
        html = home.content.decode()
        self.assertEqual([(item.rule, item.detail) for item in probe(html)], [])
        self.assertEqual(missing_fragment_targets(html), [])

        for name, expected_url in (
            ("bot:miniapp_courses", reverse("my_courses")),
            ("bot:miniapp_ai", reverse("messenger:ai")),
            ("bot:miniapp_profile", reverse("profile")),
        ):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertTemplateUsed(
                    response, "frontend_v1/calm/bot/miniapp_home.html"
                )
                self.assertEqual(response.context["miniapp_initial_url"], expected_url)
                self.assertContains(response, f'src="{expected_url}"')

    def test_calm_home_accepts_only_an_internal_non_recursive_frame_target(self):
        self.set_calm(True)
        internal = self.client.get(
            reverse("bot:miniapp_home"), {"target": reverse("exam_center")}
        )
        self.assertEqual(internal.context["miniapp_initial_url"], reverse("exam_center"))

        recursive = self.client.get(
            reverse("bot:miniapp_home"), {"target": reverse("bot:miniapp_ai")}
        )
        self.assertEqual(recursive.context["miniapp_initial_url"], "")

        external = self.client.get(
            reverse("bot:miniapp_home"), {"target": "https://example.com/"}
        )
        self.assertNotContains(external, "example.com")
        self.assertEqual(external.context["miniapp_initial_url"], "/users/dashboard/")

    def test_local_calm_preview_gets_the_same_frame_session_as_telegram_auth(self):
        self.set_calm(True)
        with patch("bot.views.settings.IS_LOCAL", True):
            response = self.client.get(reverse("bot:miniapp_entry"), {"preview": "1"})

        self.assertRedirects(
            response, reverse("bot:miniapp_home"), fetch_redirect_response=False
        )
        self.assertTrue(self.client.session["telegram_miniapp"])

    @override_settings(TELEGRAM_BOT_TOKEN=TEST_TOKEN)
    def test_calm_auth_wraps_a_deep_link_in_the_named_frame_shell(self):
        self.set_calm(True)
        self.client.logout()
        response = self.client.post(
            reverse("bot:miniapp_auth"),
            data=json.dumps(
                {
                    "init_data": make_init_data(self.user.telegram_id),
                    "next": reverse("exam_center"),
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        redirect = response.json()["redirect"]
        parsed = urlparse(redirect)
        self.assertEqual(parsed.path, reverse("bot:miniapp_home"))
        self.assertEqual(parse_qs(parsed.query)["target"], [reverse("exam_center")])
        self.assertTrue(self.client.session["telegram_miniapp"])

    def test_calm_and_legacy_home_keep_the_same_query_budget(self):
        self.set_calm(False)
        with CaptureQueriesContext(connection) as legacy_queries:
            self.client.get(reverse("bot:miniapp_home"))
        self.set_calm(True)
        with CaptureQueriesContext(connection) as calm_queries:
            self.client.get(reverse("bot:miniapp_home"))

        self.assertLessEqual(len(calm_queries), len(legacy_queries))

    def test_canonical_calm_page_gets_the_mini_frame_bootstrap_only_in_session(self):
        for slug in ("platform_calm_v1", "frontend_v1_learning"):
            FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": True})
        session = self.client.session
        session["telegram_miniapp"] = True
        session.save()

        framed = self.client.get(reverse("dashboard"))
        self.assertContains(framed, "frontend_v1/js/mini-frame.js")

        session = self.client.session
        session.pop("telegram_miniapp")
        session.save()
        regular = self.client.get(reverse("dashboard"))
        self.assertNotContains(regular, "frontend_v1/js/mini-frame.js")
