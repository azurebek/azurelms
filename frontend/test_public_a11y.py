"""PUB1.7c — qulaylik qabuli: avtomatik qismi.

Asosiy da'volar, ikkala rendererda (legacy va V1), mehmon va kirgan foydalanuvchi uchun:
* har ochiq, kirish va holat sahifasida statik a11y qoidalari (`frontend/a11y_probe.py` —
  axe-core'ning HTML'dan aniqlanadigan critical/serious qoidalari) topilmasi 0;
* ichki `#…` havolalar mavjud elementga olib boradi;
* JavaScriptsiz asosiy yo'llar ishlaydi: katalog qidiruvi → kurs, Blog qidiruvi → maqola,
  SIT filtri, kirish, parol tiklash, izoh yozish — sahifadagi formaning o'zi bilan;
* fokus ko'rinishi va harakatni kamaytirish CSS'da bor.
Rang kontrasti, 320px reflow, klaviatura tartibi brauzerda tekshiriladi
(`nuclear-program/frontend-v1/PUBLIC-A11Y-EVIDENCE.md`); ekran o'quvchi va qurilma — OPEN.
"""

import re
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core import mail
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag
from blog.models import BlogComment, BlogPost
from courses.certificate_verifier import ensure_public_token
from courses.models import Certificate, Course
from frontend.a11y_probe import missing_fragment_targets, page_forms, probe
from frontend.testing_legal import publish_legal
from sit.models import KnowledgeArticle, University, UniversityFaculty, UniversityProgram
from users.models import CustomUser

# PUBLIC-02: editorial ramka ham shu probe'dan o'tadi (V1 ustida, `public_editorial_v1`).
RENDERERS = (("legacy", False, False), ("v1", True, False), ("editorial", True, True))
HREF_RE = re.compile(r'href="([^"]+)"')


class A11yWorld(TestCase):
    def setUp(self):
        self.member = CustomUser.objects.create_user("azo", "azo@example.test", "Sinov-parol-123", first_name="Ali", last_name="Valiyev")
        self.post = BlogPost.objects.create(title="Unli uyg'unligi", author=self.member, excerpt="Qisqa", body="<h2>Bo'lim</h2><p>Matn</p>",
                                            status=BlogPost.STATUS_PUBLISHED, published_at=timezone.now())
        BlogComment.objects.create(post=self.post, user=self.member, content="Foydali izoh")
        self.course = Course.objects.create(title="Turk tili A1", description="<p>Boshlang'ich</p>", level="beginner")
        self.university = University.objects.create(
            name="Istanbul Texnika", short_name="ITU", city="Istanbul", is_published=True, admission_status="open",
            source_url="https://example.edu.tr/", last_verified_on=date.today())
        faculty = UniversityFaculty.objects.create(university=self.university, name="Muhandislik")
        UniversityProgram.objects.create(faculty=faculty, name="Dasturlash", degree_level="bachelor", language="tr",
                                         duration="4 yil", tuition_fee=1200)
        self.guide = KnowledgeArticle.objects.create(title="Viza", category="Viza", body="<p>Matn</p>", is_published=True,
                                                     source_url="https://example.gov.tr/", last_verified_on=date.today())
        certificate = Certificate.objects.create(student=self.member, course=self.course, certificate_id="AZ-A11Y-1", final_score=90)
        self.token = ensure_public_token(certificate)
        for kind in ("privacy", "terms"):
            publish_legal(kind)
        # Rasmli holatlar ham chizilsin (alt tekshiruvi): brend belgisi va maqola muqovasi.
        from frontend.models import SiteSettings

        SiteSettings.load()
        SiteSettings.objects.update(logo_mark_image="brand/belgi.png")
        BlogPost.objects.filter(pk=self.post.pk).update(cover_image="blog/covers/muqova.jpg")

    def renderer(self, v1, editorial=False):
        for slug in ("frontend_v1_public", "frontend_v1_auth"):
            FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": v1})
        FeatureFlag.objects.update_or_create(slug="public_editorial_v1", defaults={"enabled": editorial})
        FeatureFlag.objects.update_or_create(slug="certificate_public_verifier", defaults={"enabled": True})

    def guest_pages(self):
        return {
            "home": reverse("home"), "about": reverse("about"), "courses": reverse("courses"),
            "course": reverse("course_detail", args=[self.course.pk]), "pricing": reverse("subscriptions:pricing"),
            "blog": reverse("blog:list"), "post": self.post.get_absolute_url(), "sit": reverse("sit:home"),
            "universities": reverse("sit:university_list"), "university": self.university.get_absolute_url(),
            "guide": self.guide.get_absolute_url(), "privacy": reverse("privacy_policy"), "terms": reverse("terms_of_service"),
            "verify": reverse("certificate_verify", args=[self.token]), "login": reverse("login"),
            "register": reverse("register"), "reset": reverse("password_reset"), "reset_done": reverse("password_reset_done"),
            "maintenance": reverse("maintenance"), "offline": reverse("offline"), "404": "/yoq-sahifa/",
        }


class ProbeTests(A11yWorld):
    def test_public_auth_and_state_pages_have_no_findings(self):
        for renderer, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            for who in ("guest", "member"):
                client = Client()
                if who == "member":
                    client.force_login(self.member)
                for name, url in self.guest_pages().items():
                    response = client.get(url)
                    if response.status_code in (301, 302):
                        continue  # kirgan foydalanuvchi kirish sahifasidan ilovaga yo'naltiriladi
                    html = response.content.decode()
                    with self.subTest(renderer=renderer, who=who, page=name):
                        self.assertEqual([(f.rule, f.detail) for f in probe(html)], [])
                        self.assertEqual(missing_fragment_targets(html), [])


class ProbeSelfTests(SimpleTestCase):
    """Probe ko'r bo'lib qolmasin: har qoida buzilgan HTML'da ishlaydi."""

    def test_every_rule_fires_on_a_broken_page(self):
        bad = ('<html><head><title></title><meta name="viewport" content="width=device-width, user-scalable=no"></head><body>'
               '<main><h1>A</h1><h1>B</h1><img src="x.png"><input name="q"><a href="/x"></a><button></button>'
               '<label for="nope">X</label><div id="d"></div><a id="d" href="/y">y</a><span aria-describedby="zz">t</span>'
               '<div tabindex="3">t</div><div aria-hidden="true"><a href="/z">z</a></div><a href="/p"><button>b</button></a>'
               '<a href="javascript:void(0)">j</a><a href="#yoq">ichki</a></main><main></main></body></html>')
        rules = {finding.rule for finding in probe(bad)}
        expected = {"html-has-lang", "document-title", "meta-viewport", "page-has-heading-one", "landmark-one-main",
                    "duplicate-id-active", "label-for-missing", "image-alt", "label", "link-name", "button-name",
                    "aria-valid-ref", "tabindex", "aria-hidden-focus", "nested-interactive", "link-javascript"}
        self.assertEqual(expected - rules, set())
        self.assertEqual(missing_fragment_targets(bad), ["#yoq"])

    def test_a_good_page_is_clean(self):
        good = ('<html lang="uz"><head><title>T</title></head><body><main id="main"><h1>A</h1><img src="x" alt="">'
                '<label for="q">Q</label><input id="q" name="q"><label>S <select name="s"></select></label>'
                '<a href="/x"><svg aria-hidden="true"></svg>Bor</a><button aria-label="Yop"><svg></svg></button>'
                '<a href="#main">Asosiy</a></main></body></html>')
        self.assertEqual(probe(good), [])
        self.assertEqual(missing_fragment_targets(good), [])


class NoScriptJourneyTests(A11yWorld):
    """JavaScriptsiz brauzer: faqat sahifadagi havola va formalar bilan."""

    def form_with(self, html, control):
        form = next((f for f in page_forms(html) if control in f["controls"]), None)
        self.assertIsNotNone(form, f"`{control}` maydonli forma yo'q")
        return form

    def submit(self, client, page_url, form, **values):
        data = dict(form["fields"], **values)
        target = form["action"] or page_url
        if form["method"] == "post":
            return client.post(target, data)
        return client.get(target, data)

    def test_catalog_blog_and_sit_work_without_javascript(self):
        for renderer, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            with self.subTest(renderer=renderer, flow="catalog"):
                page = self.client.get(reverse("courses")).content.decode()
                results = self.submit(self.client, reverse("courses"), self.form_with(page, "q"), q="Turk").content.decode()
                course_link = next(h for h in HREF_RE.findall(results) if h.startswith(f"/courses/{self.course.pk}/"))
                self.assertEqual(self.client.get(course_link.replace("&amp;", "&")).status_code, 200)
            with self.subTest(renderer=renderer, flow="blog"):
                page = self.client.get(reverse("blog:list")).content.decode()
                results = self.submit(self.client, reverse("blog:list"), self.form_with(page, "q"), q="Unli").content.decode()
                post_link = next(h for h in HREF_RE.findall(results) if h.startswith(self.post.get_absolute_url()))
                detail = self.client.get(post_link.replace("&amp;", "&"))
                self.assertContains(detail, "Foydali izoh")
            with self.subTest(renderer=renderer, flow="sit"):
                page = self.client.get(reverse("sit:university_list")).content.decode()
                results = self.submit(self.client, reverse("sit:university_list"), self.form_with(page, "city"), city="Istanbul")
                self.assertContains(results, "Istanbul Texnika")

    def test_login_reset_and_comment_work_without_javascript(self):
        for renderer, v1, editorial in RENDERERS:
            self.renderer(v1, editorial)
            client = Client()
            with self.subTest(renderer=renderer, flow="login"):
                page = client.get(reverse("login")).content.decode()
                form = self.form_with(page, "password")
                user_field = next(name for name in form["controls"] if name in ("username", "login", "identifier", "email"))
                response = self.submit(client, reverse("login"), form, **{user_field: "azo", "password": "Sinov-parol-123"})
                self.assertEqual(response.status_code, 302)
            with self.subTest(renderer=renderer, flow="comment"):
                detail = client.get(self.post.get_absolute_url()).content.decode()
                form = self.form_with(detail, "content")
                self.assertEqual(form["method"], "post")
                self.assertIn("csrfmiddlewaretoken", form["fields"])
                response = self.submit(client, self.post.get_absolute_url(), form, content=f"JS'siz izoh {renderer}")
                self.assertEqual(response.status_code, 302)
                self.assertTrue(BlogComment.objects.filter(content=f"JS'siz izoh {renderer}").exists())
            with self.subTest(renderer=renderer, flow="reset"):
                guest = Client()
                mail.outbox = []
                page = guest.get(reverse("password_reset")).content.decode()
                response = self.submit(guest, reverse("password_reset"), self.form_with(page, "email"), email="azo@example.test")
                self.assertEqual(response.status_code, 302)


class CssContractTests(SimpleTestCase):
    def test_focus_and_reduced_motion_rules_exist(self):
        base = Path(settings.BASE_DIR) / "static"
        expectations = {
            "frontend_v1/css/base.css": ("prefers-reduced-motion", ":focus-visible { outline: 2px solid"),
            "css/system-states.css": (".sys-button:focus-visible", "prefers-reduced-motion", "forced-colors"),
            "css/public-shell.css": ("prefers-reduced-motion", ":focus-visible"),
            "css/sit.css": ("prefers-reduced-motion",),
        }
        for path, needles in expectations.items():
            text = (base / path).read_text(encoding="utf-8")
            for needle in needles:
                with self.subTest(path=path, rule=needle):
                    self.assertIn(needle, text)

    def test_legacy_faint_text_meets_aa_contrast_without_a_published_theme(self):
        def luminance(hex_color):
            channels = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        def ratio(a, b):
            high, low = sorted((luminance(a), luminance(b)), reverse=True)
            return (high + 0.05) / (low + 0.05)

        # Yorug' va qorong'i rejimdagi "xira matn" ranglari (PUB1.7c) — eng och/eng to'q fonda ham 4.5:1.
        light, dark = "#626b79", "#868e9d"
        self.assertGreaterEqual(min(ratio(light, bg) for bg in ("#fbfcfd", "#ffffff", "#f1f4f9", "#eef1f6")), 4.5)
        self.assertGreaterEqual(min(ratio(dark, bg) for bg in ("#090b0f", "#0e1117", "#12151c", "#161a22", "#1d222b")), 4.5)
        base = Path(settings.BASE_DIR) / "static"
        old_failing = {"#8a92a0", "#69717f", "#b3bac6", "#454c58"}
        for path in ("css/tokens.css", "css/sit.css", "backoffice/design-runtime.css"):
            text = (base / path).read_text(encoding="utf-8")
            colors = set(re.findall(r"--ink-[34]:\s*(?:var\(--az-faint,\s*)?(#[0-9a-fA-F]{6})", text))
            with self.subTest(path=path):
                self.assertTrue(colors)
                self.assertEqual(colors - {light, dark}, set(), "xira matn rangi AA'dan past qiymatga qaytdi")
                self.assertFalse(colors & old_failing)
