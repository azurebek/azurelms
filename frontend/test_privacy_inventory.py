"""PUB1.5b — brauzerda nima saqlanadi, qaysi tashqi manba yuklanadi va forma nima yig'adi.

Asosiy da'volar:
* brauzer xotirasi yoki cookie'ga tegadigan har fayl ro'yxatda; ro'yxatdan
  yaratilgan hujjat repo'dagi bilan bir xil (qo'lda tahrir ushlanadi);
* public va auth javoblari faqat ro'yxatdagi cookie'larni qo'yadi; sahifalar
  faqat ro'yxatdagi tashqi manbalarni yuklaydi; kuzatuv xizmati na sahifada,
  na CSP'da bor — ya'ni rozilikdan oldin ixtiyoriy so'rov 0, banner kerak emas;
* "KVKK/GDPR mos" kabi tasdiqlanmagan da'vo yo'q;
* ma'lumot yig'adigan har forma yonida eslatma va maxfiylik havolasi.
"""

import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from aicontrol.models import FeatureFlag
from cohorts.test_checkout_side_effects import CheckoutFixtureMixin
from core.csp_policy import build_csp_policy
from frontend import privacy_inventory as inventory
from frontend.activity_notices import NOTICES
from frontend.public_policy import route_inventory, surface_by_name
from frontend.test_public_route_registry import fixture_world, kwargs_for
from users.forms import CustomUserCreationForm

User = get_user_model()
V1_FLAGS = ("frontend_v1_public", "frontend_v1_auth", "frontend_v1_certificates")
EXTERNAL = re.compile(r'''<(?:script|link|img|iframe|source)\b[^>]*?\b(?:src|href)=["'](https?:)?//([^/"']+)''', re.I)
COMPLIANCE_CLAIM = re.compile(r"\b(kvkk|gdpr)\b[^<]{0,40}\b(compliant|mos keladi|muvofiq|to‘liq mos|to'liq mos)", re.I)


def set_v1(enabled):
    for slug in V1_FLAGS:
        FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": enabled})


class InventoryCoverageTests(TestCase):
    def test_every_file_that_touches_browser_storage_is_inventoried(self):
        self.assertEqual(inventory.uncovered_files(), [])
        self.assertEqual(inventory.missing_code_paths(), [])

    def test_discovery_catches_a_new_storage_write_in_js_templates_and_python(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            (base / "static" / "js").mkdir(parents=True)
            (base / "static" / "js" / "yangi.js").write_text('localStorage.setItem("yangi-kalit", "1");')
            (base / "templates").mkdir()
            (base / "templates" / "sahifa.html").write_text("<script>document.cookie = 'x=1';</script>")
            (base / "core").mkdir()
            (base / "core" / "korinish.py").write_text("response.set_cookie('kuzatuv', '1')\n")
            (base / "core" / "faqat_oqish.js").write_text("const t = document.cookie.match(/csrftoken=/);")
            found = inventory.storage_files(root)
        self.assertIn("static/js/yangi.js", found)
        self.assertIn("templates/sahifa.html", found)
        self.assertIn("core/korinish.py", found)
        self.assertNotIn("core/faqat_oqish.js", found)  # faqat o'qish — yozuv emas

    def test_the_committed_document_matches_the_registry(self):
        self.assertEqual(inventory.inventory_path().read_text(encoding="utf-8"), inventory.render_markdown())

    def test_django_cookie_names_come_from_settings(self):
        names = inventory.active_cookie_names()
        self.assertEqual(names, {settings.SESSION_COOKIE_NAME, settings.CSRF_COOKIE_NAME, "messages"})


class ResponseEvidenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixture_world(cls)

    def public_get_urls(self):
        provider = kwargs_for(self)
        surfaces = surface_by_name()
        for name, _pattern, converters in route_inventory():
            policy = surfaces.get(name)
            if policy is None or "GET" not in policy.methods or name == "telegram_auth_status":
                continue
            yield name, reverse(name, kwargs={param: provider(name, param) for param in converters})

    def test_responses_set_only_inventoried_cookies_and_pages_load_only_listed_third_parties(self):
        known = {item.name for item in inventory.ITEMS}
        allowed = {origin.split("//", 1)[1] for origin in inventory.allowed_origins()}
        seen_cookies, seen_hosts = set(), set()
        own_host = urlsplit(settings.PUBLIC_CANONICAL_ORIGIN).netloc.lower()
        for enabled in (False, True):
            set_v1(enabled)
            for viewer in (None, self.member):
                self.client.logout()
                if viewer:
                    self.client.force_login(viewer)
                for name, url in self.public_get_urls():
                    response = self.client.get(url)
                    html = response.content.decode("utf-8", errors="ignore")
                    # O'z saytimizning to'liq manzili (canonical, og) — birinchi tomon.
                    hosts = {match[1].lower() for match in EXTERNAL.findall(html)} - {own_host, "testserver"}
                    with self.subTest(v1=enabled, viewer=getattr(viewer, "username", "mehmon"), name=name):
                        self.assertLessEqual(set(response.cookies), known)
                        self.assertLessEqual(hosts, allowed)
                        for tracker in inventory.TRACKER_HOSTS:
                            self.assertNotIn(tracker, html)
                    seen_cookies |= set(response.cookies)
                    seen_hosts |= hosts
        self.assertIn(settings.CSRF_COOKIE_NAME, seen_cookies)  # formali sahifalar haqiqatan tekshirildi

    def test_login_and_logout_set_only_inventoried_cookies(self):
        known = {item.name for item in inventory.ITEMS}
        response = self.client.post(reverse("login"), {"username": "oquvchi", "password": "Oquvchi-parol-2026!"})
        self.assertEqual(response.status_code, 302)
        self.assertIn(settings.SESSION_COOKIE_NAME, response.cookies)
        self.assertLessEqual(set(response.cookies), known)
        self.assertLessEqual(set(self.client.post(reverse("logout")).cookies), known)

    def test_the_csp_allows_no_tracking_service(self):
        policy = build_csp_policy("azurelms.example")
        flat = " ".join(" ".join(values) for values in policy["DIRECTIVES"].values())
        for tracker in inventory.TRACKER_HOSTS:
            self.assertNotIn(tracker, flat)

    def test_templates_make_no_unverified_compliance_claim(self):
        offenders = []
        for path in (Path(settings.BASE_DIR) / "templates").rglob("*.html"):
            if COMPLIANCE_CLAIM.search(path.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(path.as_posix())
        self.assertEqual(offenders, [])


class ActivityNoticeTests(CheckoutFixtureMixin, TestCase):
    def setUp(self):
        FeatureFlag.objects.update_or_create(slug="public_registration", defaults={"enabled": True})
        self.privacy_link = f'href="{reverse("privacy_policy")}"'

    def assert_notice(self, html, key, count=1):
        block = re.findall(rf'<p[^>]*data-activity-notice="{key}"[^>]*>(.*?)</p>', html, re.S)
        self.assertEqual(len(block), count, key)
        self.assertIn(NOTICES[key].text, block[0])
        self.assertIn(self.privacy_link, block[0])

    def test_auth_forms_carry_their_notice_on_both_renderers(self):
        for enabled in (False, True):
            set_v1(enabled)
            with self.subTest(v1=enabled):
                self.assert_notice(self.client.get(reverse("register")).content.decode(), "register")
                self.assert_notice(self.client.get(reverse("password_reset")).content.decode(), "password_reset")
                login = self.client.get(reverse("login")).content.decode()
                self.assert_notice(login, "telegram_login")

    def test_closed_registration_does_not_promise_a_new_profile(self):
        FeatureFlag.objects.update_or_create(slug="public_registration", defaults={"enabled": False})
        for enabled in (False, True):
            set_v1(enabled)
            with self.subTest(v1=enabled):
                self.assertNotIn('data-activity-notice="telegram_login"', self.client.get(reverse("login")).content.decode())

    def test_blog_comment_notice_appears_once_above_the_main_form(self):
        world = type("World", (), {})
        fixture_world(world)
        world.post.allow_comments = True
        world.post.save()
        self.client.force_login(world.member)
        for enabled in (False, True):
            set_v1(enabled)
            with self.subTest(v1=enabled):
                html = self.client.get(reverse("blog:detail", args=[world.post.slug])).content.decode()
                self.assert_notice(html, "blog_comment")

    @override_settings(PRIVATE_MEDIA_ROOT=tempfile.gettempdir())
    def test_payment_receipt_notice_sits_on_both_checkout_forms(self):
        from core.flags import set_flag

        self.build_course_with_cohort()
        self.client.force_login(self.student)
        url = reverse("cohorts:checkout", args=[self.course.pk])
        for enabled in (False, True):
            set_flag("frontend_v1_checkout", enabled=enabled, reason="PUB1.5b test")
            with self.subTest(v1=enabled):
                html = self.client.get(url, {"plan_id": self.plan.pk}).content.decode()
                self.assertIn('name="receipt_image"', html)
                self.assert_notice(html, "payment_receipt")

    def test_the_register_notice_names_exactly_the_fields_the_form_collects(self):
        # Formaga yangi maydon qo'shilsa, eslatma ham yangilanishi kerak.
        self.assertEqual(set(CustomUserCreationForm().fields), {"first_name", "last_name", "email", "password1", "password2"})
