"""Read-only, allowlisted self-report for the tutor; never a mastery record."""

from django.db import DatabaseError

from core.flags import flag_enabled
from users.models import UserOnboarding


def onboarding_context_enabled(user):
    return bool(
        getattr(user, "pk", None)
        and getattr(user, "ai_memory_enabled", False)
        and flag_enabled("ai_onboarding_context")
    )


def build_onboarding_context(user):
    if not onboarding_context_enabled(user):
        return ""
    try:
        profile = UserOnboarding.objects.filter(user_id=user.pk).values(
            "goal", "current_level"
        ).first()
    except DatabaseError:
        return ""
    if not profile:
        return ""
    # Never interpolate arbitrary stored text or `extra` into instructions.
    goal = dict(UserOnboarding.GOAL_CHOICES).get(profile["goal"])
    level = dict(UserOnboarding.LEVEL_CHOICES).get(profile["current_level"])
    if not goal and not level:
        return ""
    fields = []
    if goal:
        fields.append(f"Maqsad: {goal}.")
    if level:
        fields.append(f"O'zi bildirgan daraja: {level}.")
    return (
        "ONBOARDING — FOYDALANUVCHINING O'ZI BILDIRGAN MA'LUMOT:\n"
        + " ".join(fields)
        + "\nMisollar va izohning murakkabligini tanlashda hisobga ol. "
        "Bu tekshirilgan CEFR darajasi, baho yoki o'zlashtirish dalili emas. "
        "Joriy suhbatdagi tuzatish ustun; 'Bilmayman' uchun darajani taxmin qilma. "
        "Kursga kirish, baho yoki progress haqida bundan xulosa chiqarma.\n\n"
    )
