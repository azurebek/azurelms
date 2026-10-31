"""PUBLIC-02 / PE2 — editorial ramka: renderer tanlovi, flag matritsasi va bitta ramka.

Flag OFF'da hech narsa o'zgarmaydi; ON bo'lsa barcha V1 ochiq sahifalar yangi header/footer ichida, mazmuni
hozirgi V1 shablonidan (sahifama-sahifa ko'chish). Ikkala flag bitta so'rovda o'qiladi — so'rov byudjeti
qulflangan ochiq sahifalarga yangi so'rov qo'shilmaydi.
"""
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from aicontrol.models import FeatureFlag
from core.flags import flags_enabled
from frontend.models import LegalPage, SiteSettings
from frontend.public_content import EDITORIAL, LEGACY, V1, current_renderer
from frontend.public_v1 import public_template_names
# Modul orqali — klass bu modul nomlar fazosiga tushsa, uning testlari bu yerda ham ikkinchi marta yuguradi.
from frontend import test_public_v1 as v1_world

EDITORIAL_BASE = "frontend_v1/editorial/base.html"
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


def set_flags(*, v1, editorial):
    FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": v1})
    FeatureFlag.objects.update_or_create(slug="public_editorial_v1", defaults={"enabled": editorial})


class RendererChoiceTests(TestCase):
    def test_flags_enabled_reads_overrides_and_defaults_in_one_query(self):
        FeatureFlag.objects.create(slug="frontend_v1_public", enabled=True)
        with self.assertNumQueries(1):
            flags = flags_enabled("frontend_v1_public", "public_editorial_v1")
        self.assertEqual(flags, {"frontend_v1_public": True, "public_editorial_v1": False})
        with patch("aicontrol.models.FeatureFlag.objects.filter", side_effect=DatabaseError("yo'q")):
            self.assertEqual(flags_enabled("public_editorial_v1"), {"public_editorial_v1": False})

    def test_editorial_needs_v1_and_the_decision_is_one_query(self):
        for v1, editorial, expected in ((False, False, LEGACY), (False, True, LEGACY), (True, False, V1), (True, True, EDITORIAL)):
            set_flags(v1=v1, editorial=editorial)
            with self.subTest(v1=v1, editorial=editorial), self.assertNumQueries(1):
                self.assertEqual(current_renderer(), expected)

    def test_template_names_fall_back_to_the_current_v1_page(self):
        self.assertEqual(public_template_names("index.html", V1), ["frontend_v1/public/index.html"])
        self.assertEqual(public_template_names("index.html", EDITORIAL),
                         ["frontend_v1/editorial/index.html", "frontend_v1/public/index.html"])


class EditorialFrameTests(TestCase):
    """14 ta V1 ochiq marshrut (`PublicV1Tests` dunyosi) uchala holatda."""

    setUp = v1_world.PublicV1Tests.setUp
    routes = v1_world.PublicV1Tests.routes

    def publish_legal(self):
        for kind in ("privacy", "terms", "faq"):
            LegalPage.objects.create(page_type=kind, title=f"Owner {kind}", content="<p>Owner matni</p>")
        from frontend.testing_legal import publish_all_legal

        publish_all_legal()

    def test_every_v1_route_gets_the_editorial_frame_only_when_both_flags_are_on(self):
        self.publish_legal()
        for v1, editorial in ((True, True), (True, False), (False, True)):
            set_flags(v1=v1, editorial=editorial)
            for name, args, template in self.routes():
                with self.subTest(name=name, v1=v1, editorial=editorial):
                    response = self.client.get(reverse(name, args=args))
                    self.assertEqual(response.status_code, 200)
                    html = response.content.decode()
                    on = v1 and editorial
                    if v1:
                        # Mazmun hozirgi V1 sahifasidan — PE3+ dan oldin editorial sahifa yo'q.
                        self.assertTemplateUsed(response, "frontend_v1/public/" + template)
                        self.assertIn("private", response["Cache-Control"])
                    self.assertEqual(EDITORIAL_BASE in [t.name for t in response.templates], on)
                    self.assertEqual('class="s-editorial"' in html, on)
                    self.assertEqual("frontend_v1/css/public-editorial.css" in html, on)
                    self.assertEqual("data-editorial-footer" in html, on)
                    if on:
                        # Footer to'q (inverse) bandda; menyu va footer guruhlari bitta manbadan.
                        band = html[html.index("data-editorial-footer"):]
                        self.assertIn('data-surface="inverse"', html[html.index("p-public-band"):html.index("data-editorial-footer")])
                        self.assertIn('class="s-public-footer"', band)
                        self.assertEqual(html.count('aria-label="Asosiy navigatsiya"'), 1)
                        self.assertNotIn("frontend_v1/css/auth.css", html)

    def test_the_frame_adds_no_query(self):
        counts = {}
        for editorial in (False, True):
            set_flags(v1=True, editorial=editorial)
            for name in ("home", "courses", "sit:home"):
                with CaptureQueriesContext(connection) as queries:
                    self.assertEqual(self.client.get(reverse(name)).status_code, 200)
                counts[(name, editorial)] = len(queries)
        for name in ("home", "courses", "sit:home"):
            self.assertEqual(counts[(name, True)], counts[(name, False)], name)


@override_settings(MEDIA_ROOT="")
class EditorialLogoTests(TestCase):
    def setUp(self):
        set_flags(v1=True, editorial=True)

    def test_without_an_uploaded_wordmark_the_mark_and_name_remain(self):
        html = self.client.get(reverse("home")).content.decode()
        header = html[html.index('<header class="s-public-header"'):html.index("</header>")]
        self.assertIn("s-brand__mark", header)
        self.assertIn(SiteSettings.load().brand_name, header)
        self.assertNotIn("s-public-logo", header)

    def test_uploaded_wordmarks_follow_the_theme_in_header_and_footer(self):
        with self.settings(MEDIA_ROOT=self.tmp_media()):
            settings_row = SiteSettings.load()
            settings_row.logo_image = SimpleUploadedFile("yorug.png", PNG, content_type="image/png")
            settings_row.logo_dark_image = SimpleUploadedFile("tuq.png", PNG, content_type="image/png")
            settings_row.save()
            html = self.client.get(reverse("home")).content.decode()
        header = html[html.index('<header class="s-public-header"'):html.index("</header>")]
        self.assertEqual(header.count("s-public-logo"), 2)
        self.assertIn('class="s-theme-light"', header)
        self.assertIn('class="s-theme-dark"', header)
        footer = html[html.index("data-editorial-footer"):]
        self.assertIn("s-public-logo", footer)
        self.assertIn(settings_row.logo_dark_image.url, footer)

    def tmp_media(self):
        import tempfile

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return directory.name
