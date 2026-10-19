"""Huquqiy hujjat versiyalari — yagona hayot sikli (PUBLIC-01 · PUB1.5a).

Maxfiylik siyosati va foydalanish shartlari ilgari bitta o'zgaruvchan
`LegalPage` qatori edi: kim, qachon, qaysi matnni tasdiqlagani, qachondan amal
qilishi va oldingi matn nima bo'lgani saqlanmasdi; birinchi GET esa umumiy
namuna matnni siyosat sifatida e'lon qilardi (PUB1.0e'da to'xtatilgan).

Endi har matn — `LegalRevision`:

* **qoralama** tahrirlanadi; **tasdiqlangan** matn hech qachon o'zgarmaydi;
* **nashr** kuchga kirish vaqti bilan: hozir yoki kelajakda (rejalashtirilgan);
* bir hujjatga bir vaqtda **bitta amaldagi** versiya — `published` va
  `effective_at <= hozir` bo'lganlarning eng kechi. U hisoblanadi, saqlanmaydi:
  public GET hech narsa yozmaydi, rejalashtirilgan versiya cron'siz kuchga kiradi;
* amaldagi versiya **arxivlansa** oldingi nashr qaytadi (rollback); qator
  o'chirilmaydi, har o'tish `SystemAuditEvent`ga yoziladi;
* nashr va arxivlash hujjat revizioniga qarshi CAS: ikki oyna bir-birini
  bosib ketmaydi.

Umumiy namuna matn (PUB1.0e'gacha avtomatik yaratilgan) qoralama bo'lib qolishi
mumkin, lekin tasdiqlanmaydi (PUB-D5). Matnni owner yoki yurist beradi va
tasdiqlaydi — bu modul faqat jarayonni qo'riqlaydi. FAQ huquqiy hujjat emas,
`LegalPage`da qoladi.
"""

import hashlib
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.rich_content_policy import public_plain_text, sanitize_public_editorial
from frontend.models import LegalDocument, LegalPage, LegalRevision

KINDS = (LegalDocument.KIND_PRIVACY, LegalDocument.KIND_TERMS)
LEGACY_LABEL = "eski-matn"
# Formadagi "hozir" bir necha daqiqa kechikib kelishi mumkin; undan eskisi rad.
PAST_TOLERANCE = timedelta(minutes=5)
AUDIT_ACTIONS = (
    "legal.draft_create", "legal.draft_update", "legal.approve", "legal.publish",
    "legal.archive", "legal.rollback",
)
CONFLICT_MESSAGE = "Hujjat boshqa oynada o'zgartirilgan. Sahifani yangilab, qayta urinib ko'ring."


class LegalConflict(Exception):
    """Holat yoki revizion kutilganidan boshqacha — hech narsa yozilmadi."""


def digest(content):
    return hashlib.sha256((content or "").encode("utf-8")).hexdigest()


def _generated_digests():
    from core.public_readiness import LEGACY_GENERATED_LEGAL_CONTENT

    return {digest(sanitize_public_editorial(LEGACY_GENERATED_LEGAL_CONTENT[kind]).strip()) for kind in KINDS}


def is_generated_sample(revision):
    """PUB1.0e'gacha avtomatik yaratilgan umumiy namuna matnmi."""
    return revision.content_digest in _generated_digests()


# --------------------------------------------------------------- o'qish (yozmaydi)


def effective_revision(kind, now=None):
    """Hozir amaldagi versiya yoki ``None``. Hech narsa yozmaydi."""
    now = now or timezone.now()
    return (
        LegalRevision.objects.select_related("document", "approved_by")
        .filter(document__kind=kind, status=LegalRevision.STATUS_PUBLISHED, effective_at__lte=now)
        .order_by("-effective_at", "-published_at", "-pk")
        .first()
    )


def scheduled_revisions(kind, now=None):
    """Nashr qilingan, lekin hali kuchga kirmagan versiyalar (eng yaqini birinchi)."""
    now = now or timezone.now()
    return list(
        LegalRevision.objects.filter(
            document__kind=kind, status=LegalRevision.STATUS_PUBLISHED, effective_at__gt=now,
        ).order_by("effective_at", "pk")
    )


@dataclass(frozen=True)
class DocumentState:
    kind: str
    label: str
    document: object
    effective: object
    scheduled: tuple
    revisions: tuple
    legacy_page: object

    @property
    def expected_revision(self):
        return self.document.revision if self.document else 0


def document_states(now=None):
    """Owner sahifasi uchun: har hujjat holati. Hech narsa yaratmaydi."""
    now = now or timezone.now()
    documents = {doc.kind: doc for doc in LegalDocument.objects.all()}
    legacy = {page.page_type: page for page in LegalPage.objects.filter(page_type__in=KINDS)}
    labels = dict(LegalDocument.KIND_CHOICES)
    states = []
    for kind in KINDS:
        document = documents.get(kind)
        revisions = tuple(
            document.revisions.select_related("created_by", "approved_by").order_by("-created_at", "-pk")
        ) if document else ()
        states.append(DocumentState(
            kind=kind, label=labels[kind], document=document,
            effective=effective_revision(kind, now), scheduled=tuple(scheduled_revisions(kind, now)),
            revisions=revisions, legacy_page=legacy.get(kind),
        ))
    return states


# --------------------------------------------------------------- hayot sikli


def _clean(content):
    clean = sanitize_public_editorial(content).strip()
    if not public_plain_text(clean).strip():
        raise ValueError("Matn bo'sh — hujjat matnini kiriting.")
    return clean


def _required(value, message, limit):
    value = (value or "").strip()
    if not value:
        raise ValueError(message)
    return value[:limit]


def _audit(action, *, actor, request, revision, reason="", before=None, after=None):
    from core.audit import record_audit_event

    record_audit_event(
        action=action, request=request, actor=actor, target=revision,
        target_label=f"{revision.document.kind} · {revision.version_label}",
        reason=reason, before=before, after=after,
    )


def _label_taken(document, label, exclude_pk=None):
    queryset = LegalRevision.objects.filter(document=document, version_label=label)
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.exists()


def create_draft(kind, *, title, version_label, content, actor, reason="", request=None,
                 source=LegalRevision.SOURCE_OWNER):
    if kind not in KINDS:
        raise ValueError("Noma'lum hujjat turi.")
    title = _required(title, "Sarlavha majburiy.", 150)
    label = _required(version_label, "Versiya nomi majburiy (masalan, 1.0).", 40)
    clean = _clean(content)
    with transaction.atomic():
        document, _ = LegalDocument.objects.get_or_create(kind=kind)
        if _label_taken(document, label):
            raise ValueError(f"«{label}» versiya nomi bu hujjatda band.")
        revision = LegalRevision.objects.create(
            document=document, version_label=label, title=title, content=clean, content_digest=digest(clean),
            source=source, reason=(reason or "").strip()[:240], created_by=actor,
        )
        _audit("legal.draft_create", actor=actor, request=request, revision=revision, reason=reason,
               after={"status": revision.status, "digest": revision.content_digest, "source": source})
    return revision


def _locked(revision):
    return LegalRevision.objects.select_for_update().select_related("document").get(pk=revision.pk)


def update_draft(revision, *, title, version_label, content, actor, reason="", request=None):
    title = _required(title, "Sarlavha majburiy.", 150)
    label = _required(version_label, "Versiya nomi majburiy (masalan, 1.0).", 40)
    clean = _clean(content)
    with transaction.atomic():
        row = _locked(revision)
        if row.status != LegalRevision.STATUS_DRAFT:
            raise LegalConflict("Faqat qoralama tahrirlanadi — tasdiqlangan matn o'zgarmaydi. Yangi qoralama yarating.")
        if _label_taken(row.document, label, exclude_pk=row.pk):
            raise ValueError(f"«{label}» versiya nomi bu hujjatda band.")
        before = {"digest": row.content_digest, "version": row.version_label}
        row.title, row.version_label, row.content, row.content_digest = title, label, clean, digest(clean)
        row.save(update_fields=["title", "version_label", "content", "content_digest"])
        _audit("legal.draft_update", actor=actor, request=request, revision=row, reason=reason,
               before=before, after={"digest": row.content_digest, "version": row.version_label})
    return row


def approve(revision, *, actor, reason, request=None, now=None):
    reason = _required(reason, "Tasdiqlash sababi majburiy.", 240)
    now = now or timezone.now()
    with transaction.atomic():
        row = _locked(revision)
        if row.status != LegalRevision.STATUS_DRAFT:
            raise LegalConflict("Faqat qoralama tasdiqlanadi.")
        if is_generated_sample(row):
            raise ValueError("Umumiy namuna matn huquqiy hujjat sifatida tasdiqlanmaydi — haqiqiy matnni kiriting.")
        row.status = LegalRevision.STATUS_APPROVED
        row.approved_by, row.approved_at = actor, now
        row.save(update_fields=["status", "approved_by", "approved_at"])
        _audit("legal.approve", actor=actor, request=request, revision=row, reason=reason,
               before={"status": LegalRevision.STATUS_DRAFT},
               after={"status": row.status, "digest": row.content_digest})
    return row


def _lock_document(revision, expected_document_revision):
    document = LegalDocument.objects.select_for_update().get(pk=revision.document_id)
    if document.revision != expected_document_revision:
        raise LegalConflict(CONFLICT_MESSAGE)
    return document


def _effective_label(kind, now):
    current = effective_revision(kind, now)
    return current.version_label if current else None


def publish(revision, *, actor, reason, effective_at, expected_document_revision, request=None, now=None):
    """Tasdiqlangan versiyani nashr qiladi: hozir yoki `effective_at` kelganda kuchga kiradi."""
    reason = _required(reason, "Nashr sababi majburiy.", 240)
    now = now or timezone.now()
    if effective_at < now - PAST_TOLERANCE:
        raise ValueError("Kuchga kirish vaqti o'tmishda bo'lishi mumkin emas.")
    effective_at = max(effective_at, now)
    with transaction.atomic():
        document = _lock_document(revision, expected_document_revision)
        row = _locked(revision)
        if row.status != LegalRevision.STATUS_APPROVED:
            raise LegalConflict("Faqat tasdiqlangan versiya nashr qilinadi.")
        before = {"effective": _effective_label(document.kind, now)}
        row.status = LegalRevision.STATUS_PUBLISHED
        row.effective_at, row.published_at = effective_at, now
        row.save(update_fields=["status", "effective_at", "published_at"])
        document.revision += 1
        document.save(update_fields=["revision"])
        _audit("legal.publish", actor=actor, request=request, revision=row, reason=reason, before=before,
               after={"version": row.version_label, "effective_at": effective_at.isoformat(),
                      "digest": row.content_digest, "document_revision": document.revision})
    return row


def archive(revision, *, actor, reason, expected_document_revision, request=None, now=None):
    """Versiyani bekor qiladi. Amaldagisi bo'lsa — oldingi nashr qaytadi (rollback)."""
    reason = _required(reason, "Sabab majburiy.", 240)
    now = now or timezone.now()
    with transaction.atomic():
        document = _lock_document(revision, expected_document_revision)
        row = _locked(revision)
        if row.status == LegalRevision.STATUS_ARCHIVED:
            raise LegalConflict("Bu versiya allaqachon arxivlangan.")
        before_label = _effective_label(document.kind, now)
        was_effective = before_label is not None and effective_revision(document.kind, now).pk == row.pk
        before_status = row.status
        row.status, row.archived_at = LegalRevision.STATUS_ARCHIVED, now
        row.save(update_fields=["status", "archived_at"])
        document.revision += 1
        document.save(update_fields=["revision"])
        _audit("legal.rollback" if was_effective else "legal.archive", actor=actor, request=request,
               revision=row, reason=reason,
               before={"status": before_status, "effective": before_label},
               after={"status": row.status, "effective": _effective_label(document.kind, now),
                      "document_revision": document.revision})
    return row


# --------------------------------------------------------------- eski qatorlardan ko'chirish


@dataclass(frozen=True)
class BackfillRow:
    kind: str
    action: str  # created | would_create | exists | no_legacy | empty
    generated: bool = False


def backfill_from_legacy(*, apply=False, actor=None, kinds=KINDS):
    """Eski `LegalPage` matnidan **tasdiqlanmagan qoralama** (PUB1.5a).

    Qayta yugurish xavfsiz: hujjatda eski matndan qoralama bo'lsa hech narsa
    qilmaydi. `LegalPage` qatori tegilmaydi (expand-only) — eski matn yo'qolmaydi.
    """
    rows = []
    for kind in kinds:
        page = LegalPage.objects.filter(page_type=kind).first()
        if page is None:
            rows.append(BackfillRow(kind, "no_legacy"))
            continue
        clean = sanitize_public_editorial(page.content).strip()
        generated = digest(clean) in _generated_digests()
        if LegalRevision.objects.filter(document__kind=kind, source=LegalRevision.SOURCE_LEGACY).exists():
            rows.append(BackfillRow(kind, "exists", generated))
            continue
        if not public_plain_text(clean).strip():
            rows.append(BackfillRow(kind, "empty", generated))
            continue
        if apply:
            document, _ = LegalDocument.objects.get_or_create(kind=kind)
            label, suffix = LEGACY_LABEL, 2
            while _label_taken(document, label):
                label, suffix = f"{LEGACY_LABEL}-{suffix}", suffix + 1
            create_draft(
                kind, title=page.title or dict(LegalDocument.KIND_CHOICES)[kind], version_label=label,
                content=page.content, actor=actor, source=LegalRevision.SOURCE_LEGACY,
                reason="Eski sahifa matnidan qoralama — tasdiqlanmagan (PUB1.5a).",
            )
        rows.append(BackfillRow(kind, "created" if apply else "would_create", generated))
    return rows
