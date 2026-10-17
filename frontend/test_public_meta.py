"""PUB1.1b — deterministik metadata va sozlangan canonical origin.

Har `<head>` bitta `{% public_meta_tags %}` blokidan: bitta robots, bittadan
ortiq bo'lmagan description/canonical, takrorlanmaydigan OG. Canonical va
ulashish havolalari faqat `PUBLIC_CANONICAL_ORIGIN`dan — `Host` sarlavhasi
ta'sir qilmaydi.
"""

import json
import re
import shutil
import tempfile
from collections import Counter

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag
from blog.models import BlogPost
from courses.models import Course
from frontend.checks import CANONICAL_ORIGIN_CHECK_ID, check_canonical_origin
from frontend.public_meta import DESCRIPTION_MAX, ROBOTS_INDEX, ROBOTS_NOINDEX, ROBOTS_QUERY, ROBOTS_SENSITIVE
from frontend.public_policy import CacheClass, route_inventory, surface_by_name
from frontend.test_public_route_registry import fixture_world, kwargs_for
from sit.models import KnowledgeArticle


ORIGIN = "https://lms.example.test"
V1_FLAGS = ("frontend_v1_public", "frontend_v1_auth", "frontend_v1_certificates")
GIF = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00"
       b",\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")


def set_v1(enabled):
    for slug in V1_FLAGS:
        FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": enabled})


def head_of(response):
    return response.content.decode("utf-8", "ignore").split("</head>", 1)[0]


def meta(head):
    return {
        "titles": len(re.findall(r"<title>", head)),
        "robots": re.findall(r'<meta name="robots" content="([^"]*)"', head),
        "descriptions": re.findall(r'<meta name="description" content="([^"]*)"', head),
        "canonicals": re.findall(r'<link rel="canonical" href="([^"]*)"', head),
        "og": re.findall(r'<meta property="(og:[^"]+)" content="([^"]*)"', head),
        "json_ld": re.findall(r'<script type="application/ld\+json">(.*?)</script>', head, re.S),
    }


@override_settings(PUBLIC_CANONICAL_ORIGIN=ORIGIN)
class PublicHeadContractTests(TestCase):
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
            yield name, policy, reverse(name, kwargs={param: provider(name, param) for param in converters})

    def expected(self, name, policy, url):
        if policy.audience == "sensitive":
            return ROBOTS_SENSITIVE, []
        if policy.cache_class == CacheClass.STATUS_NO_STORE or name == "subscriptions:pricing":
            return ROBOTS_NOINDEX, []
        return ROBOTS_INDEX, [ORIGIN + url]

    def test_every_public_head_is_single_sourced_and_follows_the_registry(self):
        seen = {}
        for enabled in (False, True):
            set_v1(enabled)
            for name, policy, url in self.public_get_urls():
                with self.subTest(name=name, v1=enabled):
                    found = meta(head_of(self.client.get(url)))
                    self.assertEqual(found["titles"], 1)
                    self.assertEqual(len(found["robots"]), 1)
                    self.assertLessEqual(len(found["descriptions"]), 1)
                    self.assertLessEqual(len(found["canonicals"]), 1)
                    duplicates = [prop for prop, count in Counter(p for p, _ in found["og"]).items() if count > 1]
                    self.assertEqual(duplicates, [])
                    robots, canonicals = self.expected(name, policy, url)
                    self.assertEqual(found["robots"], [robots])
                    self.assertEqual(found["canonicals"], canonicals)
                    if canonicals:
                        self.assertIn(("og:url", canonicals[0]), found["og"])
                    else:
                        self.assertEqual(found["og"], [])
                    for description in found["descriptions"]:
                        self.assertLessEqual(len(description), DESCRIPTION_MAX)
                        self.assertNotIn("<", description)
                    # Legacy va V1 bir xil qaror beradi.
                    decision = (tuple(found["robots"]), tuple(found["canonicals"]))
                    self.assertEqual(seen.setdefault(name, decision), decision)

    @override_settings(ALLOWED_HOSTS=["*"])
    def test_hostile_host_header_never_reaches_absolute_urls(self):
        for enabled in (False, True):
            set_v1(enabled)
            for url in (reverse("course_detail", args=[self.course.pk]), self.post.get_absolute_url(), reverse("home")):
                with self.subTest(url=url, v1=enabled):
                    response = self.client.get(url, HTTP_HOST="evil.example")
                    self.assertEqual(response.status_code, 200)
                    self.assertNotIn("evil.example", head_of(response))
                    self.assertTrue(all(c.startswith(ORIGIN) for c in meta(head_of(response))["canonicals"]))
        response = self.client.get(self.post.get_absolute_url(), HTTP_HOST="evil.example")
        self.assertNotIn("evil.example", response.content.decode())
        self.assertIn("lms.example.test", response.context["telegram_share_url"])

    def test_query_and_page_variants_are_not_indexed_but_point_to_the_clean_base(self):
        cases = {
            reverse("courses") + "?q=turk": (ROBOTS_QUERY, ORIGIN + reverse("courses")),
            reverse("blog:list") + "?q=maqola": (ROBOTS_QUERY, ORIGIN + reverse("blog:list")),
            reverse("blog:list") + "?page=1": (ROBOTS_QUERY, ORIGIN + reverse("blog:list")),
            reverse("sit:university_list") + "?city=Istanbul": (ROBOTS_QUERY, ORIGIN + reverse("sit:university_list")),
            reverse("courses") + "?utm_source=telegram": (ROBOTS_INDEX, ORIGIN + reverse("courses")),
            reverse("course_detail", args=[self.course.pk]) + "?utm_campaign=x": (
                ROBOTS_INDEX, ORIGIN + reverse("course_detail", args=[self.course.pk])),
        }
        for url, (robots, canonical) in cases.items():
            with self.subTest(url=url):
                found = meta(head_of(self.client.get(url)))
                self.assertEqual((found["robots"], found["canonicals"]), ([robots], [canonical]))

    def test_preview_and_unpublished_pages_are_never_indexed(self):
        draft = BlogPost.objects.create(title="Qoralama", author=self.staff, body="<p>q</p>")
        hidden = KnowledgeArticle.objects.create(title="Yashirin", category="Q", body="<p>y</p>")
        editor = Client()
        editor.force_login(self.staff)
        for url in (draft.get_absolute_url() + "?preview=1", hidden.get_absolute_url() + "?preview=1",
                    self.post.get_absolute_url() + "?preview=1"):
            with self.subTest(url=url):
                response = editor.get(url)
                self.assertEqual(response.status_code, 200)
                found = meta(head_of(response))
                self.assertEqual((found["robots"], found["canonicals"], found["og"]), ([ROBOTS_NOINDEX], [], []))
        # Xato sahifasi ochiq route ostida ham indekslanmaydi va canonical bermaydi.
        for url in (draft.get_absolute_url(), reverse("courses") + "?page=99", reverse("blog:list") + "?page=99"):
            with self.subTest(url=url):
                missing = self.client.get(url)
                self.assertEqual(missing.status_code, 404)
                found = meta(head_of(missing))
                self.assertEqual((found["robots"], found["canonicals"]), ([ROBOTS_NOINDEX], []))

    def test_private_pages_are_noindex_without_canonical(self):
        member = Client()
        member.force_login(self.member)
        for name in ("dashboard", "my_courses", "profile"):
            with self.subTest(name=name):
                found = meta(head_of(member.get(reverse(name))))
                self.assertEqual((found["robots"], found["canonicals"]), ([ROBOTS_NOINDEX], []))

    def test_metadata_is_escaped_bounded_and_matches_the_visible_page(self):
        course = Course.objects.create(
            title='Kurs "><script>alert(1)</script>', level="beginner",
            description="<p>" + "Uzun tavsif so‘zi " * 60 + "</p><script>yashirin()</script>",
        )
        response = self.client.get(reverse("course_detail", args=[course.pk]))
        head = head_of(response)
        self.assertNotIn("<script>alert(1)", head)
        self.assertNotIn("yashirin()", head)
        found = meta(head)
        self.assertLessEqual(len(found["descriptions"][0]), DESCRIPTION_MAX)
        blocks = [json.loads(block) for block in found["json_ld"]]
        course_ld = next(block for block in blocks if block["@type"] == "Course")
        self.assertEqual(course_ld["name"], course.title)
        self.assertEqual(course_ld["url"], ORIGIN + reverse("course_detail", args=[course.pk]))
        self.assertNotIn("offers", course_ld)
        self.assertNotIn("</script", "".join(found["json_ld"]))
        breadcrumbs = next(block for block in blocks if block["@type"] == "BreadcrumbList")
        self.assertEqual(breadcrumbs["itemListElement"][-1]["name"], course.title)


@override_settings(PUBLIC_CANONICAL_ORIGIN=ORIGIN)
class SocialImageTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.author = get_user_model().objects.create_user("rasm", email="rasm@example.test", is_staff=True)

    def test_og_image_is_public_media_on_the_canonical_origin(self):
        with override_settings(MEDIA_ROOT=self.media):
            post = BlogPost.objects.create(
                title="Rasmli maqola", author=self.author, body="<p>x</p>", status=BlogPost.STATUS_PUBLISHED,
                published_at=timezone.now(), cover_image=SimpleUploadedFile("muqova.gif", GIF, content_type="image/gif"),
                cover_alt_text="Muqova",
            )
            found = meta(head_of(self.client.get(post.get_absolute_url())))
        images = [value for prop, value in found["og"] if prop == "og:image"]
        self.assertEqual(len(images), 1)
        self.assertTrue(images[0].startswith(ORIGIN + "/media/"))
        self.assertIn(("og:image:alt", "Muqova"), found["og"])

    def test_no_image_means_no_og_image(self):
        post = BlogPost.objects.create(
            title="Rasmsiz", author=self.author, body="<p>x</p>", status=BlogPost.STATUS_PUBLISHED,
            published_at=timezone.now(),
        )
        found = meta(head_of(self.client.get(post.get_absolute_url())))
        self.assertNotIn("og:image", [prop for prop, _ in found["og"]])


class CanonicalOriginCheckTests(TestCase):
    def test_bad_origins_are_rejected(self):
        for origin, local in (("lms.example.test", True), ("https://lms.example.test/yol", True),
                              ("https://user@lms.example.test", True), ("http://lms.example.test", False),
                              ("https://lms.example.test?x=1", True)):
            with self.subTest(origin=origin, local=local), override_settings(PUBLIC_CANONICAL_ORIGIN=origin, IS_LOCAL=local):
                self.assertEqual([error.id for error in check_canonical_origin(None)], [CANONICAL_ORIGIN_CHECK_ID])

    def test_good_origins_pass(self):
        for origin, local in (("https://lms.example.test", False), ("http://localhost:8000", True)):
            with self.subTest(origin=origin), override_settings(PUBLIC_CANONICAL_ORIGIN=origin, IS_LOCAL=local):
                self.assertEqual(check_canonical_origin(None), [])
