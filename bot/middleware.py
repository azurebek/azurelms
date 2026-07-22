"""Identity middleware — har update'da Telegram user → LMS user + rol.

Handler'lar `lms_user` va `lms_role` kwarg'larini qabul qilishi mumkin:

    async def handler(message, lms_user, lms_role): ...

Rollar: "admin" (is_staff/superuser), "teacher" (biror kursning instructori),
"student" (faol enrollment bor), "linked" (bog'langan, lekin rolsiz),
"guest" (bog'lanmagan).
"""

from aiogram import BaseMiddleware
from asgiref.sync import sync_to_async


def resolve_identity(telegram_id):
    """Sync: telegram_id → (user|None, rol)."""
    from cohorts.models import Enrollment, enrollment_active_access_q
    from courses.models import Course
    from users.models import CustomUser

    user = CustomUser.objects.filter(telegram_id=telegram_id).first()
    if not user:
        return None, "guest"
    # O'chirilgan (bloklangan) hisob botda hech qanday huquq olmaydi.
    if not user.is_active:
        return None, "guest"
    if user.is_staff or user.is_superuser:
        return user, "admin"
    if Course.objects.filter(instructor=user).exists():
        return user, "teacher"
    if Enrollment.objects.filter(enrollment_active_access_q(), student=user).exists():
        return user, "student"
    return user, "linked"


class IdentityMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        telegram_user = data.get("event_from_user")
        if telegram_user is not None:
            user, role = await sync_to_async(resolve_identity)(telegram_user.id)
        else:
            user, role = None, "guest"
        data["lms_user"] = user
        data["lms_role"] = role
        return await handler(event, data)
