"""PUB1.1d — public route javob matritsasi: method, cache, robots, referrer.

Sarlavhalar `frontend/public_policy.py` registridan bitta middleware orqali
qo'llanadi. Shared cache hali yo'q: mehmon sahifasi `private, no-cache`
(ETag → 304), shaxsiy javob `private, no-store`, sensitive/holat/xato/preview
`no-store`.
"""

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from aicontrol.models import FeatureFlag
from blog.models import BlogPost
from core.design_schema import compile_css, defaults
from core.design_service import execute
from core.flags import set_flag
from frontend.public_policy import CacheClass, route_inventory, surface_by_name
from frontend.public_response import PERMISSIONS_POLICY
from frontend.test_public_route_registry import fixture_world, kwargs_for


V1_FLAGS = ("frontend_v1_public", "frontend_v1_auth", "frontend_v1_certificates")


def set_v1(enabled):
    for slug in V1_FLAGS:
        FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": enabled})


class HeaderMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixture_world(cls)

    def routes(self, *, method="GET"):
        provider = kwargs_for(self)
        for name, _pattern, converters in route_inventory():
            policy = surface_by_name().get(name)
            if policy is not None and method in policy.methods:
                yield name, policy, reverse(name, kwargs={param: provider(name, param) for param in converters})

    def assert_no_store(self, response):
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("ETag", response)

    def test_every_public_route_for_guest_member_and_both_renderers(self):
        member = Client()
        member.force_login(self.member)
        seen = {}
        for enabled in (False, True):
            set_v1(enabled)
            for name, policy, url in self.routes():
                for label, client in (("guest", Client()), ("member", member)):
                    with self.subTest(name=name, viewer=label, v1=enabled):
                        response = client.get(url)
                        cache = response["Cache-Control"]
                        self.assertNotIn("public", cache)
                        self.assertNotIn("s-maxage", cache)
                        self.assertEqual(response["Permissions-Policy"], PERMISSIONS_POLICY)
                        if policy.cache_class == CacheClass.SENSITIVE_NO_STORE:
                            self.assert_no_store(response)
                            self.assertEqual(response["Pragma"], "no-cache")
                            self.assertEqual(response["Referrer-Policy"], "no-referrer")
                            self.assertIn("noindex", response["X-Robots-Tag"])
                        elif policy.cache_class == CacheClass.STATUS_NO_STORE or response.status_code >= 400:
                            self.assert_no_store(response)
                            self.assertIn("noindex", response["X-Robots-Tag"])
                        elif label == "member" or response.cookies:
                            # Shaxsiy javob diskda qolmaydi.
                            self.assert_no_store(response)
                        else:
                            self.assertEqual(cache, "private, no-cache")
                            self.assertIn("ETag", response)
                        decision = (cache, response.get("Referrer-Policy"))
                        self.assertEqual(seen.setdefault((name, label), decision), decision)

    def test_preview_query_token_and_error_variants(self):
        editor = Client()
        editor.force_login(self.staff)
        draft = BlogPost.objects.create(title="Qoralama", author=self.staff, body="<p>q</p>")
        preview = editor.get(draft.get_absolute_url() + "?preview=1")
        self.assertEqual(preview.status_code, 200)
        self.assert_no_store(preview)
        self.assertIn("noindex", preview["X-Robots-Tag"])

        query = self.client.get(reverse("courses") + "?q=turk")
        self.assertEqual(query["Cache-Control"], "private, no-cache")

        token = self.client.get(reverse("password_reset_confirm", args=["MQ", "yaroqsiz-token"]))
        self.assert_no_store(token)
        self.assertEqual(token["Referrer-Policy"], "no-referrer")

        status = self.client.get(reverse("telegram_auth_status", args=["yoq-token"]))
        self.assert_no_store(status)
        self.assertIn("noindex", status["X-Robots-Tag"])

        missing = self.client.get(reverse("blog:detail", args=["yoq-maqola"]))
        self.assertEqual(missing.status_code, 404)
        self.assert_no_store(missing)

    def test_guest_pages_revalidate_with_etag(self):
        url = reverse("terms_of_service")
        first = self.client.get(url)
        self.assertEqual(first.status_code, 200)
        again = self.client.get(url, HTTP_IF_NONE_MATCH=first["ETag"])
        self.assertEqual(again.status_code, 304)
        self.assertEqual(again.content, b"")
        changed = self.client.get(url, HTTP_IF_NONE_MATCH='"eskirgan"')
        self.assertEqual(changed.status_code, 200)

    def test_methods_follow_the_registry(self):
        for name, policy, url in self.routes():
            if "POST" in policy.methods:
                continue
            with self.subTest(name=name):
                response = self.client.post(url)
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response["Allow"], ", ".join(sorted(policy.methods)))
                self.assert_no_store(response)
        # Formasi bor sahifa POST'ni qabul qiladi (CSRF va forma o'z ishini qiladi).
        self.assertEqual(self.client.post(reverse("login"), {"username": "x", "password": "y"}).status_code, 200)
        self.assertEqual(self.client.head(reverse("telegram_auth_status", args=["yoq-token"])).status_code, 405)


class ThemeRevisionTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("dizayner", email="dizayner@example.test",
                                                          is_staff=True, is_superuser=True)
        set_flag("backoffice_design_workspace", enabled=True, reason="Theme revision test")

    def theme_link(self):
        html = self.client.get(reverse("about")).content.decode()
        marker = reverse("design_theme_css") + "?v="
        start = html.index(marker)
        return html[start:html.index('"', start)]

    def publish(self, radius):
        value = defaults()
        value["values"]["button-radius"] = radius
        saved = execute(self.owner, "save_draft", str(uuid4()), {"value": value, "draft_revision": 0,
                                                                 "base_version": 0})
        return execute(self.owner, "publish", str(uuid4()), {
            "draft_revision": saved["result"]["draft_revision"], "base_version": 0,
            "reason": "Theme revision test", "confirmed": True,
        })

    def test_current_revision_is_immutable_and_others_are_not_cached(self):
        link = self.theme_link()
        current = self.client.get(link)
        self.assertEqual(current["Cache-Control"], "public, max-age=31536000, immutable")
        self.assertEqual(current.content.decode(), compile_css(defaults()))
        for url in (reverse("design_theme_css"), reverse("design_theme_css") + "?v=eskirgan"):
            with self.subTest(url=url):
                self.assertIn("no-store", self.client.get(url)["Cache-Control"])

    def test_publish_and_rollback_move_pages_to_a_new_url(self):
        before = self.theme_link()
        self.publish(20)
        after = self.theme_link()
        self.assertNotEqual(before, after)
        self.assertIn("no-store", self.client.get(before)["Cache-Control"])
        self.assertIn("20px", self.client.get(after).content.decode())
        execute(self.owner, "rollback", str(uuid4()), {"target_version": 0, "base_version": 1,
                                                        "reason": "Theme revision rollback", "confirmed": True})
        rolled_back = self.theme_link()
        self.assertNotEqual(rolled_back, after)
        self.assertEqual(self.client.get(rolled_back).content.decode(), compile_css(defaults()))

    def test_flag_off_never_marks_anything_immutable(self):
        link = self.theme_link()
        set_flag("backoffice_design_workspace", enabled=False, reason="Theme revision test off")
        response = self.client.get(link)
        self.assertEqual(response.content, b"")
        self.assertIn("no-store", response["Cache-Control"])
