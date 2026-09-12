"""Dispatcher kuzatuvi — jarayon ichida o'lchash, navbatda yozish (T4).

Audit (2026-09-11) topgan bo'shliq: **bot tomonida hech qanday metrika yo'q**.
Outbox navbati Control Center'da ko'rinadi, handler yo'li esa butunlay jim.
Ya'ni «bot tirikmi?» degan savolga bugun javob beradigan yo'l bor edi —
foydalanuvchiga yozib ko'rish — va bu javob **xabar yuborishni** talab qiladi.

Shu modul uchta narsani beradi:

1. **Tiriklik.** Jarayon o'zini `WorkerHeartbeat` ga belgilaydi. Bu
   `telegram-outbox` uchun allaqachon ishlaydigan naqsh — yangi monitoring
   tizimi qurilmaydi, mavjudi ikkinchi ism bilan ishlatiladi.
2. **Tezlik.** Har update qancha ishlaganini o'lchaydi va o'rtacha/p95 beradi.
3. **Xato.** Handler'dan chiqqan istisnolar soni.

**Nega tiriklik update kelishidan ajratilgan.** Eng aldamchi dizayn —
"oxirgi update vaqti"ni sog'liq deb o'qish. Tunda hech kim yozmasa bot
**sog'lom** bo'ladi, chiroq esa qizil bo'lib turardi va owner har tongda
mavjud bo'lmagan nosozlikni qidirardi. Shuning uchun:

* `last_seen_at` — **flush sikli** yozadi, trafikdan qat'i nazar. Bu tiriklik.
* `detail["last_update_at"]` — oxirgi update. Bu **trafik**, sog'liq emas.

**Nega o'lchov DB'ga har update'da yozilmaydi.** Update'lar seriyasi jonli
darsda portlaydi: 50 o'quvchi bir vaqtda «Keldim» bosadi. Har biri uchun
bitta `UPDATE` — bu o'lchovning o'zi nosozlik manbasiga aylanishi. Shuning
uchun `record()` faqat xotiraga yozadi (lock + deque, mikrosekundlar), DB'ga
esa sikl bo'yicha bitta yozuv boradi.
"""

import asyncio
import logging
import math
import threading
import time
from collections import deque

from django.utils import timezone

from bot.runtime_settings import DEFAULTS, DeliveryPolicy

logger = logging.getLogger(__name__)

#: Heartbeat ismi. `telegram-outbox` dan ataylab alohida: ular **boshqa
#: jarayonlar** va biri o'lganda ikkinchisi tirik qolishi mumkin.
WORKER_NAME = "telegram-dispatcher"

#: Xotirada saqlanadigan maksimal namuna. Bu **siyosat emas, xotira
#: kafolati** — shuning uchun sozlamada yo'q. Owner uchun ma'noli savol
#: «qancha vaqtlik oyna» (u sozlamada), «nechta tuple RAM'da» emas.
#: 2000 × ~40 bayt ≈ 80 KB, ya'ni cheksiz o'sish xavfi yopiladi.
MAX_SAMPLES = 2000

#: Xato foizini rang qilish uchun minimal namuna. Bittadan bitta xato = 100%
#: bo'ladi va bot ishga tushgan zahoti qizil chiroq berardi. Bu statistik
#: to'r, operatsion qaror emas — shuning uchun ham sozlamada yo'q.
MIN_ERROR_SAMPLES = 20

#: p95 — eng yaqin darajali (nearest-rank) usul.
P95 = 0.95


class DispatcherMetrics:
    """Jarayon ichidagi yig'uvchi.

    Thread-safe, chunki webhook rejimida Django sync view'i threadpool'da
    yuguradi — ya'ni bir nechta thread bir vaqtda `record()` chaqirishi
    mumkin. Polling rejimida bitta event loop bor va lock hech qachon
    kutmaydi (band bo'lmagan `Lock.acquire` ≈ 100 ns).
    """

    def __init__(self):
        self._lock = threading.Lock()
        #: `(monotonic, duration_ms, failed, unhandled)`
        self._samples = deque(maxlen=MAX_SAMPLES)
        self._updates_total = 0
        self._errors_total = 0
        self._last_update_at = None

    def record(self, *, duration_ms, failed=False, unhandled=False, monotonic=None, wall=None):
        """Bitta update natijasini yozadi. DB'ga tegmaydi."""
        stamp = monotonic if monotonic is not None else time.monotonic()
        # Vaqtni lock'dan TASHQARIDA olamiz: lock ichida faqat ro'yxatga
        # qo'shish qoladi, ya'ni bir vaqtda kelgan update'lar bir-birini
        # kutmaydi.
        moment = wall or timezone.now()
        with self._lock:
            self._samples.append((stamp, float(duration_ms), bool(failed), bool(unhandled)))
            self._updates_total += 1
            if failed:
                self._errors_total += 1
            self._last_update_at = moment

    def reset(self):
        """Faqat test uchun — jarayon davomida hech qachon chaqirilmaydi."""
        with self._lock:
            self._samples.clear()
            self._updates_total = 0
            self._errors_total = 0
            self._last_update_at = None

    def snapshot(self, *, window_seconds, monotonic=None):
        """Oynadagi o'lchovlar — heartbeat `detail` ga tushadigan lug'at.

        Oyna **o'tkir** (sliding): oynadan tashqaridagi namuna hisobga
        olinmaydi. Sabab — aks holda uch soat oldin o'lchangan p95 hozirgi
        tezlik bo'lib ko'rinardi va owner mavjud bo'lmagan sekinlikni
        ko'rardi. Trafik bo'lmasa javob «namuna yo'q», «hammasi tez» emas.
        """
        now = monotonic if monotonic is not None else time.monotonic()
        cutoff = now - max(1, int(window_seconds))
        with self._lock:
            recent = [item for item in self._samples if item[0] >= cutoff]
            updates_total = self._updates_total
            errors_total = self._errors_total
            last_update_at = self._last_update_at

        durations = sorted(item[1] for item in recent)
        errors = sum(1 for item in recent if item[2])
        unhandled = sum(1 for item in recent if item[3])
        detail = {
            "window_seconds": int(window_seconds),
            "samples": len(recent),
            "updates_total": updates_total,
            "errors_total": errors_total,
            "errors": errors,
            "unhandled": unhandled,
            "last_update_at": (
                timezone.localtime(last_update_at).isoformat(timespec="seconds")
                if last_update_at
                else None
            ),
        }
        if durations:
            detail["avg_ms"] = round(sum(durations) / len(durations), 1)
            detail["p95_ms"] = round(percentile(durations, P95), 1)
            detail["max_ms"] = round(durations[-1], 1)
        return detail


def percentile(sorted_values, fraction):
    """Eng yaqin darajali percentil.

    Interpolatsiya qilinmaydi: o'lchangan haqiqiy qiymat qaytariladi, chunki
    «p95 = 1,4 ta update» degan son ma'nosiz. Bitta namunada p95 = shu
    namuna — bu to'g'ri va halol javob.
    """
    if not sorted_values:
        raise ValueError("bo'sh ro'yxatdan percentil olinmaydi")
    rank = max(1, math.ceil(fraction * len(sorted_values)))
    return sorted_values[min(rank, len(sorted_values)) - 1]


#: Jarayon bo'yicha bitta yig'uvchi.
METRICS = DispatcherMetrics()


# --------------------------------------------------------------------------- #
# Heartbeat yozuvi
# --------------------------------------------------------------------------- #


def _current_policy():
    from bot.runtime_settings import current_policy

    return current_policy()


def flush_metrics(*, policy=None, stopped=False, now=None):
    """O'lchovni `WorkerHeartbeat` ga yozadi.

    `flush_seconds` ataylab `detail` ga qo'shiladi: Control Center probe'i
    «qancha kutsam eskirgan hisoblanadi» ni shundan hisoblaydi. Sozlamadagi
    joriy qiymatni o'qish xato bo'lardi — jarayon **o'zi ishlatayotgan**
    oraliq muhim, owner bir daqiqa oldin o'zgartirgani emas.

    `stopped=True` — ataylab to'xtatish. Buni yozmasa, halokat va rejali
    to'xtatish Control Center'da bir xil ko'rinardi.
    """
    from aicontrol.models import WorkerHeartbeat

    policy = policy or _current_policy()
    detail = METRICS.snapshot(window_seconds=policy.metrics_window_seconds)
    detail["flush_seconds"] = policy.metrics_flush_seconds
    detail["mode"] = _telegram_mode()
    if stopped:
        # Muhim: `last_seen_at` bu yozuvda **yangi** bo'ladi, ya'ni yosh
        # bo'yicha tekshiruv uni tirik deb o'qiydi. Probe shu sabab bayroqni
        # yoshdan OLDIN ko'radi.
        detail["stopped_at"] = timezone.localtime().isoformat(timespec="seconds")
    return WorkerHeartbeat.record(WORKER_NAME, detail=detail, now=now)


def _telegram_mode():
    from django.conf import settings

    return str(getattr(settings, "TELEGRAM_MODE", "unknown"))


def safe_flush(*, stopped=False):
    """Yozuvni yutadigan o'ram.

    O'lchov hech qachon botni yiqitmasligi kerak: kuzatuv vositasi
    kuzatilayotgan tizimdan ko'ra ishonchliroq bo'lishi mumkin emas, ammo
    uni o'chirishi ham mumkin emas.
    """
    try:
        return flush_metrics(stopped=stopped)
    except Exception:  # noqa: BLE001 — DB yo'q, jadval yo'q, migratsiyadan oldin
        logger.warning("Dispatcher heartbeat yozilmadi", exc_info=True)
        return None


# --------------------------------------------------------------------------- #
# Flush sikli (polling) va piggy-back (webhook)
# --------------------------------------------------------------------------- #

_flusher_active = False
_last_flush_monotonic = None
#: Piggy-back yo'li uchun keshlangan oraliq. Har update'da sozlamani o'qish
#: o'lchovni aynan u oldini olishi kerak bo'lgan narsaga aylantirardi —
#: update boshiga qo'shimcha DB so'rovi. Qiymat flush paytida yangilanadi.
_piggyback_interval = DEFAULTS["metrics_flush_seconds"]


def flusher_active():
    """Alohida flush sikli ishlayaptimi (polling rejimi)."""
    return _flusher_active


async def run_metrics_flusher():
    """Trafikdan qat'i nazar heartbeat yozadigan sikl.

    Birinchi yozuv **kutmasdan** boradi: bot ishga tushganda chiroq darhol
    yashil bo'lishi kerak, bir oraliq o'tgandan keyin emas.

    Sikl kutilmaganda tugasa (bekor qilindi yoki thread pool yiqildi) bayroq
    `finally` da tushadi va piggy-back yo'li o'z-o'zidan yoqiladi: trafik bor
    bo'lsa heartbeat yozilishda davom etadi. Ya'ni kuzatuvning o'zi bitta
    nuqtaga bog'lanmagan.
    """
    global _flusher_active

    from asgiref.sync import sync_to_async

    _flusher_active = True
    try:
        while True:
            policy = await sync_to_async(_safe_flush_and_policy)()
            await asyncio.sleep(max(1, policy.metrics_flush_seconds))
    finally:
        _flusher_active = False


def _safe_flush_and_policy():
    """Bitta DB o'qish bilan ham yozadi, ham keyingi oraliqni qaytaradi."""
    try:
        policy = _current_policy()
    except Exception:  # noqa: BLE001 — sozlama jadvali hali yo'q bo'lishi mumkin
        policy = DeliveryPolicy.defaults()
    try:
        flush_metrics(policy=policy)
    except Exception:  # noqa: BLE001
        logger.warning("Dispatcher heartbeat yozilmadi", exc_info=True)
    return policy


async def maybe_flush():
    """Webhook rejimi uchun piggy-back yozuv.

    Webhook'da uzoq yashovchi event loop yo'q — har so'rov `async_to_sync`
    bilan o'z loop'ini ochadi va yopadi, ya'ni fon task'i tirik qolmaydi.
    Shuning uchun yozuv update'ning o'ziga ilashtiriladi, lekin **oraliqqa
    bir marta**: 30 soniyalik oynada yuzlab update bo'lsa ham bitta `UPDATE`
    bajariladi.

    Polling rejimida sikl bor — bu funksiya darhol qaytadi va hech narsa
    kutmaydi (shutdown paytidagi `CancelledError` ga tushmaslik uchun ham).
    """
    global _last_flush_monotonic, _piggyback_interval

    if _flusher_active:
        return False

    from asgiref.sync import sync_to_async

    now = time.monotonic()
    if _last_flush_monotonic is not None and (now - _last_flush_monotonic) < _piggyback_interval:
        return False
    # Vaqtni yozuvdan OLDIN belgilaymiz: yozuv xato bersa ham keyingi update
    # darhol qayta urinmaydi, aks holda DB yiqilganda har update bitta
    # muvaffaqiyatsiz so'rov qo'shardi.
    _last_flush_monotonic = now
    policy = await sync_to_async(_safe_flush_and_policy)()
    _piggyback_interval = max(1, policy.metrics_flush_seconds)
    return True


def reset_flush_clock():
    """Faqat test uchun — piggy-back oraliq hisobini nolga qaytaradi."""
    global _last_flush_monotonic, _piggyback_interval

    _last_flush_monotonic = None
    _piggyback_interval = DEFAULTS["metrics_flush_seconds"]
