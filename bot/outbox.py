"""Telegram outbox yuboruvchisi (F4).

Sinxron DB funksiyalari (testlanadi) + yupqa async worker (run_bot ichida
polling bilan yonma-yon yuguradi). Telegram rate-limit: har siklda ko'pi
bilan BATCH_SIZE ta xabar, sikllar orasi POLL_INTERVAL soniya.
"""

import asyncio
import html
import logging
import uuid
from datetime import timedelta

from aiogram.types import InlineKeyboardMarkup
from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone

from bot.models import TelegramOutbox

logger = logging.getLogger(__name__)

BATCH_SIZE = 25
POLL_INTERVAL = 15  # soniya
MAX_ATTEMPTS = 3
# Lease muddati: worker o'lib qolsa qator shuncha vaqtdan keyin qayta oqimga
# qaytadi. Bitta sikl (BATCH_SIZE ta xabar) bundan ancha tez tugaydi.
LEASE_SECONDS = 120


def reclaim_expired_outbox(lease_seconds=LEASE_SECONDS):
    """Muzlab qolgan `sending` qatorlarni qaytadan `pending` qiladi.

    Worker xabarni yuborayotganda o'lib qolsa qator `sending` holatida qolib
    ketardi va uni hech kim olmasdi. Lease muddati o'tgach qator yana oqimga
    qo'shiladi — narxi: o'sha xabar ikki marta ketishi mumkin (pastdagi
    at-least-once eslatmasiga qarang).
    """
    deadline = timezone.now() - timedelta(seconds=lease_seconds)
    return TelegramOutbox.objects.filter(
        status=TelegramOutbox.STATUS_SENDING,
        claimed_at__lt=deadline,
    ).update(status=TelegramOutbox.STATUS_PENDING, claimed_at=None, claim_token="")


def claim_pending_outbox(limit=BATCH_SIZE, lease_seconds=LEASE_SECONDS):
    """Bir necha pending qatorni atomik ravishda shu workerga biriktiradi.

    Ilgari worker shunchaki `status=pending` bo'yicha tanlardi. Ikki worker
    (masalan `runbot` ichidagi va alohida `telegram_outbox --loop`) bir vaqtda
    ishlaganda ikkalasi ham bir xil qatorlarni olib, bir xil DM'ni ikki marta
    yuborardi. Shu sabab hujjatlarda "aynan 1 replica xavfsizroq" deb turardi.

    Atomiklik shartli `UPDATE` ga tayanadi: `status=pending` filtri bilan
    yangilash faqat bitta workerda mos keladi, ikkinchisiniki `0` qator
    yangilaydi. `SELECT ... FOR UPDATE SKIP LOCKED` ishlatilmadi — SQLite uni
    qo'llab-quvvatlamaydi.
    """
    reclaim_expired_outbox(lease_seconds)

    token = uuid.uuid4().hex
    candidate_ids = list(
        TelegramOutbox.objects.filter(status=TelegramOutbox.STATUS_PENDING)
        .order_by("id")
        .values_list("id", flat=True)[:limit]
    )
    if not candidate_ids:
        return []

    TelegramOutbox.objects.filter(
        id__in=candidate_ids,
        status=TelegramOutbox.STATUS_PENDING,
    ).update(
        status=TelegramOutbox.STATUS_SENDING,
        claimed_at=timezone.now(),
        claim_token=token,
    )
    return list(
        TelegramOutbox.objects.filter(claim_token=token)
        .select_related("notification")
        .order_by("id")
    )


def fetch_pending_outbox(limit=BATCH_SIZE):
    """Faqat kuzatish uchun: hech narsa band qilmaydi."""
    return list(
        TelegramOutbox.objects.filter(status=TelegramOutbox.STATUS_PENDING)
        .select_related("notification")
        .order_by("id")[:limit]
    )


def render_outbox_text(item):
    note = item.notification
    title = (note.title or "Bildirishnoma").strip()
    lines = [f"🔔 <b>{html.escape(title)}</b>"]
    if note.message:
        lines.append("")
        lines.append(html.escape(note.message))
    domain = getattr(settings, "APP_DOMAIN", "") or ""
    # Mini App tugmasi qo'yilganda oddiy havola matnga qo'shilmaydi: aks holda
    # bir xil manzil ikki marta ko'rinadi va o'quvchi aynan avto-login
    # bermaydigan nusxasini bosishi mumkin.
    if note.url and not render_outbox_markup(item) and "localhost" not in domain and not domain.startswith("127."):
        url = note.url if note.url.startswith("http") else f"https://{domain}{note.url}"
        lines.append("")
        lines.append(url)
    return "\n".join(lines)


def render_outbox_markup(item):
    """Bildirishnoma havolasini Mini App tugmasiga aylantiradi.

    Ilgari worker matnga oddiy `https://.../courses/...` havolasini qo'shardi.
    Telegram-only o'quvchi uni bosganda brauzerda **autentifikatsiyasiz**
    sahifa ochilardi: "yangi dars ochildi" yoki "vazifa tekshirildi" xabari
    kerakli joyga olib bormasdi. Mini App tugmasi esa `initData` bilan
    ochiladi va avto-login ishlaydi (`bot/keyboards.py::miniapp_button`).

    Lokalda (`localhost`) Telegram `web_app` tugmasini rad etadi — u yerda
    `None` qaytadi va matn eski oddiy havola bilan ketaveradi.
    """
    from bot.keyboards import miniapp_button

    note = item.notification
    path = (note.url or "").strip()
    # Tashqi (absolute) havola Mini App ichida ochilmaydi — u boshqa saytga
    # ketadi, `?next=` esa faqat o'z sahifalarimiz uchun.
    if not path.startswith("/"):
        return None

    button = miniapp_button("📱 Ilovada ochish", path)
    if button is None:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def mark_outbox_sent(item):
    item.status = TelegramOutbox.STATUS_SENT
    item.sent_at = timezone.now()
    item.claim_token = ""
    item.save(update_fields=["status", "sent_at", "claim_token"])


def mark_outbox_attempt_failed(item, error):
    """Urinish muvaffaqiyatsiz: lease bo'shatiladi, qator yana navbatga qaytadi."""
    item.attempts += 1
    item.last_error = str(error)[:255]
    if item.attempts >= MAX_ATTEMPTS:
        item.status = TelegramOutbox.STATUS_FAILED
    else:
        item.status = TelegramOutbox.STATUS_PENDING
    item.claimed_at = None
    item.claim_token = ""
    item.save(
        update_fields=["attempts", "last_error", "status", "claimed_at", "claim_token"]
    )


WORKER_NAME = "telegram-outbox"


def record_worker_heartbeat(*, sent=0, claimed=0, paused=False):
    """Workerni tirik deb belgilaydi (A2).

    Sikl boshida emas, oxirida yoziladi: "men uyg'onib, ishimni qildim"
    degani "men jarayon sifatida mavjudman" dan kuchliroq signal.

    `paused` — flag bilan to'xtatilgan sikl. Bu ham tirik zarba: worker
    ishlayapti, faqat ataylab yubormayapti. Farqi detailda ko'rinadi, aks
    holda pauza va nosozlik bir xil ko'rinardi.
    """
    from aicontrol.models import WorkerHeartbeat

    detail = {"sent": sent, "claimed": claimed}
    if paused:
        detail["paused"] = True
    return WorkerHeartbeat.record(WORKER_NAME, detail=detail)


async def process_outbox_once(bot):
    """Bitta sikl: pending'larni olib yuborishga urinadi. Yuborilganlar sonini qaytaradi."""
    from core.flags import flag_enabled

    # Pauza qilinganda xabarlar navbatda **saqlanib turadi**: ularni olmaymiz,
    # ya'ni lease ham ochilmaydi va hech narsa yo'qolmaydi. Heartbeat esa
    # baribir yoziladi — aks holda pauza Control Center'da worker o'lgandek
    # ko'rinardi va owner yo'q muammoni qidirardi.
    if not await sync_to_async(flag_enabled)("telegram_outbox_sending"):
        await sync_to_async(record_worker_heartbeat)(sent=0, claimed=0, paused=True)
        return 0

    items = await sync_to_async(claim_pending_outbox)()
    sent = 0
    for item in items:
        try:
            await bot.send_message(
                item.telegram_id,
                render_outbox_text(item),
                parse_mode="HTML",
                reply_markup=render_outbox_markup(item),
            )
        except Exception as exc:  # user botni bloklagan / ochmagan bo'lishi mumkin
            await sync_to_async(mark_outbox_attempt_failed)(item, exc)
            continue
        await sync_to_async(mark_outbox_sent)(item)
        sent += 1

    # Navbat bo'sh bo'lsa ham belgilanadi — aynan shu holat ilgari ko'r nuqta
    # edi: ishlaydigan narsa yo'qligi worker tirikligini isbotlamasdi.
    await sync_to_async(record_worker_heartbeat)(sent=sent, claimed=len(items))
    return sent


async def outbox_worker(bot):
    """Cheksiz worker — run_bot polling bilan parallel yuguradi."""
    logger.info("Telegram outbox worker ishga tushdi (har %ss).", POLL_INTERVAL)
    while True:
        try:
            await process_outbox_once(bot)
        except Exception:
            logger.exception("Outbox siklida kutilmagan xato")
        await asyncio.sleep(POLL_INTERVAL)
