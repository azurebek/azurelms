"""Ochiq sayt reliz tayyorligi darvozasi (PUB1.8b) — bitta selector.

Control Center (`public_release` capability), `manage.py public_release_gate` va owner
sahifasi (`/backoffice/release/`) ayni `release_readiness()` natijasini ko'rsatadi:
ikkinchi hisob yo'q. Har band — yashil, sariq yoki qizil, sababi va tuzatish yo'li bilan.

Bandlar (PUBLIC-REFORM-PLAN §PUB1.8b): majburiy — maxfiylik, shartlar, sotuvdagi kurs, aloqa, to'lov
rekvizitlari, email, asosiy manzil, sitemap, ochiq media; ixtiyoriy — FAQ, yopiq kurslar, da'volar, fikrlar, sertifikat,
SIT dolzarbligi, sozlama qatorlari.

Pilot faqat **majburiy** bandlarning hammasi yashil bo'lganda: `ready_for_pilot`. Qizil bandni
saytdan yashirish (masalan, eskirgan da'vo avtomatik yashiriladi) reliz isboti emas — band
o'zi yashil bo'lishi kerak. Owner tasdig'i (`sign_off`) faqat shu holatda qabul qilinadi va
audit yozuvi (`public.release.signoff`) sifatida qoladi: holatlar xeshi bilan.

Muhitga qarab: lokal profilda console email va `localhost` origin ataylab ruxsat etilgan —
sariq; production'da qizil. Faqat o'qiydi.
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.utils import timezone

GREEN, AMBER, RED = "green", "amber", "red"
ORDER = {GREEN: 0, AMBER: 1, RED: 2}
SIGNOFF_ACTION = "public.release.signoff"
CLAIM_EXPIRY_WARNING_DAYS = 14


@dataclass(frozen=True)
class ReadinessItem:
    key: str
    label: str
    status: str
    required: bool
    summary: str
    fix: str = ""
    link: str = ""  # tuzatish sahifasining route nomi

    @property
    def href(self):
        if not self.link:
            return ""
        from django.urls import NoReverseMatch, reverse

        try:
            return reverse(self.link)
        except NoReverseMatch:
            return ""


@dataclass(frozen=True)
class ReleaseReadiness:
    items: tuple
    checked_at: object

    @property
    def ready_for_pilot(self):
        return all(item.status == GREEN for item in self.items if item.required)

    @property
    def status(self):
        """Umumiy holat: majburiy bandlar bo'yicha eng yomoni; ixtiyoriy sariq/qizil — ko'pi bilan sariq."""
        worst = GREEN
        for item in self.items:
            level = item.status if item.required else (AMBER if item.status != GREEN else GREEN)
            if ORDER[level] > ORDER[worst]:
                worst = level
        return worst

    @property
    def blockers(self):
        return tuple(item for item in self.items if item.required and item.status != GREEN)

    def digest(self):
        """Holatlar izi: tasdiq aynan qaysi holatga berilganini ko'rsatadi."""
        state = [(item.key, item.status) for item in self.items]
        return hashlib.sha256(json.dumps(state).encode()).hexdigest()[:16]

    def as_dict(self):
        return {"ready_for_pilot": self.ready_for_pilot, "status": self.status, "digest": self.digest(),
                "items": [asdict(item) for item in self.items]}


def _item(key, label, status, required, summary, fix="", link=""):
    return ReadinessItem(key, label, status, required, summary, fix, link)


def _legal_items():
    from core.public_readiness import STATE_GENERATED, STATE_MISSING, legal_readiness

    labels = {"privacy": "Maxfiylik siyosati", "terms": "Foydalanish shartlari", "faq": "FAQ"}
    items = []
    for page in legal_readiness():
        required = page.page_type in ("privacy", "terms")
        fix, link = "Sayt va dizayn → Huquqiy hujjatlar: versiyani tasdiqlang va nashr qiling.", "backoffice_legal_documents"
        if page.page_type == "faq":
            fix, link = ("Admin → Huquqiy sahifalar (ENABLE_LEGACY_ADMIN=True): FAQ'ni haqiqiy savol-javob bilan yozing.",
                         "admin:frontend_legalpage_changelist")
        if page.state == STATE_MISSING:
            items.append(_item(f"legal_{page.page_type}", labels[page.page_type], RED if required else AMBER, required,
                               "E'lon qilinmagan.", fix, link))
        elif page.state == STATE_GENERATED:
            items.append(_item(f"legal_{page.page_type}", labels[page.page_type], RED if required else AMBER, required,
                               "Umumiy namuna matn turibdi — haqiqiy matn emas.", fix, link))
        else:
            items.append(_item(f"legal_{page.page_type}", labels[page.page_type], GREEN, required, "Amaldagi matn bor."))
    return items


def _claims_item():
    from frontend.public_claims import EXPIRED, STALE, VERIFIED, all_claims

    claims = all_claims()
    stale = [claim for claim in claims if claim.status in (STALE, EXPIRED)]
    soon = timezone.now() + timedelta(days=CLAIM_EXPIRY_WARNING_DAYS)
    expiring = [claim for claim in claims if claim.status == VERIFIED and claim.evidence and claim.evidence.expires_at <= soon]
    if stale:
        return _item("claims", "Da'volar dalili", AMBER, False,
                     f"{len(stale)} ta tasdiqlangan da'vo yashirildi (matn o'zgargan yoki muddati o'tgan).",
                     "Sayt va dizayn → Da'volar dalili: qayta tasdiqlang yoki yashirin qolsin.", "backoffice_claim_evidence")
    if expiring:
        return _item("claims", "Da'volar dalili", AMBER, False,
                     f"{len(expiring)} ta da'vo dalili {CLAIM_EXPIRY_WARNING_DAYS} kun ichida tugaydi.",
                     "Sayt va dizayn → Da'volar dalili: muddatni yangilang.", "backoffice_claim_evidence")
    return _item("claims", "Da'volar dalili", GREEN, False,
                 "Dalilsiz da'vo saytda ko'rinmaydi; eskirgani yo'q.")


def _testimonials_item():
    from frontend.models import Testimonial
    from frontend.public_claims import public_testimonials

    public = len(public_testimonials(limit=None))
    hidden = Testimonial.objects.filter(is_active=True).count() - public
    if hidden:
        return _item("testimonials", "O'quvchilar fikri", AMBER, False,
                     f"{hidden} ta faol fikr rozilik qayd etilmagani (yoki matn o'zgargani) uchun yashirin; ochiq: {public}.",
                     "Sayt va dizayn → Da'volar dalili: rozilikni qayd eting yoki fikrni o'chiring.",
                     "backoffice_claim_evidence")
    return _item("testimonials", "O'quvchilar fikri", GREEN, False, f"Saytdagi fikrlar: {public} (hammasi rozilik bilan).")


def _offer_items():
    from courses.models import Course
    from courses.public_offer import build_offers

    courses = list(Course.objects.filter(is_active=True).order_by("pk"))
    offers = build_offers(courses) if courses else {}
    open_courses = [course for course in courses if offers[course.pk].available]
    closed = len(courses) - len(open_courses)
    live = (_item("live_offer", "Sotuvdagi kurs", GREEN, True, f"{len(open_courses)} ta kursga hozir yozilish mumkin.")
            if open_courses else
            _item("live_offer", "Sotuvdagi kurs", RED, True, "Hech qaysi kursga hozir yozilib bo'lmaydi.",
                  "Kursga ochiq guruh va sotuvdagi tarif qo'shing (Kurslar → guruhlar; To'lovlar → tariflar).",
                  "backoffice_courses"))
    others = (_item("closed_offers", "Yopiq kurslar", AMBER, False,
                    f"{closed} ta faol kurs hozir yozilish qabul qilmaydi (guruh yoki tarif yo'q/to'lgan).",
                    "Kurs sahifasi buni ochiq aytadi; kerak bo'lsa guruh yoki tarif qo'shing.", "backoffice_courses")
              if closed else _item("closed_offers", "Yopiq kurslar", GREEN, False, "Har faol kursda yozilish ochiq."))
    return [live, others]


def _contact_item():
    from core.public_readiness import contact_readiness

    channels = contact_readiness()
    if channels:
        return _item("support_contact", "Aloqa kanali", GREEN, True, f"Saytda ko'rinadi: {', '.join(channels)}.")
    return _item("support_contact", "Aloqa kanali", RED, True,
                 "Telefon ham, email ham sozlanmagan (namuna qiymatlar ko'rsatilmaydi).",
                 "Admin → Platforma sozlamalari (ENABLE_LEGACY_ADMIN=True): telefon yoki email kiriting.",
                 "admin:frontend_sitesettings_changelist")


def _payment_item():
    from frontend.models import SiteSettings

    site = SiteSettings.current()
    card = (site.payment_card_number or "").strip()
    fix = "Admin → Platforma sozlamalari (ENABLE_LEGACY_ADMIN=True): haqiqiy karta raqami va egasini kiriting."
    if not card:
        return _item("payment_details", "To'lov rekvizitlari", RED, True,
                     "Karta raqami kiritilmagan — checkout qayerga to'lashni ko'rsatmaydi.", fix,
                     "admin:frontend_sitesettings_changelist")
    if card == SiteSettings._meta.get_field("payment_card_number").default:
        return _item("payment_details", "To'lov rekvizitlari", RED, True,
                     "Namuna karta raqami turibdi — xaridor checkout va botda shu raqamni ko'radi.", fix,
                     "admin:frontend_sitesettings_changelist")
    return _item("payment_details", "To'lov rekvizitlari", GREEN, True, f"Karta …{card[-4:]} ko'rsatiladi.")


def _email_item():
    from core import email_delivery

    kind = email_delivery.backend_kind()
    failures = email_delivery.recent_reset_delivery_failures()
    if email_delivery.is_silent_backend():
        if settings.IS_LOCAL:
            return _item("email_delivery", "Email yuborish", AMBER, True,
                         f"Lokal profil: xatlar {kind} orqali terminalga chiqadi.",
                         "Production'da deploy/.env fayliga SMTP sozlamalarini (EMAIL_HOST va boshq.) yozing.")
        return _item("email_delivery", "Email yuborish", RED, True,
                     f"Xat yuborilmaydi ({kind}) — parol tiklash yopiq.",
                     "deploy/.env fayliga SMTP sozlamalarini yozing va xizmatni qayta ishga tushiring.")
    if failures:
        return _item("email_delivery", "Email yuborish", AMBER, True,
                     f"So'nggi 24 soatda {failures} ta parol tiklash xati yuborilmadi.",
                     "SMTP hisobini tekshiring (audit: auth.password_reset.delivery_failed).")
    return _item("email_delivery", "Email yuborish", GREEN, True, f"SMTP ({kind}) sozlangan.")


def _origin_item():
    origin = getattr(settings, "PUBLIC_CANONICAL_ORIGIN", "") or ""
    parts = urlsplit(origin)
    local_host = parts.hostname in (None, "localhost", "127.0.0.1", "::1") or (parts.hostname or "").endswith(".localhost")
    # `frontend/checks.py` (azurelms.E202) bilan bir qoida: faqat `sxema://host[:port]` — `absolute_url()`
    # yo'lni shu qiymatga to'g'ridan-to'g'ri ulaydi.
    if parts.path or parts.query or parts.fragment or parts.username or parts.password:
        return _item("canonical_origin", "Saytning asosiy manzili", RED, True,
                     f"Faqat sxema va domen bo'lishi kerak (yo'l, so'rov satri yoki login emas): {origin}.",
                     "deploy/.env: APP_DOMAIN (yoki PUBLIC_CANONICAL_ORIGIN) — masalan https://lms.example.com.")
    if parts.scheme == "https" and not local_host:
        return _item("canonical_origin", "Saytning asosiy manzili", GREEN, True, origin)
    if settings.IS_LOCAL:
        return _item("canonical_origin", "Saytning asosiy manzili", AMBER, True,
                     f"Lokal profil: {origin or 'sozlanmagan'}.", "Production'da APP_DOMAIN https domen bo'lsin.")
    return _item("canonical_origin", "Saytning asosiy manzili", RED, True,
                 f"Canonical/sitemap manzili noto'g'ri: {origin or 'sozlanmagan'}.",
                 "deploy/.env: APP_DOMAIN (yoki PUBLIC_CANONICAL_ORIGIN) https domen bo'lsin.")


def _sitemap_item():
    from frontend.public_sitemap import sitemap_entries

    try:
        entries = sitemap_entries()
    except ValueError as exc:
        return _item("sitemap", "Sitemap", RED, True, str(exc), "Route registri va sitemap manbalarini tekshiring.")
    return _item("sitemap", "Sitemap", GREEN if entries else RED, True, f"{len(entries)} ta ochiq manzil.",
                 "" if entries else "Ochiq sahifalar yo'q — kontent nashr qiling.")


def _media_item():
    from frontend.public_media import missing_public_media

    checked, missing = missing_public_media()
    if missing:
        sample = ", ".join(f"{item.source} #{item.pk}" for item in missing[:3])
        return _item("public_media", "Ochiq media fayllari", RED, True,
                     f"{len(missing)} / {checked} faylda fayl yo'q ({sample}…).",
                     "manage.py audit_public_media ro'yxati bo'yicha faylni qayta yuklang yoki olib tashlang.")
    return _item("public_media", "Ochiq media fayllari", GREEN, True,
                 f"{checked} ta fayl joyida." if checked else "Ochiq sahifalarda yuklangan fayl yo'q.")


def _certificate_item():
    from core.flags import flag_enabled
    from courses.models import Certificate

    missing = Certificate.objects.filter(public_token__isnull=True).count()
    if not flag_enabled("certificate_public_verifier"):
        return _item("certificates", "Sertifikat tekshiruvi", GREEN, False,
                     f"Ochiq tekshiruv o'chiq (owner qarori); kodsiz sertifikat: {missing}.")
    if missing:
        return _item("certificates", "Sertifikat tekshiruvi", AMBER, False,
                     f"Tekshiruv yoqilgan, lekin {missing} ta sertifikatda kod yo'q.",
                     "manage.py backfill_certificate_tokens --apply buyrug'ini ishga tushiring.")
    return _item("certificates", "Sertifikat tekshiruvi", GREEN, False, "Har sertifikatda tekshiruv kodi bor.")


def _sit_item():
    from sit.backoffice_views import STALE_AFTER_DAYS
    from sit.public import effective_universities

    cutoff = timezone.localdate() - timedelta(days=STALE_AFTER_DAYS)
    stale = effective_universities().filter(last_verified_on__lt=cutoff).count()
    if stale:
        return _item("sit_freshness", "SIT ma'lumoti dolzarbligi", AMBER, False,
                     f"{stale} ta universitet {STALE_AFTER_DAYS} kundan beri tekshirilmagan.",
                     "Turkiyada o'qish boshqaruvi: rasmiy manbadan qayta tekshirib sanani yangilang.",
                     "sit_backoffice:dashboard")
    return _item("sit_freshness", "SIT ma'lumoti dolzarbligi", GREEN, False, "Eskirgan universitet yo'q.")


def _settings_item():
    from django.apps import apps

    from core.public_readiness import missing_singletons

    missing = [str(apps.get_model(label)._meta.verbose_name) for label in missing_singletons()]
    if missing:
        return _item("settings_rows", "Sahifa sozlamalari", AMBER, False,
                     f"Hali saqlanmagan, kod default'lari chiqmoqda: {', '.join(missing)}.",
                     "Admin'da (ENABLE_LEGACY_ADMIN=True) tegishli sozlamani ochib bir marta saqlang.", "admin:index")
    return _item("settings_rows", "Sahifa sozlamalari", GREEN, False, "Hammasi owner tomonidan saqlangan.")


# (kalit, nom, tekshiruv) — tekshiruv yiqilsa ayni kalit va nom bilan qizil majburiy band chiqadi.
CHECKS = (
    ("legal", "Huquqiy hujjatlar", _legal_items),
    ("live_offer", "Sotuvdagi kurs", _offer_items),
    ("support_contact", "Aloqa kanali", _contact_item),
    ("payment_details", "To'lov rekvizitlari", _payment_item),
    ("email_delivery", "Email yuborish", _email_item),
    ("canonical_origin", "Saytning asosiy manzili", _origin_item),
    ("sitemap", "Sitemap", _sitemap_item),
    ("public_media", "Ochiq media fayllari", _media_item),
    ("claims", "Da'volar dalili", _claims_item),
    ("testimonials", "O'quvchilar fikri", _testimonials_item),
    ("certificates", "Sertifikat tekshiruvi", _certificate_item),
    ("sit_freshness", "SIT ma'lumoti dolzarbligi", _sit_item),
    ("settings_rows", "Sahifa sozlamalari", _settings_item),
)


def release_readiness():
    """Barcha bandlar; bitta tekshiruv yiqilsa u qizil band bo'ladi, qolganlari baribir hisoblanadi."""
    items = []
    for key, label, check in CHECKS:
        try:
            result = check()
        except Exception as exc:  # noqa: BLE001 — darvoza o'qishda yiqilmasin, holatni ko'rsatsin
            items.append(_item(key, label, RED, True, f"Tekshirib bo'lmadi: {type(exc).__name__}.",
                               "Server jurnalini ko'ring."))
            continue
        items.extend(result if isinstance(result, list) else [result])
    return ReleaseReadiness(items=tuple(items), checked_at=timezone.now())


class NotReady(Exception):
    pass


def sign_off(*, actor, reason, request=None):
    """Owner tasdig'i: faqat majburiy bandlar yashil bo'lsa; audit yozuvi — tasdiq kvitansiyasi."""
    from core.audit import record_audit_event

    readiness = release_readiness()
    if not readiness.ready_for_pilot:
        raise NotReady(", ".join(item.label for item in readiness.blockers))
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("Sabab majburiy.")
    record_audit_event(
        action=SIGNOFF_ACTION, request=request, actor=actor, target_label=f"Reliz tayyorligi {readiness.digest()}",
        reason=reason, after={"digest": readiness.digest(), "items": {item.key: item.status for item in readiness.items}},
    )
    return readiness


def last_sign_off():
    from aicontrol.models import SystemAuditEvent

    return SystemAuditEvent.objects.filter(action=SIGNOFF_ACTION).select_related("actor").order_by("-id").first()
