"""PUB1.5a — maxfiylik va shartlar: o'zgarmas versiyalar, bitta amaldagi versiya.

Asosiy da'volar:
* saytda faqat tasdiqlangan va nashr qilingan versiya; bir vaqtda bittasi;
* tasdiqlangan matn o'zgarmaydi; rejalashtirilgan versiya o'z vaqtida o'zi
  kuchga kiradi; amaldagisi bekor qilinsa oldingisi qaytadi;
* ikki oyna bir-birini bosib ketmaydi (CAS); har o'tish auditda;
* umumiy namuna matn tasdiqlanmaydi; eski qatorlar faqat tasdiqlanmagan
  qoralamaga ko'chadi va yo'qolmaydi;
* public GET va ko'rib chiqish hech narsa yozmaydi; yo'q hujjat — halol 503.
"""

import threading
from datetime import timedelta
from io import StringIO
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag, SystemAuditEvent
from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import PROBE_FUNCTIONS
from core.public_readiness import LEGACY_GENERATED_LEGAL_CONTENT
from frontend import legal_revisions as legal
from frontend.models import LegalDocument, LegalPage, LegalRevision

User = get_user_model()
PRIVACY, TERMS = LegalDocument.KIND_PRIVACY, LegalDocument.KIND_TERMS


def set_v1(enabled):
    FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": enabled})


class LegalWorld(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser("egasi", email="egasi@example.test", password="Egasi-2026!")

    def draft(self, kind=PRIVACY, label="1.0", content="<p>Haqiqiy maxfiylik matni.</p>", title="Maxfiylik siyosati"):
        return legal.create_draft(kind, title=title, version_label=label, content=content, actor=self.owner)

    def approved(self, **kwargs):
        return legal.approve(self.draft(**kwargs), actor=self.owner, reason="Yurist tekshirdi")

    def doc_revision(self, kind=PRIVACY):
        return LegalDocument.objects.get(kind=kind).revision

    def published(self, effective_at=None, now=None, **kwargs):
        row = self.approved(**kwargs)
        return legal.publish(row, actor=self.owner, reason="Nashr", effective_at=effective_at or timezone.now(),
                             expected_document_revision=self.doc_revision(row.document.kind), now=now)


class LifecycleTests(LegalWorld):
    def test_only_a_published_version_is_effective_and_only_one_at_a_time(self):
        first = self.approved()
        self.assertIsNone(legal.effective_revision(PRIVACY))  # tasdiqlangan, lekin nashr emas
        legal.publish(first, actor=self.owner, reason="Nashr", effective_at=timezone.now(),
                      expected_document_revision=self.doc_revision())
        self.assertEqual(legal.effective_revision(PRIVACY).pk, first.pk)
        second = self.published(label="2.0", content="<p>Yangilangan matn.</p>")
        self.assertEqual(legal.effective_revision(PRIVACY).pk, second.pk)
        self.assertEqual(LegalRevision.objects.filter(document__kind=PRIVACY, status="published").count(), 2)
        self.assertIsNone(legal.effective_revision(TERMS))

    def test_a_scheduled_version_takes_over_exactly_at_its_time(self):
        current = self.published()
        start = timezone.now() + timedelta(days=3)
        scheduled = self.published(label="2.0", content="<p>Keyingi matn.</p>", effective_at=start)
        self.assertEqual(legal.effective_revision(PRIVACY, now=start - timedelta(seconds=1)).pk, current.pk)
        self.assertEqual(legal.effective_revision(PRIVACY, now=start).pk, scheduled.pk)
        self.assertEqual([row.pk for row in legal.scheduled_revisions(PRIVACY)], [scheduled.pk])

    def test_approved_text_never_changes(self):
        row = self.approved()
        with self.assertRaises(legal.LegalConflict):
            legal.update_draft(row, title="Boshqa", version_label="1.0", content="<p>Boshqa matn</p>", actor=self.owner)
        with self.assertRaises(legal.LegalConflict):
            legal.approve(row, actor=self.owner, reason="Qayta")
        row.refresh_from_db()
        self.assertEqual(row.content, "<p>Haqiqiy maxfiylik matni.</p>")

    def test_only_an_approved_version_can_be_published(self):
        draft = self.draft()
        with self.assertRaises(legal.LegalConflict):
            legal.publish(draft, actor=self.owner, reason="Nashr", effective_at=timezone.now(),
                          expected_document_revision=self.doc_revision())

    def test_a_stale_window_cannot_overwrite_the_newer_decision(self):
        first, second = self.approved(), self.approved(label="2.0", content="<p>Ikkinchi</p>")
        stale = self.doc_revision()
        legal.publish(first, actor=self.owner, reason="Birinchi oyna", effective_at=timezone.now(),
                      expected_document_revision=stale)
        audit_before = SystemAuditEvent.objects.count()
        with self.assertRaises(legal.LegalConflict):
            legal.publish(second, actor=self.owner, reason="Eski oyna", effective_at=timezone.now(),
                          expected_document_revision=stale)
        second.refresh_from_db()
        self.assertEqual(second.status, LegalRevision.STATUS_APPROVED)
        self.assertEqual(SystemAuditEvent.objects.count(), audit_before)

    def test_past_effective_dates_are_refused(self):
        row = self.approved()
        with self.assertRaises(ValueError):
            legal.publish(row, actor=self.owner, reason="Nashr", effective_at=timezone.now() - timedelta(days=1),
                          expected_document_revision=self.doc_revision())

    def test_archiving_the_effective_version_rolls_back_to_the_previous_one(self):
        first = self.published()
        second = self.published(label="2.0", content="<p>Xato matn</p>")
        legal.archive(second, actor=self.owner, reason="Xato chiqdi", expected_document_revision=self.doc_revision())
        self.assertEqual(legal.effective_revision(PRIVACY).pk, first.pk)
        event = SystemAuditEvent.objects.filter(action="legal.rollback").get()
        self.assertEqual(event.before["effective"], "2.0")
        self.assertEqual(event.after["effective"], "1.0")
        legal.archive(first, actor=self.owner, reason="Hammasi qaytarildi", expected_document_revision=self.doc_revision())
        self.assertIsNone(legal.effective_revision(PRIVACY))
        self.assertEqual(LegalRevision.objects.count(), 2)  # hech biri o'chirilmadi

    def test_every_transition_is_audited_with_reason(self):
        row = self.published()
        actions = list(SystemAuditEvent.objects.order_by("pk").values_list("action", flat=True))
        self.assertEqual(actions, ["legal.draft_create", "legal.approve", "legal.publish"])
        publish = SystemAuditEvent.objects.get(action="legal.publish")
        self.assertEqual(publish.reason, "Nashr")
        self.assertEqual(publish.after["digest"], row.content_digest)

    def test_reasons_are_required(self):
        draft = self.draft()
        with self.assertRaises(ValueError):
            legal.approve(draft, actor=self.owner, reason="  ")


class ContentSafetyTests(LegalWorld):
    def test_content_is_sanitized_on_save_and_empty_text_is_refused(self):
        row = self.draft(content='<p>Matn</p><script>alert(1)</script><img src=x onerror="alert(2)">')
        self.assertNotIn("<script", row.content)
        self.assertNotIn("onerror", row.content)
        self.assertEqual(row.content_digest, legal.digest(row.content))
        for empty in ("", "<p> </p>", "<script>alert(1)</script>"):
            with self.subTest(content=empty), self.assertRaises(ValueError):
                self.draft(label=f"bo'sh-{len(empty)}", content=empty)

    def test_the_generated_sample_text_cannot_be_approved(self):
        row = self.draft(content=LEGACY_GENERATED_LEGAL_CONTENT["privacy"])
        with self.assertRaises(ValueError):
            legal.approve(row, actor=self.owner, reason="Shunchaki")
        row.refresh_from_db()
        self.assertEqual(row.status, LegalRevision.STATUS_DRAFT)

    def test_version_labels_are_unique_per_document(self):
        self.draft()
        with self.assertRaises(ValueError):
            self.draft()
        self.draft(kind=TERMS, title="Shartlar")  # boshqa hujjatda ayni nom mumkin


class BackfillTests(LegalWorld):
    def setUp(self):
        super().setUp()
        LegalPage.objects.create(page_type=PRIVACY, title="Privacy Policy", content=LEGACY_GENERATED_LEGAL_CONTENT["privacy"])
        LegalPage.objects.create(page_type=TERMS, title="Shartlar", content="<p>Owner yozgan shartlar</p><script>x</script>")
        self.before = list(LegalPage.objects.order_by("pk").values())

    def test_dry_run_writes_nothing_and_reports_what_would_happen(self):
        rows = legal.backfill_from_legacy()
        self.assertEqual([(row.kind, row.action, row.generated) for row in rows],
                         [(PRIVACY, "would_create", True), (TERMS, "would_create", False)])
        self.assertFalse(LegalRevision.objects.exists())
        self.assertFalse(LegalDocument.objects.exists())

    def test_apply_creates_unapproved_drafts_reruns_safely_and_reads_back(self):
        legal.backfill_from_legacy(apply=True)
        again = legal.backfill_from_legacy(apply=True)
        self.assertEqual([row.action for row in again], ["exists", "exists"])
        drafts = LegalRevision.objects.order_by("document__kind")
        self.assertEqual(drafts.count(), 2)
        self.assertTrue(all(row.status == "draft" and row.source == "legacy_backfill" for row in drafts))
        terms = drafts.get(document__kind=TERMS)
        self.assertEqual(terms.content, "<p>Owner yozgan shartlar</p>")
        self.assertEqual(terms.title, "Shartlar")
        self.assertEqual(list(LegalPage.objects.order_by("pk").values()), self.before)  # eski qator yo'qolmadi
        self.assertIsNone(legal.effective_revision(PRIVACY))
        self.assertIsNone(legal.effective_revision(TERMS))
        with self.assertRaises(ValueError):
            legal.approve(drafts.get(document__kind=PRIVACY), actor=self.owner, reason="Namuna")

    def test_the_command_defaults_to_a_dry_run(self):
        out = StringIO()
        call_command("backfill_legal_revisions", stdout=out)
        self.assertIn("mashq", out.getvalue())
        self.assertFalse(LegalRevision.objects.exists())
        call_command("backfill_legal_revisions", "--apply", stdout=out)
        self.assertEqual(LegalRevision.objects.count(), 2)
        self.assertIn("umumiy namuna matn, tasdiqlanmaydi", out.getvalue())


class PublicPageTests(LegalWorld):
    def counts(self):
        return LegalDocument.objects.count(), LegalRevision.objects.count(), SystemAuditEvent.objects.count()

    def test_missing_document_is_an_honest_503_and_legacy_rows_do_not_publish(self):
        LegalPage.objects.create(page_type=PRIVACY, title="Eski", content="<p>Eski matn</p>")
        self.approved()  # tasdiqlangan, lekin nashr qilinmagan
        before = self.counts()
        for enabled in (False, True):
            set_v1(enabled)
            response = self.client.get(reverse("privacy_policy"))
            with self.subTest(v1=enabled):
                self.assertEqual(response.status_code, 503)
                self.assertIn("noindex", response["X-Robots-Tag"])
                self.assertIn("no-store", response["Cache-Control"])
                self.assertNotContains(response, "Eski matn", status_code=503)
                self.assertNotContains(response, "Haqiqiy maxfiylik matni", status_code=503)
        self.assertEqual(self.counts(), before)

    def test_effective_version_is_shown_with_its_version_and_date_on_both_renderers(self):
        row = self.published(content="<p>Haqiqiy maxfiylik matni.</p><script>alert(1)</script>")
        before = self.counts()
        for enabled in (False, True):
            set_v1(enabled)
            response = self.client.get(reverse("privacy_policy"))
            html = response.content.decode()
            with self.subTest(v1=enabled):
                self.assertEqual(response.status_code, 200)
                self.assertIn("Haqiqiy maxfiylik matni.", html)
                self.assertIn(f"Versiya {row.version_label} · {timezone.localtime(row.effective_at):%d.%m.%Y} dan amal qiladi", html)
                self.assertNotIn("<script>alert(1)", html)
        self.assertEqual(self.counts(), before)

    def test_sitemap_lists_a_document_only_while_a_version_is_in_force(self):
        self.assertNotIn("/privacy-policy/", self.client.get("/sitemap.xml").content.decode())
        row = self.published()
        body = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("/privacy-policy/", body)
        self.assertIn(row.effective_at.date().isoformat(), body)

    def test_readiness_is_red_until_both_documents_are_in_force(self):
        LegalPage.objects.create(page_type="faq", title="FAQ", content="<p>Owner savol-javobi</p>")
        probe = lambda: PROBE_FUNCTIONS["public_content"](capability_by_slug("public_content"))  # noqa: E731
        self.published()
        result = probe()
        self.assertEqual(result.status, "red")
        self.assertIn(("legal_missing", "terms"), result.details)
        self.published(kind=TERMS, title="Shartlar", content="<p>Haqiqiy shartlar.</p>")
        self.assertNotIn(("legal_missing", "terms"), probe().details)


class OwnerPageTests(LegalWorld):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)

    def post(self, **data):
        return self.client.post(reverse("backoffice_legal_documents"), data)

    def test_only_the_owner_can_open_the_pages(self):
        staff = User.objects.create_user("xodim", email="xodim@example.test", password="Xodim-2026!", is_staff=True)
        row = self.draft()
        urls = [reverse("backoffice_legal_documents"), reverse("backoffice_legal_new", args=[PRIVACY]),
                reverse("backoffice_legal_edit", args=[row.pk]), reverse("backoffice_legal_preview", args=[row.pk])]
        for client_user in (None, staff):
            self.client.logout()
            if client_user:
                self.client.force_login(client_user)
            for url in urls:
                with self.subTest(user=getattr(client_user, "username", "anon"), url=url):
                    self.assertEqual(self.client.get(url).status_code, 302)

    def test_full_flow_through_the_owner_page(self):
        response = self.client.post(reverse("backoffice_legal_new", args=[TERMS]), {
            "version_label": "1.0", "title": "Foydalanish shartlari", "content": "<p>Shartlar matni.</p>", "reason": "",
        })
        self.assertRedirects(response, reverse("backoffice_legal_documents"))
        row = LegalRevision.objects.get(document__kind=TERMS)
        self.assertEqual(self.post(action="approve", revision_id=row.pk, reason="Yurist", confirm="on").status_code, 302)
        page = self.client.get(reverse("backoffice_legal_documents"))
        self.assertContains(page, 'name="document_revision" value="0"')
        self.assertEqual(self.post(action="publish", revision_id=row.pk, document_revision=0, reason="Ishga tushirish",
                                   effective_at=timezone.localtime().strftime("%Y-%m-%dT%H:%M"), confirm="on").status_code, 302)
        self.assertEqual(legal.effective_revision(TERMS).pk, row.pk)
        stale = self.post(action="archive", revision_id=row.pk, document_revision=0, reason="Eski oyna", confirm="on")
        self.assertEqual(stale.status_code, 400)
        self.assertContains(stale, "boshqa oynada o", status_code=400)
        self.assertEqual(legal.effective_revision(TERMS).pk, row.pk)

    def test_approved_versions_cannot_be_edited(self):
        row = self.approved()
        response = self.client.get(reverse("backoffice_legal_edit", args=[row.pk]))
        self.assertRedirects(response, reverse("backoffice_legal_documents"))

    def test_preview_is_private_uncached_and_writes_nothing(self):
        row = self.draft(content="<p>Hali chiqmagan matn</p>")
        before = (LegalRevision.objects.count(), SystemAuditEvent.objects.count())
        response = self.client.get(reverse("backoffice_legal_preview", args=[row.pk]))
        self.assertContains(response, "Hali chiqmagan matn")
        self.assertContains(response, 'name="robots" content="noindex, nofollow"')
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotContains(response, reverse("register"))  # CTA'siz
        self.assertEqual((LegalRevision.objects.count(), SystemAuditEvent.objects.count()), before)
        self.assertEqual(self.client.get(reverse("privacy_policy")).status_code, 503)

    def test_backfill_button_appears_only_while_there_is_something_to_copy(self):
        LegalPage.objects.create(page_type=PRIVACY, title="Eski", content="<p>Eski matn</p>")
        self.assertContains(self.client.get(reverse("backoffice_legal_documents")), "data-legal-backfill")
        self.assertEqual(self.post(action="backfill", kind=PRIVACY, confirm="on").status_code, 302)
        self.assertNotContains(self.client.get(reverse("backoffice_legal_documents")), "data-legal-backfill")
        self.assertEqual(LegalRevision.objects.get().status, "draft")


@skipUnless(connection.vendor == "postgresql", "qator qulfi faqat PostgreSQL'da haqiqiy")
class ConcurrentPublishTests(TransactionTestCase):
    def test_two_windows_publishing_at_once_yield_one_winner(self):
        owner = User.objects.create_superuser("egasi", email="egasi@example.test", password="Egasi-2026!")
        rows = [legal.approve(legal.create_draft(PRIVACY, title="M", version_label=label, content=f"<p>{label}</p>",
                                                  actor=owner), actor=owner, reason="ok") for label in ("1.0", "2.0")]
        barrier, results = threading.Barrier(2), []

        def attempt(row):
            try:
                barrier.wait()
                legal.publish(row, actor=owner, reason="parallel", effective_at=timezone.now(),
                              expected_document_revision=0)
                results.append("ok")
            except legal.LegalConflict:
                results.append("conflict")
            finally:
                connections.close_all()

        threads = [threading.Thread(target=attempt, args=(row,)) for row in rows]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(results), ["conflict", "ok"])
        self.assertEqual(LegalRevision.objects.filter(status="published").count(), 1)
        self.assertEqual(LegalDocument.objects.get().revision, 1)
