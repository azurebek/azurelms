"""Telegram outbox yuboruvchisi (F4).

Sinxron DB funksiyalari (testlanadi) + yupqa async worker (run_bot ichida
polling bilan yonma-yon yuguradi). Telegram rate-limit: har siklda ko'pi
bilan BATCH_SIZE ta xabar, sikllar orasi POLL_INTERVAL soniya.
"""

import asyncio
import html
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils import timezone

from bot.models import TelegramOutbox

logger = logging.getLogger(__name__)

BATCH_SIZE = 25
POLL_INTERVAL = 15  # soniya
MAX_ATTEMPTS = 3


def fetch_pending_outbox(limit=BATCH_SIZE):
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
    if note.url and "localhost" not in domain and not domain.startswith("127."):
        url = note.url if note.url.startswith("http") else f"https://{domain}{note.url}"
        lines.append("")
        lines.append(url)
    return "\n".join(lines)


def mark_outbox_sent(item):
    item.status = TelegramOutbox.STATUS_SENT
    item.sent_at = timezone.now()
    item.save(update_fields=["status", "sent_at"])


def mark_outbox_attempt_failed(item, error):
    item.attempts += 1
    item.last_error = str(error)[:255]
    if item.attempts >= MAX_ATTEMPTS:
        item.status = TelegramOutbox.STATUS_FAILED
    item.save(update_fields=["attempts", "last_error", "status"])


async def process_outbox_once(bot):
    """Bitta sikl: pending'larni olib yuborishga urinadi. Yuborilganlar sonini qaytaradi."""
    items = await sync_to_async(fetch_pending_outbox)()
    sent = 0
    for item in items:
        try:
            await bot.send_message(item.telegram_id, render_outbox_text(item), parse_mode="HTML")
        except Exception as exc:  # user botni bloklagan / ochmagan bo'lishi mumkin
            await sync_to_async(mark_outbox_attempt_failed)(item, exc)
            continue
        await sync_to_async(mark_outbox_sent)(item)
        sent += 1
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
