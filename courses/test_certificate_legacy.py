"""PUB1.5d — eski sertifikat havolasi, ballar ilovasi va mavjud sertifikatlarga kod.

Asosiy da'volar:
* to'liq hujjat va ballar ilovasi faqat egasi va xodimlarga; ilova mehmonga hech
  qachon ochilmaydi, boshqa foydalanuvchi uchun sertifikat borligi ham bilinmaydi;
* eski `AZ-…` havola boshqalarga o'tish davrida faqat minimal tasdiq, owner
  yopgach — "topilmadi"; egasining hujjati yo'qolmaydi (chop etish ham ishlaydi);
* eski havola ochilishlari kunlik sanaladi (bazaga yozilmaydi, ID/IP yo'q);
* kodsiz sertifikatlarga kod — mashq, davom ettirish, qayta yugurish, to'qnashuv;
* o'quvchiga yangi havola faqat flag yoqilganda; flag o'chsa eski holat qaytadi.
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from aicontrol.models import FeatureFlag
from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import PROBE_FUNCTIONS
from core.models import OperationalSettings
from courses import certificate_verifier as verifier
from courses.models import Certificate, Course
from users.models import AuthThrottleBucket

User = get_user_model()


def set_flag(slug, enabled):
    FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": enabled})


class LegacyWorld(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user("egasi", email="egasi@example.test", password="x", first_name="Ali", last_name="Valiyev")
        self.other = User.objects.create_user("begona", email="begona@example.test", password="x")
        self.staff = User.objects.create_user("xodim", email="xodim@example.test", password="x", is_staff=True)
        self.course = Course.objects.create(title="Turk tili A1", description="d", level="beginner")
        self.certificate = Certificate.objects.create(
            student=self.owner, course=self.course, certificate_id=f"AZ-{self.course.pk}-{self.owner.pk}-ABC123", final_score=91,
        )
        self.detail = reverse("certificate_detail", args=[self.certificate.certificate_id])
        self.appendix = reverse("certificate_appendix", args=[self.certificate.certificate_id])

    def as_user(self, user):
        self.client.logout()
        if user is not None:
            self.client.force_login(user)


class RoleMatrixTests(LegacyWorld):
    def test_full_document_only_for_the_owner_and_staff(self):
        for user, full in ((self.owner, True), (self.staff, True), (self.other, False), (None, False)):
            self.as_user(user)
            response = self.client.get(self.detail)
            with self.subTest(user=getattr(user, "username", "mehmon")):
                self.assertEqual(response.status_code, 200)
                if full:
                    self.assertContains(response, "91")
                    self.assertContains(response, "Ali Valiyev")
                else:
                    self.assertNotContains(response, "91")
                    self.assertNotContains(response, "Valiyev")
                    self.assertContains(response, "Ali V.")
                    self.assertNotContains(response, self.appendix)

    def test_the_appendix_is_never_public(self):
        expected = {self.owner: 200, self.staff: 200, self.other: 404}
        for user, status in expected.items():
            self.as_user(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get(self.appendix).status_code, status)
        self.as_user(None)
        response = self.client.get(self.appendix)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_the_owner_keeps_printing_the_full_document(self):
        set_flag("frontend_v1_certificates", True)
        self.as_user(self.owner)
        response = self.client.get(self.detail + "?download=1")
        self.assertContains(response, "data-certificate-print")
        self.assertContains(response, "91 / 100")


@override_settings(TRUSTED_PROXY_HOPS=0)
class LegacyLinkTests(LegacyWorld):
    def test_random_ids_are_generic_and_counted(self):
        row = OperationalSettings.load()
        row.certificate_verify_ip_limit = 2
        row.save()
        for index in range(2):
            response = self.client.get(reverse("certificate_detail", args=[f"AZ-1-1-ZZZ{index}"]))
            self.assertEqual(response.status_code, 404)
            self.assertContains(response, "Sertifikat topilmadi", status_code=404)
        self.assertEqual(self.client.get(self.detail).status_code, 429)

    def test_ending_the_grace_period_closes_the_legacy_link_for_strangers_only(self):
        set_flag("certificate_legacy_public_view", False)
        stranger = self.client.get(self.detail)
        self.assertEqual(stranger.status_code, 404)
        self.assertEqual(stranger.content, self.client.get(reverse("certificate_detail", args=["AZ-9-9-NONE"])).content)
        self.as_user(self.owner)
        self.assertContains(self.client.get(self.detail), "91")

    def test_hidden_and_revoked_follow_the_public_status(self):
        verifier.set_public_status(self.certificate, status=Certificate.PUBLIC_REVOKED, actor=None, reason="Sinov",
                                   expected_revision=0)
        response = self.client.get(self.detail)
        self.assertContains(response, "Bekor qilingan sertifikat")
        verifier.set_public_status(self.certificate, status=Certificate.PUBLIC_HIDDEN, actor=None, reason="Sinov",
                                   expected_revision=1)
        self.assertEqual(self.client.get(self.detail).status_code, 404)

    def test_stranger_views_are_counted_without_touching_the_database(self):
        before = (AuthThrottleBucket.objects.count(), Certificate.objects.count())
        self.client.get(self.detail)
        self.client.get(self.detail)
        self.as_user(self.owner)
        self.client.get(self.detail)  # egasi sanalmaydi
        self.assertEqual(verifier.legacy_public_views(30), 2)
        self.assertEqual((AuthThrottleBucket.objects.count(), Certificate.objects.count()), before)
        result = PROBE_FUNCTIONS["public_content"](capability_by_slug("public_content"))
        self.assertIn(("certificate_legacy_views_30d", "2"), result.details)

    def test_the_legacy_page_explains_itself(self):
        self.assertContains(self.client.get(self.detail), "Bu eski havola")


class LearnerLinkTests(LegacyWorld):
    def test_the_new_link_appears_only_while_the_verifier_is_on(self):
        token = verifier.ensure_public_token(self.certificate)
        set_flag("frontend_v1_records", True)
        set_flag("frontend_v1_certificates", True)
        self.as_user(self.owner)
        records, document = reverse("certificates"), self.detail
        self.assertNotContains(self.client.get(records), token)
        self.assertNotContains(self.client.get(document), token)
        set_flag("certificate_public_verifier", True)
        verify = reverse("certificate_verify", args=[token])
        self.assertContains(self.client.get(records), verify)
        self.assertContains(self.client.get(document), verify)
        set_flag("certificate_public_verifier", False)  # rollback: eski havola qaytadi, kod saqlanadi
        self.assertNotContains(self.client.get(document), verify)
        self.assertEqual(Certificate.objects.get(pk=self.certificate.pk).public_token, token)

    def test_no_token_means_no_link(self):
        set_flag("certificate_public_verifier", True)
        set_flag("frontend_v1_records", True)
        self.as_user(self.owner)
        self.assertNotContains(self.client.get(reverse("certificates")), "data-certificate-verify-link")


class BackfillTests(LegacyWorld):
    def setUp(self):
        super().setUp()
        for index in range(4):
            course = Course.objects.create(title=f"K{index}", description="d", level="beginner")
            Certificate.objects.create(student=self.owner, course=course, certificate_id=f"AZ-B-{index}", final_score=70)
        self.has_token = Certificate.objects.create(
            student=self.other, course=self.course, certificate_id="AZ-HAS", final_score=80)
        verifier.ensure_public_token(self.has_token)
        self.existing = Certificate.objects.get(pk=self.has_token.pk).public_token

    def test_dry_run_writes_nothing(self):
        report = verifier.backfill_tokens()
        self.assertEqual((report.missing_before, report.processed, report.missing_after), (5, 5, 5))
        self.assertEqual(Certificate.objects.filter(public_token__isnull=True).count(), 5)

    def test_apply_resumes_reruns_safely_and_reads_back(self):
        first = verifier.backfill_tokens(apply=True, limit=2)
        self.assertEqual((first.processed, first.missing_after), (2, 3))
        second = verifier.backfill_tokens(apply=True)
        self.assertEqual((second.processed, second.missing_after), (3, 0))
        third = verifier.backfill_tokens(apply=True)
        self.assertEqual((third.processed, third.missing_after), (0, 0))
        tokens = list(Certificate.objects.values_list("public_token", flat=True))
        self.assertEqual(len(set(tokens)), len(tokens))
        self.assertTrue(all(verifier.TOKEN_RE.match(token) for token in tokens))
        self.assertEqual(Certificate.objects.get(pk=self.has_token.pk).public_token, self.existing)

    def test_the_same_set_gives_the_same_digest(self):
        self.assertEqual(verifier.backfill_tokens().digest, verifier.backfill_tokens().digest)

    def test_a_collision_during_backfill_is_retried(self):
        with mock.patch.object(verifier, "new_token", side_effect=[self.existing] + [f"{i}" * 32 for i in range(1, 9)]):
            report = verifier.backfill_tokens(apply=True)
        self.assertEqual(report.missing_after, 0)

    def test_the_command_reports_without_printing_tokens(self):
        from io import StringIO

        out = StringIO()
        call_command("backfill_certificate_tokens", stdout=out)
        self.assertIn("mashq", out.getvalue())
        call_command("backfill_certificate_tokens", "--apply", stdout=out)
        self.assertIn("kodsiz qoldi: 0", out.getvalue())
        for token in Certificate.objects.values_list("public_token", flat=True):
            self.assertNotIn(token, out.getvalue())
