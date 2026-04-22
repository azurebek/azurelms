import base64
import datetime
from dataclasses import dataclass

from django.core.signing import BadSignature, Signer
from django.db import IntegrityError, transaction
from django.utils import timezone

from bot.models import TelegramLessonCheckIn, TelegramLessonSession
from cohorts.attendance_service import upsert_attendance_and_xp
from cohorts.models import Attendance, Cohort, Enrollment, enrollment_active_access_q
from courses.models import Lesson
from users.models import CustomUser, Notification


@dataclass
class ActionResult:
    ok: bool
    code: str
    message: str


@dataclass
class StartLessonResult(ActionResult):
    session: TelegramLessonSession | None = None
    lesson_index: int | None = None
    checkin_count: int = 0


@dataclass
class CheckInResult(ActionResult):
    session: TelegramLessonSession | None = None
    checkin_count: int = 0


@dataclass
class CloseLessonResult(ActionResult):
    session: TelegramLessonSession | None = None
    summary: dict | None = None


def get_user_role(telegram_id):
    user = CustomUser.objects.filter(telegram_id=telegram_id).first()
    if not user:
        return "Mehmon"
    if user.is_staff or user.is_superuser:
        return "Admin"
    is_student = Enrollment.objects.filter(enrollment_active_access_q(), student=user).exists()
    if is_student:
        return "Talaba"
    return "Mehmon"


def link_user_from_start_token(token, telegram_user_id, telegram_username=""):
    if not token:
        return ActionResult(ok=False, code="missing_token", message="Bog'lash tokeni topilmadi.")

    try:
        padded_token = token + "=" * ((4 - len(token) % 4) % 4)
        raw_token = base64.urlsafe_b64decode(padded_token.encode()).decode()
        signer = Signer()
        user_id = signer.unsign(raw_token)
    except (ValueError, BadSignature):
        return ActionResult(ok=False, code="invalid_token", message="Xatolik: havola yaroqsiz yoki buzilgan!")

    try:
        with transaction.atomic():
            user = CustomUser.objects.select_for_update().get(id=user_id)
            if user.telegram_id:
                return ActionResult(
                    ok=False,
                    code="already_linked",
                    message="Sizning profilingizga allaqachon Telegram hisob ulangan. O'zgartirish uchun adminga murojaat qiling.",
                )

            exists = CustomUser.objects.filter(telegram_id=telegram_user_id).exists()
            if exists:
                return ActionResult(
                    ok=False,
                    code="telegram_used",
                    message="Bu Telegram akkaunt boshqa o'quvchi profiliga ulangan!",
                )

            user.telegram_id = telegram_user_id
            user.telegram_username = telegram_username or user.telegram_username
            user.save(update_fields=["telegram_id", "telegram_username"])

            Notification.objects.get_or_create(
                recipient=user,
                external_key=f"telegram-linked-{user.id}-{telegram_user_id}",
                defaults={
                    "title": "Telegram hisobi ulandi",
                    "message": "Profilingiz Telegram botiga muvaffaqiyatli bog'landi.",
                    "icon": "telegram",
                    "url": "/users/settings/",
                    "category": Notification.CATEGORY_SYSTEM,
                },
            )
            return ActionResult(
                ok=True,
                code="success",
                message=f"Tabriklaymiz! Hisobingiz muvaffaqiyatli ulandi, {user.first_name or user.username}!",
            )
    except CustomUser.DoesNotExist:
        return ActionResult(ok=False, code="not_found", message="Foydalanuvchi topilmadi!")


def get_linked_user(telegram_user_id):
    return CustomUser.objects.filter(telegram_id=telegram_user_id).first()


def can_manage_cohort(user, cohort):
    return bool(
        user
        and (
            user.is_superuser
            or user.is_staff
            or cohort.course.instructor_id == user.id
        )
    )


def bind_chat_to_cohort(*, cohort_id, chat_id, chat_title, actor_telegram_id):
    actor = get_linked_user(actor_telegram_id)
    if not actor:
        return ActionResult(
            ok=False,
            code="actor_unlinked",
            message="Avval o'z profilingizni LMS dashboard orqali Telegramga ulang.",
        )

    cohort = Cohort.objects.select_related("course__instructor").filter(id=cohort_id).first()
    if not cohort:
        return ActionResult(ok=False, code="cohort_missing", message="Cohort topilmadi.")

    if not can_manage_cohort(actor, cohort):
        return ActionResult(
            ok=False,
            code="permission_denied",
            message="Bu cohortni Telegram guruhiga bog'lash huquqi sizda yo'q.",
        )

    occupied = Cohort.objects.filter(telegram_chat_id=chat_id).exclude(id=cohort.id).first()
    if occupied:
        return ActionResult(
            ok=False,
            code="chat_already_bound",
            message=f"Bu Telegram guruh allaqachon {occupied.name} cohortiga bog'langan.",
        )

    update_fields = []
    if cohort.telegram_chat_id != chat_id:
        cohort.telegram_chat_id = chat_id
        update_fields.append("telegram_chat_id")
    if cohort.telegram_chat_title != (chat_title or ""):
        cohort.telegram_chat_title = chat_title or ""
        update_fields.append("telegram_chat_title")
    if update_fields:
        cohort.save(update_fields=update_fields)

    return ActionResult(
        ok=True,
        code="bound",
        message=f"Telegram guruh {cohort.name} cohortiga muvaffaqiyatli bog'landi.",
    )


def get_bound_cohort(chat_id):
    return Cohort.objects.select_related("course__instructor").filter(telegram_chat_id=chat_id).first()


def ordered_cohort_lessons(cohort):
    return list(
        Lesson.objects.filter(module__course=cohort.course)
        .select_related("module")
        .order_by("module__order", "order", "id")
    )


def resolve_lesson_reference(cohort, lesson_ref):
    lessons = ordered_cohort_lessons(cohort)
    if not lessons:
        return None, None, ActionResult(ok=False, code="no_lessons", message="Bu cohort kursida hali darslar yo'q.")

    ref = (lesson_ref or "").strip().lower()
    if not ref:
        return None, None, ActionResult(
            ok=False,
            code="missing_lesson_ref",
            message="Dars raqamini kiriting. Masalan: /start_lesson 1 yoki /start_lesson next",
        )

    if ref == "next":
        today = timezone.localdate()
        for index, lesson in enumerate(lessons, start=1):
            already_marked = Attendance.objects.filter(
                enrollment__cohort=cohort,
                lesson=lesson,
                date=today,
            ).exists()
            if not already_marked:
                return lesson, index, None
        return None, None, ActionResult(
            ok=False,
            code="no_next_lesson",
            message="Bugun uchun navbatdagi dars topilmadi. Kerak bo'lsa aniq raqam bilan yuboring.",
        )

    if ref.startswith("id:") and ref[3:].isdigit():
        lesson_id = int(ref[3:])
        for index, lesson in enumerate(lessons, start=1):
            if lesson.id == lesson_id:
                return lesson, index, None
        return None, None, ActionResult(ok=False, code="lesson_missing", message="Berilgan lesson ID topilmadi.")

    if ref.isdigit():
        ordinal = int(ref)
        if 1 <= ordinal <= len(lessons):
            return lessons[ordinal - 1], ordinal, None
        lesson_by_id = next((lesson for lesson in lessons if lesson.id == ordinal), None)
        if lesson_by_id:
            index = lessons.index(lesson_by_id) + 1
            return lesson_by_id, index, None

    return None, None, ActionResult(
        ok=False,
        code="invalid_lesson_ref",
        message="Dars raqami noto'g'ri. Masalan: /start_lesson 1 yoki /start_lesson next",
    )


def start_lesson_session(*, chat_id, chat_title, actor_telegram_id, lesson_ref):
    cohort = get_bound_cohort(chat_id)
    if not cohort:
        return StartLessonResult(
            ok=False,
            code="chat_not_bound",
            message="Bu guruh hali cohortga bog'lanmagan. Avval /link_cohort <id> yuboring.",
        )

    actor = get_linked_user(actor_telegram_id)
    if not actor:
        return StartLessonResult(
            ok=False,
            code="actor_unlinked",
            message="Avval o'z profilingizni LMS dashboard orqali Telegramga ulang.",
        )

    if not can_manage_cohort(actor, cohort):
        return StartLessonResult(
            ok=False,
            code="permission_denied",
            message="Bu cohort uchun dars sessiyasini boshlash huquqi sizda yo'q.",
        )

    existing = (
        TelegramLessonSession.objects.select_related("cohort", "lesson")
        .filter(chat_id=chat_id, status=TelegramLessonSession.STATUS_OPEN)
        .first()
    )
    if existing:
        return StartLessonResult(
            ok=False,
            code="session_already_open",
            message=f"Hozir ochiq sessiya bor: {existing.lesson.title}. Avval /close_lesson bilan yopib oling.",
            session=existing,
            checkin_count=existing.checkins.count(),
        )

    lesson, lesson_index, error = resolve_lesson_reference(cohort, lesson_ref)
    if error:
        return StartLessonResult(ok=False, code=error.code, message=error.message)

    try:
        session = TelegramLessonSession.objects.create(
            cohort=cohort,
            lesson=lesson,
            chat_id=chat_id,
            chat_title=chat_title or cohort.telegram_chat_title,
            attendance_date=timezone.localdate(),
            started_by=actor,
        )
    except IntegrityError:
        existing = TelegramLessonSession.objects.filter(
            chat_id=chat_id,
            status=TelegramLessonSession.STATUS_OPEN,
        ).first()
        return StartLessonResult(
            ok=False,
            code="session_already_open",
            message=f"Hozir ochiq sessiya bor: {existing.lesson.title if existing else 'sessiya'}.",
            session=existing,
            checkin_count=existing.checkins.count() if existing else 0,
        )

    return StartLessonResult(
        ok=True,
        code="session_started",
        message="Davomat olish boshlandi.",
        session=session,
        lesson_index=lesson_index,
        checkin_count=0,
    )


def set_session_message_id(session_id, message_id):
    TelegramLessonSession.objects.filter(id=session_id).update(attendance_message_id=message_id)


def get_session_checkin_count(session_id):
    return TelegramLessonCheckIn.objects.filter(session_id=session_id).count()


def register_checkin(*, session_id, telegram_user_id, telegram_username=""):
    session = (
        TelegramLessonSession.objects.select_related("cohort", "lesson")
        .filter(id=session_id)
        .first()
    )
    if not session or session.status != TelegramLessonSession.STATUS_OPEN:
        return CheckInResult(
            ok=False,
            code="session_closed",
            message="Bu davomat sessiyasi yopilgan yoki topilmadi.",
        )

    user = get_linked_user(telegram_user_id)
    if not user:
        return CheckInResult(
            ok=False,
            code="user_unlinked",
            message="Avval LMS dashboard orqali Telegram hisobingizni ulang.",
            session=session,
            checkin_count=session.checkins.count(),
        )

    if telegram_username and user.telegram_username != telegram_username:
        user.telegram_username = telegram_username
        user.save(update_fields=["telegram_username"])

    enrollment = (
        Enrollment.objects.select_related("student")
        .filter(enrollment_active_access_q(), student=user, cohort=session.cohort)
        .first()
    )
    if not enrollment:
        return CheckInResult(
            ok=False,
            code="not_enrolled",
            message="Siz bu cohort uchun faol o'quvchi sifatida topilmadingiz.",
            session=session,
            checkin_count=session.checkins.count(),
        )

    checkin, created = TelegramLessonCheckIn.objects.get_or_create(
        session=session,
        enrollment=enrollment,
        defaults={
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username or "",
        },
    )

    if not created:
        return CheckInResult(
            ok=True,
            code="already_checked_in",
            message="Siz davomatga allaqachon belgilandingiz.",
            session=session,
            checkin_count=session.checkins.count(),
        )

    return CheckInResult(
        ok=True,
        code="checked_in",
        message="Davomatga muvaffaqiyatli belgilandingiz.",
        session=session,
        checkin_count=session.checkins.count(),
    )


def close_lesson_session(*, chat_id, actor_telegram_id):
    session = (
        TelegramLessonSession.objects.select_related("cohort", "lesson")
        .filter(chat_id=chat_id, status=TelegramLessonSession.STATUS_OPEN)
        .first()
    )
    if not session:
        return CloseLessonResult(
            ok=False,
            code="session_missing",
            message="Hozir ochiq dars sessiyasi topilmadi.",
        )

    actor = get_linked_user(actor_telegram_id)
    if not actor:
        return CloseLessonResult(
            ok=False,
            code="actor_unlinked",
            message="Avval o'z profilingizni LMS dashboard orqali Telegramga ulang.",
            session=session,
        )

    if not can_manage_cohort(actor, session.cohort):
        return CloseLessonResult(
            ok=False,
            code="permission_denied",
            message="Bu cohort uchun sessiyani yopish huquqi sizda yo'q.",
            session=session,
        )

    enrollments = list(
        Enrollment.objects.select_related("student")
        .filter(enrollment_active_access_q(), cohort=session.cohort)
        .order_by("student__first_name", "student__last_name", "student__username")
    )
    checkins = {
        item.enrollment_id: item
        for item in session.checkins.select_related("enrollment", "enrollment__student").all()
    }
    late_cutoff = session.started_at + datetime.timedelta(minutes=session.late_after_minutes)
    summary = {
        Attendance.STATUS_PRESENT: 0,
        Attendance.STATUS_PARTIAL: 0,
        Attendance.STATUS_ABSENT: 0,
        "total": len(enrollments),
    }

    for enrollment in enrollments:
        checkin = checkins.get(enrollment.id)
        if not checkin:
            status = Attendance.STATUS_ABSENT
        elif checkin.checked_in_at > late_cutoff:
            status = Attendance.STATUS_PARTIAL
        else:
            status = Attendance.STATUS_PRESENT

        upsert_attendance_and_xp(
            enrollment=enrollment,
            lesson=session.lesson,
            date=session.attendance_date,
            status=status,
            marked_by=actor,
        )
        summary[status] += 1

    session.status = TelegramLessonSession.STATUS_CLOSED
    session.closed_by = actor
    session.closed_at = timezone.now()
    session.save(update_fields=["status", "closed_by", "closed_at"])

    return CloseLessonResult(
        ok=True,
        code="session_closed",
        message="Davomat sessiyasi yopildi va attendance yozildi.",
        session=session,
        summary=summary,
    )
