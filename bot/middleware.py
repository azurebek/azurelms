"""Identity middleware — har update'da Telegram user → LMS user + rol.

Handler'lar `lms_user` va `lms_role` kwarg'larini qabul qilishi mumkin:

    async def handler(message, lms_user, lms_role): ...

Rollar: "admin" (is_staff/superuser), "teacher" (biror kursning instructori),
"student" (faol enrollment bor), "linked" (bog'langan, lekin rolsiz),
"guest" (bog'lanmagan).
"""

import asyncio
import time

from aiogram import BaseMiddleware
from aiogram.dispatcher.event.bases import UNHANDLED, CancelHandler, SkipHandler
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


class MetricsMiddleware(BaseMiddleware):
    """Har update'ning davomiyligi va natijasini o'lchaydi (T4).

    **Nega `IdentityMiddleware` dan tashqarida.** Identity har update'da 3 DB
    so'rovi qiladi (T5 ning mavzusi) va bu narx handler'ning o'zi qadar
    muhim. O'lchov identity'dan **tashqarida** turganda p95 foydalanuvchi
    haqiqatan kutgan vaqtni ko'rsatadi, uning bir qismini emas.

    **Nega xato bu yerda sanaladi.** aiogram o'zining `ErrorsMiddleware` ini
    eng tashqi qatlamga qo'yadi, ya'ni u bizdan **keyin** istisnoni ushlaydi.
    Shuning uchun handler xatosi bu middleware ichidan o'tib ketadi va u
    yerda ko'rinadi. `bot/routers/__init__.py::error_boundary` da qayta
    sanash ikki hisob bo'lardi.

    `SkipHandler`/`CancelHandler` — aiogram ning boshqaruv oqimi, xato emas:
    filtr mos kelmaganda tashlanadi. Ularni xato deb sanash bot ishlab
    turganda ham doimiy qizil chiroq berardi.
    """

    async def __call__(self, handler, event, data):
        from bot import metrics

        started = time.perf_counter()
        failed = False
        unhandled = False
        try:
            result = await handler(event, data)
            unhandled = result is UNHANDLED
            return result
        except (SkipHandler, CancelHandler, asyncio.CancelledError):
            raise
        except Exception:
            failed = True
            raise
        finally:
            metrics.METRICS.record(
                duration_ms=(time.perf_counter() - started) * 1000.0,
                failed=failed,
                unhandled=unhandled,
            )
            # Webhook rejimida yozuvni olib boradigan fon sikli yo'q, shuning
            # uchun u shu yerdan — oraliqqa bir marta — ilashtiriladi.
            # Polling rejimida bu darhol qaytadi.
            await metrics.maybe_flush()


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
