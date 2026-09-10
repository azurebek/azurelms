"""Telegram guruhiga yuboriladigan Classbook xabarlari uchun outbox."""

import html
import uuid
from datetime import timedelta

from aiogram.types import InlineKeyboardMarkup
from django.conf import settings
from django.utils import timezone

from bot.keyboards import attendance_checkin_markup, miniapp_button

from .models import TelegramGroupDelivery


BATCH_SIZE = 10
MAX_ATTEMPTS = 3
LEASE_SECONDS = 120


def queue_group_delivery(*, session, external_key, text, kind=TelegramGroupDelivery.KIND_TEXT,
                         activity=None, button_text="", button_path=""):
    if not session.chat_id:
        return None
    delivery, _ = TelegramGroupDelivery.objects.get_or_create(
        external_key=external_key,
        defaults={
            "session": session,
            "activity": activity,
            "chat_id": session.chat_id,
            "kind": kind,
            "text": text,
            "button_text": button_text,
            "button_path": button_path,
        },
    )
    return delivery


def reclaim_expired_group_deliveries(lease_seconds=LEASE_SECONDS):
    deadline = timezone.now() - timedelta(seconds=lease_seconds)
    return TelegramGroupDelivery.objects.filter(
        status=TelegramGroupDelivery.STATUS_SENDING,
        claimed_at__lt=deadline,
    ).update(status=TelegramGroupDelivery.STATUS_PENDING, claimed_at=None, claim_token="")


def claim_pending_group_deliveries(limit=BATCH_SIZE, lease_seconds=LEASE_SECONDS):
    reclaim_expired_group_deliveries(lease_seconds)
    token = uuid.uuid4().hex
    ids = list(
        TelegramGroupDelivery.objects.filter(status=TelegramGroupDelivery.STATUS_PENDING)
        .order_by("id")
        .values_list("id", flat=True)[:limit]
    )
    if not ids:
        return []
    TelegramGroupDelivery.objects.filter(
        id__in=ids, status=TelegramGroupDelivery.STATUS_PENDING
    ).update(
        status=TelegramGroupDelivery.STATUS_SENDING,
        claimed_at=timezone.now(),
        claim_token=token,
    )
    return list(
        TelegramGroupDelivery.objects.filter(claim_token=token)
        .select_related("session", "activity")
        .order_by("id")
    )


def render_group_delivery_markup(delivery):
    if delivery.kind == TelegramGroupDelivery.KIND_ATTENDANCE:
        return attendance_checkin_markup(delivery.session_id)
    if delivery.kind == TelegramGroupDelivery.KIND_LINK and delivery.button_path:
        button = miniapp_button(delivery.button_text or "Mashqni ochish", delivery.button_path)
        if button:
            return InlineKeyboardMarkup(inline_keyboard=[[button]])
    return None


def render_group_delivery_text(delivery):
    text = delivery.text
    if delivery.button_path and not render_group_delivery_markup(delivery):
        domain = (getattr(settings, "APP_DOMAIN", "") or "").strip()
        if domain and "localhost" not in domain and not domain.startswith("127."):
            path = delivery.button_path if delivery.button_path.startswith("/") else f"/{delivery.button_path}"
            text = f"{text}\n\nhttps://{domain}{path}"
        else:
            text = f"{text}\n\n{html.escape(delivery.button_path)}"
    return text


def mark_group_delivery_sent(delivery, telegram_message_id=None):
    delivery.status = TelegramGroupDelivery.STATUS_SENT
    delivery.sent_at = timezone.now()
    delivery.claim_token = ""
    delivery.claimed_at = None
    delivery.telegram_message_id = telegram_message_id
    delivery.save(update_fields=[
        "status", "sent_at", "claim_token", "claimed_at", "telegram_message_id"
    ])
    if delivery.kind == TelegramGroupDelivery.KIND_ATTENDANCE and telegram_message_id:
        type(delivery.session).objects.filter(pk=delivery.session_id).update(
            attendance_message_id=telegram_message_id
        )


def mark_group_delivery_failed(delivery, error):
    delivery.attempts += 1
    delivery.last_error = str(error)[:255]
    delivery.status = (
        TelegramGroupDelivery.STATUS_FAILED
        if delivery.attempts >= MAX_ATTEMPTS
        else TelegramGroupDelivery.STATUS_PENDING
    )
    delivery.claimed_at = None
    delivery.claim_token = ""
    delivery.save(update_fields=["attempts", "last_error", "status", "claimed_at", "claim_token"])
