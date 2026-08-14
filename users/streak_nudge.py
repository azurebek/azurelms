"""Seriya undash generatori — mascot nomidan re-engagement bildirishnomalari.

Rejalashtirilgan job (Celery beat / management command) xavf ostidagi yoki
seriyasi uzilgan o'quvchilarni topib, mascot xabarini yuboradi. Kuniga bir
marta (idempotent `external_key` orqali) — spam yo'q.

Xolatlar:
- at_risk  — jonli seriya bor, lekin bugun hali harakat yo'q.
- broken   — seriya yaqinda uzildi (hali qaytmagan).
- absent   — ancha vaqt kirmagan, lekin butunlay ketmagan.
Bugun faol bo'lganlar undalmaydi; tabrik xabari harakat vaqtida beriladi.
"""

from datetime import timedelta

from django.utils import timezone

from users.models import LearnerStreak, Notification
from users.streak_messages import (
    STATE_ABSENT,
    STATE_AT_RISK,
    STATE_BROKEN,
    STATE_DONE,
    pick_message,
)

# Seriya uzilganidan keyin necha kungacha "yaqinda uzildi" deb hisoblanadi.
BROKEN_WINDOW_DAYS = 3
# Undan keyin necha kungacha "sog'indim" xabari yuboriladi; keyin to'xtaydi.
ABSENT_WINDOW_DAYS = 14

_TITLES = {
    STATE_AT_RISK: "🔥 Seriyangiz kutmoqda",
    STATE_BROKEN: "💔 Seriya uzildi",
    STATE_ABSENT: "👋 Sizni sog'indim",
    STATE_DONE: "🔥 Seriya saqlandi",
}
_ICONS = {
    STATE_AT_RISK: "fire",
    STATE_BROKEN: "heartbreak",
    STATE_ABSENT: "emoji-smile",
    STATE_DONE: "fire",
}


def _streak_notification_key(day):
    return f"streak-nudge-{day.isoformat()}"


def set_daily_streak_notification(user, state, now=None):
    """Foydalanuvchining BUGUNGI yagona seriya bildirishnomasini o'rnatadi.

    Bitta kunlik bildirishnoma joyida yangilanadi — to'planmaydi. "Dars qil"
    nudge yuborilgach o'quvchi dars qilsa, aynan o'sha bildirishnoma tabrik
    xabariga aylanadi (event-bound, vaqtinchalik).
    """
    now = now or timezone.localtime()
    external_key = _streak_notification_key(timezone.localdate())
    previous_title = (
        Notification.objects.filter(recipient=user, external_key=external_key)
        .values_list("title", flat=True)
        .first()
    )
    notif, created = Notification.objects.update_or_create(
        recipient=user,
        external_key=external_key,
        defaults={
            "title": _TITLES[state],
            "message": pick_message(state, now),
            "icon": _ICONS[state],
            "url": "/users/dashboard/",
            "category": Notification.CATEGORY_STREAK,
            "is_read": False,
            "read_at": None,
        },
    )
    # Faqat holat o'zgarganda ro'yxatning tepasiga chiqsin. OS clock bir xil
    # timestamp qaytargan taqdirda ham boshqa eng yangi xabardan bir
    # mikrosoniya keyinga suramiz; shunda ordering tasodifiy bo'lmaydi.
    if not created and previous_title != _TITLES[state]:
        latest_other = (
            Notification.objects.filter(recipient=user)
            .exclude(pk=notif.pk)
            .order_by("-created_at", "-id")
            .values_list("created_at", flat=True)
            .first()
        )
        bubble_at = timezone.now()
        if latest_other and bubble_at <= latest_other:
            bubble_at = latest_other + timedelta(microseconds=1)
        Notification.objects.filter(pk=notif.pk).update(created_at=bubble_at)
    return notif


def mark_streak_done(user, now=None):
    """Malakali harakatdan keyin — nudge'ni tabrikka aylantiradi.

    `users.streak.record_activity` bugungi haqiqiy faollikdan keyin chaqiradi.
    """
    set_daily_streak_notification(user, STATE_DONE, now)


def classify(streak, today):
    """Seriya holatini undash uchun aniqlaydi (yoki None — undalmaydi)."""
    if streak.is_active_today(today):
        return None
    if streak.effective_current(today) > 0:
        return STATE_AT_RISK
    # Seriya buzilgan. Faqat haqiqatan seriya qurgan bo'lsa eslataмиз.
    if streak.current_streak < 1 or streak.last_activity_date is None:
        return None
    gap = (today - streak.last_activity_date).days
    if gap <= BROKEN_WINDOW_DAYS:
        return STATE_BROKEN
    if gap <= ABSENT_WINDOW_DAYS:
        return STATE_ABSENT
    return None  # butunlay ketgan — bezovta qilmaymiz


def send_streak_nudges(now=None):
    """Barcha mos o'quvchilarga kunlik mascot xabarini yuboradi.

    Idempotent: bir o'quvchi kuniga bitta seriya xabari oladi.
    Yuborilgan xabarlar sonini qaytaradi.
    """
    now = now or timezone.localtime()
    today = timezone.localdate()
    sent = 0

    streaks = (
        LearnerStreak.objects
        .filter(user__is_active=True, last_activity_date__isnull=False)
        .select_related("user")
    )
    for streak in streaks:
        state = classify(streak, today)
        if state is None:
            continue
        set_daily_streak_notification(streak.user, state, now)
        sent += 1
    return sent
