"""AI token-limit boshqaruvi: limit hal qilish, usage o'lchash, enforcement, reset/bonus.

Oyna: rolling 5 soat + haftalik (7 kun). Usage = messenger.AIResponseRun.total_tokens
yig'indisi (reset markeridan keyin). Limit = override → tarif → global default (+ bonus).
"""
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Min, Q, Sum
from django.utils import timezone

from .models import AISettings, AIPlanPolicy, AIUserAllowance, AIUsageResetEvent

User = get_user_model()

WINDOW_5H = timedelta(hours=5)
WINDOW_WEEK = timedelta(days=7)


@dataclass
class QuotaStatus:
    allowed: bool
    reason: str  # "", "blocked", "5h", "weekly", "exempt", "disabled"
    used_5h: int
    limit_5h: int
    used_weekly: int
    limit_weekly: int
    reset_5h_at: object = None
    reset_weekly_at: object = None

    @property
    def remaining_5h(self):
        return max(self.limit_5h - self.used_5h, 0)

    @property
    def remaining_weekly(self):
        return max(self.limit_weekly - self.used_weekly, 0)


def get_allowance(user):
    allowance, _ = AIUserAllowance.objects.get_or_create(user=user)
    return allowance


def _effective_plan(user):
    """Foydalanuvchining amaldagi tarifi — so'nggi faol enrollment plani (bo'lmasa None)."""
    from cohorts.models import Enrollment, enrollment_active_access_q

    enrollment = (
        Enrollment.objects.filter(enrollment_active_access_q(), student=user, plan__isnull=False)
        .select_related("plan")
        .order_by("-joined_at", "-id")
        .first()
    )
    return enrollment.plan if enrollment else None


def resolve_limits(user, *, allowance=None, settings_obj=None):
    """(limit_5h, limit_weekly) — override → tarif siyosati → global default."""
    allowance = allowance or get_allowance(user)
    settings_obj = settings_obj or AISettings.load()

    limit_5h = allowance.override_5h_token_limit
    limit_weekly = allowance.override_weekly_token_limit

    if limit_5h is None or limit_weekly is None:
        plan = _effective_plan(user)
        policy = None
        if plan is not None:
            policy = AIPlanPolicy.objects.filter(plan=plan, is_active=True).first()
        if limit_5h is None:
            limit_5h = policy.token_limit_5h if policy else settings_obj.default_5h_token_limit
        if limit_weekly is None:
            limit_weekly = policy.token_limit_weekly if policy else settings_obj.default_weekly_token_limit

    return int(limit_5h), int(limit_weekly)


def _window_usage(user, *, window, reset_at, now):
    """Rolling oynadagi token yig'indisi + (agar bor bo'lsa) oyna bo'shash vaqti."""
    from messenger.models import AIResponseRun

    since = now - window
    if reset_at and reset_at > since:
        since = reset_at
    rows = AIResponseRun.objects.filter(student=user, created_at__gte=since, total_tokens__gt=0)
    agg = rows.aggregate(total=Sum("total_tokens"), oldest=Min("created_at"))
    used = int(agg["total"] or 0)
    # oyna bo'shash vaqti: eng eski hisoblangan so'rov + oyna uzunligi (rolling)
    free_at = (agg["oldest"] + window) if agg["oldest"] else None
    return used, free_at


def get_quota_status(user) -> QuotaStatus:
    """Foydalanuvchining hozirgi kvota holati (bloklash qarori shu yerda)."""
    settings_obj = AISettings.load()
    now = timezone.now()

    if not settings_obj.enforcement_enabled:
        return QuotaStatus(True, "disabled", 0, 0, 0, 0)
    if settings_obj.exempt_staff and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)):
        return QuotaStatus(True, "exempt", 0, 0, 0, 0)

    allowance = get_allowance(user)
    if allowance.is_blocked:
        return QuotaStatus(False, "blocked", 0, 0, 0, 0)

    limit_5h, limit_weekly = resolve_limits(user, allowance=allowance, settings_obj=settings_obj)
    limit_5h += int(allowance.bonus_5h_tokens or 0)
    limit_weekly += int(allowance.bonus_weekly_tokens or 0)

    used_5h, free_5h = _window_usage(user, window=WINDOW_5H, reset_at=allowance.reset_5h_at, now=now)
    used_week, free_week = _window_usage(user, window=WINDOW_WEEK, reset_at=allowance.reset_weekly_at, now=now)

    reason = ""
    if used_week >= limit_weekly:
        reason = "weekly"
    elif used_5h >= limit_5h:
        reason = "5h"

    return QuotaStatus(
        allowed=(reason == ""),
        reason=reason,
        used_5h=used_5h,
        limit_5h=limit_5h,
        used_weekly=used_week,
        limit_weekly=limit_weekly,
        reset_5h_at=free_5h,
        reset_weekly_at=free_week,
    )


def limit_message(status: QuotaStatus) -> str:
    """Bloklangan foydalanuvchiga ko'rsatiladigan halol xabar."""
    if status.reason == "blocked":
        return "AI yordamchidan foydalanish administrator tomonidan vaqtincha to'xtatilgan."
    if status.reason == "weekly":
        when = status.reset_weekly_at
        tail = f" Taxminan {timezone.localtime(when):%d-%b %H:%M} da yangilanadi." if when else ""
        return f"Haftalik AI limitingiz tugadi.{tail} Keyinroq qayta urinib ko'ring 🙏"
    when = status.reset_5h_at
    tail = f" Taxminan {timezone.localtime(when):%H:%M} da yangilanadi." if when else ""
    return f"5 soatlik AI limitingiz tugadi.{tail} Biroz dam olib, keyin davom eting 🙂"


def build_usage_panel(user) -> dict:
    """Foydalanuvchiga ko'rsatiladigan AI foydalanish paneli (settings/dashboard uchun).

    get_quota_status'ni tayyor-shablon dict'ga aylantiradi: har oyna uchun
    used/limit/percent/remaining/reset_at + umumiy 'unlimited'/'blocked' bayroq.
    """
    status = get_quota_status(user)
    unlimited = status.reason in {"exempt", "disabled"}

    def pct(used, limit):
        return min(round(used / limit * 100), 100) if limit else 0

    return {
        "unlimited": unlimited,
        "blocked": status.reason == "blocked",
        "reason": status.reason,
        "session": {
            "used": status.used_5h,
            "limit": status.limit_5h,
            "percent": pct(status.used_5h, status.limit_5h),
            "remaining": status.remaining_5h,
            "reset_at": status.reset_5h_at,
        },
        "weekly": {
            "used": status.used_weekly,
            "limit": status.limit_weekly,
            "percent": pct(status.used_weekly, status.limit_weekly),
            "remaining": status.remaining_weekly,
            "reset_at": status.reset_weekly_at,
        },
    }


# ---------------------------------------------------------------- reset / bonus

def _scope_users(event: AIUsageResetEvent, *, active_since):
    """Reset/bonus qamragan foydalanuvchilar (bo'sh-yumaloq bo'lmasligi uchun
    faqat so'nggi faollar yoki allowance'i borlar)."""
    from cohorts.models import Enrollment

    qs = User.objects.all()
    if event.scope == AIUsageResetEvent.SCOPE_COHORT and event.cohort_id:
        student_ids = Enrollment.objects.filter(cohort_id=event.cohort_id).values_list("student_id", flat=True)
        qs = qs.filter(id__in=student_ids)
    elif event.scope == AIUsageResetEvent.SCOPE_PLAN and event.plan_id:
        student_ids = Enrollment.objects.filter(plan_id=event.plan_id).values_list("student_id", flat=True)
        qs = qs.filter(id__in=student_ids)
    elif event.scope != AIUsageResetEvent.SCOPE_ALL:
        return User.objects.none()

    # Bounded: so'nggi haftada AI ishlatganlar YOKI allowance'i borlar
    return qs.filter(
        Q(ai_response_runs__created_at__gte=active_since) | Q(ai_allowance__isnull=False)
    ).distinct()


def apply_reset_event(event: AIUsageResetEvent) -> int:
    """Reset/bonus'ni qamragan foydalanuvchilarga qo'llaydi, ta'sirlangan sonini qaytaradi."""
    now = timezone.now()
    users = _scope_users(event, active_since=now - WINDOW_WEEK)

    do_5h = event.window in (AIUsageResetEvent.WINDOW_5H, AIUsageResetEvent.WINDOW_BOTH)
    do_week = event.window in (AIUsageResetEvent.WINDOW_WEEKLY, AIUsageResetEvent.WINDOW_BOTH)

    count = 0
    for user in users.iterator():
        allowance = get_allowance(user)
        fields = []
        if event.kind == AIUsageResetEvent.KIND_RESET:
            if do_5h:
                allowance.reset_5h_at = now
                fields.append("reset_5h_at")
            if do_week:
                allowance.reset_weekly_at = now
                fields.append("reset_weekly_at")
        else:  # BONUS
            if do_5h:
                allowance.bonus_5h_tokens = (allowance.bonus_5h_tokens or 0) + int(event.bonus_tokens or 0)
                fields.append("bonus_5h_tokens")
            if do_week:
                allowance.bonus_weekly_tokens = (allowance.bonus_weekly_tokens or 0) + int(event.bonus_tokens or 0)
                fields.append("bonus_weekly_tokens")
        if fields:
            allowance.save(update_fields=fields + ["updated_at"])
            count += 1

            # Notification yaratish (post_save orqali Telegram outboxga ham oyna ulanadi)
            from users.models import Notification
            reason_str = f" Sabab: {event.reason}" if event.reason else ""
            if event.kind == AIUsageResetEvent.KIND_RESET:
                title = "AI limitlari yangilandi"
                if event.window == AIUsageResetEvent.WINDOW_BOTH:
                    msg = f"Sizning AzureAI yordamchisi uchun 5 soatlik va haftalik limitlaringiz yangilandi (foydalanish nolga tushirildi).{reason_str}"
                elif event.window == AIUsageResetEvent.WINDOW_5H:
                    msg = f"Sizning AzureAI yordamchisi uchun 5 soatlik limitlaringiz yangilandi.{reason_str}"
                else:
                    msg = f"Sizning AzureAI yordamchisi uchun haftalik limitlaringiz yangilandi.{reason_str}"
            else:  # BONUS
                title = "AI bonus tokenlari taqdim etildi"
                bonus_val = int(event.bonus_tokens or 0)
                if event.window == AIUsageResetEvent.WINDOW_BOTH:
                    msg = f"Sizga AzureAI uchun {bonus_val:,} ta 5 soatlik va haftalik bonus tokenlar taqdim etildi!{reason_str}"
                elif event.window == AIUsageResetEvent.WINDOW_5H:
                    msg = f"Sizga AzureAI uchun {bonus_val:,} ta 5 soatlik bonus tokenlar taqdim etildi!{reason_str}"
                else:
                    msg = f"Sizga AzureAI uchun {bonus_val:,} ta haftalik bonus tokenlar taqdim etildi!{reason_str}"

            Notification.objects.get_or_create(
                recipient=user,
                external_key=f"ai-limit-event-{event.id}-{user.id}",
                defaults={
                    "title": title,
                    "message": msg,
                    "icon": "cpu",
                    "url": "/users/settings/",
                    "category": Notification.CATEGORY_SYSTEM,
                }
            )

    event.affected_count = count
    event.save(update_fields=["affected_count"])
    return count

