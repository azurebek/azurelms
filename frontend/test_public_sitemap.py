"""PUB1.1c — robots.txt va faqat e'lon qilingan sitemap.

Sitemap'dagi har URL: sozlangan origin'da, 200 qaytaradi, `index, follow` va
sahifaning o'z canonical'iga teng. Preview, filtr, token, auth va e'lon
qilinmagan obyekt kirmaydi.
"""

import re
from datetime import timedelta
from unittest import mock

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from blog.models import BlogPost
from courses.models import Course
from frontend import public_sitemap
from frontend.models import LegalPage
from frontend.public_meta import ROBOTS_INDEX
from frontend.public_sitemap import SitemapEntry, sitemap_entries
from frontend.test_public_meta import ORIGIN, head_of, meta
from frontend.test_public_route_registry import fixture_world
from sit.models import KnowledgeArticle, University


def sitemap(client=None, **extra):
    response = (client or Client()).get(reverse("sitemap_xml"), **extra)
    body = response.content.decode()
    urls = re.findall(r"<url><loc>([^<]+)</loc>(?:<lastmod>([^<]+)</lastmod>)?</url>", body)
    return response, {loc.replace("&amp;", "&"): lastmod for loc, lastmod in urls}


@override_settings(PUBLIC_CANONICAL_ORIGIN=ORIGIN)
class SitemapTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixture_world(cls)

    def test_every_entry_is_a_live_indexable_canonical_page(self):
        response, urls = sitemap()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml; charset=utf-8")
        self.assertIn("no-cache", response["Cache-Control"])
        self.assertGreater(len(urls), 5)
        for loc in urls:
            with self.subTest(loc=loc):
                self.assertTrue(loc.startswith(ORIGIN + "/"))
                self.assertNotIn("?", loc)
                page = self.client.get(loc[len(ORIGIN):])
                self.assertEqual(page.status_code, 200)
                found = meta(head_of(page))
                self.assertEqual(found["robots"], [ROBOTS_INDEX])
                self.assertEqual(found["canonicals"], [loc])

    def test_published_objects_are_listed(self):
        _, urls = sitemap()
        for path in (reverse("home"), reverse("courses"), reverse("course_detail", args=[self.course.pk]),
                     self.post.get_absolute_url(), self.university.get_absolute_url(), self.article.get_absolute_url(),
                     reverse("privacy_policy")):
            with self.subTest(path=path):
                self.assertIn(ORIGIN + path, urls)

    def test_unpublished_expired_inactive_and_sensitive_urls_are_excluded(self):
        draft = BlogPost.objects.create(title="Qoralama", author=self.staff, body="<p>q</p>")
        future = BlogPost.objects.create(title="Kelajak", author=self.staff, body="<p>k</p>",
                                         status=BlogPost.STATUS_PUBLISHED,
                                         published_at=timezone.now() + timedelta(days=3))
        hidden_university = University.objects.create(name="Yashirin universitet", short_name="YU", city="Ankara")
        hidden_article = KnowledgeArticle.objects.create(title="Yashirin qo‘llanma", category="Q", body="<p>y</p>")
        inactive = Course.objects.create(title="Yopilgan kurs", description="<p>x</p>", level="beginner", is_active=False)
        LegalPage.objects.filter(page_type="faq").delete()
        _, urls = sitemap()
        excluded = [draft.get_absolute_url(), future.get_absolute_url(), hidden_university.get_absolute_url(),
                    hidden_article.get_absolute_url(), reverse("course_detail", args=[inactive.pk]), reverse("faq_page"),
                    reverse("subscriptions:pricing"), reverse("login"), reverse("register"), reverse("password_reset"),
                    reverse("certificate_detail", args=[self.certificate.certificate_id]), reverse("healthz")]
        for path in excluded:
            with self.subTest(path=path):
                self.assertNotIn(ORIGIN + path, urls)

    def test_removed_object_leaves_on_the_next_fetch(self):
        _, before = sitemap()
        self.assertIn(ORIGIN + self.post.get_absolute_url(), before)
        BlogPost.objects.filter(pk=self.post.pk).update(status=BlogPost.STATUS_DRAFT)
        _, after = sitemap()
        self.assertNotIn(ORIGIN + self.post.get_absolute_url(), after)
        self.assertEqual(self.client.get(self.post.get_absolute_url()).status_code, 404)

    def test_lastmod_is_the_real_modification_time(self):
        _, urls = sitemap()
        post_loc = ORIGIN + self.post.get_absolute_url()
        self.assertEqual(urls[post_loc], self.post.updated_at.isoformat(timespec="seconds"))
        # Kursda haqiqiy o'zgarish vaqti yo'q — sana o'ylab topilmaydi.
        self.assertEqual(urls[ORIGIN + reverse("course_detail", args=[self.course.pk])], "")
        self.assertEqual(urls[ORIGIN + reverse("home")], "")
        reader = Client()
        reader.force_login(self.member)
        reader.post(reverse("blog:clap", args=[self.post.slug]), HTTP_ACCEPT="application/json")
        _, again = sitemap()
        self.assertEqual(again[post_loc], urls[post_loc])

    @override_settings(ALLOWED_HOSTS=["*"])
    def test_host_header_never_reaches_the_sitemap_or_robots(self):
        response, urls = sitemap(HTTP_HOST="evil.example")
        self.assertNotIn("evil.example", response.content.decode())
        robots = self.client.get(reverse("robots_txt"), HTTP_HOST="evil.example").content.decode()
        self.assertNotIn("evil.example", robots)

    def test_registry_guard_rejects_an_excluded_route(self):
        with mock.patch.object(public_sitemap, "SOURCES", (lambda: [SitemapEntry("login", ORIGIN + "/users/login/")],)):
            with self.assertRaises(ValueError):
                sitemap_entries()

    def test_locations_are_xml_escaped(self):
        entry = SitemapEntry("home", ORIGIN + "/?a=1&b=<2>")
        with mock.patch.object(public_sitemap, "SOURCES", (lambda: [entry],)):
            body = self.client.get(reverse("sitemap_xml")).content.decode()
        self.assertIn("&amp;b=&lt;2&gt;", body)
        self.assertNotIn("&b=<2>", body)


@override_settings(PUBLIC_CANONICAL_ORIGIN=ORIGIN)
class RobotsTxtTests(TestCase):
    def test_points_to_the_sitemap_and_hides_nothing(self):
        response = self.client.get(reverse("robots_txt"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        body = response.content.decode()
        self.assertIn(f"Sitemap: {ORIGIN}/sitemap.xml", body)
        # Private yo'llar ro'yxati xaritaga aylanmasin; noindex sahifa crawler'ga ochiq qoladi.
        self.assertEqual([line for line in body.splitlines() if line.startswith("Disallow")], ["Disallow:"])
        for private in ("/backoffice", "/users/", "/messenger", "/admin"):
            self.assertNotIn(private, body)

    def test_crawler_endpoints_are_read_only(self):
        for name in ("robots_txt", "sitemap_xml"):
            with self.subTest(name=name):
                self.assertEqual(self.client.post(reverse(name)).status_code, 405)
                self.assertEqual(self.client.head(reverse(name)).status_code, 200)
