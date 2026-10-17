"""Public da'volar (claim) dalili: kim, qachon, qaysi matn uchun tasdiqlagan (PUB1.2a).

Bosh sahifa va "Biz haqimizda" statistikasi (talaba soni, foiz, reyting) va
o'quvchilar fikri faqat dalil bilan chiqadi:

* statistika — `PublicClaimEvidence` yozuvi bor, `content_digest` hozir
  ko'rsatilayotgan matnga teng (tahrir dalilni eskirtiradi), muddati o'tmagan
  va qaytarib olinmagan bo'lsa;
* fikr — egasining ochiq sayt uchun roziligi tasdiqlangan va qaytarilmagan
  bo'lsa; barqaror tartibda (random emas).

Seed/default qatorlar avtomatik tasdiqlanmaydi. Tasdiqlash va qaytarish
owner amali: sabab bilan, revizion (CAS) tekshiruvi va audit yozuvi bilan.
"""

import hashlib
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from core.rich_content_policy import safe_url
from frontend.models import AboutStatistic, PublicClaimEvidence, Statistic, Testimonial

VERIFIED = "verified"
MISSING = "missing"
STALE = "stale"
EXPIRED = "expired"
REVOKED = "revoked"
STATUS_LABELS = {
    VERIFIED: "Tasdiqlangan",
    MISSING: "Dalil yo'q",
    STALE: "Matn o'zgargan — qayta tasdiqlang",
    EXPIRED: "Muddati o'tgan",
    REVOKED: "Qaytarib olingan",
}


class ClaimConflict(Exception):
    """Boshqa oynada o'zgartirilgan: eski revizion bilan saqlab bo'lmaydi."""


@dataclass(frozen=True)
class GovernedClaim:
    key: str
    surface: str
    text: str
    status: str
    evidence: PublicClaimEvidence | None
    obj: object

    @property
    def status_label(self):
        return STATUS_LABELS[self.status]

    @property
    def is_public(self):
        return self.status == VERIFIED


def normalize(text):
    return " ".join(str(text or "").split())


def digest(text):
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def statistic_key(stat):
    return f"landing.statistic.{stat.pk}"


def about_statistic_key(stat):
    return f"about.statistic.{stat.pk}"


def statistic_text(stat):
    """Ko'rsatiladigan qiymat va nomi — dalil aynan shunga bog'lanadi."""
    return f"{stat.display_value} | {stat.label}"


def about_statistic_text(stat):
    return f"{stat.value} | {stat.label}"


def status_of(evidence, text, now=None):
    if evidence is None:
        return MISSING
    if evidence.revoked_at is not None:
        return REVOKED
    if evidence.content_digest != digest(text):
        return STALE
    if (now or timezone.now()) >= evidence.expires_at:
        return EXPIRED
    return VERIFIED


def _govern(items, key_for, text_for, surface, now=None):
    items = list(items)
    evidence = {row.claim_key: row for row in PublicClaimEvidence.objects.filter(
        claim_key__in=[key_for(item) for item in items])}
    claims = []
    for item in items:
        key, text = key_for(item), text_for(item)
        row = evidence.get(key)
        claims.append(GovernedClaim(key, surface, text, status_of(row, text, now), row, item))
    return claims


def landing_statistic_claims(now=None):
    stats = Statistic.objects.filter(is_active=True).order_by("order", "id")
    return _govern(stats, statistic_key, statistic_text, "Bosh sahifa", now)


def about_statistic_claims(now=None):
    stats = AboutStatistic.objects.order_by("order", "id")
    return _govern(stats, about_statistic_key, about_statistic_text, "Biz haqimizda", now)


def all_claims(now=None):
    return landing_statistic_claims(now) + about_statistic_claims(now)


def verified_landing_statistics(limit=None):
    stats = [claim.obj for claim in landing_statistic_claims() if claim.is_public]
    return stats[:limit] if limit else stats


def verified_about_statistics():
    return [claim.obj for claim in about_statistic_claims() if claim.is_public]


def public_testimonials(limit=3):
    """Rozilik bilan va barqaror tartibda (random emas)."""
    queryset = Testimonial.objects.filter(
        is_active=True, consent_scope=Testimonial.CONSENT_PUBLIC_SITE,
        consent_confirmed_at__isnull=False, consent_revoked_at__isnull=True,
    ).order_by("order", "id")
    # Rozilikdan keyin ism, rol yoki matn o'zgargan bo'lsa fikr chiqmaydi.
    consented = [item for item in queryset if item.has_public_consent]
    return consented[:limit] if limit else consented


def _claim_for(key, now=None):
    for claim in all_claims(now):
        if claim.key == key:
            return claim
    raise LookupError(f"{key}: bunday boshqariladigan da'vo yo'q.")


def approve(key, *, actor, reason, expires_at, expected_revision, source_url="", evidence_note="",
            request=None, now=None):
    """Ko'rsatilayotgan aynan shu matnni tasdiqlaydi. Eski revizion — `ClaimConflict`."""
    from core.audit import record_audit_event

    now = now or timezone.now()
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Tasdiqlash sababi majburiy.")
    if expires_at <= now:
        raise ValueError("Amal qilish muddati kelajakda bo'lishi kerak.")
    clean_url = safe_url(source_url, schemes=("https",), allow_local=False) if source_url else ""
    if source_url and not clean_url:
        raise ValueError("Manba havolasi faqat https bo'lishi mumkin.")
    claim = _claim_for(key, now)
    with transaction.atomic():
        row = PublicClaimEvidence.objects.select_for_update().filter(claim_key=key).first()
        current = row.revision if row else 0
        if current != expected_revision:
            raise ClaimConflict("Bu da'vo boshqa oynada o'zgartirilgan. Sahifani yangilab, qayta ko'ring.")
        before = {"status": claim.status, "revision": current}
        if row is None:
            row = PublicClaimEvidence(claim_key=key, revision=0)
        row.content_digest = digest(claim.text)
        row.source_url = clean_url
        row.evidence_note = (evidence_note or "").strip()[:1000]
        row.verified_at = now
        row.expires_at = expires_at
        row.approved_by = actor
        row.approval_reason = reason[:240]
        row.revoked_at = None
        row.revision = current + 1
        row.save()
        record_audit_event(
            action="public_claim.approve", request=request, actor=actor, target=row, target_label=key,
            reason=reason, before=before,
            after={"status": VERIFIED, "revision": row.revision, "expires_at": expires_at.isoformat(), "text": claim.text},
        )
    return row


def revoke(key, *, actor, reason, expected_revision, request=None, now=None):
    from core.audit import record_audit_event

    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Qaytarish sababi majburiy.")
    with transaction.atomic():
        row = PublicClaimEvidence.objects.select_for_update().filter(claim_key=key).first()
        if row is None or row.revision != expected_revision:
            raise ClaimConflict("Bu da'vo boshqa oynada o'zgartirilgan. Sahifani yangilab, qayta ko'ring.")
        if row.revoked_at is not None:
            return row
        row.revoked_at = now or timezone.now()
        row.revision += 1
        row.save(update_fields=["revoked_at", "revision", "updated_at"])
        record_audit_event(
            action="public_claim.revoke", request=request, actor=actor, target=row, target_label=key,
            reason=reason, after={"status": REVOKED, "revision": row.revision},
        )
    return row


def set_testimonial_consent(testimonial, *, actor, confirmed, reason, display_name="", source_reference="",
                            request=None, now=None):
    """Rozilikni tasdiqlaydi yoki qaytaradi (audit bilan)."""
    from core.audit import record_audit_event

    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Sabab majburiy.")
    now = now or timezone.now()
    with transaction.atomic():
        row = Testimonial.objects.select_for_update().get(pk=testimonial.pk)
        before = {"public": row.has_public_consent}
        if confirmed:
            row.consent_scope = Testimonial.CONSENT_PUBLIC_SITE
            row.consent_confirmed_at = now
            row.consent_revoked_at = None
            row.display_name = (display_name or "").strip()[:100]
            row.source_reference = (source_reference or "").strip()[:240]
            # Rozilik aynan hozirgi ism, rol va matnga bog'lanadi.
            row.consent_digest = row.content_digest()
        else:
            row.consent_revoked_at = now
        row.save()
        record_audit_event(
            action="public_testimonial.consent" if confirmed else "public_testimonial.revoke",
            request=request, actor=actor, target=row, target_label=f"Fikr #{row.pk}", reason=reason,
            before=before, after={"public": row.has_public_consent},
        )
    return row
