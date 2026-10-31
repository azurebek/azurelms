"""PUBLIC-02 / PE2 — editorial ramka: renderer tanlovi, flag matritsasi va bitta ramka.

Flag OFF'da hech narsa o'zgarmaydi; ON bo'lsa barcha V1 ochiq sahifalar yangi header/footer ichida, mazmuni
hozirgi V1 shablonidan (sahifama-sahifa ko'chish). Ikkala flag bitta so'rovda o'qiladi — so'rov byudjeti
qulflangan ochiq sahifalarga yangi so'rov qo'shilmaydi.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
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
# Editorial nusxasi bor sahifalar (PE3+ har kesimda to'ldiradi); qolganlari hozirgi V1 shablonida.
PORTED = {"index.html", "about.html", "courses/course_list.html", "courses/course_detail.html", "subscriptions/pricing.html"}
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


def real_png():
    """Pillow'dan o'tadigan haqiqiy PNG (kurs rasmi saqlashda qayta ishlanadi)."""
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (8, 8), (18, 87, 230)).save(buffer, "PNG")
    return buffer.getvalue()


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
                        # Ko'chirilgan sahifa editorial nusxadan, qolgani hozirgi V1 shablonidan.
                        ported = on and template in PORTED
                        self.assertTemplateUsed(response, ("frontend_v1/editorial/" if ported else "frontend_v1/public/") + template)
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
        # Faqat hali ko'chirilmagan sahifalar: ramkaning o'zi so'rov qo'shmaydi (bandlar o'z testida).
        counts = {}
        for editorial in (False, True):
            set_flags(v1=True, editorial=editorial)
            for name in ("blog:list", "sit:home"):
                with CaptureQueriesContext(connection) as queries:
                    self.assertEqual(self.client.get(reverse(name)).status_code, 200)
                counts[(name, editorial)] = len(queries)
        for name in ("blog:list", "sit:home"):
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


class EditorialHomeAboutTests(TestCase):
    """PE3: editorial bosh sahifa va "Biz haqimizda" — owner mazmuni, rostlik qoidalari, bo'sh holat, so'rov soni."""

    def setUp(self):
        set_flags(v1=True, editorial=True)

    def journal_and_sit(self, count):
        from django.utils import timezone

        from blog.models import BlogPost, BlogTag
        from sit.models import University, UniversityFaculty, UniversityProgram

        User = get_user_model()
        author = User.objects.filter(username="jurnal-muallif").first() or User.objects.create_user(
            "jurnal-muallif", email="muallif@example.test")
        tag, _ = BlogTag.objects.get_or_create(slug="grammatika", defaults={"name": "Grammatika"})
        offset = BlogPost.objects.count()
        for index in range(offset, offset + count):
            post = BlogPost.objects.create(title=f"Maqola {index}", author=author, excerpt=f"Qisqa {index}",
                                           body="<p>Matn</p>", status=BlogPost.STATUS_PUBLISHED,
                                           published_at=timezone.now())
            post.tags.add(tag)
            # Eng og'ir holat: faqat bittasi "bosh sahifada" belgilangan — qolgani zaxira so'rovidan keladi;
            # har birida fakultet va dastur (prefetch) bor.
            university = University.objects.create(
                name=f"Universitet {index}", short_name=f"U{index}", city="Istanbul", is_published=True,
                admission_status="open", is_featured=index == 0, source_url="https://example.edu.tr/",
                last_verified_on=timezone.now().date())
            faculty = UniversityFaculty.objects.create(university=university, name="Muhandislik")
            UniversityProgram.objects.create(faculty=faculty, name="Dasturlash", degree_level="bachelor",
                                             language="tr", duration="4 yil", tuition_fee=1200)

    def count(self, url):
        self.client.get(url)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return response, len(queries)

    def test_home_bands_have_a_flat_query_count(self):
        from frontend.test_public_content import EDITORIAL_HOME_BUDGET

        counts = []
        for size in (6, 6):
            self.journal_and_sit(size)
            response, total = self.count(reverse("home"))
            self.assertTemplateUsed(response, "frontend_v1/editorial/index.html")
            counts.append(total)
        self.assertEqual(counts[0], counts[1], "maqola/universitet soniga qarab so'rov ko'paymasin")
        self.assertLessEqual(counts[1], EDITORIAL_HOME_BUDGET, counts)

    def test_home_draws_owner_content_and_only_verified_or_consented_claims(self):
        from courses.models import Course
        from frontend.models import LandingPage, Statistic, Testimonial
        from frontend.test_public_claims import approve_for_test

        page = LandingPage.load()
        page.hero_title_start = "EGASI-SARLAVHA"
        page.final_cta_title = "EGASI-CHAQIRIQ"
        page.save()
        Course.objects.create(title="KURS-A1", description="<p>Tavsif</p>", level="beginner")
        approve_for_test(Statistic.objects.create(value="77", label="TASDIQLANGAN-RAQAM", order=0))
        Statistic.objects.create(value="999", label="DALILSIZ-RAQAM", order=1)
        Testimonial.objects.create(name="ROZILIKSIZ", text="ROZILIKSIZ-FIKR", order=0)
        self.journal_and_sit(2)
        response = self.client.get(reverse("home"))
        self.assertTemplateUsed(response, "frontend_v1/editorial/index.html")
        html = response.content.decode()
        for expected in ("EGASI-SARLAVHA", "EGASI-CHAQIRIQ", "KURS-A1", "TASDIQLANGAN-RAQAM", "Maqola 0", "Universitet 0",
                         'class="p-public-stats"', 'data-surface="inverse"'):
            self.assertIn(expected, html)
        for absent in ("DALILSIZ-RAQAM", "ROZILIKSIZ-FIKR", "p-public-picker--solo"):
            self.assertNotIn(absent, html)
        # Daraja tanlash — katalog filtrining o'zi qabul qiladigan qiymatlar.
        for value, label in Course.LEVEL_CHOICES:
            self.assertIn(f'<option value="{value}">', html)
        self.assertIn(f'action="{reverse("courses")}" method="get"', html)

    def test_empty_site_draws_no_fake_bands(self):
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn("Hozircha kurslar e’lon qilinmagan", html)
        for absent in ('class="p-public-stats"', "Azure Journal</h2>", "Turkiyada o‘qish</h2>", "O‘quvchilar fikri"):
            self.assertNotIn(absent, html)
        # Raqamlar bandi bo'lmasa tanlash bandi chiqib turmaydi, oddiy oqimda.
        self.assertIn("p-public-picker--solo", html)

    def test_about_draws_owner_text_team_and_verified_numbers(self):
        from frontend.models import AboutPage, AboutStatistic, TeamMember
        from frontend.test_public_claims import approve_for_test

        page = AboutPage.load()
        page.mission_title = "EGASI-MAQSAD"
        page.save()
        TeamMember.objects.create(name="Dilnoza Karimova", role_1="Ustoz", role_2="", bio="<p>BIO-MATN</p>", order=0)
        approve_for_test(AboutStatistic.objects.create(value="12", label="TASDIQLANGAN-HAQIDA", order=0))
        AboutStatistic.objects.create(value="99", label="DALILSIZ-HAQIDA", order=1)
        response = self.client.get(reverse("about"))
        self.assertTemplateUsed(response, "frontend_v1/editorial/about.html")
        html = response.content.decode()
        for expected in ("EGASI-MAQSAD", "Dilnoza Karimova", "BIO-MATN", "TASDIQLANGAN-HAQIDA", "Qaysi kursdan boshlaysiz?"):
            self.assertIn(expected, html)
        self.assertNotIn("DALILSIZ-HAQIDA", html)

    def test_sit_home_and_platform_home_share_one_selection_rule(self):
        from sit.selectors import featured_open_universities

        self.journal_and_sit(5)
        expected = [university.pk for university in featured_open_universities(3)]
        self.assertEqual([u.pk for u in self.client.get(reverse("home")).context["sit_universities"]], expected)
        self.assertEqual([u.pk for u in self.client.get(reverse("sit:home")).context["featured_universities"]], expected)


class EditorialCatalogCoursePricingTests(TestCase):
    """PE4: katalog, kurs va tariflar — V1 bilan bitta tana, muqova so'rovsiz, tariflarda rostlik."""

    def setUp(self):
        from courses.models import Course, Lesson, Module

        set_flags(v1=True, editorial=True)
        self.courses = []
        for index in range(5):
            course = Course.objects.create(title=f"KURS-{index}", description=f"<p>Tavsif {index}</p>", level="beginner")
            module = Module.objects.create(course=course, title=f"Modul {index}")
            Lesson.objects.create(module=module, title=f"Dars {index}", content="<p>x</p>")
            self.courses.append(course)
        Course.objects.create(title="YOPIQ-KURS", description="<p>x</p>", level="beginner", is_active=False)

    def html(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return response, response.content.decode()

    def test_catalog_cards_get_a_cover_without_extra_queries(self):
        counts = {}
        for editorial in (False, True):
            set_flags(v1=True, editorial=editorial)
            self.client.get(reverse("courses"))
            with CaptureQueriesContext(connection) as queries:
                response, html = self.html(reverse("courses"))
            counts[editorial] = len(queries)
            self.assertTemplateUsed(response, "frontend_v1/public/courses/_catalog_body.html")
            self.assertEqual("p-public-cover" in html, editorial)
        self.assertEqual(counts[True], counts[False])

    def test_uploaded_course_image_becomes_the_cover(self):
        import tempfile

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        with self.settings(MEDIA_ROOT=directory.name):
            course = self.courses[0]
            course.cover_mode = "image"
            course.thumbnail = SimpleUploadedFile("muqova.png", real_png(), content_type="image/png")
            course.save()
            _, catalog = self.html(reverse("courses"))
            _, detail = self.html(reverse("course_detail", args=[course.pk]))
        for html in (catalog, detail):
            self.assertIn(course.thumbnail.url, html)
            self.assertIn("p-public-media__image", html)

    def test_course_page_next_step_is_the_same_markup_as_v1(self):
        import re

        course = self.courses[1]
        offers = {}
        for editorial in (False, True):
            set_flags(v1=True, editorial=editorial)
            response, html = self.html(reverse("course_detail", args=[course.pk]))
            self.assertTemplateUsed(response, "frontend_v1/public/courses/_detail_body.html")
            offers[editorial] = re.search(r'<section class="c-card p-public-detail__next".*?</section>', html, re.S).group(0)
        self.assertEqual(offers[True], offers[False])

    def test_related_courses_follow_the_catalog_rule_and_add_one_query(self):
        from courses.catalog import CatalogQuery, catalog_queryset

        course = self.courses[2]
        counts = {}
        for editorial in (False, True):
            set_flags(v1=True, editorial=editorial)
            url = reverse("course_detail", args=[course.pk])
            self.client.get(url)
            with CaptureQueriesContext(connection) as queries:
                response, html = self.html(url)
            counts[editorial] = len(queries)
        related = [item.pk for item in response.context["related_courses"]]
        expected = [item.pk for item in catalog_queryset(CatalogQuery()).exclude(pk=course.pk)[:3]]
        self.assertEqual(related, expected)
        self.assertNotIn(course.pk, related)
        self.assertNotIn("YOPIQ-KURS", html)
        self.assertIn("Boshqa kurslar", html)
        self.assertEqual(counts[True] - counts[False], 1, counts)

    def test_pricing_is_truthful_and_leads_to_course_choice(self):
        from courses.public_offer import billing_period_days
        from subscriptions.models import Plan, PlanFeature

        plan = Plan.objects.create(name="Guruh", price=290000, is_popular=True)
        PlanFeature.objects.create(plan=plan, name="Jonli darslar", is_included=True)
        PlanFeature.objects.create(plan=plan, name="Shaxsiy ustoz", is_included=False)
        Plan.objects.create(name="SOTUVDA-EMAS", price=1, is_available_for_purchase=False)
        response, html = self.html(reverse("subscriptions:pricing"))
        self.assertTemplateUsed(response, "frontend_v1/editorial/subscriptions/pricing.html")
        self.assertIn(f"{billing_period_days()} kunlik davr uchun", html)
        self.assertIn("Jonli darslar", html)
        self.assertIn("Shaxsiy ustoz (kiritilmagan)", html)
        self.assertNotIn("SOTUVDA-EMAS", html)
        # "Ommabop" PUB1.4a dalil darvozasigacha yo'q; narx kursga bog'liq deb da'vo qilinmaydi (Plan.price).
        self.assertNotIn("Ommabop", html)
        self.assertNotIn("Narx kursga bog", html)
        card = html[html.index('class="c-card p-public-price-card"'):]
        card = card[:card.index("</article>")]
        self.assertIn(f'href="{reverse("courses")}"', card)
        self.assertNotIn(reverse("register"), card)
        # Kurslar bandi bosh sahifa bilan bir tanlovdan (`home_courses`): eng yangi uchtasi.
        self.assertIn("KURS-4", html)
        self.assertNotIn("YOPIQ-KURS", html)
