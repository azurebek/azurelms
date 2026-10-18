"""PUB1.3c — kurs sahifasi va kartasi: qaror uchun bor faktlar, dalilsiz va'da yo'q.

Faktlar faqat bazadan (`courses.public_offer.build_course_facts`), tarif va narx
checkout bilan bir manbadan (`build_offer`). 0 yoki bo'sh fakt ko'rsatilmaydi;
sertifikat faqat kursda oraliq va yakuniy imtihon ikkalasi bo'lsa va'da qilinadi
(`courses.completion_service` aynan shu ikkisini talab qiladi).
"""

import html
import json
import re
from datetime import timedelta
from decimal import Decimal
from html.parser import HTMLParser

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag
from cohorts.models import Cohort
from courses.models import Course, Exam, Lesson, Module
from frontend.models import SiteSettings
from subscriptions.models import Plan, PlanFeature

UNSUPPORTED = ("Cheksiz AI repetitor", "Jonli guruh darslari", "To'liq imtihon muhiti", "Tasdiqlangan sertifikat",
               "umrbod", "0 dars", "0 modul", "0 imtihon", "0 o'quvchi")
NBSP = " "


def renderers():
    for enabled, name in ((False, "legacy"), (True, "v1")):
        FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": enabled})
        yield name


def visible_text(page):
    """Ko'rinadigan matn: skript/style'siz, teglar olib tashlangan, bo'shliqlar bittaga."""
    body = page[page.index("<body"):]
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", body, flags=re.S)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", body)).split())


def squash(value):
    return re.sub(r"\s+", "", value)


class _EventAttributes(HTMLParser):
    """Haqiqiy teglardagi `on*` atributlari va bajariladigan `<script>` ichidagi `alert(`."""

    def __init__(self):
        super().__init__()
        self.handlers, self.scripts, self._script = [], [], None

    def handle_starttag(self, tag, attrs):
        self.handlers += [f"{tag}[{name}]" for name, _ in attrs if name.startswith("on")]
        self._script = dict(attrs).get("type") or "" if tag == "script" else None

    def handle_data(self, data):
        if self._script is not None and self._script != "application/ld+json" and "alert(" in data:
            self.scripts.append(data)

    def handle_endtag(self, tag):
        self._script = None


def injected(page):
    parser = _EventAttributes()
    parser.feed(page)
    return parser.handlers, parser.scripts


class CoursePageWorld(TestCase):
    def setUp(self):
        # Migratsiya seed'idagi tariflar sotuvdan olinadi — narx kutilmasi aniq bo'lsin.
        Plan.objects.update(is_available_for_purchase=False)
        self.plan = Plan.objects.create(name="Oddiy tarif", price=Decimal("250000"), order=1)
        PlanFeature.objects.create(plan=self.plan, name="Darslar va mashqlar", is_included=True, order=1)
        PlanFeature.objects.create(plan=self.plan, name="Shaxsiy ustoz", is_included=False, order=2)

    def complete_course(self):
        course = Course.objects.create(
            title="Turk tili B1", description="<p>Grammatika va <strong>suhbat</strong>.</p>", level="intermediate",
            certificate_min_lesson_completion_percent=80, certificate_requires_all_assignments_approved=True,
        )
        module = Module.objects.create(course=course, title="1-modul")
        Lesson.objects.create(module=module, title="Salomlashish", content="<p>x</p>")
        Lesson.objects.create(module=module, title="Tanishuv", content="<p>x</p>")
        for exam_type in ("visa", "final"):
            Exam.objects.create(course=course, title=f"{exam_type} imtihon", exam_type=exam_type, weight_percentage=50)
        Cohort.objects.create(course=course, name="Ochiq guruh", start_date=timezone.localdate() + timedelta(days=5))
        return course

    def page(self, course):
        response = self.client.get(reverse("course_detail", args=[course.pk]))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()


class FactsTests(CoursePageWorld):
    def test_complete_course_shows_every_canonical_fact(self):
        course = self.complete_course()
        for name in renderers():
            text = visible_text(self.page(course))
            with self.subTest(renderer=name):
                for fact in ("2 dars", "1 modul", "2 imtihon", "Salomlashish", "Oraliq va yakuniy imtihondan",
                             "darslarning kamida 80% bajarilgan", "barcha topshiriqlar tasdiqlangan",
                             "Oddiy tarif", "250 000 so", "/ 30 kun", "Darslar va mashqlar",
                             "Shaxsiy ustoz (kiritilmagan)"):
                    self.assertIn(fact, text)
                for claim in UNSUPPORTED:  # faol o'quvchi 0 — ko'rsatilmaydi
                    self.assertNotIn(claim, text)

    def test_empty_course_shows_no_zero_or_blank_facts(self):
        course = Course.objects.create(title="Bo'sh kurs", description="", level="beginner")
        for name in renderers():
            body = self.page(course)
            text = visible_text(body)
            with self.subTest(renderer=name):
                for claim in UNSUPPORTED:
                    self.assertNotIn(claim, text)
                for heading in ("Dastur", "O'qituvchi", "O‘qituvchi", "Baholash", "Tanishtiruv videosi", "Savolingiz bormi"):
                    self.assertNotIn(heading, text)
                self.assertNotIn("<video", body)

    def test_certificate_is_promised_only_when_both_exams_exist(self):
        course = Course.objects.create(title="Faqat final", description="<p>d</p>", level="beginner")
        Exam.objects.create(course=course, title="Final", exam_type="final", weight_percentage=100)
        for name in renderers():
            text = visible_text(self.page(course))
            with self.subTest(renderer=name):
                self.assertNotIn("sertifikat", text.lower())
                self.assertIn("1 imtihon", text)

    def test_preview_video_and_configured_support_only(self):
        course = self.complete_course()
        course.preview_video = SimpleUploadedFile("intro.mp4", b"\x00\x00\x00\x18ftypmp42", content_type="video/mp4")
        course.save()
        SiteSettings.objects.create(contact_email="kurs@example.test")  # telefon — model namunasi
        try:
            for name in renderers():
                body = self.page(course)
                with self.subTest(renderer=name):
                    self.assertRegex(body, r'<video[^>]*controls[^>]*preload="none"[^>]*src="[^"]*intro')
                    self.assertIn('href="mailto:kurs@example.test"', body)
                    self.assertNotIn("123 45 67", body)
        finally:
            course.preview_video.delete(save=False)

    def test_first_screen_summary_points_to_the_offer(self):
        course = self.complete_course()
        for name in renderers():
            body = self.page(course)
            summary_class = "pub-course-summary" if name == "legacy" else "p-public-offer-summary"
            start = body.index(f'class="{summary_class}') if name == "legacy" else body.index(summary_class)
            summary = visible_text("<body>" + body[start:body.index("</div>", body.index('href="#kurs-taklifi"', start))])
            with self.subTest(renderer=name):
                self.assertIn('id="kurs-taklifi"', body)
                self.assertIn("250 000 so", summary)
                self.assertIn("Qabul ochiq", summary)
                self.assertIn("Tariflar va yozilish", summary)

    def test_closed_offer_hides_prices(self):
        course = self.complete_course()
        Cohort.objects.filter(course=course).update(is_active=False)
        for name in renderers():
            text = visible_text(self.page(course))
            with self.subTest(renderer=name):
                self.assertNotIn("250", text)
                self.assertIn("Bu kursga qabul hozircha ochilmagan.", text)


class SafetyAndNamesTests(CoursePageWorld):
    def test_rich_content_and_titles_cannot_inject_markup(self):
        course = Course.objects.create(
            title='<img src=x onerror=alert(1)>Uzun ' + "nom " * 40,
            description='<p>Toza</p><script>alert(2)</script><img src="x" onerror="alert(3)">',
            level="beginner",
        )
        module = Module.objects.create(course=course, title="<script>alert(4)</script>")
        Lesson.objects.create(module=module, title='<a href="javascript:alert(5)">x</a>', content="<p>x</p>")
        for name in renderers():
            body = self.page(course)
            with self.subTest(renderer=name):
                # Escape qilingan matn (`&lt;img … onerror=`) xavfsiz: tekshiriladi faqat haqiqiy teglar.
                self.assertEqual(injected(body), ([], []))
                self.assertNotIn('href="javascript:', body)
                self.assertIn("Toza", body)

    def test_catalog_card_links_have_unique_names_and_no_zero_counts(self):
        for index in range(3):
            Course.objects.create(title=f"Kurs {index}", description="<p>d</p>", level="beginner")
        for name in renderers():
            body = self.client.get(reverse("courses")).content.decode()
            text = visible_text(body)
            with self.subTest(renderer=name):
                self.assertNotIn("0 dars", text)
                self.assertNotIn("0 o'quvchi", text)
                if name == "v1":
                    labels = re.findall(r'aria-label="([^"]+ — kursni ko‘rish)"', body)
                    self.assertEqual(len(labels), 3)
                    self.assertEqual(len(set(labels)), 3)

    def test_catalog_card_shows_the_offer_price(self):
        self.complete_course()
        # Arzonroq, lekin bu kurs uchun guruhi ochilmagan tarif — kartadagi narx bo'lmasligi kerak.
        Plan.objects.create(name="Guruh tarifi", price=Decimal("1000"), order=2, cohort_capacity_limit=8)
        for name in renderers():
            body = self.client.get(reverse("courses")).content.decode()
            text = visible_text(body)  # `split()` bo'linmaydigan bo'shliqni ham oddiy bo'shliqqa aylantiradi
            with self.subTest(renderer=name):
                self.assertIn(f"250{NBSP}000", body)  # narx ikki qatorga bo'linmaydi
                self.assertIn("250 000 so‘mdan" if name == "v1" else "250 000 so'mdan", text)
                self.assertIn("/ 30 kun", text)


class StructuredDataTests(CoursePageWorld):
    def test_json_ld_only_states_what_the_page_shows(self):
        course = self.complete_course()
        for name in renderers():
            body = self.page(course)
            blocks = [json.loads(raw) for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)]
            data = next(block for block in blocks if block.get("@type") == "Course")
            text = visible_text(body)
            with self.subTest(renderer=name):
                self.assertIn(data["name"], text)
                self.assertIn(squash(data["description"]), squash(text))
                self.assertNotIn("offers", data)  # narx JSON-LD'da yo'q — sahifadagi tarif bloki yagona manba
