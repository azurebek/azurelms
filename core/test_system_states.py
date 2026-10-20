"""PUB1.7a — rost va o'zi yetarli holat sahifalari, qo'pol health javoblari.

Asosiy da'volar:
* 403/404/500/texnik ishlar/oflayn/CSRF to'g'ri status kodi bilan, `no-store` va `noindex`;
  tashqi shrift/ikonka/CDN, skript, inline style yo'q — faqat lokal CSS;
* 500 bazaga tegmaydi, so'rov tanasini ko'rsatmaydi, "xabardor qilindi" demaydi; GET'ni
  qayta ochish havolasi bor, POST hech qachon ko'r-ko'rona qayta yuborilmaydi;
* 403 kirishni faqat mehmonga taklif qiladi; 404 real davom yo'llarini beradi;
* texnik ishlar 503, `Retry-After` faqat owner belgilagan bo'lsa (taxmin yo'q);
* `/healthz` va `/readyz` begonaga faqat holatni beradi; tafsilot — Control Center egasiga.
"""

import re
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import HttpResponse
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import include, path, reverse

from core.models import OperationalSettings

User = get_user_model()


def _boom(request):
    raise RuntimeError("ichki xato tafsiloti")


def _forbidden(request):
    raise PermissionDenied


def _ok(request):
    return HttpResponse("ok")


urlpatterns = [
    path("_test/boom/", _boom),
    path("_test/forbidden/", _forbidden),
    path("_test/ok/", _ok),
    path("", include("core.urls")),
]
handler403 = "core.views.permission_denied"
handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"

EXTERNAL = re.compile(r'(?:href|src)="(?:https?:)?//', re.I)


class ShellAssertions:
    def assert_self_contained(self, response):
        html = response.content.decode()
        self.assertNotRegex(html, EXTERNAL)
        for forbidden in ("<script", "style=", "onclick", "fonts.googleapis", "jsdelivr", "bootstrap-icons"):
            self.assertNotIn(forbidden, html)
        self.assertIn("css/system-states.css", html)
        self.assertEqual(html.count('<meta name="robots" content="noindex, nofollow">'), 1)
        self.assertNotIn('rel="canonical"', html)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("noindex", response["X-Robots-Tag"])
        self.assertIn('<main id="main"', html)
        self.assertEqual(html.count("<h1>"), 1)


@override_settings(ROOT_URLCONF=__name__)
class StatusPageTests(ShellAssertions, TestCase):
    def setUp(self):
        self.client = Client(raise_request_exception=False)

    def test_every_state_has_its_status_and_is_self_contained(self):
        cases = {
            "/_test/nowhere/": 404,
            "/_test/forbidden/": 403,
            "/_test/boom/": 500,
            reverse("maintenance"): 503,
            reverse("offline"): 200,
        }
        for url, status in cases.items():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status)
                self.assert_self_contained(response)

    def test_500_claims_nothing_leaks_nothing_and_never_replays_a_post(self):
        get = self.client.get("/_test/boom/?sahifa=2")
        self.assertNotContains(get, "xabardor", status_code=500)
        self.assertNotContains(get, "ichki xato tafsiloti", status_code=500)
        self.assertContains(get, 'href="/_test/boom/?sahifa=2"', status_code=500)
        post = self.client.post("/_test/boom/", {"telefon": "+998901112233"})
        self.assertNotContains(post, "+998901112233", status_code=500)
        self.assertNotContains(post, 'href="/_test/boom/', status_code=500)
        self.assertContains(post, "data-no-replay", status_code=500)

    def test_500_works_without_the_database(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/_test/boom/")
        self.assertEqual(response.status_code, 500)
        self.assertEqual([q["sql"] for q in queries if "session" not in q["sql"].lower()], [])
        with mock.patch("django.template.loader.render_to_string", side_effect=ValueError("manifest")):
            bare = self.client.get("/_test/boom/")
        self.assertEqual(bare.status_code, 500)
        self.assertContains(bare, "Serverda xatolik", status_code=500)
        self.assertNotRegex(bare.content.decode(), EXTERNAL)

    def test_a_broken_database_still_gives_a_branded_404(self):
        with mock.patch("frontend.models.SiteSettings.current", side_effect=RuntimeError("baza yo'q")):
            response = self.client.get("/_test/nowhere/")
        self.assertContains(response, "AzureLMS", status_code=404)

    def test_403_offers_login_only_when_it_can_help(self):
        guest = self.client.get("/_test/forbidden/")
        self.assertContains(guest, f'href="{reverse("login")}?next=/_test/forbidden/"', status_code=403)
        user = User.objects.create_user("oddiy", "o@example.test", "x")
        self.client.force_login(user)
        member = self.client.get("/_test/forbidden/")
        self.assertNotContains(member, reverse("login"), status_code=403)

    def test_404_gives_real_ways_forward(self):
        response = self.client.get("/_test/nowhere/")
        for href in ('href="/"', 'href="/courses/"', 'href="/blog/"'):
            self.assertContains(response, href, status_code=404)


class MaintenanceTests(ShellAssertions, TestCase):
    def test_no_owner_time_means_no_guess(self):
        response = self.client.get(reverse("maintenance"))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("Retry-After", response)
        self.assertContains(response, "hali belgilanmagan", status_code=503)
        self.assertNotContains(response, "data-retry-after", status_code=503)
        self.assertNotContains(response, "Tez orada", status_code=503)

    def test_owner_time_is_sent_and_shown(self):
        row = OperationalSettings.load()
        row.maintenance_retry_after_minutes = 30
        row.save()
        response = self.client.get(reverse("maintenance"))
        self.assertEqual(response["Retry-After"], "1800")
        self.assertContains(response, "30 daqiqadan", status_code=503)

    def test_a_broken_database_drops_the_promise_not_the_page(self):
        with mock.patch("core.operational_settings.current_thresholds", side_effect=RuntimeError("baza yo'q")):
            response = self.client.get(reverse("maintenance"))
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("Retry-After", response)

    def test_retry_is_a_plain_get_link(self):
        response = self.client.get(reverse("maintenance"))
        self.assertContains(response, 'href="/"', status_code=503)
        self.assertNotContains(response, "reload", status_code=503)


class OfflineTests(TestCase):
    def test_offline_does_not_promise_an_offline_app(self):
        response = self.client.get(reverse("offline"))
        self.assertContains(response, "oflayn rejimda ishlamaydi")
        self.assertNotContains(response, "reload")


class CsrfPageTests(ShellAssertions, TestCase):
    def test_csrf_failure_uses_the_same_shell_and_reopens_with_get(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("login"), {"username": "x", "password": "y"})
        self.assertEqual(response.status_code, 403)
        self.assert_self_contained(response)
        self.assertContains(response, f'href="{reverse("login")}"', status_code=403)


class HealthPayloadTests(TestCase):
    def test_strangers_get_only_the_status(self):
        self.assertEqual(self.client.get(reverse("healthz")).json(), {"status": "alive"})
        self.assertEqual(self.client.get(reverse("readyz")).json(), {"status": "ready"})
        member = User.objects.create_user("oddiy", "o@example.test", "x")
        self.client.force_login(member)
        self.assertEqual(self.client.get(reverse("readyz")).json(), {"status": "ready"})

    def test_the_owner_gets_the_detail(self):
        owner = User.objects.create_superuser("owner", "owner@example.test", "x")
        self.client.force_login(owner)
        readyz = self.client.get(reverse("readyz")).json()
        self.assertEqual(set(readyz), {"status", "environment", "release", "checks"})
        self.assertEqual(set(self.client.get(reverse("healthz")).json()), {"status", "environment", "release"})

    def test_orchestrator_semantics_are_kept(self):
        with CaptureQueriesContext(connection) as queries:
            alive = self.client.get(reverse("healthz"))
        self.assertEqual((alive.status_code, len(queries)), (200, 0))
        for name in ("healthz", "readyz"):
            with self.subTest(name=name):
                self.assertEqual(self.client.post(reverse(name)).status_code, 405)
                self.assertIn("no-store", self.client.get(reverse(name))["Cache-Control"])


class AssetTests(SimpleTestCase):
    def test_the_state_stylesheet_is_local_and_complete(self):
        css = (Path(settings.BASE_DIR) / "static" / "css" / "system-states.css").read_text(encoding="utf-8")
        self.assertNotRegex(css, r"@import|url\(\s*['\"]?(?:https?:)?//")
        for rule in ("prefers-color-scheme: dark", "forced-colors: active", ":focus-visible"):
            self.assertIn(rule, css)
