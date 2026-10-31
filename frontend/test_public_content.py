"""PUB1.2b — bosh sahifa va "Biz haqimizda" deterministik proyeksiyasi.

Har renderer faqat o'zi chizadiganini o'qiydi; foydalanuvchi PII'si (oxirgi
ro'yxatdan o'tganlar) o'qilmaydi; ro'yxatlar to'liq tartibda (oxirida `id`);
bir xil ma'lumot — bir xil HTML; so'rovlar soni ma'lumot hajmiga bog'liq emas.
"""

import re
from datetime import datetime, timezone as dt_timezone

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from aicontrol.models import FeatureFlag
from courses.models import Course, Lesson, Module
from frontend.models import AboutStatistic, LandingAIFeature, Statistic, TeamMember, Testimonial
from frontend import public_claims
from frontend.public_content import HOME_COURSE_LIMIT
from frontend.test_public_claims import approve_for_test

# Har renderer uchun so'rovlar chegarasi (mavjud ma'lumot hajmidan qat'i nazar).
# Bosh sahifa: +1 — voronka o'lchovi flagini o'qish (PUB1.8a; flag yoqilganda hodisa yozuvi alohida).
QUERY_BUDGET = {("legacy", "home"): 15, ("v1", "home"): 14, ("legacy", "about"): 12, ("v1", "about"): 11}
USER_TABLE_SCAN = re.compile(r'FROM\s+"users_customuser"', re.IGNORECASE)
# Public sahifa hech qachon o'qimasligi kerak bo'lgan foydalanuvchi ustunlari.
PII_COLUMNS = ("email", "phone_number", "password", "telegram_id", "date_joined", "last_login")


def set_v1(enabled):
    FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": enabled})


def renderers():
    for enabled, name in ((False, "legacy"), (True, "v1")):
        set_v1(enabled)
        yield name


class ContentWorld:
    def populate(self, count):
        User = get_user_model()
        owner = User.objects.filter(username="mazmun-egasi").first() or User.objects.create_superuser(
            "mazmun-egasi", email="mazmun@example.test", password="Mazmun-2026!")
        teacher, _ = User.objects.get_or_create(username="ustoz", defaults={"email": "ustoz@example.test",
                                                                         "first_name": "Ustoz"})
        offset = Statistic.objects.count()
        for index in range(offset, offset + count):
            stat = Statistic.objects.create(value=f"{index + 1}0", label=f"Ko‘rsatkich {index}", order=0)
            approve_for_test(stat)
            about = AboutStatistic.objects.create(value=f"{index}", label=f"Haqida {index}", order=0)
            approve_for_test(about)
            TeamMember.objects.create(name=f"A’zo {index}", role_1="Ustoz", role_2="Mentor", bio="<p>Bio</p>", order=0)
            item = Testimonial.objects.create(name=f"O‘quvchi {index}", text=f"Fikr {index}", order=0)
            public_claims.set_testimonial_consent(item, actor=owner, confirmed=True, reason="Rozilik", source_reference="x")
            course = Course.objects.create(title=f"Kurs {index}", description="<p>d</p>", level="beginner", instructor=teacher)
            module = Module.objects.create(course=course, title="M")
            Lesson.objects.create(module=module, title="L", content="<p>x</p>")
        # Barcha kurslarda bir xil sana: tartib baribir deterministik bo'lishi kerak.
        Course.objects.update(created_at=datetime(2026, 10, 1, tzinfo=dt_timezone.utc))


class ProjectionTests(ContentWorld, TestCase):
    def queries_for(self, url):
        self.client.get(url)  # birinchi so'rov (lazy importlar) hisobga kirmaydi
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return response, [q["sql"] for q in queries.captured_queries]

    def test_query_budget_holds_for_empty_one_and_many(self):
        for count in (0, 1, 8):
            with self.subTest(items=count):
                if count:
                    self.populate(count if count == 1 else count - 1)
                for name in renderers():
                    for page, url in (("home", reverse("home")), ("about", reverse("about"))):
                        _, sql = self.queries_for(url)
                        self.assertLessEqual(len(sql), QUERY_BUDGET[(name, page)], (name, page, count))

    def test_no_learner_pii_is_read(self):
        self.populate(2)
        for name in renderers():
            for url in (reverse("home"), reverse("about")):
                with self.subTest(renderer=name, url=url):
                    _, sql = self.queries_for(url)
                    self.assertFalse([q for q in sql if USER_TABLE_SCAN.search(q)])
                    for column in PII_COLUMNS:
                        self.assertFalse([q for q in sql if f'"users_customuser"."{column}"' in q], column)

    def test_each_renderer_receives_only_what_it_draws(self):
        self.populate(1)
        for name in renderers():
            home = self.client.get(reverse("home")).context
            about = self.client.get(reverse("about")).context
            for gone in ("recent_students", "hero_slides", "portal_tabs", "portal_items"):
                self.assertNotIn(gone, home)
            if name == "legacy":
                self.assertIn("level_stages", home)
                self.assertNotIn("popular_courses", home)
                self.assertIn("featured_member", about)
            else:
                self.assertIn("popular_courses", home)
                self.assertNotIn("level_stages", home)
                self.assertNotIn("featured_member", about)

    def test_same_content_renders_the_same_html_in_a_stable_order(self):
        self.populate(4)
        for name in renderers():
            for url in (reverse("home"), reverse("about")):
                with self.subTest(renderer=name, url=url):
                    first = self.client.get(url)
                    second = self.client.get(url)
                    self.assertEqual(first.content, second.content)
        set_v1(True)
        courses = list(self.client.get(reverse("home")).context["popular_courses"])
        self.assertEqual(len(courses), HOME_COURSE_LIMIT)
        self.assertEqual([c.pk for c in courses], sorted((c.pk for c in courses), reverse=True))
        team = list(self.client.get(reverse("about")).context["team"])
        self.assertEqual([m.pk for m in team], sorted(m.pk for m in team))
        stats = list(self.client.get(reverse("home")).context["statistics"])
        self.assertEqual([s.pk for s in stats], sorted(s.pk for s in stats))

    def test_hidden_inactive_and_unverified_items_are_excluded(self):
        self.populate(1)
        hidden = LandingAIFeature.objects.create(text="YASHIRIN-AI", is_visible=False, order=1)
        Course.objects.create(title="YOPIQ-KURS", description="<p>x</p>", level="beginner", is_active=False)
        Statistic.objects.create(value="999", label="DALILSIZ-STAT", order=1)
        for name in renderers():
            body = self.client.get(reverse("home")).content.decode()
            self.assertNotIn(hidden.text, body)
            self.assertNotIn("YOPIQ-KURS", body)
            self.assertNotIn("DALILSIZ-STAT", body)

    def test_renderer_is_decided_once_per_request(self):
        """Codex review (PR #214): bayroq ikki o'qish orasida o'zgarsa ham shablon va kontekst mos."""
        from unittest import mock

        self.populate(1)
        for first, template, key in ((True, "frontend_v1/public/index.html", "popular_courses"),
                                     (False, "index.html", "level_stages")):
            # Birinchi o'qish `first`, keyingi har qanday o'qish teskarisi: kod qarorni qayta o'qisa shablon va
            # kontekst ajralib qoladi va test yiqiladi (PUBLIC-02 dan beri ikkala flag bitta `flags_enabled` o'qishida).
            reads = iter([first])

            def flags(*slugs, reads=reads, first=first):
                value = next(reads, not first)
                return {slug: value if slug == "frontend_v1_public" else False for slug in slugs}

            with self.subTest(first_read=first), mock.patch("frontend.public_content.flags_enabled", side_effect=flags):
                response = self.client.get(reverse("home"))
                self.assertTemplateUsed(response, template)
                self.assertIn(key, response.context)

    def test_empty_site_shows_truthful_empty_states(self):
        Statistic.objects.all().delete()
        for name in renderers():
            for url in (reverse("home"), reverse("about")):
                with self.subTest(renderer=name, url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)
        set_v1(True)
        self.assertContains(self.client.get(reverse("home")), "Hozircha kurslar e’lon qilinmagan")
