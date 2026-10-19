"""PUB1.0a — public rich text va URL siyosati.

Asosiy da'vo: DB'dagi public HTML va admin kiritgan havola hech bir legacy/V1,
preview yoki flag holatida executable markup yoki xavfli manzil chiqarmaydi,
semantik kontent esa saqlanadi. Har bir public maydon nomma-nom tekshiriladi —
bitta umumiy "sahifa toza" testi yangi maydon qo'shilganda jim qolardi.
"""

import datetime
import json
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from aicontrol.models import FeatureFlag
from blog.models import BlogPost
from core.rich_content_policy import public_plain_text, safe_url, sanitize_public_editorial
from courses.models import Course
from frontend.testing_legal import publish_legal
from frontend.models import (
    AboutPage,
    AuthPageSettings,
    LandingNavItem,
    LandingPage,
    LegalPage,
    SiteSettings,
    TeamMember,
)
from frontend.public_url_policy import public_link_url, public_nav_url
from frontend.templatetags.public_v1 import public_url
from sit.models import KnowledgeArticle, University
from subscriptions.models import Plan

BACKSLASH = "\\"

# Har biri ko'rinadigan xavfsiz matn + barcha asosiy hujum turlari. `PWNED`
# faqat executable qismda uchraydi: sahifada topilsa, nimadir o'tib ketgan.
PAYLOAD = (
    '<h2>SAFE-{tag} sarlavha</h2>'
    '<p id="clobber" class="evil" style="clobber-style:1" onclick="PWNED()">SAFE-{tag} matn</p>'
    '<script>PWNED()</script><style>body{{PWNED:1}}</style>'
    '<img src="x" onerror="PWNED()"><iframe srcdoc="PWNED"></iframe>'
    '<a href="javascript:PWNED()">j</a><a href="//evil.test/x">pr</a>'
    '<a href="/' + BACKSLASH + 'evil.test">bs</a><a href="data:text/html,PWNED">d</a>'
    '<svg><script>PWNED()</script></svg><math><mi>PWNED</mi></math>'
    '<form action="https://evil.test"><input name="p"></form>'
    '<object data="PWNED.swf"></object><template><b>PWNED</b></template>'
)

# `onerror` umumiy emas: ilovaning o'z AI widget rasmi ham shu atributni ishlatadi.
FORBIDDEN = ("PWNED", 'id="clobber"', "clobber-style", "evil.test", "srcdoc", 'onerror="PWNED')


def payload(tag):
    return PAYLOAD.format(tag=tag)


class SanitizerCorpusTests(SimpleTestCase):
    def test_executable_markup_and_its_text_are_removed(self):
        out = sanitize_public_editorial(payload("X"))
        for marker in FORBIDDEN + ("<script", "<style", "<svg", "<math", "<form", "<input", "<object", "<template", "<iframe"):
            self.assertNotIn(marker, out)
        self.assertIn("<h2>SAFE-X sarlavha</h2>", out)
        self.assertIn("<p>SAFE-X matn</p>", out)

    def test_hostile_links_become_plain_text(self):
        # `href`siz `<a>` CSSda havoladek chiziladi va bosilmaydi — matn qoladi.
        for href in ("javascript:alert(1)", "&#106;avascript:alert(1)", "java\tscript:alert(1)",
                     "data:text/html,abc", "//evil.test", "/" + BACKSLASH + "evil.test",
                     "https://user@evil.test", "https://evil.test:99999", "vbscript:x", "file:///etc/passwd"):
            with self.subTest(href=href):
                self.assertEqual(sanitize_public_editorial(f'<p>a <a href="{href}">x</a> b</p>'), "<p>a x b</p>")
        self.assertEqual(sanitize_public_editorial('<a name="old-anchor">nom</a>'), "nom")
        self.assertEqual(
            sanitize_public_editorial('<a href="javascript:x">yomon</a><a href="/ok/">yaxshi</a>'),
            'yomon<a href="/ok/">yaxshi</a>',
        )

    def test_links_get_safe_rel_and_target_policy(self):
        external = sanitize_public_editorial('<a href="https://ok.test/x" rel="opener" target="_blank">e</a>')
        self.assertEqual(external, '<a href="https://ok.test/x" target="_blank" rel="noopener noreferrer">e</a>')
        self.assertEqual(sanitize_public_editorial('<a href="http://ok.test/">h</a>'),
                         '<a href="http://ok.test/" rel="noopener noreferrer">h</a>')
        self.assertEqual(sanitize_public_editorial('<a href="/courses/" target="_top">l</a>'), '<a href="/courses/">l</a>')
        for href in ("#bolim", "mailto:a@b.uz", "tel:+998 90 000"):
            self.assertEqual(sanitize_public_editorial(f'<a href="{href}">x</a>'), f'<a href="{href}">x</a>')

    def test_semantic_content_is_preserved(self):
        html = (
            '<h3>Sarlavha</h3><ul><li>bir</li></ul><ol start="3"><li>uch</li></ol>'
            '<blockquote>iqtibos</blockquote><pre><code>x = 1</code></pre>'
            '<table><tbody><tr><th scope="col">A</th><td colspan="2">B</td></tr></tbody></table>'
            '<figure class="image image-style-side"><img src="/media/a.png" alt="Rasm" width="300"></figure>'
            '<p><strong>q</strong> <em>k</em> <u>t</u> <s>c</s></p>'
        )
        self.assertEqual(sanitize_public_editorial(html), html)

    def test_presentation_attributes_are_stripped(self):
        self.assertEqual(sanitize_public_editorial('<figure class="image evil"><img src="/media/a.png" alt=""></figure>'),
                         '<figure><img src="/media/a.png" alt=""></figure>')
        self.assertEqual(sanitize_public_editorial('<td colspan="x" rowspan="2">c</td>'), "c")
        self.assertEqual(sanitize_public_editorial('<table><tr><td colspan="x" rowspan="2">c</td></tr></table>'),
                         '<table><tbody><tr><td rowspan="2">c</td></tr></tbody></table>')

    def test_images_only_from_own_media_and_keep_alt_meaning(self):
        self.assertEqual(sanitize_public_editorial('<img src="https://evil.test/a.png" alt="Sertifikat">'), "Sertifikat")
        self.assertEqual(sanitize_public_editorial('<img src="data:image/png;base64,AAA" alt="d">'), "d")
        self.assertEqual(sanitize_public_editorial('<img src="/media/a.png">'), '<img src="/media/a.png" alt="">')
        self.assertEqual(sanitize_public_editorial('<img src="/media/a.png" height="9e9">'), '<img src="/media/a.png" alt="">')
        for src in ("/media/../users/logout/", "/media/%2e%2e/admin/", "/media/./a.png", "/static/../x"):
            with self.subTest(src=src):
                self.assertEqual(sanitize_public_editorial(f'<img src="{src}" alt="t">'), "t")

    @override_settings(MEDIA_URL="https://cdn.example.test/media/")
    def test_absolute_s3_media_host_is_approved(self):
        self.assertEqual(sanitize_public_editorial('<img src="https://cdn.example.test/media/a.png" alt="a">'),
                         '<img src="https://cdn.example.test/media/a.png" alt="a">')
        self.assertEqual(sanitize_public_editorial('<img src="https://cdn.example.test/other/a.png" alt="a">'), "a")

    def test_embed_becomes_a_plain_link_or_disappears(self):
        self.assertEqual(
            sanitize_public_editorial('<iframe src="https://www.youtube.com/embed/x" srcdoc="z">f</iframe>'),
            '<a href="https://www.youtube.com/embed/x" target="_blank" rel="noopener noreferrer">Videoni ochish</a>',
        )
        self.assertEqual(sanitize_public_editorial('<iframe src="javascript:alert(1)"></iframe>'), "")
        self.assertEqual(sanitize_public_editorial('<iframe src="http://plain.test/v"></iframe>'), "")

    def test_malformed_html_is_balanced(self):
        self.assertEqual(sanitize_public_editorial("<p><b>x</p></b>"), "<p><b>x</b></p>")
        self.assertEqual(sanitize_public_editorial("<!-- izoh --><p>x</p>"), "<p>x</p>")

    def test_sanitizer_is_idempotent(self):
        corpus = [payload("I"), '<a href="https://ok.test" target="_blank">e</a>', '<iframe src="https://v.test/e"></iframe>',
                  '<img src="/media/a.png">', '<p><b>x</p></b>', '<table><tr><td>1</td></tr></table>']
        for html in corpus:
            once = sanitize_public_editorial(html)
            self.assertEqual(sanitize_public_editorial(once), once)

    def test_empty_values(self):
        self.assertEqual(sanitize_public_editorial(None), "")
        self.assertEqual(sanitize_public_editorial(""), "")

    def test_plain_text_uses_the_same_profile(self):
        self.assertEqual(public_plain_text('<h2>Salom</h2><p>Dunyo &amp; <b>turk</b></p><script>PWNED()</script>'),
                         "Salom Dunyo & turk")
        self.assertEqual(public_plain_text("<p>bir ikki uch tort</p>", 9), "bir ikki…")


class UrlPolicyTests(SimpleTestCase):
    HOSTILE = ("javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,abc", "//evil.test",
               "/" + BACKSLASH + "evil.test", "https:\n//evil.test", "https://user@evil.test",
               "https://", "#", "#x", "courses/", "file:///etc/passwd", "", None)

    def test_navigation_allows_only_local_https_mailto_tel(self):
        for value in ("/faq/", "https://t.me/azure", "mailto:a@b.uz", "tel:+998901112233"):
            self.assertEqual(public_nav_url(value), value)
        self.assertEqual(public_nav_url("http://plain.test/"), "")
        for value in self.HOSTILE:
            with self.subTest(value=value):
                self.assertEqual(public_nav_url(value), "")

    def test_content_link_also_allows_plain_http_sources(self):
        self.assertEqual(public_link_url("http://universitet.edu.tr/"), "http://universitet.edu.tr/")
        for value in self.HOSTILE:
            with self.subTest(value=value):
                self.assertEqual(public_link_url(value), "")

    def test_v1_filter_delegates_to_the_shared_link_policy(self):
        self.assertEqual(public_url("https://example.edu.tr/docs"), "https://example.edu.tr/docs")
        self.assertEqual(public_url("https://user@evil.test"), "")

    def test_rich_text_fragment_is_opt_in(self):
        self.assertEqual(safe_url("#bolim"), "")
        self.assertEqual(safe_url("#bolim", allow_fragment=True), "#bolim")


class PublicFieldMatrixTests(TestCase):
    """Har public rich maydon × legacy/V1 × flag ON/OFF × kerak bo'lsa preview."""

    def setUp(self):
        self.flag = FeatureFlag.objects.create(slug="frontend_v1_public", enabled=False)
        User = get_user_model()
        self.staff = User.objects.create_user("pub-staff", email="pub-staff@example.test", is_staff=True)
        self.learner = User.objects.create_user("pub-learner", email="pub-learner@example.test")
        # Singletonlarning birinchi `load()`i GET ichida row yaratadi — bu PUB1.0e
        # qarzi, PUB1.0a emas. Shu sabab ular oldindan yaratiladi.
        for singleton in (SiteSettings, LandingPage, AboutPage, AuthPageSettings):
            singleton.load()

        landing = LandingPage.load(); landing.hero_subtitle = payload("LANDING"); landing.save()
        about = AboutPage.load()
        about.hero_subtitle = payload("ABOUTHERO"); about.mission_text = payload("MISSION"); about.vision_text = payload("VISION")
        about.save()
        TeamMember.objects.create(name="Birinchi", role_1="Ustoz", role_2="CEO", bio=payload("FEATURED"), order=1)
        TeamMember.objects.create(name="Ikkinchi", role_1="Ustoz", role_2="Mentor", bio=payload("MEMBER"), order=2)
        LegalPage.objects.create(page_type=LegalPage.PAGE_TERMS, title="Shartlar", content=payload("TERMS"))
        # Shartlar amaldagi versiyadan o'qiladi (PUB1.5a); render yana `public_rich` orqali.
        publish_legal(LegalPage.PAGE_TERMS, title="Shartlar", content=payload("TERMS"))
        LegalPage.objects.create(page_type=LegalPage.PAGE_FAQ, title="FAQ", content=payload("FAQ"))
        self.course = Course.objects.create(title="Turk tili A1", description=payload("COURSE"), level="beginner")
        self.plan = Plan.objects.create(name="Faol tarif", price=230000, description=payload("PLAN"))
        self.post = BlogPost.objects.create(title="Maqola", author=self.staff, body=payload("BLOG"), status=BlogPost.STATUS_PUBLISHED)
        self.draft = BlogPost.objects.create(title="Qoralama", author=self.staff, body=payload("BLOGDRAFT"), status=BlogPost.STATUS_DRAFT)
        common = dict(category="Qabul", source_url="https://example.edu.tr/docs", last_verified_on=datetime.date(2026, 9, 25))
        self.article = KnowledgeArticle.objects.create(title="Hujjatlar", body=payload("GUIDE"), is_published=True, **common)
        self.draft_article = KnowledgeArticle.objects.create(title="Qoralama qo'llanma", body=payload("GUIDEDRAFT"), is_published=False, **common)

    def cases(self):
        return [
            ("home", [], None, ["LANDING"]),
            ("about", [], None, ["ABOUTHERO", "MISSION", "VISION", "FEATURED", "MEMBER"]),
            ("terms_of_service", [], None, ["TERMS"]),
            ("faq_page", [], None, ["FAQ"]),
            ("course_detail", [self.course.pk], None, ["COURSE"]),
            ("blog:detail", [self.post.slug], None, ["BLOG"]),
            ("blog:detail", [self.draft.slug], self.staff, ["BLOGDRAFT"]),
            ("sit:knowledge_detail", [self.article.slug], None, ["GUIDE"]),
            ("sit:knowledge_detail", [self.draft_article.slug], self.staff, ["GUIDEDRAFT"]),
        ]

    def assert_clean(self, response, tags):
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        for marker in FORBIDDEN:
            self.assertNotIn(marker, body)
        for tag in tags:
            self.assertIn(f"SAFE-{tag} matn", body)

    def test_every_public_field_on_both_renderers(self):
        for enabled in (False, True):
            self.flag.enabled = enabled; self.flag.save()
            for name, args, user, tags in self.cases():
                with self.subTest(route=name, args=args, v1=enabled):
                    self.client.logout()
                    params = {}
                    if user:
                        self.client.force_login(user); params = {"preview": "1"}
                    self.assert_clean(self.client.get(reverse(name, args=args), params), tags)

    def test_pricing_plan_description(self):
        for enabled in (False, True):
            self.flag.enabled = enabled; self.flag.save()
            with self.subTest(v1=enabled):
                body = self.client.get(reverse("subscriptions:pricing")).content.decode()
                for marker in FORBIDDEN:
                    self.assertNotIn(marker, body)
                self.assertIn("SAFE-PLAN", body)

    def test_plain_text_previews_use_the_public_profile(self):
        # Katalog kartasi, kurs detail lead'i va legacy pricing qisqa matni.
        routes = [("courses", []), ("course_detail", [self.course.pk]), ("subscriptions:pricing", [])]
        for enabled in (False, True):
            self.flag.enabled = enabled; self.flag.save()
            for name, args in routes:
                with self.subTest(route=name, v1=enabled):
                    body = self.client.get(reverse(name, args=args)).content.decode()
                    self.assertNotIn("PWNED", body)
                    self.assertNotIn("body{", body)

    def test_help_center_faq_on_both_renderers(self):
        records = FeatureFlag.objects.create(slug="frontend_v1_records", enabled=False)
        self.client.force_login(self.learner)
        for enabled in (False, True):
            records.enabled = enabled; records.save()
            with self.subTest(v1=enabled):
                self.assert_clean(self.client.get(reverse("help_center")), ["FAQ"])

    def test_public_get_does_not_write(self):
        LegalPage.objects.create(page_type=LegalPage.PAGE_PRIVACY, title="Maxfiylik", content=payload("PRIVACY"))
        publish_legal(LegalPage.PAGE_PRIVACY, title="Maxfiylik", content=payload("PRIVACY"))
        routes = [("home", []), ("about", []), ("terms_of_service", []), ("privacy_policy", []), ("faq_page", []),
                  ("course_detail", [self.course.pk]), ("subscriptions:pricing", []),
                  ("sit:knowledge_detail", [self.article.slug])]
        for enabled in (False, True):
            self.flag.enabled = enabled; self.flag.save()
            for name, args in routes:
                with self.subTest(route=name, v1=enabled), CaptureQueriesContext(connection) as queries:
                    self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200)
                writes = [q["sql"] for q in queries if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))]
                self.assertEqual(writes, [])


class PublicNavigationTests(TestCase):
    def setUp(self):
        self.flag = FeatureFlag.objects.create(slug="frontend_v1_public", enabled=False)
        for placement in (LandingNavItem.Placement.MAIN, LandingNavItem.Placement.FOOTER_PLATFORM):
            for order, (label, url) in enumerate([
                ("OK-LOCAL", "/faq/"), ("OK-HTTPS", "https://t.me/azurelms"),
                ("BAD-JS", "javascript:PWNED()"), ("BAD-HTTP", "http://plain.test/"),
                ("BAD-PROTOCOL-RELATIVE", "//evil.test/x"), ("BAD-BACKSLASH", "/" + BACKSLASH + "evil.test"),
                ("BAD-USERINFO", "https://user@evil.test/"),
            ]):
                LandingNavItem.objects.create(placement=placement, key="custom", label=label, custom_url=url, order=order)
        SiteSettings.load()
        SiteSettings.objects.update(telegram_url="javascript:PWNED()", instagram_url="http://insta.test/x",
                                    youtube_url="https://youtube.test/c")

    def test_main_nav_in_v1_and_footer_in_legacy_share_one_policy(self):
        for enabled, checks in ((True, ["OK-LOCAL", "OK-HTTPS"]), (False, ["OK-LOCAL", "OK-HTTPS"])):
            self.flag.enabled = enabled; self.flag.save()
            with self.subTest(v1=enabled):
                body = self.client.get(reverse("home")).content.decode()
                for label in checks:
                    self.assertIn(label, body)
                for label in ("BAD-JS", "BAD-HTTP", "BAD-PROTOCOL-RELATIVE", "BAD-BACKSLASH", "BAD-USERINFO"):
                    self.assertNotIn(label, body)
                for marker in ("PWNED", "evil.test", "plain.test", "insta.test"):
                    self.assertNotIn(marker, body)

    def test_legacy_social_links_use_navigation_policy(self):
        body = self.client.get(reverse("about")).content.decode()
        self.assertIn('href="https://youtube.test/c"', body)
        self.assertNotIn("PWNED", body)
        self.assertNotIn("insta.test", body)


class SitLinkTests(TestCase):
    def test_sit_source_links_follow_the_link_policy_on_both_renderers(self):
        flag = FeatureFlag.objects.create(slug="frontend_v1_public", enabled=False)
        university = University.objects.create(
            name="Sinov universiteti", short_name="SU", city="Istanbul", is_published=True,
            source_url="https://example.edu.tr/", last_verified_on=datetime.date(2026, 9, 25), admission_status="open",
        )
        # URLField validatsiyasini chetlab o'tgan (admin/ORM) qiymat ham chiqmasligi kerak.
        University.objects.filter(pk=university.pk).update(source_url="javascript:PWNED()", official_website="//evil.test/x")
        for enabled in (False, True):
            flag.enabled = enabled; flag.save()
            with self.subTest(v1=enabled):
                response = self.client.get(reverse("sit:university_detail", args=[university.slug]))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "PWNED")
                self.assertNotContains(response, "evil.test")


class AuditCommandTests(TestCase):
    def test_audit_reports_ids_and_kinds_without_content_or_writes(self):
        course = Course.objects.create(title="Kurs", description=payload("AUDIT"), level="beginner")
        clean = Course.objects.create(title="Toza", description="<p>Oddiy</p>", level="beginner")
        LandingNavItem.objects.create(key="custom", label="Yomon", custom_url="javascript:PWNED()")
        out = StringIO()
        with CaptureQueriesContext(connection) as queries:
            call_command("audit_public_content", "--format=json", stdout=out)
        writes = [q["sql"] for q in queries if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))]
        self.assertEqual(writes, [])
        text = out.getvalue()
        self.assertNotIn("PWNED", text)
        self.assertNotIn("SAFE-AUDIT", text)
        report = json.loads(text)
        self.assertEqual(report["profile"], "PUBLIC_EDITORIAL_V1")
        course_row = next(row for row in report["rich_text"] if row["field"] == "courses.Course.description")
        self.assertEqual(course_row["rows"], 2)
        self.assertEqual(course_row["flagged"], 1)
        for kind in ("executable", "embed", "unsafe_url", "presentation"):
            self.assertEqual(course_row["findings"][kind], [course.pk])
        self.assertNotIn(clean.pk, sum(course_row["findings"].values(), []))
        nav_row = next(row for row in report["urls"] if row["field"] == "frontend.LandingNavItem.custom_url")
        self.assertEqual(len(nav_row["rejected"]), 1)

    def test_text_format_lists_fields(self):
        out = StringIO()
        call_command("audit_public_content", stdout=out)
        self.assertIn("PUBLIC_EDITORIAL_V1", out.getvalue())
        self.assertIn("blog.BlogPost.body", out.getvalue())


class SharedPrimitiveCompatibilityTests(TestCase):
    def test_global_bleach_filter_for_private_consumers_is_unchanged(self):
        # Dars/imtihon/amaliyot kontenti hali shu filterda; PUB1.0a uni ataylab o'zgartirmaydi.
        from frontend.templatetags.bleach_tags import ALLOWED_ATTRIBUTES, ALLOWED_TAGS, sanitize

        self.assertIn("iframe", ALLOWED_TAGS)
        self.assertIn("class", ALLOWED_ATTRIBUTES["*"])
        self.assertEqual(str(sanitize('<p class="x">a</p>')), '<p class="x">a</p>')

    def test_blog_excerpt_and_meta_come_from_the_public_profile(self):
        author = get_user_model().objects.create_user("blog-author", email="author@example.test", is_staff=True)
        post = BlogPost.objects.create(title="T", author=author, body="<p>Haqiqiy matn</p><script>PWNED()</script>")
        self.assertEqual(post.excerpt, "Haqiqiy matn")
        self.assertNotIn("PWNED", post.meta_description)
