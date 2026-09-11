"""Telegram outbox yuboruvchisi (F4).

Sinxron DB funksiyalari (testlanadi) + yupqa async worker (run_bot ichida
polling bilan yonma-yon yuguradi). Telegram rate-limit ikki qatlamda: har
siklda ko'pi bilan BATCH_SIZE ta xabar, sikllar orasi POLL_INTERVAL soniya,
va sikl **ichida** har yuborish orasida kichik oraliq.

Qayta urinish, backoff va dead-letter qarorlari bu yerda emas,
`bot/retry_policy.py` da (F10): xuddi shu siyosat Classbook guruh navbatida
ham ishlatiladi va ikki joyda takrorlanishi kerak emas.
"""

import asyncio
import html
import logging
import uuid
from datetime import timedelta

from aiogram.types import InlineKeyboardMarkup
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from bot import retry_policy
from bot.models import TelegramOutbox
# `MAX_ATTEMPTS` eski import yo'li orqali ham ochiq qoladi (mavjud testlar).
from bot.retry_policy import MAX_ATTEMPTS, plan_retry  # noqa: F401

logger = logging.getLogger(__name__)

BATCH_SIZE = 25
POLL_INTERVAL = 15  # soniya
# `MAX_ATTEMPTS` va backoff siyosati `bot/retry_policy.py` da — DM navbati
# bilan Classbook guruh navbati bitta siyosatni ishlatishi uchun.
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
    # `next_attempt_at` kelajakda bo'lsa qator olinmaydi — backoff aynan shu
    # bilan amalga oshadi. `Q(isnull=True)` shart: eski qatorlarda va birinchi
    # urinishda qiymat yo'q, va ularni chiqarib tashlash butun navbatni
    # to'xtatib qo'yardi.
    now = timezone.now()
    candidate_ids = list(
        TelegramOutbox.objects.filter(status=TelegramOutbox.STATUS_PENDING)
        .filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
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
    # Oldingi nosozlik izi tozalanadi: aks holda muvaffaqiyatli yuborilgan
    # qator Control Center'da hamon "permanent xato" deb ko'rinardi.
    item.next_attempt_at = None
    item.failure_kind = ""
    item.save(
        update_fields=[
            "status", "sent_at", "claim_token", "next_attempt_at", "failure_kind",
        ]
    )


def mark_outbox_attempt_failed(item, error):
    """Urinish muvaffaqiyatsiz: qaror `bot/retry_policy.py` dan olinadi.

    Uch yo'l bor va ular ataylab farq qiladi: `429` urinishni sarflamaydi va
    qatorni Telegram aytgan vaqtga suradi; foydalanuvchi botni bloklagan bo'lsa
    qator darhol terminal bo'ladi; qolgan nosozliklar exponential backoff bilan
    qayta urinadi. Sabab modul docstringida.
    """
    kind, attempts, give_up, next_attempt_at = plan_retry(
        error=error, attempts=item.attempts
    )
    item.attempts = attempts
    item.last_error = str(error)[:255]
    item.failure_kind = kind
    item.status = (
        TelegramOutbox.STATUS_FAILED if give_up else TelegramOutbox.STATUS_PENDING
    )
    item.next_attempt_at = next_attempt_at
    item.claimed_at = None
    item.claim_token = ""
    item.save(
        update_fields=[
            "attempts", "last_error", "status", "claimed_at", "claim_token",
            "next_attempt_at", "failure_kind",
        ]
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


async def _space_out_sends():
    """Ketma-ket yuborishlar orasiga kichik oraliq qo'yadi.

    Telegram turli chatlarga ~30 xabar/sekundga ruxsat beradi. Ilgari sikl 25
    ta `send_message` ni orasiz otardi va 50 o'quvchilik Classbook darsidan
    keyin aynan shu `429 Flood control` ni keltirardi. Oraliq `retry_policy`
    da, chunki u navbat tezligi siyosatining bir qismi; test uni `0` ga
    qo'yib sikllarni tezlashtira oladi.
    """
    interval = retry_policy.SEND_INTERVAL_SECONDS
    if interval > 0:
        await asyncio.sleep(interval)


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

    # Classbook web yuzasidan boshlangan dars Telegram guruhiga bevosita
    # HTTP request ichida yozmaydi. Xabar ham shu worker orqali, lease va
    # retry bilan yetadi. Guruhdagi jonli buyruq eski DM navbatidan oldin
    # borishi kerak; aks holda o'qituvchi "Ochish"ni bosib, 25 ta DM
    # tugashini kutib qoladi. Lazy import app-registry siklini oldini oladi.
    from classbook.delivery import (
        claim_pending_group_deliveries,
        mark_group_delivery_failed,
        mark_group_delivery_sent,
        render_group_delivery_markup,
        render_group_delivery_text,
    )

    group_items = await sync_to_async(claim_pending_group_deliveries)()
    sent = 0
    for item in group_items:
        try:
            message = await bot.send_message(
                item.chat_id,
                render_group_delivery_text(item),
                parse_mode="HTML",
                reply_markup=render_group_delivery_markup(item),
            )
        except Exception as exc:
            await sync_to_async(mark_group_delivery_failed)(item, exc)
            continue
        await sync_to_async(mark_group_delivery_sent)(
            item, getattr(message, "message_id", None)
        )
        sent += 1
        await _space_out_sends()

    items = await sync_to_async(claim_pending_outbox)()
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
        await _space_out_sends()

    # Navbat bo'sh bo'lsa ham belgilanadi — aynan shu holat ilgari ko'r nuqta
    # edi: ishlaydigan narsa yo'qligi worker tirikligini isbotlamasdi.
    await sync_to_async(record_worker_heartbeat)(sent=sent, claimed=len(items) + len(group_items))
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
