"""Sertifikatni ochiq tekshirish — tasodifiy kod va eng kam ma'lumot (PUBLIC-01 · PUB1.5c).

Eski havola `/courses/certificate/AZ-<kurs>-<o'quvchi>-<6 belgi>/` o'quvchi va
kurs ID'sini o'z ichiga oladi; qolgan 24 bit taxmin qilinadi, sahifa esa ism,
ball va ilovada imtihon natijalarini ko'rsatadi. Yangi tekshiruv:

* faqat `public_token` (192 bit, `secrets`) bilan — ketma-ket ID hech narsa ochmaydi;
* javob eng kam: holat, ism ko'rinishi (default qisqartirilgan), kurs nomi va sana.
  Ball, imtihonlar, email yoki boshqa bog'liq yozuv so'ralmaydi ham;
* `hidden`, yo'q va noto'g'ri kod bir xil "topilmadi"; `revoked` rost aytiladi,
  sababi esa hech qachon ochiq emas;
* noto'g'ri kodlar IP bo'yicha cheklanadi (`users.auth_abuse`), kodning o'zi
  logga yoki auditga yozilmaydi.

Yangi havola owner qarorigacha o'chiq (`certificate_public_verifier`, PUB-D4).
Eski havolalarni ko'chirish va ilovani yopish — PUB1.5d.
"""

import re
import secrets
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

from courses.models import Certificate

TOKEN_BYTES = 24  # 192 bit → 32 belgi
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32}$")
MAX_TOKEN_ATTEMPTS = 5
STATUS_LABELS = {
    Certificate.PUBLIC_VERIFIABLE: "Haqiqiy sertifikat",
    Certificate.PUBLIC_REVOKED: "Bekor qilingan sertifikat",
}


class VerifierConflict(Exception):
    """Holat boshqa oynada o'zgargan — hech narsa yozilmadi."""


def new_token():
    return secrets.token_urlsafe(TOKEN_BYTES)


def ensure_public_token(certificate):
    """Kodsiz sertifikatga bir marta kod beradi (to'qnashuvda qayta urinadi). Kodni qaytaradi."""
    if certificate.public_token:
        return certificate.public_token
    for _ in range(MAX_TOKEN_ATTEMPTS):
        token = new_token()
        try:
            with transaction.atomic():
                updated = Certificate.objects.filter(pk=certificate.pk, public_token__isnull=True).update(public_token=token)
        except IntegrityError:
            continue  # boshqa sertifikatda ayni kod — yangisi bilan qayta
        if not updated:
            # Parallel jarayon allaqachon kod bergan: o'shani olamiz.
            token = Certificate.objects.filter(pk=certificate.pk).values_list("public_token", flat=True).get()
        certificate.public_token = token
        return token
    raise RuntimeError("Sertifikat uchun noyob kod yaratib bo'lmadi.")


def holder_display(first_name, last_name, mode):
    """Ism ko'rinishi: to'liq, qisqartirilgan ("Ali V.") yoki umuman yo'q. Username hech qachon."""
    first, last = (first_name or "").strip(), (last_name or "").strip()
    if mode == Certificate.NAME_OMITTED or not (first or last):
        return ""
    if mode == Certificate.NAME_FULL:
        return f"{first} {last}".strip()
    if first and last:
        return f"{first} {last[0]}."
    return f"{(first or last)[0]}."


@dataclass(frozen=True)
class PublicCertificate:
    status: str
    status_label: str
    holder: str
    course_title: str
    issued_on: object
    revoked_on: object = None

    @property
    def is_revoked(self):
        return self.status == Certificate.PUBLIC_REVOKED


def lookup(token):
    """Kod bo'yicha ochiq ko'rinish yoki ``None`` (yo'q, yashirin, noto'g'ri — bir xil).

    Faqat bitta so'rov va faqat kerakli ustunlar: o'quvchining ismi, kurs nomi,
    sana va holat. Ball, imtihon, email, yozilish yoki boshqa yozuvga tegilmaydi.
    """
    if not token or not TOKEN_RE.match(token):
        return None
    row = (
        Certificate.objects.filter(public_token=token)
        .exclude(public_status=Certificate.PUBLIC_HIDDEN)
        .values("public_status", "public_name_mode", "issued_at", "revoked_at",
                "student__first_name", "student__last_name", "course__title")
        .first()
    )
    if row is None:
        return None
    revoked = row["public_status"] == Certificate.PUBLIC_REVOKED
    return PublicCertificate(
        status=row["public_status"],
        status_label=STATUS_LABELS[row["public_status"]],
        holder=holder_display(row["student__first_name"], row["student__last_name"], row["public_name_mode"]),
        course_title=row["course__title"],
        issued_on=timezone.localtime(row["issued_at"]).date(),
        revoked_on=timezone.localtime(row["revoked_at"]).date() if revoked and row["revoked_at"] else None,
    )


def set_public_status(certificate, *, status, actor, reason, expected_revision, name_mode=None, request=None, now=None):
    """Ochiq holat/ism ko'rinishini o'zgartiradi (CAS + audit). Bekor qilish sababi ochiq emas."""
    from core.audit import record_audit_event

    if status not in dict(Certificate.PUBLIC_STATUS_CHOICES):
        raise ValueError("Noma'lum holat.")
    if name_mode is not None and name_mode not in dict(Certificate.NAME_MODE_CHOICES):
        raise ValueError("Noma'lum ism ko'rinishi.")
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Sabab majburiy.")
    now = now or timezone.now()
    with transaction.atomic():
        row = Certificate.objects.select_for_update().get(pk=certificate.pk)
        if row.verification_revision != expected_revision:
            raise VerifierConflict("Sertifikat boshqa oynada o'zgartirilgan. Sahifani yangilab, qayta urinib ko'ring.")
        before = {"status": row.public_status, "name_mode": row.public_name_mode}
        row.public_status = status
        if name_mode is not None:
            row.public_name_mode = name_mode
        if status == Certificate.PUBLIC_REVOKED:
            row.revoked_at = row.revoked_at or now
            row.revocation_reason = reason[:240]
        else:
            row.revoked_at, row.revocation_reason = None, ""
        row.verification_revision += 1
        row.save(update_fields=["public_status", "public_name_mode", "revoked_at", "revocation_reason",
                                "verification_revision"])
        # Audit kodni emas, sertifikat raqamini (ichki) yozadi.
        record_audit_event(
            action="certificate.public_status", request=request, actor=actor, target=row,
            target_label=f"Sertifikat #{row.pk}", reason=reason, before=before,
            after={"status": row.public_status, "name_mode": row.public_name_mode,
                   "revision": row.verification_revision},
        )
    return row
