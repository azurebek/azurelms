"""Kurs sahifasidan boshlangan xarid niyati — imzoli, turlangan havola (PUB1.3d).

Mehmon kurs sahifasida “Kirish”/“Ro‘yxatdan o‘tish”ni bossa, auth oqimi
(login, ro'yxat, onboarding, Telegram) uni boshqa sahifaga emas, aynan o'sha
kursning to'lov sahifasiga qaytarishi kerak. Ilgari `next=/courses/7/` raw URL
edi; uni `next=/checkout/…&plan_id=…` ga almashtirish mijozga checkout
parametrlarini boshqarish imkonini berardi.

Bu yerda niyat — Django `signing` bilan imzolangan kichik konvert:
`{versiya, manzil turi, kurs id, tarif kodi, nonce}`. Unda URL, narx, joy,
huquq yoki shaxsiy ma'lumot yo'q; mijoz uni o'zgartira olmaydi. Konvert mavjud
auth oqimida xavfsiz ichki `next` sifatida yuradi
(`/courses/continue/?intent=…`) — login, ro'yxat, onboarding va Telegram uni
o'zgarishsiz olib o'tadi. Niyat hech qachon buyurtma emas: qaytishda kurs,
tarif va qabul `courses.public_offer` orqali qayta tekshiriladi, checkout esa
narxni o'zi hisoblaydi.

Muddat owner sozlamasi — `OperationalSettings.public_intent_minutes`.
"""

import logging
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

from django.core import signing
from django.core.cache import cache
from django.urls import reverse

SALT = "frontend.public-intent.v1"
PARAM = "intent"
VERSION = 1
COURSE_CHECKOUT = "course_checkout"
COURSE_DETAIL = "course_detail"
CATALOG = "catalog"
DESTINATIONS = frozenset({COURSE_CHECKOUT, COURSE_DETAIL, CATALOG})
MAX_TOKEN_LENGTH = 512
INVALID_MESSAGES = {
    "expired": "Kursga qaytish havolasining muddati o‘tgan. Kursni katalogdan qayta tanlang.",
}
DEFAULT_INVALID_MESSAGE = "Kursga qaytish havolasi yaroqsiz. Kursni katalogdan tanlang."
logger = logging.getLogger("frontend.public_intent")


@dataclass(frozen=True)
class PublicIntent:
    destination: str
    course_id: int | None = None
    plan_code: str | None = None
    nonce: str = ""


def max_age_seconds():
    from core.operational_settings import current_thresholds

    return current_thresholds().public_intent_minutes * 60


def issue(destination, *, course_id=None, plan_code=None):
    if destination not in DESTINATIONS:
        raise ValueError(destination)
    payload = {"v": VERSION, "d": destination, "c": course_id, "p": plan_code or None, "n": secrets.token_urlsafe(8)}
    return signing.dumps(payload, salt=SALT, compress=True)


def continue_url(destination, *, course_id=None, plan_code=None):
    """Auth oqimiga `next` sifatida beriladigan ichki manzil."""
    token = issue(destination, course_id=course_id, plan_code=plan_code)
    return f"{reverse('public_intent_continue')}?{urlencode({PARAM: token})}"


class InvalidIntent(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def read(token):
    """Imzosi, muddati va shakli to'g'ri niyat; aks holda `InvalidIntent` (sababi bilan)."""
    if not token or len(token) > MAX_TOKEN_LENGTH:
        raise InvalidIntent("missing")
    try:
        payload = signing.loads(token, salt=SALT, max_age=max_age_seconds())
    except signing.SignatureExpired as exc:
        raise InvalidIntent("expired") from exc
    except signing.BadSignature as exc:
        raise InvalidIntent("tampered") from exc
    if not isinstance(payload, dict) or payload.get("v") != VERSION or payload.get("d") not in DESTINATIONS:
        raise InvalidIntent("unknown")
    course_id, plan_code = payload.get("c"), payload.get("p")
    if course_id is not None and (not isinstance(course_id, int) or isinstance(course_id, bool) or course_id < 1):
        raise InvalidIntent("unknown")
    if plan_code is not None and (not isinstance(plan_code, str) or not 0 < len(plan_code) <= 40):
        raise InvalidIntent("unknown")
    if payload["d"] != CATALOG and course_id is None:
        raise InvalidIntent("unknown")
    return PublicIntent(payload["d"], course_id, plan_code, str(payload.get("n", ""))[:32])


def record(*, outcome, intent=None):
    """Hal qilish natijasi jurnalga: bitta niyat (nonce) birinchi marta — `replay=False`.

    Faqat natija, manzil turi va kurs id; foydalanuvchi, token yoki URL yozilmaydi.
    """
    replay = False
    if intent is not None and intent.nonce:
        replay = not cache.add(f"public-intent:{intent.nonce}", 1, timeout=max_age_seconds())
    logger.info(
        "public_intent",
        extra={
            "intent_outcome": outcome,
            "intent_destination": intent.destination if intent else "",
            "intent_course": intent.course_id if intent else None,
            "intent_replay": replay,
        },
    )
    return replay
