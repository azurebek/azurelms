"""PUB1.3a — ochiq katalogning chegaralangan so'rov contracti.

Qidiruv boy HTML'da emas, oddiy-matn proyeksiyasida; kirish uzunligi va so'z
soni cheklangan; noma'lum filtr/tartib tashlanadi; tartib to'liq (oxirida
`id`); havolalar faqat normallashgan parametrlardan; so'rovlar soni ma'lumot
hajmiga bog'liq emas.
"""

import importlib
import re
from datetime import datetime, timezone as dt_timezone
from io import StringIO
from urllib.parse import parse_qsl, urljoin, urlsplit

from django.apps import apps
from django.core.management import call_command
from django.db import connection
from django.http import QueryDict
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from aicontrol.models import FeatureFlag
from courses.catalog import MAX_QUERY_CHARS, MAX_TERMS, CatalogQuery, fold, search_document
from courses.models import Course

search_migration = importlib.import_module("courses.migrations.0026_course_search_text")
# Har renderer uchun so'rovlar chegarasi (kurslar sonidan qat'i nazar; bo'sh katalogda biri kam).
CATALOG_QUERY_BUDGET = {"legacy": 9, "v1": 9}


def renderers():
    for enabled, name in ((False, "legacy"), (True, "v1")):
        FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": enabled})
        yield name


def params(query=""):
    return QueryDict(query)


class NormalisationTests(TestCase):
    def test_folding_unifies_case_apostrophes_and_unicode_forms(self):
        self.assertEqual(fold("O‘QISH oʻqish o`qish O’qish"), "o'qish o'qish o'qish o'qish")
        self.assertEqual(fold("İSTANBUL Türkçe"), "istanbul türkçe")
        self.assertEqual(fold("ﬁ  Ａ1​\x00x"), "fi a1 x")

    def test_document_is_plain_text_without_markup(self):
        document = search_document("Kurs", '<p class="lead"><strong>Salom</strong> <script>alert(1)</script>dunyo</p>')
        self.assertEqual(document, "kurs salom dunyo")

    def test_query_is_bounded_and_filters_are_validated(self):
        long = CatalogQuery.from_params(params("q=" + "a" * 500))
        self.assertEqual(len(long.q), MAX_QUERY_CHARS)
        many = CatalogQuery.from_params(params("q=" + "+".join(f"w{i}" for i in range(20))))
        self.assertEqual(len(many.terms), MAX_TERMS)
        query = CatalogQuery.from_params(params("q=+%00Turk%09%09A1+turk+&level=advanced&level=bogus&level=beginner&level=beginner&sort=DROP"))
        self.assertEqual(query.q, "Turk A1 turk")
        self.assertEqual(query.terms, ("turk", "a1"))
        self.assertEqual(query.levels, ("beginner", "advanced"))  # tanlov tartibi emas, kanonik tartib
        self.assertEqual(query.sort, "newest")
        self.assertFalse(CatalogQuery.from_params(params("q=+++")).is_filtered)


class CatalogWorld(TestCase):
    def course(self, title, description="<p>Tavsif</p>", level="beginner", **extra):
        return Course.objects.create(title=title, description=description, level=level, **extra)

    def results(self, **query):
        response = self.client.get(reverse("courses"), query)
        self.assertEqual(response.status_code, 200)
        return response, [course.title for course in response.context["courses"]]


class SearchBehaviourTests(CatalogWorld):
    def setUp(self):
        self.course("O‘qish kursi", '<p class="lead"><strong>Salom</strong> dunyo</p>')
        self.course("İstanbul Türkçe A1", "<p>Turk tili</p>", level="intermediate")
        self.course("Turk tili A1", "<p>Grammatika</p>")

    def test_markup_is_not_searchable_but_text_is(self):
        for name in renderers():
            with self.subTest(renderer=name):
                self.assertEqual(self.results(q="strong")[1], [])
                self.assertEqual(self.results(q="lead")[1], [])
                self.assertEqual(self.results(q="SALOM")[1], ["O‘qish kursi"])

    def test_uzbek_and_turkish_spellings_match(self):
        for name in renderers():
            with self.subTest(renderer=name):
                self.assertEqual(self.results(q="o'qish")[1], ["O‘qish kursi"])
                self.assertEqual(self.results(q="OʻQISH")[1], ["O‘qish kursi"])
                self.assertEqual(self.results(q="istanbul TÜRKÇE")[1], ["İstanbul Türkçe A1"])

    def test_every_term_must_match(self):
        _, titles = self.results(q="turk a1")
        self.assertEqual(sorted(titles), ["Turk tili A1", "İstanbul Türkçe A1"])
        self.assertEqual(self.results(q="turk a1", level="beginner")[1], ["Turk tili A1"])

    def test_hostile_and_oversized_queries_are_echoed_safely(self):
        for name in renderers():
            with self.subTest(renderer=name):
                response, titles = self.results(q='"><script>alert(1)</script>' + "x" * 400)
                self.assertEqual(titles, [])
                body = response.content.decode()
                self.assertNotIn("<script>alert(1)", body)
                self.assertEqual(len(response.context["search_query"]), MAX_QUERY_CHARS)
                self.assertIn(f'maxlength="{MAX_QUERY_CHARS}"', body)

    def test_unknown_filters_do_not_empty_the_catalog(self):
        _, titles = self.results(level="bogus", sort="'; DROP TABLE", foo="bar")
        self.assertEqual(len(titles), 3)


class ProjectionFreshnessTests(CatalogWorld):
    def find(self, q):
        return list(Course.objects.filter(search_text__contains=fold(q)).values_list("title", flat=True))

    def test_every_write_path_keeps_search_current(self):
        course = self.course("Eski nom")
        course.title = "Yangi nom"
        course.save(update_fields=["title"])
        self.assertEqual(self.find("yangi"), ["Yangi nom"])
        Course.objects.filter(pk=course.pk).update(description="<p>Ommaviy tahrir</p>")
        self.assertEqual(self.find("ommaviy"), ["Yangi nom"])
        Course.objects.bulk_create([Course(title="Ko‘p kurs", description="<p>x</p>")])
        self.assertEqual(self.find("ko'p"), ["Ko‘p kurs"])
        rows = list(Course.objects.filter(title="Ko‘p kurs"))
        rows[0].title = "Bulk yangilandi"
        Course.objects.bulk_update(rows, ["title"])
        self.assertEqual(self.find("bulk"), ["Bulk yangilandi"])

    def test_refresh_reads_and_writes_in_bounded_batches(self):
        """PR #216 review: katta katalogda ham hamma tavsif birdan xotiraga olinmaydi."""
        from courses.catalog import refresh_search_text

        for index in range(5):
            self.course(f"Partiya {index}")
        Course.objects.update(search_text="")
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(refresh_search_text(Course.objects.all(), batch_size=2), 5)
        selects = [q["sql"] for q in queries.captured_queries if q["sql"].lstrip().upper().startswith("SELECT")]
        self.assertEqual(len(selects), 4)  # 2 + 2 + 1, so'ng bo'sh sahifa
        self.assertTrue(all("LIMIT 2" in sql for sql in selects), selects)
        self.assertFalse(Course.objects.filter(search_text="").exists())

    def test_migration_backfill_and_rebuild_command(self):
        course = self.course("To‘ldiriladi")
        Course.objects.filter(pk=course.pk).update(search_text="")
        out = StringIO()
        call_command("rebuild_course_search", stdout=out)
        self.assertIn("Eskirgan (o'zgartirilmadi): 1 ta kurs.", out.getvalue())
        self.assertEqual(Course.objects.get(pk=course.pk).search_text, "")
        search_migration.backfill_search_text(apps, None)
        self.assertEqual(Course.objects.get(pk=course.pk).search_text, "to'ldiriladi tavsif")
        Course.objects.filter(pk=course.pk).update(search_text="")
        call_command("rebuild_course_search", "--apply", stdout=StringIO())
        out = StringIO()
        call_command("rebuild_course_search", stdout=out)
        self.assertIn(": 0 ta kurs.", out.getvalue())


class OrderingAndPaginationTests(CatalogWorld):
    def setUp(self):
        for index in range(19):
            self.course(f"Kurs & #{index:02d}")
        # Hammasida bir xil sana: tartib baribir to'liq bo'lishi kerak.
        Course.objects.update(created_at=datetime(2026, 10, 1, tzinfo=dt_timezone.utc))

    def walk(self, **query):
        seen, page = [], 1
        while True:
            response = self.client.get(reverse("courses"), {**query, "page": page})
            seen += [course.pk for course in response.context["courses"]]
            if not response.context["page_obj"].has_next():
                return seen
            page += 1

    def test_pages_cover_every_course_exactly_once_in_a_stable_order(self):
        all_ids = sorted(Course.objects.values_list("pk", flat=True))
        for sort in ("newest", "oldest", "popular"):
            with self.subTest(sort=sort):
                first, second = self.walk(sort=sort), self.walk(sort=sort)
                self.assertEqual(first, second)
                self.assertEqual(sorted(first), all_ids)
        self.assertEqual(self.walk(sort="oldest"), all_ids)
        self.assertEqual(self.walk(), all_ids[::-1])

    def test_links_carry_only_normalised_parameters(self):
        for name in renderers():
            response = self.client.get(reverse("courses"), {
                "q": "Kurs & #", "level": ["bogus", "beginner"], "sort": "oldest", "utm_source": "ad", "foo": "bar",
            })
            body = response.content.decode()
            # Nisbiy `?...` havolalar ham shu sahifaga nisbatan hal qilinadi.
            hrefs = [urljoin(reverse("courses"), href.replace("&amp;", "&")) for href in re.findall(r'href="([^"]*)"', body)]
            catalog_links = [href for href in hrefs if urlsplit(href).path == reverse("courses") and urlsplit(href).query]
            with self.subTest(renderer=name):
                self.assertTrue(catalog_links)
                for href in catalog_links:
                    parts = urlsplit(href)
                    pairs = parse_qsl(parts.query)
                    # Kodlanmagan `&`/`#` qidiruvni bo'lib yuborardi: har havola aynan bir xil `q` tashiydi.
                    self.assertEqual(parts.fragment, "", href)
                    self.assertIn(("q", "Kurs & #"), pairs, href)
                    self.assertLessEqual({key for key, _ in pairs}, {"q", "level", "sort", "page"}, href)
                    self.assertNotIn("bogus", href)
                page_two = next(href for href in catalog_links if "page=2" in href)
                self.assertEqual(dict(parse_qsl(urlsplit(page_two).query))["q"], "Kurs & #")

    def test_pagination_marks_the_current_page_and_rejects_missing_pages(self):
        for name in renderers():
            with self.subTest(renderer=name):
                body = self.client.get(reverse("courses"), {"page": 2}).content.decode()
                nav = body[body.index('aria-label="Kurslar sahifalari"'):]
                nav = nav[:nav.index("</nav>")]
                self.assertEqual(re.findall(r'aria-label="(\d+)-sahifa" aria-current="page"', nav), ["2"])
                self.assertIn('rel="prev"', nav)
                self.assertIn('rel="next"', nav)
                for page in ("99", "abc"):
                    self.assertEqual(self.client.get(reverse("courses"), {"page": page}).status_code, 404)


class CatalogContractTests(CatalogWorld):
    def test_query_count_does_not_grow_with_results(self):
        for count in (0, 1, 12):
            Course.objects.all().delete()
            for index in range(count):
                self.course(f"Kurs {index}")
            for name in renderers():
                self.client.get(reverse("courses"))  # lazy importlar hisobga kirmaydi
                with CaptureQueriesContext(connection) as queries:
                    response = self.client.get(reverse("courses"), {"q": "kurs", "level": "beginner"})
                with self.subTest(renderer=name, courses=count):
                    self.assertEqual(response.status_code, 200)
                    self.assertLessEqual(len(queries.captured_queries), CATALOG_QUERY_BUDGET[name])
                    rich = [q["sql"] for q in queries.captured_queries if re.search(r'"description"\s+LIKE', q["sql"])]
                    self.assertEqual(rich, [])

    def test_search_and_filter_pages_are_not_indexed(self):
        self.course("Kurs")
        for name in renderers():
            with self.subTest(renderer=name):
                plain = self.client.get(reverse("courses")).content.decode()
                self.assertIn('content="index, follow"', plain)
                filtered = self.client.get(reverse("courses"), {"q": "kurs"}).content.decode()
                self.assertIn('content="noindex, follow"', filtered)
                self.assertRegex(filtered, r'rel="canonical" href="[^"?]*/courses/"')

    def test_forms_work_without_javascript_and_are_labelled(self):
        for name in renderers():
            body = self.client.get(reverse("courses")).content.decode()
            form = body[body.index('role="search"') - 200:]
            form = form[form.index("<form"):form.index("</form>")]
            with self.subTest(renderer=name):
                self.assertIn('method="get"', form)
                self.assertIn(f'action="{reverse("courses")}"', form)
                self.assertRegex(form, r'(aria-label="Kurs qidirish"|<label[^>]*for="catalog-q")')

    def test_empty_states_offer_a_real_way_out(self):
        for name in renderers():
            with self.subTest(renderer=name, state="no courses"):
                body = self.client.get(reverse("courses")).content.decode()
                self.assertNotIn("Filtrni tozalash", body)
                self.assertNotIn("Bu filtr bo‘yicha", body)
        self.course("Kurs")
        for name in renderers():
            with self.subTest(renderer=name, state="filtered"):
                response = self.client.get(reverse("courses"), {"q": "yo‘q-narsa"})
                self.assertEqual(list(response.context["courses"]), [])
                self.assertContains(response, f'href="{reverse("courses")}"')

    def test_course_detail_returns_to_the_same_catalog_view(self):
        course = self.course("Qaytish kursi")
        FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": True})
        catalog = self.client.get(reverse("courses"), {"q": "qaytish", "sort": "oldest", "junk": "1"})
        expected = catalog.context["catalog_return_to"]
        self.assertEqual(expected, reverse("courses") + "?q=qaytish&sort=oldest")
        detail_href = re.search(r'href="(%s\?return_to=[^"]+)"' % reverse("course_detail", args=[course.pk]),
                                catalog.content.decode()).group(1)
        detail = self.client.get(detail_href.replace("&amp;", "&"))
        self.assertEqual(detail.context["public_back_url"], expected)
