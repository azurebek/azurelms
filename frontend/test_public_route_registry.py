"""PUB1.1a — public route registry, inventar tekshiruvi va xulq snapshot'i.

Snapshot'ni ongli yangilash (xulq ataylab o'zgarganda):

    UPDATE_PUBLIC_ROUTE_SNAPSHOT=1 python manage.py test frontend.test_public_route_registry
"""

import datetime
import json
import os
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from blog.models import BlogPost
from courses.models import Certificate, Course, Lesson, Module
from frontend import public_policy
from frontend.checks import PUBLIC_ROUTE_REGISTRY_CHECK_ID, check_public_route_registry
from frontend.models import LegalPage
from frontend.public_policy import (
    OPS, PRIVATE, PUBLIC, CacheClass, PublicSurfacePolicy, classify, registry_errors, route_inventory,
)
from frontend.public_route_audit import MISSING_ID, final_hop, observe
from sit.models import KnowledgeArticle, University
from subscriptions.models import Plan


SNAPSHOT = Path(__file__).with_name("public_route_snapshot.json")
LEAKS = ("maxfiy.oquvchi@example.test", "maxfiy.xodim@example.test", "MAXFIY-DARS-MATNI-7731", "+998900000731")


def fixture_world(cls):
    User = get_user_model()
    cls.staff = User.objects.create_user("xodim", email="maxfiy.xodim@example.test", is_staff=True, password="Xodim-parol-2026!")
    cls.member = User.objects.create_user(
        "oquvchi", email="maxfiy.oquvchi@example.test", password="Oquvchi-parol-2026!",
        first_name="Ali", phone_number="+998900000731",
    )
    cls.inactive = User.objects.create_user("faolsiz", email="faolsiz@example.test", password="Faolsiz-2026!", is_active=False)
    cls.course = Course.objects.create(title="Turk tili A1", description="<p>Ochiq tavsif</p>", level="beginner")
    module = Module.objects.create(course=cls.course, title="Modul")
    cls.lesson = Lesson.objects.create(module=module, title="Dars", content="<p>MAXFIY-DARS-MATNI-7731</p>")
    cls.post = BlogPost.objects.create(
        title="Ochiq maqola", author=cls.staff, body="<p>Maqola</p>",
        status=BlogPost.STATUS_PUBLISHED, published_at=timezone.now(),
    )
    cls.university = University.objects.create(
        name="Sinov universiteti", short_name="SU", city="Istanbul", is_published=True,
        source_url="https://example.edu.tr/", last_verified_on=datetime.date(2026, 9, 25), admission_status="open",
    )
    cls.article = KnowledgeArticle.objects.create(
        title="Hujjatlar", category="Qabul", body="<p>Qo‘llanma</p>", is_published=True,
        source_url="https://example.edu.tr/docs", last_verified_on=datetime.date(2026, 9, 25),
    )
    cls.certificate = Certificate.objects.create(student=cls.member, course=cls.course, certificate_id="AZ-PUB11A-1", final_score=91)
    Plan.objects.create(name="Faol tarif", price=230000)
    for page_type in ("privacy", "terms", "faq"):
        LegalPage.objects.create(page_type=page_type, title=f"Owner {page_type}", content="<p>Owner matni</p>")


def kwargs_for(test):
    def provider(name, param):
        if param in {"pk", "course_id"}:
            return test.course.pk
        if param == "lesson_id":
            return test.lesson.pk
        if param == "certificate_id":
            return test.certificate.certificate_id
        if param == "slug":
            if name.startswith("blog:"):
                return test.post.slug
            return {"sit:university_detail": test.university.slug,
                    "sit:knowledge_detail": test.article.slug}.get(name, "yoq-slug")
        if param == "uidb64":
            return urlsafe_base64_encode(force_bytes(MISSING_ID))
        if param == "token":
            return "yoq-token"
        if param == "direction":
            return "up"
        return MISSING_ID
    return provider


class RegistryContractTests(TestCase):
    def test_real_registry_classifies_every_route(self):
        self.assertEqual(registry_errors(), [])
        self.assertEqual(check_public_route_registry(None), [])

    def test_inventory_counts_are_consistent(self):
        names = [name for name, _pattern, _converters in route_inventory()]
        self.assertEqual(len(names), len(set(names)))
        classes = {classify(name) for name in names}
        self.assertLessEqual(classes, {PUBLIC, OPS, PRIVATE})

    def test_broken_registries_are_rejected(self):
        names = ["sahifa", "maxfiy", "ops_route"]
        ok = PublicSurfacePolicy("sahifa", frozenset({"GET"}), "anonymous", "index", "self", "include",
                                 CacheClass.PUBLIC_CONTENT)
        bad = {
            "registryda ikki marta": [ok, ok],
            "URL inventarida bunday": [PublicSurfacePolicy("yoq", ok.methods, "anonymous", "index", "self", "include", CacheClass.PUBLIC_CONTENT)],
            "noto'g'ri method": [PublicSurfacePolicy("sahifa", frozenset({"DELETE"}), "anonymous", "index", "self", "include", CacheClass.PUBLIC_CONTENT)],
            "noindex bo'lishi shart": [PublicSurfacePolicy("sahifa", ok.methods, "sensitive", "index", "none", "exclude", CacheClass.SENSITIVE_NO_STORE)],
            "faqat SENSITIVE_NO_STORE": [PublicSurfacePolicy("sahifa", ok.methods, "sensitive", "noindex", "none", "exclude", CacheClass.PUBLIC_QUERY)],
            "shared cache'ga tushmaydi": [PublicSurfacePolicy("sahifa", ok.methods, "mixed", "noindex", "self", "exclude", CacheClass.PUBLIC_CONTENT)],
            "canonical'siz route sitemap": [PublicSurfacePolicy("sahifa", ok.methods, "anonymous", "noindex", "none", "include", CacheClass.PUBLIC_QUERY)],
            "noma'lum rich-content": [PublicSurfacePolicy("sahifa", ok.methods, "anonymous", "index", "self", "include", CacheClass.PUBLIC_CONTENT, "RAW_HTML")],
            "faqat anonim kontent indekslanadi": [PublicSurfacePolicy("sahifa", ok.methods, "mixed", "index", "self", "include", CacheClass.PUBLIC_QUERY)],
        }
        for needle, surfaces in bad.items():
            with self.subTest(needle=needle):
                errors = registry_errors(surfaces=surfaces, ops={"ops_route": "x"}, private={"maxfiy"}, route_names=names)
                self.assertTrue(any(needle in error for error in errors), errors)

        unclassified = registry_errors(surfaces=[ok], ops={"ops_route": "x"}, private=set(), route_names=names)
        self.assertTrue(any("maxfiy: tasniflanmagan" in error for error in unclassified), unclassified)
        overlap = registry_errors(surfaces=[ok], ops={"ops_route": "x"}, private={"maxfiy", "sahifa"}, route_names=names)
        self.assertTrue(any("ikki guruhda" in error for error in overlap), overlap)
        missing_ops = registry_errors(surfaces=[ok], ops={"yoq_ops": "x"}, private={"maxfiy", "ops_route"}, route_names=names)
        self.assertTrue(any("ops allowlist" in error for error in missing_ops), missing_ops)

    def test_system_check_reports_registry_errors(self):
        with mock.patch("frontend.public_policy.registry_errors", return_value=["yangi_route: tasniflanmagan route"]):
            errors = check_public_route_registry(None)
        self.assertEqual([error.id for error in errors], [PUBLIC_ROUTE_REGISTRY_CHECK_ID])

    def test_health_upload_and_webhook_are_ops_not_pages(self):
        for name in ("healthz", "readyz", "ck_editor_5_upload_file", "bot:telegram_webhook", "design_theme_css"):
            with self.subTest(name=name):
                self.assertEqual(classify(name), OPS)
                self.assertNotIn(name, public_policy.surface_by_name())


class RouteBehaviourTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixture_world(cls)
        cls.rows = {row["name"]: row for row in observe(
            kwargs_for(cls), authenticated_user=cls.member, deactivated_user=cls.inactive,
        )}

    def test_every_route_reachable_by_a_guest_is_registered(self):
        for name, row in self.rows.items():
            if row["anonymous"].startswith("2") or row["anonymous"].startswith("503"):
                with self.subTest(name=name):
                    self.assertIn(row["class"], {PUBLIC, OPS})

    def test_private_routes_never_serve_a_guest(self):
        provider = kwargs_for(self)
        for name, _pattern, converters in route_inventory():
            if classify(name) != PRIVATE:
                continue
            first = self.rows[name]["anonymous"]
            if first.startswith(("4", "5")) or first == "302>login":
                continue
            # Ichki redirect (masalan sozlamalar bo'limiga) — zanjir oxirigacha.
            with self.subTest(name=name):
                url = reverse(name, kwargs={param: provider(name, param) for param in converters})
                status, final_route = final_hop(Client(), url)
                self.assertTrue(status >= 400 or final_route == "login", (status, final_route))

    def test_a_deactivated_account_sees_exactly_what_a_guest_sees(self):
        for name, row in self.rows.items():
            with self.subTest(name=name):
                self.assertEqual(row["deactivated"], row["anonymous"])

    def test_public_pages_disclose_no_private_data(self):
        provider = kwargs_for(self)
        guest, member = Client(), Client()
        member.force_login(self.member)
        for name, _pattern, converters in route_inventory():
            if classify(name) != PUBLIC or "GET" not in public_policy.surface_by_name()[name].methods:
                continue
            url = reverse(name, kwargs={param: provider(name, param) for param in converters})
            for label, client in (("guest", guest), ("member", member)):
                with self.subTest(name=name, viewer=label):
                    body = client.get(url).content.decode("utf-8", "ignore")
                    for leak in LEAKS:
                        if label == "member" and leak in {"maxfiy.oquvchi@example.test", "+998900000731"}:
                            continue  # o'z ma'lumotini ko'rishi mumkin
                        self.assertNotIn(leak, body)

    def test_behaviour_matches_the_recorded_snapshot(self):
        rows = [self.rows[name] for name in sorted(self.rows)]
        if os.environ.get("UPDATE_PUBLIC_ROUTE_SNAPSHOT") == "1":
            SNAPSHOT.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        recorded = {row["name"]: row for row in json.loads(SNAPSHOT.read_text(encoding="utf-8"))}
        changed = sorted(name for name in set(recorded) | set(self.rows) if recorded.get(name) != self.rows.get(name))
        details = {name: {"snapshot": recorded.get(name), "hozir": self.rows.get(name)} for name in changed}
        self.assertEqual(changed, [], "Route xulqi o'zgardi — ataylabmi? Snapshot'ni yangilang:\n"
                         + json.dumps(details, ensure_ascii=False, indent=1))
