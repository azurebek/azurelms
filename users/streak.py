"""O'quv seriyasi (streak) — yagona canonical service.

Seriyaga tegishli BARCHA mantiq shu yerda. Adapterlar (dars tugatish, quiz,
vazifa, imtihon, davomat) faqat `record_activity` ni chaqiradi — o'zlari
seriya hisobini yuritmaydi. Bu qoida "adapter biznes qoidasini egallamaydi"
tamoyiliga rioya qiladi.

Seriya kun asosida: bir kun ichida qancha harakat qilinsa ham seriya bir
marta oshadi (idempotent). Ketma-ket kunlar seriyani oshiradi; bir kunlik
bo'shliq freeze bilan qoplansa seriya uziladi emas.
"""

from dataclasses import dataclass

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import LearnerStreak


@dataclass(frozen=True)
class StreakEvent:
    """`record_activity` natijasi."""

    outcome: str  # "started" | "extended" | "maintained_with_freeze" | "reset" | "already" | "ignored"
    current_streak: int
    longest_streak: int
    is_new_record: bool = False
    freezes_used: int = 0

    @property
    def changed(self):
        return self.outcome not in ("already", "ignored")


@transaction.atomic
def record_activity(user, on_date=None):
    """O'quvchining bir kunlik malakali faolligini qayd etadi.

    Kuniga bir marta ta'sir qiladi (idempotent). Bir nechta harakat bir
    kunda seriyani bir marta oshiradi.
    """
    on_date = on_date or timezone.localdate()

    streak, _ = LearnerStreak.objects.select_for_update().get_or_create(user=user)
    last = streak.last_activity_date

    # Birinchi faollik
    if last is None:
        event = _apply(streak, "started", on_date, new_current=1)
        _notify_done_if_today(user, on_date)
        return event

    # O'sha kun ichida takror harakat — seriya o'zgarmaydi
    if on_date == last:
        return _event(streak, "already")

    # O'tmishdagi (kech belgilangan) faollik seriyani orqaga surmaydi
    if on_date < last:
        return _event(streak, "ignored")

    gap = (on_date - last).days
    if gap == 1:
        # Ketma-ket kun
        event = _apply(streak, "extended", on_date, new_current=streak.current_streak + 1)
        _notify_done_if_today(user, on_date)
        return event

    # Bo'shliq bor: oradagi o'tkazib yuborilgan kunlar
    missed = gap - 1
    if missed <= streak.freezes_available:
        # Freeze bilan qoplanadi — seriya davom etadi
        event = _apply(
            streak,
            "maintained_with_freeze",
            on_date,
            new_current=streak.current_streak + 1,
            freezes_used=missed,
        )
        _notify_done_if_today(user, on_date)
        return event

    # Seriya uzildi — bugundan qayta boshlanadi
    event = _apply(streak, "reset", on_date, new_current=1)
    _notify_done_if_today(user, on_date)
    return event


def _notify_done_if_today(user, on_date):
    """Bugungi haqiqiy faollikda kunlik seriya bildirishnomasini tabrikка
    aylantiradi (agar nudge bo'lgan bo'lsa — o'sha o'zgaradi, yangisi emas).

    Faqat bugungi harakat uchun — kech belgilangan o'tmish sana bugungi
    bildirishnomaga tegmaydi. Side-effect yozuvi transaction commitidan
    keyin bajariladi.
    """
    if on_date != timezone.localdate():
        return
    from django.db import transaction
    from users.streak_nudge import mark_streak_done
    transaction.on_commit(lambda: mark_streak_done(user))


def _apply(streak, outcome, on_date, *, new_current, freezes_used=0):
    previous_longest = streak.longest_streak

    streak.current_streak = new_current
    streak.longest_streak = max(previous_longest, new_current)
    streak.total_active_days += 1
    streak.last_activity_date = on_date
    if freezes_used:
        streak.freezes_available -= freezes_used
        streak.freezes_used_total += freezes_used
    streak.save(update_fields=[
        "current_streak", "longest_streak", "total_active_days",
        "last_activity_date", "freezes_available", "freezes_used_total",
        "updated_at",
    ])
    return _event(
        streak,
        outcome,
        is_new_record=new_current > previous_longest and new_current > 1,
        freezes_used=freezes_used,
    )


def _event(streak, outcome, *, is_new_record=False, freezes_used=0):
    return StreakEvent(
        outcome=outcome,
        current_streak=streak.current_streak,
        longest_streak=streak.longest_streak,
        is_new_record=is_new_record,
        freezes_used=freezes_used,
    )


def grant_freeze(user, count=1):
    """Foydalanuvchiga freeze token beradi (mukofot yoki admin)."""
    streak, _ = LearnerStreak.objects.get_or_create(user=user)
    LearnerStreak.objects.filter(pk=streak.pk).update(
        freezes_available=F("freezes_available") + count
    )
    streak.refresh_from_db(fields=["freezes_available"])
    return streak.freezes_available


def streak_snapshot(user, today=None):
    """Ko'rsatish uchun read-only holat (yozmaydi)."""
    today = today or timezone.localdate()
    streak = LearnerStreak.objects.filter(user=user).first()
    if streak is None:
        return {
            "current": 0,
            "longest": 0,
            "active_today": False,
            "at_risk": False,
            "freezes": 0,
            "total_active_days": 0,
        }
    return {
        "current": streak.effective_current(today),
        "longest": streak.longest_streak,
        "active_today": streak.is_active_today(today),
        "at_risk": streak.at_risk(today),
        "freezes": streak.freezes_available,
        "total_active_days": streak.total_active_days,
    }
