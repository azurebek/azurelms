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

PUB1.5d — eski havola va ilova:

* to'liq hujjat va ballar ilovasi faqat sertifikat egasi va xodimlarga
  (`can_view_document`); ilova mehmonga umuman ochilmaydi;
* eski `AZ-…` havolani boshqa odam ochsa — o'tish davrida (`certificate_legacy_public_view`,
  owner yopadi) faqat yangi tekshiruvdagi minimal ko'rinish, keyin "topilmadi";
* bunday ochishlar kesh hisoblagichida kunlik sanaladi (ID, IP yoki kod yozilmaydi) —
  owner o'tish davrini qachon yopishni shundan biladi;
* mavjud sertifikatlarga kod `backfill_tokens` bilan (qayta yugurish xavfsiz).
"""

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.urls import reverse
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


def _projection(status, name_mode, issued_at, revoked_at, first_name, last_name, course_title):
    revoked = status == Certificate.PUBLIC_REVOKED
    return PublicCertificate(
        status=status,
        status_label=STATUS_LABELS[status],
        holder=holder_display(first_name, last_name, name_mode),
        course_title=course_title,
        issued_on=timezone.localtime(issued_at).date(),
        revoked_on=timezone.localtime(revoked_at).date() if revoked and revoked_at else None,
    )


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
    return _projection(row["public_status"], row["public_name_mode"], row["issued_at"], row["revoked_at"],
                       row["student__first_name"], row["student__last_name"], row["course__title"])


def project(certificate):
    """Yuklangan sertifikatdan ayni minimal ko'rinish (eski havola uchun); yashirin — ``None``."""
    if certificate.public_status == Certificate.PUBLIC_HIDDEN:
        return None
    return _projection(certificate.public_status, certificate.public_name_mode, certificate.issued_at,
                       certificate.revoked_at, certificate.student.first_name, certificate.student.last_name,
                       certificate.course.title)


def can_view_document(user, certificate):
    """To'liq hujjat va ballar ilovasi: faqat sertifikat egasi va faol xodim (PUB1.5d)."""
    return bool(
        user is not None and user.is_authenticated and user.is_active
        and (certificate.student_id == user.id or user.is_staff or user.is_superuser)
    )


def verify_url(certificate):
    """Egasiga ko'rsatiladigan yangi tekshiruv havolasi — faqat flag yoqilgan va kod bo'lsa."""
    from core.flags import flag_enabled
    from frontend.public_meta import absolute_url

    if not certificate.public_token or not flag_enabled("certificate_public_verifier"):
        return ""
    return absolute_url(reverse("certificate_verify", args=[certificate.public_token]))


# --------------------------------------------------------------- eski havola telemetriyasi

LEGACY_VIEW_KEY = "certificate-legacy-public-view:{day}"
LEGACY_VIEW_TTL = 40 * 24 * 3600


def record_legacy_public_view(today=None):
    """Eski havolani boshqa odam ochdi — kunlik son. ID, IP, kod yozilmaydi; bazaga ham (GET yozmaydi)."""
    key = LEGACY_VIEW_KEY.format(day=(today or timezone.localdate()).isoformat())
    cache.add(key, 0, LEGACY_VIEW_TTL)
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, LEGACY_VIEW_TTL)


def legacy_public_views(days=30, today=None):
    today = today or timezone.localdate()
    keys = [LEGACY_VIEW_KEY.format(day=(today - timedelta(days=offset)).isoformat()) for offset in range(days)]
    return sum(int(value or 0) for value in cache.get_many(keys).values())


# --------------------------------------------------------------- mavjud sertifikatlarga kod


@dataclass(frozen=True)
class BackfillReport:
    missing_before: int
    processed: int
    missing_after: int
    digest: str


def backfill_tokens(*, apply=False, batch_size=200, limit=None):
    """Kodsiz sertifikatlarga kod (pk tartibida, qayta yugurish xavfsiz — faqat kodsizlar).

    `digest` — ishlangan pk'lar ro'yxatining SHA-256 qisqasi: ikki yugurishni solishtirish uchun.
    Kodlarning o'zi chiqarilmaydi.
    """
    missing = Certificate.objects.filter(public_token__isnull=True)
    missing_before = missing.count()
    pks, last_pk = [], 0
    while limit is None or len(pks) < limit:
        batch = list(missing.filter(pk__gt=last_pk).order_by("pk").values_list("pk", flat=True)[:batch_size])
        if not batch:
            break
        for pk in batch:
            if limit is not None and len(pks) >= limit:
                break
            if apply:
                ensure_public_token(Certificate(pk=pk, public_token=None))
            pks.append(pk)
        last_pk = batch[-1]
    digest = hashlib.sha256(",".join(map(str, pks)).encode()).hexdigest()[:16]
    missing_after = Certificate.objects.filter(public_token__isnull=True).count() if apply else missing_before
    return BackfillReport(missing_before, len(pks), missing_after, digest)


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
