"""PUB1.0g — Blog anonim kuzatuvi yopildi.

Ilgari maqolani ochgan har anonimga bir yillik `blog_visitor` cookie qo'yilar,
o'qish IP xeshi (soxtalashtiriladigan chap XFF'dan) va user-agent bilan
yozilardi; anonim olqish ham ayni cookie'ni yaratardi. Owner qarori (PUB-D6)
bo'lmaguncha anonim kuzatuv yo'q, kirgan o'quvchi uchun IP/UA saqlanmaydi.
"""

import re
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag
from blog.models import BlogPost, BlogPostClap, BlogPostRead
from blog.tracking_cleanup import legacy_tracking
from blog.utils import LEGACY_VISITOR_COOKIE
from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import PROBE_FUNCTIONS


User = get_user_model()
WRITE = re.compile(r"^\s*(INSERT|UPDATE|DELETE|REPLACE)\b", re.IGNORECASE)
BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0 Safari/537.36"


def set_v1(enabled):
    FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": enabled})


class TrackingMixin:
    def setUp(self):
        self.author = User.objects.create_user("muallif", email="muallif@example.test", is_staff=True)
        self.reader = User.objects.create_user("oquvchi", email="oquvchi@example.test", password="Kuchli-parol-2026")
        self.post = BlogPost.objects.create(
            title="Kuzatuvsiz maqola", author=self.author, body="<p>Matn</p>",
            status=BlogPost.STATUS_PUBLISHED, published_at=timezone.now(),
        )
        self.detail = reverse("blog:detail", args=[self.post.slug])
        self.clap = reverse("blog:clap", args=[self.post.slug])

    def writes(self, call):
        with CaptureQueriesContext(connection) as queries:
            response = call()
        return response, [q["sql"] for q in queries.captured_queries if WRITE.match(q["sql"])]


class AnonymousReadTests(TrackingMixin, TestCase):
    def test_guest_reading_sets_no_cookie_and_writes_nothing(self):
        for enabled in (False, True):
            set_v1(enabled)
            with self.subTest(v1=enabled):
                response, writes = self.writes(lambda: self.client.get(
                    self.detail, HTTP_USER_AGENT=BROWSER, HTTP_X_FORWARDED_FOR="203.0.113.7",
                ))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(writes, [])
                self.assertNotIn(LEGACY_VISITOR_COOKIE, response.cookies)
        self.assertFalse(BlogPostRead.objects.exists())
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, 0)

    def test_legacy_one_year_cookie_is_removed_and_ignored(self):
        BlogPostClap.objects.create(post=self.post, viewer_key="anon:eski-token", clap_count=7)
        self.client.cookies[LEGACY_VISITOR_COOKIE] = "eski-token"
        for enabled in (False, True):
            set_v1(enabled)
            with self.subTest(v1=enabled):
                response, writes = self.writes(lambda: self.client.get(self.detail, HTTP_USER_AGENT=BROWSER))
                self.assertEqual(writes, [])
                cookie = response.cookies[LEGACY_VISITOR_COOKIE]
                self.assertEqual(cookie.value, "")
                self.assertEqual(cookie["max-age"], 0)
                # Eski cookie bilan olingan olqish holati endi tiklanmaydi.
                self.assertEqual(response.context["my_clap_count"], 0)
                self.client.cookies[LEGACY_VISITOR_COOKIE] = "eski-token"

    def test_staff_preview_and_bots_write_nothing(self):
        bot = Client()
        bot.force_login(self.reader)
        _, writes = self.writes(lambda: bot.get(self.detail, HTTP_USER_AGENT="Googlebot/2.1"))
        self.assertEqual(writes, [])
        draft = BlogPost.objects.create(title="Qoralama", author=self.author, body="<p>x</p>")
        editor = Client()
        editor.force_login(self.author)
        response, writes = self.writes(lambda: editor.get(reverse("blog:detail", args=[draft.slug]) + "?preview=1"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(writes, [])


class SignedInReadTests(TrackingMixin, TestCase):
    def test_signed_in_read_counts_once_without_ip_or_user_agent(self):
        self.client.force_login(self.reader)
        for _ in range(2):
            self.client.get(self.detail, HTTP_USER_AGENT=BROWSER, HTTP_X_FORWARDED_FOR="203.0.113.7")
        read = BlogPostRead.objects.get()
        self.assertEqual((read.user, read.viewer_key), (self.reader, f"user:{self.reader.pk}"))
        self.assertEqual((read.ip_hash, read.user_agent), ("", ""))
        self.post.refresh_from_db()
        self.assertEqual(self.post.view_count, 1)


class ClapTests(TrackingMixin, TestCase):
    def test_guest_clap_requires_login_and_leaves_no_trace(self):
        response, writes = self.writes(lambda: self.client.post(self.clap, HTTP_ACCEPT="application/json"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "auth_required")
        self.assertIn(reverse("login"), response.json()["login_url"])
        self.assertEqual(writes, [])
        self.assertNotIn(LEGACY_VISITOR_COOKIE, response.cookies)

        plain = self.client.post(self.clap)
        self.assertEqual(plain.status_code, 302)
        self.assertTrue(plain["Location"].startswith(reverse("login") + "?next="))
        self.assertFalse(BlogPostClap.objects.exists())
        self.post.refresh_from_db()
        self.assertEqual(self.post.clap_count, 0)

    def test_guest_sees_a_sign_in_link_instead_of_the_clap_form(self):
        for enabled in (False, True):
            set_v1(enabled)
            with self.subTest(v1=enabled):
                response = self.client.get(self.detail)
                self.assertContains(response, "data-clap-login")
                self.assertNotContains(response, f'action="{self.clap}"')

    def test_signed_in_clap_accumulates_per_reader_without_cookie(self):
        self.client.force_login(self.reader)
        first = self.client.post(self.clap, HTTP_ACCEPT="application/json")
        second = self.client.post(self.clap, HTTP_ACCEPT="application/json")
        self.assertEqual((first.status_code, second.json()["my_clap_count"]), (200, 2))
        self.assertNotIn(LEGACY_VISITOR_COOKIE, second.cookies)
        clap = BlogPostClap.objects.get()
        self.assertEqual((clap.user, clap.viewer_key), (self.reader, f"user:{self.reader.pk}"))
        for enabled in (False, True):
            set_v1(enabled)
            with self.subTest(v1=enabled):
                self.assertNotContains(self.client.get(self.detail), "data-clap-login")


class LegacyCleanupTests(TrackingMixin, TestCase):
    def seed_legacy(self):
        BlogPostRead.objects.create(post=self.post, viewer_key="anon:a", ip_hash="f" * 64, user_agent=BROWSER)
        BlogPostRead.objects.create(post=self.post, viewer_key="anon:b", ip_hash="e" * 64, user_agent=BROWSER)
        BlogPostRead.objects.create(post=self.post, viewer_key=f"user:{self.reader.pk}", user=self.reader,
                                    ip_hash="d" * 64, user_agent=BROWSER)
        BlogPostClap.objects.create(post=self.post, viewer_key="anon:a", clap_count=3)
        BlogPostClap.objects.create(post=self.post, viewer_key=f"user:{self.reader.pk}", user=self.reader, clap_count=1)
        BlogPost.objects.filter(pk=self.post.pk).update(view_count=3, clap_count=4)

    def test_report_mode_changes_nothing(self):
        self.seed_legacy()
        out = StringIO()
        call_command("purge_blog_read_tracking", stdout=out)
        self.assertIn("anonim o'qish 2", out.getvalue())
        self.assertIn("--apply", out.getvalue())
        self.assertEqual(legacy_tracking().total, 4)

    def test_apply_purges_anonymous_rows_redacts_readers_and_keeps_totals(self):
        self.seed_legacy()
        call_command("purge_blog_read_tracking", "--apply", stdout=StringIO())
        self.assertEqual(legacy_tracking().total, 0)
        read = BlogPostRead.objects.get()
        self.assertEqual((read.user, read.ip_hash, read.user_agent), (self.reader, "", ""))
        self.assertEqual(list(BlogPostClap.objects.values_list("viewer_key", flat=True)), [f"user:{self.reader.pk}"])
        self.post.refresh_from_db()
        self.assertEqual((self.post.view_count, self.post.clap_count), (3, 4))
        # Qayta yugurish xavfsiz.
        call_command("purge_blog_read_tracking", "--apply", stdout=StringIO())
        self.assertEqual(BlogPostRead.objects.count(), 1)

    def test_control_center_shows_leftover_tracking(self):
        from frontend.models import AboutPage, AuthPageSettings, LandingPage, LegalPage, SiteSettings
        from blog.models import BlogHomeSettings

        for model in (SiteSettings, AuthPageSettings, LandingPage, AboutPage, BlogHomeSettings):
            model.objects.create()
        for page_type in ("privacy", "terms", "faq"):
            LegalPage.objects.create(page_type=page_type, title="Owner", content="<p>Owner matni</p>")
        probe = lambda: PROBE_FUNCTIONS["public_content"](capability_by_slug("public_content"))  # noqa: E731
        self.seed_legacy()
        result = probe()
        self.assertEqual(result.status, "amber")
        self.assertIn(("blog_legacy_tracking", "4"), result.details)
        call_command("purge_blog_read_tracking", "--apply", stdout=StringIO())
        self.assertEqual(probe().status, "green")
