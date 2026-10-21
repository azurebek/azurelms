"""PUB1.8b — ochiq sayt reliz tayyorligi darvozasi.

Asosiy da'volar:
* bitta selector: owner sahifasi, Control Center va CLI ayni natijani ko'rsatadi;
* har band yashil/sariq/qizil, sababi va tuzatish yo'li bilan; bitta tekshiruv
  yiqilsa u qizil band bo'ladi, qolganlari baribir hisoblanadi;
* lokal profilda console email va localhost origin — sariq; production'da qizil;
* owner tasdig'i faqat majburiy bandlar yashil bo'lganda, sabab bilan, holat izi
  (digest) mos bo'lsa; natija audit yozuvi. Owner bo'lmagan kirolmaydi.
"""

import json
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import resolve, reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag, SystemAuditEvent
from cohorts.models import Cohort
from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import PROBE_FUNCTIONS
from core.email_delivery import RESET_DELIVERY_FAILED_ACTION
from core.public_readiness import STATE_GENERATED, STATE_MISSING, STATE_READY, LegalPageState
from courses.models import Certificate, Course
from frontend import legal_revisions as legal
from frontend import public_claims
from frontend import release_readiness as gate
from frontend.models import LegalDocument, SiteSettings, Testimonial
from subscriptions.models import Plan

User = get_user_model()
URL = reverse("backoffice_release_readiness")
SMTP = "django.core.mail.backends.smtp.EmailBackend"
CONSOLE = "django.core.mail.backends.console.EmailBackend"
PRODUCTION = {"EMAIL_BACKEND": SMTP, "PUBLIC_CANONICAL_ORIGIN": "https://azurelms.uz", "IS_LOCAL": False}


def by_key(readiness):
    return {item.key: item for item in readiness.items}


def fake_checks(*items):
    """`CHECKS` o'rniga: aynan berilgan bandlar (sahifa, tasdiq va CLI testlari uchun)."""
    return tuple((item.key, item.label, (lambda item=item: item)) for item in items)


GREEN_REQUIRED = gate.ReadinessItem("legal_privacy", "Maxfiylik siyosati", gate.GREEN, True, "Amaldagi matn bor.")
RED_REQUIRED = gate.ReadinessItem("support_contact", "Aloqa kanali", gate.RED, True, "Sozlanmagan.", "Telefon kiriting.")
AMBER_OPTIONAL = gate.ReadinessItem("claims", "Da'volar dalili", gate.AMBER, False, "1 ta da'vo yashirildi.", "Qayta tasdiqlang.")


@override_settings(**PRODUCTION)
class ReadyWorld(TestCase):
    """Mock'siz haqiqiy ma'lumot: majburiy bandlarning hammasi yashil."""

    def setUp(self):
        self.owner = User.objects.create_superuser("egasi", email="egasi@example.test", password="Egasi-2026!")
        for kind, title in ((LegalDocument.KIND_PRIVACY, "Maxfiylik"), (LegalDocument.KIND_TERMS, "Shartlar")):
            row = legal.approve(legal.create_draft(kind, title=title, version_label="1.0", content=f"<p>Haqiqiy {title} matni.</p>",
                                                   actor=self.owner), actor=self.owner, reason="Yurist tekshirdi")
            legal.publish(row, actor=self.owner, reason="Nashr", effective_at=timezone.now(),
                          expected_document_revision=LegalDocument.objects.get(kind=kind).revision)
        SiteSettings.objects.update_or_create(pk=1, defaults={"contact_phone": "+998 90 000 00 00",
                                                              "payment_card_number": "8600 5555 6666 7777"})
        Plan.objects.create(name="Oddiy", price=Decimal("200000"), order=1)
        self.course = Course.objects.create(title="Turk tili A1", description="<p>d</p>", level="beginner")
        Cohort.objects.create(course=self.course, name="Guruh 1", start_date=timezone.localdate())


class SelectorTests(ReadyWorld):
    def test_a_real_ready_world_is_ready_for_pilot(self):
        readiness = gate.release_readiness()
        items = by_key(readiness)
        for key in ("legal_privacy", "legal_terms", "live_offer", "support_contact", "payment_details", "email_delivery",
                    "canonical_origin", "sitemap", "public_media"):
            self.assertEqual(items[key].status, gate.GREEN, (key, items[key].summary))
            self.assertTrue(items[key].required, key)
        for key in ("legal_faq", "closed_offers", "claims", "testimonials", "certificates", "sit_freshness",
                    "settings_rows"):
            self.assertFalse(items[key].required, key)
        self.assertTrue(readiness.ready_for_pilot)
        self.assertEqual(readiness.blockers, ())

    def test_unpublished_legal_text_blocks_the_pilot(self):
        legal.LegalRevision.objects.filter(document__kind=LegalDocument.KIND_TERMS).delete()
        readiness = gate.release_readiness()
        self.assertEqual(by_key(readiness)["legal_terms"].status, gate.RED)
        self.assertEqual(by_key(readiness)["legal_privacy"].status, gate.GREEN)
        self.assertFalse(readiness.ready_for_pilot)
        self.assertEqual([item.key for item in readiness.blockers], ["legal_terms"])
        self.assertTrue(by_key(readiness)["legal_terms"].fix)

    def test_generated_sample_text_is_not_a_real_policy(self):
        states = (LegalPageState("privacy", STATE_GENERATED), LegalPageState("terms", STATE_READY),
                  LegalPageState("faq", STATE_MISSING))
        with mock.patch("core.public_readiness.legal_readiness", return_value=states):
            items = by_key(gate.release_readiness())
        self.assertEqual(items["legal_privacy"].status, gate.RED)
        self.assertIn("namuna", items["legal_privacy"].summary)
        self.assertEqual(items["legal_faq"].status, gate.AMBER)  # FAQ ixtiyoriy — ko'pi bilan sariq
        self.assertFalse(items["legal_faq"].required)

    def test_no_course_open_for_enrollment_is_red(self):
        Cohort.objects.all().delete()
        items = by_key(gate.release_readiness())
        self.assertEqual(items["live_offer"].status, gate.RED)
        self.assertEqual(items["closed_offers"].status, gate.AMBER)

    def test_one_closed_course_next_to_an_open_one_is_only_a_warning(self):
        Course.objects.create(title="Yopiq kurs", description="<p>d</p>", level="beginner")
        readiness = gate.release_readiness()
        self.assertEqual(by_key(readiness)["live_offer"].status, gate.GREEN)
        self.assertEqual(by_key(readiness)["closed_offers"].status, gate.AMBER)
        self.assertTrue(readiness.ready_for_pilot)
        self.assertEqual(readiness.status, gate.AMBER)

    def test_missing_contact_is_red(self):
        SiteSettings.objects.filter(pk=1).update(contact_phone="", contact_email="")
        self.assertEqual(by_key(gate.release_readiness())["support_contact"].status, gate.RED)

    def test_a_sample_or_empty_card_number_blocks_the_pilot(self):
        sample = SiteSettings._meta.get_field("payment_card_number").default
        for card in (sample, "", "   "):
            with self.subTest(card=card):
                SiteSettings.objects.filter(pk=1).update(payment_card_number=card)
                readiness = gate.release_readiness()
                self.assertEqual(by_key(readiness)["payment_details"].status, gate.RED)
                self.assertFalse(readiness.ready_for_pilot)
        SiteSettings.objects.filter(pk=1).delete()  # qator yo'q — model namunasi chiqadi
        self.assertEqual(by_key(gate.release_readiness())["payment_details"].status, gate.RED)

    def test_a_real_card_shows_only_its_last_digits(self):
        item = by_key(gate.release_readiness())["payment_details"]
        self.assertIn("7777", item.summary)
        self.assertNotIn("5555", item.summary)

    def test_console_email_is_red_in_production_and_amber_locally(self):
        with override_settings(EMAIL_BACKEND=CONSOLE):
            self.assertEqual(by_key(gate.release_readiness())["email_delivery"].status, gate.RED)
        with override_settings(EMAIL_BACKEND=CONSOLE, IS_LOCAL=True):
            item = by_key(gate.release_readiness())["email_delivery"]
        self.assertEqual(item.status, gate.AMBER)
        self.assertTrue(item.required)

    def test_recent_reset_delivery_failures_are_a_warning(self):
        SystemAuditEvent.objects.create(action=RESET_DELIVERY_FAILED_ACTION, outcome=SystemAuditEvent.OUTCOME_FAILURE)
        item = by_key(gate.release_readiness())["email_delivery"]
        self.assertEqual(item.status, gate.AMBER)
        self.assertIn("1", item.summary)

    def test_origin_must_be_a_real_https_domain(self):
        for origin in ("http://azurelms.uz", "https://localhost:8000", "https://app.localhost", "",
                       "https://azurelms.uz/", "https://azurelms.uz/kurslar", "https://azurelms.uz?ref=1",
                       "https://azurelms.uz#top", "https://egasi@azurelms.uz", "https://egasi:parol@azurelms.uz"):
            with self.subTest(origin=origin), override_settings(PUBLIC_CANONICAL_ORIGIN=origin):
                self.assertEqual(by_key(gate.release_readiness())["canonical_origin"].status, gate.RED)
        with override_settings(PUBLIC_CANONICAL_ORIGIN="http://localhost:8000", IS_LOCAL=True):
            self.assertEqual(by_key(gate.release_readiness())["canonical_origin"].status, gate.AMBER)
        with override_settings(PUBLIC_CANONICAL_ORIGIN="http://localhost:8000/app", IS_LOCAL=True):
            self.assertEqual(by_key(gate.release_readiness())["canonical_origin"].status, gate.RED)

    def test_a_public_file_missing_from_storage_is_red(self):
        Course.objects.filter(pk=self.course.pk).update(thumbnail="courses/yoq-rasm.jpg")
        item = by_key(gate.release_readiness())["public_media"]
        self.assertEqual(item.status, gate.RED)
        self.assertIn(f"courses.Course #{self.course.pk}", item.summary)

    def test_only_publicly_shown_testimonial_photos_can_block(self):
        hidden = Testimonial.objects.create(name="Vali", text="Yaxshi", is_active=True, avatar="testimonials/yoq-1.jpg")
        self.assertEqual(by_key(gate.release_readiness())["public_media"].status, gate.GREEN)
        public_claims.set_testimonial_consent(hidden, actor=self.owner, confirmed=True, reason="Yozma rozilik")
        item = by_key(gate.release_readiness())["public_media"]
        self.assertEqual(item.status, gate.RED)
        self.assertIn(f"frontend.Testimonial #{hidden.pk}", item.summary)

    def test_a_broken_sitemap_is_red(self):
        with mock.patch("frontend.public_sitemap.sitemap_entries", side_effect=ValueError("blog_tags: exclude")):
            item = by_key(gate.release_readiness())["sitemap"]
        self.assertEqual(item.status, gate.RED)
        self.assertIn("blog_tags", item.summary)

    def test_hidden_or_expiring_claims_warn_but_do_not_block(self):
        soon = SimpleNamespace(expires_at=timezone.now() + timedelta(days=3))
        later = SimpleNamespace(expires_at=timezone.now() + timedelta(days=90))
        cases = (
            ([SimpleNamespace(status=public_claims.STALE, evidence=later)], gate.AMBER),
            ([SimpleNamespace(status=public_claims.EXPIRED, evidence=later)], gate.AMBER),
            ([SimpleNamespace(status=public_claims.VERIFIED, evidence=soon)], gate.AMBER),
            ([SimpleNamespace(status=public_claims.VERIFIED, evidence=later),
              SimpleNamespace(status=public_claims.MISSING, evidence=None)], gate.GREEN),
        )
        for claims, expected in cases:
            with self.subTest(claims=claims), mock.patch("frontend.public_claims.all_claims", return_value=claims):
                readiness = gate.release_readiness()
            self.assertEqual(by_key(readiness)["claims"].status, expected)
            self.assertFalse(by_key(readiness)["claims"].required)
            self.assertTrue(readiness.ready_for_pilot)  # yashirilgan da'vo reliz to'sig'i emas

    def test_testimonials_without_consent_are_hidden_and_flagged(self):
        self.assertEqual(by_key(gate.release_readiness())["testimonials"].status, gate.GREEN)
        Testimonial.objects.create(name="Ali", text="Zo'r kurs", is_active=True)
        readiness = gate.release_readiness()
        item = by_key(readiness)["testimonials"]
        self.assertEqual((item.status, item.required), (gate.AMBER, False))
        self.assertIn("1 ta", item.summary)
        self.assertTrue(readiness.ready_for_pilot)

    def test_certificate_codes_matter_only_when_the_verifier_is_on(self):
        Certificate.objects.create(student=self.owner, course=self.course, certificate_id="AZ-1", final_score=90)
        Certificate.objects.filter(certificate_id="AZ-1").update(public_token=None)
        self.assertEqual(by_key(gate.release_readiness())["certificates"].status, gate.GREEN)
        FeatureFlag.objects.update_or_create(slug="certificate_public_verifier", defaults={"enabled": True})
        self.assertEqual(by_key(gate.release_readiness())["certificates"].status, gate.AMBER)

    def test_a_failing_check_becomes_a_red_required_item_and_the_rest_still_run(self):
        with mock.patch("core.public_readiness.contact_readiness", side_effect=RuntimeError("db")):
            readiness = gate.release_readiness()
        item = by_key(readiness)["support_contact"]
        self.assertEqual((item.status, item.required), (gate.RED, True))
        self.assertIn("RuntimeError", item.summary)
        self.assertEqual(by_key(readiness)["live_offer"].status, gate.GREEN)
        self.assertFalse(readiness.ready_for_pilot)

    def test_digest_follows_statuses_not_wording(self):
        first = gate.release_readiness()
        self.assertEqual(gate.release_readiness().digest(), first.digest())
        second = Course.objects.create(title="Turk tili A2", description="<p>d</p>", level="beginner")
        Cohort.objects.create(course=second, name="Guruh 2", start_date=timezone.localdate())
        now = gate.release_readiness()
        self.assertNotEqual(by_key(now)["live_offer"].summary, by_key(first)["live_offer"].summary)
        self.assertEqual(now.digest(), first.digest())  # matn o'zgardi, holat emas
        first = first.digest()
        SiteSettings.objects.filter(pk=1).update(contact_phone="")
        self.assertNotEqual(gate.release_readiness().digest(), first)


class FixLinkTests(ReadyWorld):
    def test_every_non_green_item_points_somewhere_that_resolves(self):
        Cohort.objects.all().delete()
        SiteSettings.objects.filter(pk=1).update(contact_phone="", contact_email="")
        legal.LegalRevision.objects.all().delete()
        for item in gate.release_readiness().items:
            self.assertTrue(item.fix or item.status == gate.GREEN, item.key)
            if item.link.startswith("admin:"):
                continue  # /admin/ faqat ENABLE_LEGACY_ADMIN=True bo'lsa — yo'q bo'lsa havola chiqmaydi
            if item.link:
                self.assertTrue(item.href.startswith("/"), (item.key, item.link))

    def test_an_unknown_route_gives_no_link_instead_of_crashing(self):
        self.assertEqual(gate.ReadinessItem("x", "X", gate.RED, True, "", "", "yoq_route").href, "")

    def test_settings_rows_use_human_names(self):
        item = by_key(gate.release_readiness())["settings_rows"]
        self.assertNotIn("frontend.", item.summary)


class StatusTests(TestCase):
    def readiness(self, *items):
        return gate.ReleaseReadiness(items=items, checked_at=timezone.now())

    def test_optional_red_counts_as_amber_and_required_red_as_red(self):
        optional_red = gate.ReadinessItem("x", "X", gate.RED, False, "")
        self.assertEqual(self.readiness(GREEN_REQUIRED, optional_red).status, gate.AMBER)
        self.assertTrue(self.readiness(GREEN_REQUIRED, optional_red).ready_for_pilot)
        self.assertEqual(self.readiness(GREEN_REQUIRED, RED_REQUIRED, AMBER_OPTIONAL).status, gate.RED)
        self.assertEqual(self.readiness(GREEN_REQUIRED).status, gate.GREEN)

    def test_a_required_amber_still_blocks_the_pilot(self):
        amber = gate.ReadinessItem("email_delivery", "Email", gate.AMBER, True, "console")
        readiness = self.readiness(GREEN_REQUIRED, amber)
        self.assertFalse(readiness.ready_for_pilot)
        self.assertEqual(readiness.blockers, (amber,))


class SignOffTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser("egasi", email="egasi@example.test", password="Egasi-2026!")

    def test_sign_off_is_refused_while_a_required_item_is_not_green(self):
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED, RED_REQUIRED)):
            with self.assertRaises(gate.NotReady) as raised:
                gate.sign_off(actor=self.owner, reason="Ochamiz")
        self.assertIn("Aloqa kanali", str(raised.exception))
        self.assertFalse(SystemAuditEvent.objects.filter(action=gate.SIGNOFF_ACTION).exists())

    def test_sign_off_needs_a_reason(self):
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED)), self.assertRaises(ValueError):
            gate.sign_off(actor=self.owner, reason="  ")
        self.assertIsNone(gate.last_sign_off())

    def test_sign_off_records_the_exact_state_it_approved(self):
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED, AMBER_OPTIONAL)):
            readiness = gate.sign_off(actor=self.owner, reason="Pilot 1-guruh")
        event = gate.last_sign_off()
        self.assertEqual(event.actor, self.owner)
        self.assertEqual(event.reason, "Pilot 1-guruh")
        self.assertEqual(event.after["digest"], readiness.digest())
        self.assertEqual(event.after["items"], {"legal_privacy": "green", "claims": "amber"})
        self.assertIn(readiness.digest(), event.target_label)


class OwnerPageTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser("egasi", email="egasi@example.test", password="Egasi-2026!")
        self.staff = User.objects.create_user("xodim", email="xodim@example.test", password="Xodim-2026!", is_staff=True)

    def test_only_the_owner_can_open_the_page(self):
        self.assertEqual(self.client.get(URL).status_code, 302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(URL).status_code, 302)
        self.assertEqual(self.client.post(URL, {"reason": "x", "confirm": "on", "digest": "x"}).status_code, 302)
        self.assertFalse(SystemAuditEvent.objects.filter(action=gate.SIGNOFF_ACTION).exists())

    def test_not_ready_page_shows_every_item_with_its_fix_and_no_sign_off_form(self):
        self.client.force_login(self.owner)
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED, RED_REQUIRED, AMBER_OPTIONAL)):
            response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('data-release-item="support_contact" data-status="red"', html)
        self.assertIn('data-release-item="claims" data-status="amber"', html)
        self.assertIn("Telefon kiriting.", html)
        self.assertIn(f'href="{reverse("backoffice_legal_documents")}"', OwnerPageTests.render_red_legal(self))
        self.assertIn("data-release-locked", html)
        self.assertNotIn("data-release-signoff", html)

    def test_ready_page_accepts_a_sign_off_with_the_current_digest(self):
        self.client.force_login(self.owner)
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED, AMBER_OPTIONAL)):
            page = self.client.get(URL)
            self.assertIn("data-release-signoff", page.content.decode())
            digest = page.context["readiness"].digest()
            response = self.client.post(URL, {"digest": digest, "reason": "Pilot ochiladi", "confirm": "on"})
        self.assertRedirects(response, URL, fetch_redirect_response=False)
        event = gate.last_sign_off()
        self.assertEqual((event.actor, event.after["digest"]), (self.owner, digest))

    def test_a_stale_digest_is_refused(self):
        self.client.force_login(self.owner)
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED)):
            response = self.client.post(URL, {"digest": "0" * 16, "reason": "Pilot", "confirm": "on"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("data-release-errors", response.content.decode())
        self.assertIsNone(gate.last_sign_off())

    def test_a_forged_post_cannot_sign_off_a_red_state(self):
        self.client.force_login(self.owner)
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED, RED_REQUIRED)):
            digest = gate.release_readiness().digest()
            response = self.client.post(URL, {"digest": digest, "reason": "Baribir", "confirm": "on"})
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(gate.last_sign_off())

    def test_reason_and_confirmation_are_required(self):
        self.client.force_login(self.owner)
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED)):
            digest = gate.release_readiness().digest()
            for data in ({"digest": digest, "reason": "Pilot"}, {"digest": digest, "confirm": "on"}):
                with self.subTest(data=data):
                    self.assertEqual(self.client.post(URL, data).status_code, 400)
        self.assertIsNone(gate.last_sign_off())

    def render_red_legal(self):
        item = gate.ReadinessItem("legal_terms", "Foydalanish shartlari", gate.RED, True, "E'lon qilinmagan.",
                                  "Nashr qiling.", "backoffice_legal_documents")
        with mock.patch.object(gate, "CHECKS", fake_checks(item)):
            return self.client.get(URL).content.decode()

    def test_the_page_belongs_to_the_settings_section(self):
        from core.backoffice_navigation import section_for

        request = RequestFactory().get(URL)
        request.resolver_match, request.user = resolve(URL), self.owner
        self.assertEqual(section_for(request), "settings")

    def test_control_center_links_to_the_page_without_the_new_navigation_flag(self):
        self.client.force_login(self.owner)
        self.assertIn(f'href="{URL}"', self.client.get(reverse("backoffice_control")).content.decode())

    def test_the_settings_hub_links_to_the_page(self):
        from core.backoffice_navigation import FLAG

        FeatureFlag.objects.update_or_create(slug=FLAG, defaults={"enabled": True})
        self.client.force_login(self.owner)
        self.assertIn(URL, self.client.get(reverse("backoffice_workspace_settings")).content.decode())


class SameAnswerEverywhereTests(TestCase):
    def test_strangers_see_no_readiness_detail_on_health_endpoints(self):
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED, RED_REQUIRED)):
            for name in ("healthz", "readyz"):
                with self.subTest(name=name):
                    body = self.client.get(reverse(name)).content.decode()
                    self.assertEqual(set(json.loads(body)), {"status"})
                    for leak in ("public_release", "support_contact", "Aloqa", "digest"):
                        self.assertNotIn(leak, body)

    def test_control_center_probe_matches_the_selector(self):
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED, RED_REQUIRED, AMBER_OPTIONAL)):
            readiness = gate.release_readiness()
            result = PROBE_FUNCTIONS["public_release"](capability_by_slug("public_release"))
        details = dict(result.details)
        self.assertEqual(result.status, readiness.status)
        self.assertEqual(details["digest"], readiness.digest())
        self.assertEqual(details["support_contact"], "red (majburiy)")
        self.assertEqual(details["claims"], "amber")
        self.assertIn("Aloqa kanali", result.summary)

    def test_cli_fails_by_default_when_a_required_item_is_only_amber(self):
        amber_required = gate.ReadinessItem("email_delivery", "Email yuborish", gate.AMBER, True, "console")
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED, amber_required)):
            self.assertEqual(gate.release_readiness().status, gate.AMBER)
            with self.assertRaises(CommandError) as raised:
                call_command("public_release_gate", stdout=StringIO())
            self.assertIn("Email yuborish", str(raised.exception))
            call_command("public_release_gate", "--fail-on", "red", stdout=StringIO())
            with self.assertRaises(CommandError):
                call_command("public_release_gate", "--fail-on", "amber", stdout=StringIO())

    def test_cli_reports_the_same_items_and_fails_on_red(self):
        out = StringIO()
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED, RED_REQUIRED)):
            readiness = gate.release_readiness()
            with self.assertRaises(CommandError):
                call_command("public_release_gate", "--json", stdout=out)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["digest"], readiness.digest())
            self.assertEqual([item["status"] for item in payload["items"]], ["green", "red"])
            self.assertFalse(payload["ready_for_pilot"])
            call_command("public_release_gate", "--fail-on", "never", stdout=StringIO())

    def test_cli_fail_on_amber_and_the_text_report(self):
        out = StringIO()
        with mock.patch.object(gate, "CHECKS", fake_checks(GREEN_REQUIRED, AMBER_OPTIONAL)):
            call_command("public_release_gate", stdout=out)  # sariq — default (red) bo'yicha o'tadi
            with self.assertRaises(CommandError):
                call_command("public_release_gate", "--fail-on", "amber", stdout=StringIO())
        text = out.getvalue()
        self.assertIn("PILOTGA TAYYOR", text)
        self.assertIn("Qayta tasdiqlang.", text)
