"""PUB1.0e — public va auth GET bazaga hech narsa yozmaydi.

Ilgari birinchi tashrif yo'q sozlama qatorlarini (`SiteSettings`,
`AuthPageSettings`, `LandingPage`, `AboutPage`, `BlogHomeSettings`) yaratar,
yo'q huquqiy sahifani esa umumiy namuna matn bilan yaratib, siyosat sifatida
e'lon qilardi. Endi GET faqat o'qiydi; yo'q huquqiy sahifa halol 503 bilan
"hali e'lon qilinmagan" deb chiqadi va Control Center'da qizil bo'ladi.

Blog maqolasini o'qish hisoblagichi ataylab qilingan analytics yozuvi — u
nomlangan ruxsat ro'yxatida va PUB1.0g'da alohida hal qilinadi.
"""

import datetime
import re

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from aicontrol.models import FeatureFlag
from blog.models import BlogHomeSettings, BlogPost
from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import PROBE_FUNCTIONS
from core.public_readiness import LEGACY_GENERATED_LEGAL_CONTENT
from courses.models import Course
from frontend.models import AboutPage, AuthPageSettings, LandingPage, LegalPage, SiteSettings
from sit.models import KnowledgeArticle, University
from subscriptions.models import Plan


WRITE = re.compile(r"^\s*(INSERT|UPDATE|DELETE|REPLACE)\b", re.IGNORECASE)
TABLE = re.compile(r'^\s*(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|REPLACE\s+INTO)\s+"?([\w]+)"?', re.IGNORECASE)
SINGLETONS = (SiteSettings, AuthPageSettings, LandingPage, AboutPage, BlogHomeSettings)
LEGAL_ROUTES = {"privacy_policy": "privacy", "terms_of_service": "terms", "faq_page": "faq"}
# Ataylab qilingan analytics (PUB1.0g): faqat shu jadvallar va faqat maqola sahifasida.
BLOG_READ_ANALYTICS_TABLES = {"blog_blogpostread", "blog_blogpost"}
FLAG_SLUGS = ("frontend_v1_public", "frontend_v1_auth", "frontend_v1_records")


def set_v1(enabled):
    for slug in FLAG_SLUGS:
        FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": enabled})


def table_snapshot():
    models = (*SINGLETONS, LegalPage)
    return {model._meta.label: list(model.objects.order_by("pk").values()) for model in models}


class WriteFreeMixin:
    def setUp(self):
        self.staff = get_user_model().objects.create_user("pub-editor", email="pub-editor@example.test", is_staff=True)
        self.course = Course.objects.create(title="Turk tili A1", description="<p>Kurs matni</p>", level="beginner")
        self.post = BlogPost.objects.create(
            title="Ochiq maqola", author=self.staff, body="<p>Maqola</p>", status=BlogPost.STATUS_PUBLISHED,
        )
        self.university = University.objects.create(
            name="Sinov universiteti", short_name="SU", city="Istanbul", is_published=True,
            source_url="https://example.edu.tr/", last_verified_on=datetime.date(2026, 9, 25), admission_status="open",
        )
        self.article = KnowledgeArticle.objects.create(
            title="Hujjatlar", category="Qabul", body="<p>Qo‘llanma</p>", is_published=True,
            source_url="https://example.edu.tr/docs", last_verified_on=datetime.date(2026, 9, 25),
        )
        Plan.objects.create(name="Faol tarif", price=230000)

    def public_urls(self):
        return [
            reverse("home"), reverse("about"), reverse("courses"), reverse("course_detail", args=[self.course.pk]),
            reverse("subscriptions:pricing"), reverse("blog:list"),
            reverse("sit:home"), reverse("sit:university_list"),
            reverse("sit:university_detail", args=[self.university.slug]),
            reverse("sit:knowledge_detail", args=[self.article.slug]),
            *[reverse(name) for name in LEGAL_ROUTES],
            reverse("login"), reverse("register"), reverse("password_reset"), reverse("password_reset_done"),
            reverse("password_reset_complete"), reverse("password_reset_confirm", args=["MQ", "yaroqsiz-token"]),
            reverse("design_theme_css"), reverse("offline"),
        ]

    def get_without_writes(self, url, client=None):
        with CaptureQueriesContext(connection) as queries:
            response = (client or self.client).get(url)
        writes = [q["sql"] for q in queries.captured_queries if WRITE.match(q["sql"])]
        self.assertEqual(writes, [], f"{url} GET bazaga yozdi")
        honest_unavailable = url in self.legal_urls() and response.status_code == 503
        self.assertTrue(response.status_code < 500 or honest_unavailable, (url, response.status_code))
        return response

    def legal_urls(self):
        return {reverse(name) for name in LEGAL_ROUTES}


class CleanDatabaseTests(WriteFreeMixin, TestCase):
    def test_every_public_and_auth_get_writes_nothing_on_a_clean_database(self):
        for enabled in (False, True):
            set_v1(enabled)
            before = table_snapshot()
            for url in self.public_urls():
                with self.subTest(url=url, v1=enabled):
                    self.get_without_writes(url)
            self.assertEqual(table_snapshot(), before)
        for model in SINGLETONS:
            self.assertFalse(model.objects.exists(), model._meta.label)
        self.assertFalse(LegalPage.objects.exists())

    def test_missing_legal_page_is_an_honest_unindexed_503(self):
        for enabled in (False, True):
            set_v1(enabled)
            for name, page_type in LEGAL_ROUTES.items():
                with self.subTest(name=name, v1=enabled):
                    response = self.get_without_writes(reverse(name))
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response["X-Robots-Tag"], "noindex")
                    self.assertIn("no-store", response["Cache-Control"])
                    self.assertContains(response, "e’lon qilinmagan", status_code=503)
                    self.assertContains(response, LegalPage.UNAVAILABLE_TITLES[page_type], status_code=503)
                    # Eski umumiy namuna matn hech qachon siyosat sifatida chiqmaydi.
                    self.assertNotContains(response, "Platforma foydalanuvchi hisobini yuritish", status_code=503)
                    self.assertNotContains(response, "Platformadan foydalanish orqali siz", status_code=503)
        self.assertFalse(LegalPage.objects.exists())

    def test_singleton_read_returns_code_defaults_without_a_row(self):
        for model in SINGLETONS:
            with self.subTest(model=model._meta.label):
                with CaptureQueriesContext(connection) as queries:
                    current = model.current()
                self.assertEqual([q for q in queries.captured_queries if WRITE.match(q["sql"])], [])
                self.assertTrue(current._state.adding)
                self.assertFalse(model.objects.exists())

    def test_editor_load_still_creates_the_row(self):
        self.assertEqual(SiteSettings.load().pk, 1)
        self.assertTrue(SiteSettings.objects.filter(pk=1).exists())


class PopulatedDatabaseTests(WriteFreeMixin, TestCase):
    def setUp(self):
        super().setUp()
        SiteSettings.objects.create(brand_name="Owner brendi")
        AuthPageSettings.objects.create()
        LandingPage.objects.create(hero_title_start="Owner sarlavhasi")
        AboutPage.objects.create(hero_title_start="Owner haqida")
        BlogHomeSettings.objects.create(hero_kicker="Owner jurnali")
        for page_type in LEGAL_ROUTES.values():
            LegalPage.objects.create(page_type=page_type, title=f"Owner {page_type}", content=f"<p>Owner {page_type} matni</p>")

    def test_every_public_and_auth_get_writes_nothing_and_keeps_owner_content(self):
        for enabled in (False, True):
            set_v1(enabled)
            before = table_snapshot()
            for url in self.public_urls():
                with self.subTest(url=url, v1=enabled):
                    self.assertLess(self.get_without_writes(url).status_code, 500)
            self.assertEqual(table_snapshot(), before)

    def test_owner_values_are_what_the_public_sees(self):
        for enabled in (False, True):
            set_v1(enabled)
            with self.subTest(v1=enabled):
                self.assertContains(self.client.get(reverse("about")), "Owner haqida")
                self.assertContains(self.client.get(reverse("home")), "Owner sarlavhasi")
                legal = self.client.get(reverse("terms_of_service"))
                self.assertContains(legal, "Owner terms matni")
                self.assertNotIn("X-Robots-Tag", legal)
        # Blog sozlamasini faqat V1 ko'rsatadi; brend esa legacy sarlavhada.
        self.assertContains(self.client.get(reverse("blog:list")), "Owner jurnali")
        set_v1(False)
        self.assertContains(self.client.get(reverse("login")), "Owner brendi")

    def test_blog_post_read_writes_only_the_named_analytics_tables(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("blog:detail", args=[self.post.slug]))
        self.assertEqual(response.status_code, 200)
        tables = {TABLE.match(q["sql"]).group(1) for q in queries.captured_queries if WRITE.match(q["sql"])}
        self.assertTrue(tables)
        self.assertLessEqual(tables, BLOG_READ_ANALYTICS_TABLES)


class HelpCenterTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("yordam", email="yordam@example.test", password="Kuchli-parol-2026")
        self.client.force_login(self.user)

    def test_help_center_reads_legal_pages_without_creating_them(self):
        for enabled in (False, True):
            set_v1(enabled)
            with self.subTest(v1=enabled):
                with CaptureQueriesContext(connection) as queries:
                    response = self.client.get(reverse("help_center"))
                writes = [q["sql"] for q in queries.captured_queries if WRITE.match(q["sql"])]
                self.assertEqual(writes, [])
                self.assertContains(response, "Qo‘llanma hali qo‘shilmagan")
        self.assertFalse(LegalPage.objects.exists())

    def test_help_center_shows_the_owner_faq(self):
        LegalPage.objects.create(page_type="faq", title="Owner FAQ", content="<p>Owner savol-javobi</p>")
        for enabled in (False, True):
            set_v1(enabled)
            with self.subTest(v1=enabled):
                self.assertContains(self.client.get(reverse("help_center")), "Owner savol-javobi")


class ReadinessProbeTests(TestCase):
    def probe(self):
        return PROBE_FUNCTIONS["public_content"](capability_by_slug("public_content"))

    def fill_singletons(self):
        for model in SINGLETONS:
            model.objects.create()

    def test_missing_legal_pages_are_red(self):
        result = self.probe()
        self.assertEqual(result.status, "red")
        self.assertIn(("legal_missing", "privacy, terms, faq"), result.details)

    def test_legacy_generated_sample_text_is_amber(self):
        self.fill_singletons()
        LegalPage.objects.create(page_type="privacy", title="Privacy Policy", content=LEGACY_GENERATED_LEGAL_CONTENT["privacy"])
        LegalPage.objects.create(page_type="terms", title="Shartlar", content="<p>Owner shartlari</p>")
        LegalPage.objects.create(page_type="faq", title="FAQ", content=LEGACY_GENERATED_LEGAL_CONTENT["faq"])
        result = self.probe()
        self.assertEqual(result.status, "amber")
        self.assertIn(("legal_generated", "privacy, faq"), result.details)

    def test_missing_settings_rows_are_amber_once_legal_is_ready(self):
        for page_type in LEGAL_ROUTES.values():
            LegalPage.objects.create(page_type=page_type, title="Owner", content="<p>Owner matni</p>")
        result = self.probe()
        self.assertEqual(result.status, "amber")
        self.assertIn("frontend.SiteSettings", dict(result.details)["settings_missing"])

    def test_owner_authored_content_is_green(self):
        self.fill_singletons()
        for page_type in LEGAL_ROUTES.values():
            LegalPage.objects.create(page_type=page_type, title="Owner", content="<p>Owner matni</p>")
        self.assertEqual(self.probe().status, "green")
