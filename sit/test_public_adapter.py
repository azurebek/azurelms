"""PUB1.6b — SIT umumiy ochiq infratuzilmaga bitta adapter orqali ulanadi.

Asosiy da'volar, ikkala rendererda (legacy va V1):
* katalog, bosh sahifa, sitemap faqat `sit.public` effective selectorlaridan o'qiydi —
  ikkinchi "nashr etilgan" qoidasi yo'q; SIT route'lari registr, sitemap va meta'da bir martadan;
* eskirgan (tekshirilgan sanasi eski) universitet yashirilmaydi — dolzarblik haqiqati SIT-01'da;
  nashr etilmagani hech qayerda (katalog, sitemap, e'lon) sizmaydi; qoralama faqat ruxsatli xodimga,
  `noindex` va `no-store` bilan;
* filtr → universitet → orqaga ayni filtr va sahifaga; havolalar faqat normallashgan filtrdan;
  mavjud bo'lmagan sahifa 404;
* umumiy AI suhbati, ustoz xonasi va to'lov da'vosiga yo'llovchi o'lik CTA yo'q — SIT-01 so'rov
  oqimigacha sozlangan aloqa yoki halol "hozircha qabul qilinmaydi".
"""

from datetime import date
from unittest import mock

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from aicontrol.models import FeatureFlag
from frontend import public_meta, public_policy
from frontend.models import SiteSettings
from frontend.public_query import MAX_QUERY_CHARS
from frontend.public_sitemap import sitemap_entries
from sit import public
from sit.models import Announcement, KnowledgeArticle, University, UniversityFaculty, UniversityProgram
from users.models import CustomUser

RENDERERS = (("legacy", False), ("v1", True))
SIT_ROUTES = ("sit:home", "sit:university_list", "sit:university_detail", "sit:knowledge_detail")


class SitWorld(TestCase):
    def university(self, name, *, published=True, verified=None, status=University.AdmissionStatus.OPEN, city="Istanbul",
                   order=0):
        university = University.objects.create(
            name=name, short_name=name[:10], city=city, admission_status=status, tuition_from=1200, order=order,
            is_published=published, source_url="https://example.edu.tr/international",
            last_verified_on=verified or timezone.localdate())
        faculty = UniversityFaculty.objects.create(university=university, name="Muhandislik")
        UniversityProgram.objects.create(faculty=faculty, name="Dasturlash", degree_level="bachelor", language="tr",
                                         duration="4 yil", tuition_fee=1200)
        return university

    def renderer(self, v1):
        FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": v1})


class SingleAdapterTests(SitWorld):
    def test_each_sit_route_is_registered_once(self):
        names = [surface.route_name for surface in public_policy.PUBLIC_SURFACES]
        for route in SIT_ROUTES:
            with self.subTest(route=route):
                self.assertEqual(names.count(route), 1)
        self.university("Bir")
        urls = [entry.loc for entry in sitemap_entries()]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertIn("sit:university_detail", public_meta.ADAPTERS)
        self.assertIn("sit:knowledge_detail", public_meta.ADAPTERS)

    def test_every_consumer_asks_the_adapter(self):
        self.university("Yagona universitet")
        with mock.patch.object(public, "effective_universities", return_value=University.objects.none()):
            self.assertFalse([e for e in sitemap_entries() if e.route_name == "sit:university_detail"])
            for name, v1 in RENDERERS:
                self.renderer(v1)
                with self.subTest(renderer=name):
                    self.assertNotContains(self.client.get(reverse("sit:university_list")), "Yagona universitet")
                    self.assertEqual(self.client.get(reverse("sit:home")).context["portal_stats"]["universities"], 0)


class PublicationStateTests(SitWorld):
    def setUp(self):
        self.stale = self.university("Eski tekshirilgan", verified=date(2020, 1, 1))
        self.draft = self.university("Yashirin qoralama", published=False)
        Announcement.objects.create(title="Qoralama e'loni", university=self.draft, is_published=True,
                                    show_on_home=True, published_on=timezone.localdate())
        self.staff = CustomUser.objects.create_user(username="xodim", email="x@example.test", password="x", is_staff=True)
        self.learner = CustomUser.objects.create_user(username="oquvchi", email="o@example.test", password="x")

    def test_stale_stays_public_and_says_when_it_was_checked(self):
        self.assertIn(self.stale, public.effective_universities())
        for name, v1 in RENDERERS:
            self.renderer(v1)
            with self.subTest(renderer=name):
                self.assertContains(self.client.get(reverse("sit:university_list")), "Eski tekshirilgan")
                self.assertContains(self.client.get(self.stale.get_absolute_url()), "01.01.2020")

    def test_unpublished_never_leaks(self):
        self.assertNotIn(self.draft.get_absolute_url(), "".join(entry.loc for entry in sitemap_entries()))
        for name, v1 in RENDERERS:
            self.renderer(v1)
            with self.subTest(renderer=name):
                self.assertNotContains(self.client.get(reverse("sit:home")), "Yashirin qoralama")
                self.assertNotContains(self.client.get(reverse("sit:home")), "Qoralama e'loni")
                self.assertNotContains(self.client.get(reverse("sit:university_list"), {"status": "all"}), "Yashirin qoralama")
                self.assertEqual(self.client.get(self.draft.get_absolute_url()).status_code, 404)

    def test_preview_is_staff_only_private_and_unindexed(self):
        self.client.force_login(self.learner)
        self.assertEqual(self.client.get(self.draft.get_absolute_url(), {"preview": "1"}).status_code, 404)
        self.client.force_login(self.staff)
        for name, v1 in RENDERERS:
            self.renderer(v1)
            with self.subTest(renderer=name):
                response = self.client.get(self.draft.get_absolute_url(), {"preview": "1"})
                self.assertEqual(response.status_code, 200)
                self.assertIn("no-store", response["Cache-Control"])
                self.assertContains(response, '<meta name="robots" content="noindex, nofollow">')
                self.assertNotContains(response, 'rel="canonical"')


class CatalogNavigationTests(SitWorld):
    def setUp(self):
        for index in range(14):
            self.university(f"Universitet {index:02d}", order=index)

    def test_links_are_normalized_and_back_returns_to_the_same_page(self):
        expected = "/sit/universities/?q=Universitet&city=Istanbul&page=2"
        self.assertEqual(public.catalog_url({"q": "Universitet", "city": "Istanbul", "status": "open"}, page=2), expected)
        for name, v1 in RENDERERS:
            self.renderer(v1)
            with self.subTest(renderer=name):
                page = self.client.get(reverse("sit:university_list"),
                                       {"q": "Universitet", "city": "Istanbul", "page": "2", "utm_source": "x"})
                html = page.content.decode()
                main = html[html.index("<main"):html.index("</main>")]  # header'dagi kirish havolasi `next`ni saqlaydi
                self.assertIn('aria-label="2-sahifa" aria-current="page"', html)
                self.assertIn('rel="prev"', html)
                self.assertNotIn("utm_source", main)
                self.assertNotIn("page=2&amp;page", html)
                card = f"?return_to={expected.replace('?', '%3F').replace('=', '%3D').replace('&', '%26')}"
                self.assertIn(card, html)
                detail = self.client.get(University.objects.get(name="Universitet 13").get_absolute_url(),
                                         {"return_to": expected})
                self.assertContains(detail, f'href="{expected.replace("&", "&amp;")}"')
                hostile = self.client.get(University.objects.get(name="Universitet 13").get_absolute_url(),
                                          {"return_to": "https://evil.example/sit/universities/"})
                self.assertNotContains(hostile, 'href="https://evil.example')

    def test_missing_pages_are_404_and_inputs_are_bounded(self):
        for name, v1 in RENDERERS:
            self.renderer(v1)
            with self.subTest(renderer=name):
                for page in ("99", "abc"):
                    self.assertEqual(self.client.get(reverse("sit:university_list"), {"page": page}).status_code, 404)
                response = self.client.get(reverse("sit:university_list"), {"q": "x" * 300, "city": "y" * 300})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.context["filters"]["q"]), MAX_QUERY_CHARS)
                self.assertEqual(len(response.context["filters"]["city"]), MAX_QUERY_CHARS)
                self.assertContains(response, f'maxlength="{MAX_QUERY_CHARS}"')

    def test_query_count_does_not_grow_with_universities(self):
        def count():
            with CaptureQueriesContext(connection) as queries:
                self.assertEqual(self.client.get(reverse("sit:university_list")).status_code, 200)
            return len(queries)

        for name, v1 in RENDERERS:
            self.renderer(v1)
            with self.subTest(renderer=name):
                before = count()
                extra = [self.university(f"Qo'shimcha {index}", order=50 + index) for index in range(6)]
                self.assertEqual(count(), before)
                University.objects.filter(pk__in=[university.pk for university in extra]).delete()


class TruthfulCtaTests(SitWorld):
    def setUp(self):
        self.target = self.university("Yordam universiteti")
        KnowledgeArticle.objects.create(title="Viza qo'llanmasi", category="Viza", body="<p>Matn</p>", is_published=True,
                                        is_featured=True, source_url="https://example.gov.tr/", last_verified_on=timezone.localdate())

    def dead_ends(self):
        # HTML apostrofni `&#x27;` qiladi — to'lov da'vosi chiqqan ko'rinishida qidiriladi.
        return (reverse("messenger:ai"), reverse("messenger:tutor"), escape(self.target.display_help_fee), "AI maslahatchi")

    def test_no_generic_ai_tutor_or_fee_ctas(self):
        for name, v1 in RENDERERS:
            self.renderer(v1)
            for url in (reverse("sit:home"), reverse("sit:university_list"), self.target.get_absolute_url()):
                with self.subTest(renderer=name, url=url):
                    response = self.client.get(url)
                    for dead in self.dead_ends():
                        self.assertNotContains(response, dead)
            self.assertContains(self.client.get(reverse("sit:home")), "Universitetlarni solishtirish")

    def test_help_uses_the_configured_contact_or_says_it_is_unavailable(self):
        for name, v1 in RENDERERS:
            self.renderer(v1)
            with self.subTest(renderer=name, contact=False):
                response = self.client.get(self.target.get_absolute_url())
                self.assertContains(response, "data-sit-help-unavailable")
                self.assertNotContains(response, "data-sit-help-contact")
        settings = SiteSettings.load()
        settings.contact_phone, settings.contact_email = "+998 71 200 00 00", "yordam@azurelms.test"
        settings.save()
        for name, v1 in RENDERERS:
            self.renderer(v1)
            with self.subTest(renderer=name, contact=True):
                response = self.client.get(self.target.get_absolute_url())
                self.assertContains(response, "data-sit-help-contact")
                self.assertContains(response, "yordam@azurelms.test")
                self.assertNotContains(response, "data-sit-help-unavailable")

    def test_hidden_help_shows_nothing(self):
        University.objects.filter(pk=self.target.pk).update(application_help_enabled=False)
        for name, v1 in RENDERERS:
            self.renderer(v1)
            with self.subTest(renderer=name):
                response = self.client.get(self.target.get_absolute_url())
                self.assertNotContains(response, "data-sit-help-unavailable")
                self.assertNotContains(response, "Hujjat topshirish bo")
