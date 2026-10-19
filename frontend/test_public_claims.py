"""PUB1.2a — public da'volar faqat dalil bilan, fikrlar faqat rozilik bilan.

Seed qilingan "2400+ Faol talaba / 94% Sertifikat oldi / 4.9 Reyting" va auth
panelidagi qattiq yozilgan raqamlar dalilsiz ko'rinmaydi. Tahrir dalilni
eskirtiradi, muddat tugasa yashirinadi, tasdiqlash/qaytarish audit bilan.
"""

from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag, SystemAuditEvent
from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import PROBE_FUNCTIONS
from frontend import public_claims
from frontend.models import AboutStatistic, PublicClaimEvidence, Statistic, Testimonial


def approve_for_test(stat, *, days=30):
    """Testlar uchun: statistikani owner nomidan dalil bilan tasdiqlaydi."""
    User = get_user_model()
    owner = User.objects.filter(is_superuser=True).first() or User.objects.create_superuser(
        "dalil-egasi", email="dalil-egasi@example.test", password="Dalil-egasi-2026!")
    key = public_claims.statistic_key(stat) if isinstance(stat, Statistic) else public_claims.about_statistic_key(stat)
    row = PublicClaimEvidence.objects.filter(claim_key=key).first()
    return public_claims.approve(key, actor=owner, reason="Test dalili", expected_revision=row.revision if row else 0,
                                 expires_at=timezone.now() + timedelta(days=days))


def set_v1(enabled):
    for slug in ("frontend_v1_public", "frontend_v1_auth"):
        FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": enabled})


class ClaimMixin:
    def setUp(self):
        self.owner = get_user_model().objects.create_superuser("egasi", email="egasi@example.test", password="Egasi-2026!")
        Statistic.objects.all().delete()
        self.students = Statistic.objects.create(numeric_value=2400, suffix="+", decimals=0, label="Faol talaba", order=1)
        self.rate = Statistic.objects.create(numeric_value=94, suffix="%", decimals=0, label="Sertifikat oldi", order=2)
        self.rating = Statistic.objects.create(numeric_value="4.9", suffix="", decimals=1, label="Reyting", order=3)
        self.about = AboutStatistic.objects.create(value="500+", label="Bitiruvchi", order=1)

    def approve(self, key, revision=0, **extra):
        return public_claims.approve(key, actor=self.owner, reason="Dalil tekshirildi", expected_revision=revision,
                                     expires_at=extra.pop("expires_at", timezone.now() + timedelta(days=30)), **extra)


class UnverifiedClaimsAreHiddenTests(ClaimMixin, TestCase):
    def test_seeded_numbers_never_show_without_evidence(self):
        for enabled in (False, True):
            set_v1(enabled)
            for url in (reverse("home"), reverse("about"), reverse("login"), reverse("register")):
                with self.subTest(url=url, v1=enabled):
                    body = self.client.get(url).content.decode()
                    for label in ("Faol talaba", "Sertifikat oldi", "Bitiruvchi"):
                        self.assertNotIn(label, body)
                    self.assertNotIn('data-count="2400"', body)
                    self.assertNotIn("2,400+", body)

    def test_verified_claims_show_identically_in_both_renderers(self):
        self.approve(public_claims.statistic_key(self.students))
        self.approve(public_claims.about_statistic_key(self.about))
        seen = {}
        for enabled in (False, True):
            set_v1(enabled)
            home = self.client.get(reverse("home")).content.decode()
            about = self.client.get(reverse("about")).content.decode()
            shown = ("Faol talaba" in home, "Sertifikat oldi" in home, "Bitiruvchi" in about)
            self.assertEqual(shown, (True, False, True))
            seen[enabled] = shown
        self.assertEqual(seen[False], seen[True])
        set_v1(False)  # statistika paneli legacy auth chap panelida
        auth = self.client.get(reverse("login")).content.decode()
        self.assertIn("Faol talaba", auth)
        self.assertNotIn("Sertifikat oldi", auth)


class EvidenceLifecycleTests(ClaimMixin, TestCase):
    def key(self):
        return public_claims.statistic_key(self.students)

    def status(self, now=None):
        return next(claim for claim in public_claims.landing_statistic_claims(now) if claim.key == self.key()).status

    def test_editing_the_displayed_text_invalidates_the_evidence(self):
        self.approve(self.key())
        self.assertEqual(self.status(), public_claims.VERIFIED)
        Statistic.objects.filter(pk=self.students.pk).update(numeric_value=3000)
        self.assertEqual(self.status(), public_claims.STALE)
        Statistic.objects.filter(pk=self.students.pk).update(numeric_value=2400, label="Faol o‘quvchi")
        self.assertEqual(self.status(), public_claims.STALE)

    def test_expiry_boundary(self):
        expires = timezone.now() + timedelta(days=2)
        self.approve(self.key(), expires_at=expires)
        self.assertEqual(self.status(expires - timedelta(seconds=1)), public_claims.VERIFIED)
        self.assertEqual(self.status(expires), public_claims.EXPIRED)

    def test_revoke_hides_and_keeps_actor_and_reason(self):
        row = self.approve(self.key())
        public_claims.revoke(self.key(), actor=self.owner, reason="Raqam eskirdi", expected_revision=row.revision)
        self.assertEqual(self.status(), public_claims.REVOKED)
        events = list(SystemAuditEvent.objects.filter(target_label=self.key()).order_by("created_at")
                      .values_list("action", "actor_label", "reason"))
        self.assertEqual(events, [("public_claim.approve", "egasi", "Dalil tekshirildi"),
                                  ("public_claim.revoke", "egasi", "Raqam eskirdi")])

    def test_concurrent_approval_cannot_overwrite_silently(self):
        first = self.approve(self.key(), revision=0)
        with self.assertRaises(public_claims.ClaimConflict):
            self.approve(self.key(), revision=0)
        self.assertEqual(PublicClaimEvidence.objects.get(claim_key=self.key()).revision, first.revision)
        with self.assertRaises(public_claims.ClaimConflict):
            public_claims.revoke(self.key(), actor=self.owner, reason="x", expected_revision=first.revision - 1)

    def test_bad_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            self.approve(self.key(), expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(ValueError):
            self.approve(self.key(), source_url="http://manba.example/hisobot")
        with self.assertRaises(ValueError):
            public_claims.approve(self.key(), actor=self.owner, reason="  ", expected_revision=0,
                                  expires_at=timezone.now() + timedelta(days=1))
        self.assertFalse(PublicClaimEvidence.objects.exists())


class TestimonialConsentTests(ClaimMixin, TestCase):
    def make(self, name, order):
        return Testimonial.objects.create(name=name, text=f"{name} fikri", order=order)

    def test_only_consented_testimonials_show_in_stable_order(self):
        late, early, never = self.make("Kech", 2), self.make("Erta", 1), self.make("Rozisiz", 0)
        for item in (late, early):
            public_claims.set_testimonial_consent(item, actor=self.owner, confirmed=True, reason="Telegramda rozilik",
                                                  display_name=f"{item.name} B.", source_reference="2026-10-18 xabar")
        self.assertEqual([t.pk for t in public_claims.public_testimonials()], [early.pk, late.pk])
        set_v1(True)
        body = self.client.get(reverse("home")).content.decode()
        self.assertIn("Erta B.", body)
        self.assertNotIn("Rozisiz", body)
        self.assertLess(body.index("Erta B."), body.index("Kech B."))
        self.assertIn("umumiy reyting emas", body)
        # Random emas: qayta ochilganda ham ayni tartib.
        again = self.client.get(reverse("home")).content.decode()
        self.assertLess(again.index("Erta B."), again.index("Kech B."))

    def test_revoked_or_inactive_testimonials_disappear(self):
        item = self.make("Qaytargan", 1)
        public_claims.set_testimonial_consent(item, actor=self.owner, confirmed=True, reason="Rozilik", source_reference="x")
        self.assertEqual(len(public_claims.public_testimonials()), 1)
        public_claims.set_testimonial_consent(item, actor=self.owner, confirmed=False, reason="Egasi so‘radi")
        self.assertEqual(public_claims.public_testimonials(), [])
        item.refresh_from_db()
        self.assertFalse(item.has_public_consent)
        public_claims.set_testimonial_consent(item, actor=self.owner, confirmed=True, reason="Yangi rozilik", source_reference="y")
        Testimonial.objects.filter(pk=item.pk).update(is_active=False)
        self.assertEqual(public_claims.public_testimonials(), [])


class ConsentIntegrityTests(ClaimMixin, TestCase):
    """Codex review (PR #213): rozilikni admin'dan chetlab o'tib bo'lmaydi va tahrir uni eskirtiradi."""

    def consented(self):
        item = Testimonial.objects.create(name="Ali Valiyev", role="B1 talaba", text="Darslar foydali bo‘ldi.", order=1)
        public_claims.set_testimonial_consent(item, actor=self.owner, confirmed=True, reason="Telegramda rozilik",
                                              display_name="Ali V.", source_reference="2026-10-18 xabar")
        return item

    def test_editing_name_role_or_text_after_consent_hides_the_testimonial(self):
        for field, value in (("text", "Boshqa matn"), ("role", "C1 talaba"), ("name", "Boshqa odam")):
            with self.subTest(field=field):
                Testimonial.objects.all().delete()
                item = self.consented()
                self.assertEqual(len(public_claims.public_testimonials()), 1)
                if field == "name":
                    Testimonial.objects.filter(pk=item.pk).update(display_name="")
                else:
                    Testimonial.objects.filter(pk=item.pk).update(**{field: value})
                self.assertEqual(public_claims.public_testimonials(), [])
                item.refresh_from_db()
                self.assertTrue(item.consent_is_stale)

    def test_owner_page_flags_stale_consent_and_reconsent_restores_it(self):
        item = self.consented()
        Testimonial.objects.filter(pk=item.pk).update(text="Tahrirlangan matn")
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse("backoffice_claim_evidence")), "rozilikni qayta qayd eting")
        public_claims.set_testimonial_consent(Testimonial.objects.get(pk=item.pk), actor=self.owner, confirmed=True,
                                              reason="Yangi matnga rozilik", display_name="Ali V.", source_reference="yangi xabar")
        self.assertEqual([t.pk for t in public_claims.public_testimonials()], [item.pk])

    def test_generic_admin_cannot_write_consent_fields(self):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory

        from frontend.admin import TestimonialAdmin

        model_admin = TestimonialAdmin(Testimonial, AdminSite())
        request = RequestFactory().get("/")
        request.user = self.owner
        form_fields = model_admin.get_form(request)().fields
        for field in ("display_name", "consent_scope", "consent_confirmed_at", "consent_revoked_at",
                      "source_reference", "consent_digest"):
            with self.subTest(field=field):
                self.assertIn(field, model_admin.get_readonly_fields(request))
                self.assertNotIn(field, form_fields)
        from django.contrib import admin

        self.assertNotIn(PublicClaimEvidence, admin.site._registry)


class OwnerPageTests(ClaimMixin, TestCase):
    def test_owner_approves_with_reason_and_confirmation(self):
        self.client.force_login(self.owner)
        url = reverse("backoffice_claim_evidence")
        page = self.client.get(url)
        self.assertContains(page, f'data-claim="{public_claims.statistic_key(self.students)}"')
        self.assertContains(page, 'data-claim-status="missing"')
        payload = {"action": "approve", "claim_key": public_claims.statistic_key(self.students), "revision": 0,
                   "expires_on": (timezone.localdate() + timedelta(days=60)).isoformat(),
                   "source_url": "https://hisobot.example/2026", "reason": "CRM hisobot"}
        self.assertEqual(self.client.post(url, payload).status_code, 400)  # tasdiq belgisi yo'q
        self.assertFalse(PublicClaimEvidence.objects.exists())
        self.assertRedirects(self.client.post(url, {**payload, "confirm": "on"}), url)
        self.assertContains(Client().get(reverse("home")), "Faol talaba")
        stale = self.client.post(url, {**payload, "confirm": "on"})  # eski revision=0
        self.assertEqual(stale.status_code, 400)
        self.assertContains(stale, "boshqa oynada", status_code=400)

    def test_non_owner_staff_cannot_open_the_page(self):
        staff = get_user_model().objects.create_user("xodim", email="xodim@example.test", is_staff=True)
        self.client.force_login(staff)
        self.assertNotEqual(self.client.get(reverse("backoffice_claim_evidence")).status_code, 200)


class ReadinessTests(ClaimMixin, TestCase):
    def test_audit_command_is_read_only_and_never_marks_seeds_verified(self):
        out = StringIO()
        with CaptureQueriesContext(connection) as queries:
            call_command("audit_public_readiness", stdout=out)
            call_command("audit_public_readiness", stdout=StringIO())
        writes = [q["sql"] for q in queries.captured_queries if q["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))]
        self.assertEqual(writes, [])
        self.assertIn(f"[missing] {public_claims.statistic_key(self.students)}", out.getvalue())
        self.assertNotIn("[verified]", out.getvalue())

    def test_control_center_warns_only_when_approved_claims_go_dark(self):
        from frontend.models import AboutPage, AuthPageSettings, LandingPage, LegalPage, SiteSettings
        from blog.models import BlogHomeSettings

        for model in (SiteSettings, AuthPageSettings, LandingPage, AboutPage, BlogHomeSettings):
            model.objects.create()
        for page_type in ("privacy", "terms", "faq"):
            LegalPage.objects.create(page_type=page_type, title="Owner", content="<p>Owner matni</p>")
        from frontend.testing_legal import publish_all_legal

        publish_all_legal()
        probe = lambda: PROBE_FUNCTIONS["public_content"](capability_by_slug("public_content"))  # noqa: E731
        result = probe()
        self.assertEqual(result.status, "green")  # dalilsiz = yashirin, xavfsiz holat
        self.assertIn(("claims_without_evidence", "4"), result.details)
        self.approve(public_claims.statistic_key(self.students))
        Statistic.objects.filter(pk=self.students.pk).update(label="Boshqa matn")
        result = probe()
        self.assertEqual(result.status, "amber")
        self.assertIn(("claims_stale_or_expired", "1"), result.details)
