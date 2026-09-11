"""Telegram yetkazish urinishlari siyosati — canonical (F10).

`05-launch-ops.md` §1 "Telegram outbox gate": atomik claim/lease 2026-08-15 da
qurilgan, qolgani **exponential retry/backoff va terminal dead-letter** edi.
Shu modul o'sha qolgan qismni yopadi va DM navbati (`bot/outbox.py`) bilan
Classbook guruh navbati (`classbook/delivery.py`) uchun **bitta** manba bo'ladi:
siyosat ikki joyda takrorlansa, bittasi tuzatilib ikkinchisi eskirib qolardi.

**Nima uchun xatolarni turlarga ajratish kerak.** Ilgari ikkala navbat ham
`except Exception` bilan hamma nosozlikni bir xil hisoblardi: `attempts += 1`,
qator darhol `pending` ga qaytadi, keyingi sikl 15 soniyadan keyin yana urinib
ko'radi. Uch urinishdan keyin qator `failed` bo'lib abadiy qoladi. Bu uch xil
noto'g'ri natija berardi:

1. **`429 Flood control`** — Telegram "juda tez yuboryapsan" deydi, "bu xabar
   yaroqsiz" demaydi. 50 o'quvchiga Classbook natijasi DM bo'lib ketayotganda
   aynan shu qaytadi. Har 429 bitta urinishni yeb, uch siklda (≈45 soniya)
   xabar butunlay `failed` bo'lib qolardi — ya'ni **o'quvchi natijasini hech
   qachon ko'rmaydi**, sabab esa faqat tezlik bo'lgan. Shuning uchun 429
   urinishni **sarflamaydi**, faqat qatorni Telegram aytgan vaqtga suradi.
2. **Foydalanuvchi botni bloklagan** (`403`) — qayta urinish hech qachon
   yordam bermaydi. Uch urinish shunchaki rate budjetini yeb, navbatni
   sekinlashtiradi. Bunday qator darhol dead-letter qilinadi.
3. **Tarmoq yoki `5xx`** — qayta urinish mantiqiy, ammo darhol emas.
   Backoff'siz uch urinish 45 soniyaga sig'adi va bir daqiqalik uzilish
   xabarni yo'qotadi. Endi kechikish 30s → 1m → 2m → 4m bo'lib o'sadi.

Siyosat sof funksiyalar ko'rinishida: model ham, `bot` obyekti ham kerak emas,
shuning uchun har bir qarorni to'g'ridan-to'g'ri test qilib bo'ladi.
"""

import random
from datetime import timedelta

from django.utils import timezone

#: Urinishlar soni. Ilgari 3 edi; backoff bilan birga 3 urinish ≈90 soniyaga
#: sig'ib qolardi, ya'ni bir daqiqalik uzilish xabarni yo'qotardi. 5 urinish
#: backoff bilan ≈8 daqiqani qoplaydi.
MAX_ATTEMPTS = 5

#: Birinchi transient xatodan keyingi kechikish; keyingilari ikkilanadi.
BASE_BACKOFF_SECONDS = 30
#: Yuqori chegara — aks holda 10-urinish bir necha soatga surilib ketardi.
MAX_BACKOFF_SECONDS = 15 * 60

#: Jitter ulushi. Bir vaqtda yiqilgan 50 qator bir xil sekundda qaytib kelsa,
#: ular yana bir vaqtda urinib, yana 429 oladi — ya'ni backoff o'z maqsadini
#: yo'qotardi.
JITTER_SHARE = 0.2

#: `429` uchun minimal kechikish: Telegram ba'zan `retry_after=0` beradi va
#: o'sha zahoti qayta urinish yana flood control'ga tushadi.
MIN_RATE_LIMIT_DELAY_SECONDS = 1

#: Bir sikl ichida xabarlar orasidagi oraliq. Telegram turli chatlarga ~30
#: xabar/sekundga ruxsat beradi; 25 ta `send_message` ni orasiz yuborish aynan
#: `429` ning sababi. 20/sekund ataylab chegaradan pastda turadi.
SEND_INTERVAL_SECONDS = 0.05

KIND_RATE_LIMITED = "rate_limited"
KIND_PERMANENT = "permanent"
KIND_TRANSIENT = "transient"
#: Bot darajasidagi konfiguratsiya nosozligi (noto'g'ri/eskirgan token).
#: Ataylab `permanent` emas: sabab **xabarda emas, butun botda**. Agar u
#: terminal bo'lsa, bir marta noto'g'ri token bilan chiqilgan deploy butun
#: navbatni dead-letter qilib yuboradi va tokenni tuzatish ularni qaytarmaydi
#: (replay amali hali yo'q). Navbat to'xtab turgani esa ko'rinadi va
#: tuzatiladi: Control Center eng qadimgi pending bir soatdan oshganda RED
#: beradi. Shu sabab urinish ham sarflanmaydi.
KIND_CONFIG = "config"

#: `TelegramBadRequest` matnida shular uchrasa qayta urinish befoyda: chat
#: o'chirilgan yoki bot u yerdan chiqarilgan. Aiogram bularni alohida sinf
#: bilan bermaydi, shuning uchun matndan aniqlanadi.
PERMANENT_BAD_REQUEST_MARKERS = (
    "chat not found",
    "user is deactivated",
    "bot was kicked",
    "bot is not a member",
    "group chat was upgraded",
    "peer_id_invalid",
)


def _retry_after_seconds(error):
    value = getattr(error, "retry_after", None)
    if value is None:
        return None
    try:
        return max(int(value), MIN_RATE_LIMIT_DELAY_SECONDS)
    except (TypeError, ValueError):
        return MIN_RATE_LIMIT_DELAY_SECONDS


def classify(error):
    """Xatoni `(kind, retry_after)` ga ajratadi.

    Aiogram sinflari `import` qilinadi, lekin **majburiy emas**: modul
    aiogram'siz muhitda ham (masalan sof servis testida) ishlashi kerak, shu
    sabab import xato bo'lsa faqat `retry_after` atributiga qaraladi.
    """
    retry_after = _retry_after_seconds(error)
    if retry_after is not None:
        return KIND_RATE_LIMITED, retry_after

    try:
        from aiogram.exceptions import (
            TelegramBadRequest,
            TelegramForbiddenError,
            TelegramNotFound,
            TelegramUnauthorizedError,
        )
    except ImportError:  # pragma: no cover — aiogram har doim o'rnatilgan
        return KIND_TRANSIENT, None

    # `403` — foydalanuvchi botni bloklagan yoki chatdan chiqargan.
    # `404` — chat umuman yo'q. Ikkisida ham qayta urinish hech narsani
    # o'zgartirmaydi.
    if isinstance(error, (TelegramForbiddenError, TelegramNotFound)):
        return KIND_PERMANENT, None

    # Noto'g'ri yoki eskirgan token: butun bot uchun nosozlik, bitta xabar
    # uchun emas. Shuning uchun terminal qilinmaydi — tokenni tuzatgach
    # navbatdagi hamma xabar yetib borishi kerak.
    if isinstance(error, TelegramUnauthorizedError):
        return KIND_CONFIG, None

    if isinstance(error, TelegramBadRequest):
        text = str(error).lower()
        if any(marker in text for marker in PERMANENT_BAD_REQUEST_MARKERS):
            return KIND_PERMANENT, None
        # Qolgan `400` lar (masalan noto'g'ri HTML) ham qayta urinishdan
        # tuzalmaydi, ammo ularni permanent deb yopish xabarni jim yo'qotardi.
        # Transient qoldiriladi: urinishlar tugagach dead-letter bo'ladi va
        # `failure_kind` sababni ko'rsatadi.
        return KIND_TRANSIENT, None

    return KIND_TRANSIENT, None


def backoff_seconds(attempts, *, base=BASE_BACKOFF_SECONDS, cap=MAX_BACKOFF_SECONDS):
    """`attempts`-urinishdan keyingi kechikish (jitter bilan).

    `attempts` — allaqachon **oshirilgan** qiymat, ya'ni birinchi nosozlikdan
    keyin `1` keladi va natija `base` bo'ladi.
    """
    exponent = max(int(attempts) - 1, 0)
    # `min` kappadan oldin: 2**exponent katta sonlarda keraksiz hisoblanmasin.
    delay = min(base * (2 ** min(exponent, 20)), cap)
    jitter = delay * JITTER_SHARE
    return max(delay + random.uniform(-jitter, jitter), 1.0)


def plan_retry(*, error, attempts, max_attempts=MAX_ATTEMPTS, now=None):
    """Nosozlikdan keyin nima qilishni aytadi.

    Qaytaradi: `(kind, attempts, give_up, next_attempt_at)`.

    * `attempts` — saqlanishi kerak bo'lgan yangi qiymat. `429` da o'zgarmaydi.
    * `give_up` — `True` bo'lsa qator terminal (dead-letter).
    * `next_attempt_at` — `None` bo'lsa darhol navbatga qaytadi.
    """
    now = now or timezone.now()
    kind, retry_after = classify(error)

    if kind == KIND_RATE_LIMITED:
        # Urinish sarflanmaydi: sabab xabarda emas, bizning tezligimizda.
        return kind, attempts, False, now + timedelta(seconds=retry_after)

    if kind == KIND_CONFIG:
        # Urinish sarflanmaydi va qator terminal bo'lmaydi: owner tokenni
        # tuzatgach butun navbat tiklanishi kerak. Backoff bilan kutadi,
        # shunda noto'g'ri token log va rate budjetini ham yemaydi.
        return kind, attempts, False, now + timedelta(
            seconds=backoff_seconds(max(attempts, 1))
        )

    if kind == KIND_PERMANENT:
        # Darhol dead-letter: qayta urinish hech qachon yordam bermaydi.
        return kind, attempts + 1, True, None

    new_attempts = attempts + 1
    if new_attempts >= max_attempts:
        return kind, new_attempts, True, None
    return kind, new_attempts, False, now + timedelta(seconds=backoff_seconds(new_attempts))
