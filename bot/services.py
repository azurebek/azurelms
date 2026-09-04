import datetime
import logging
import re
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.html import strip_tags

from bot.models import BotGuest, TelegramLessonCheckIn, TelegramLessonSession
from cohorts.attendance_service import upsert_attendance_and_xp
from cohorts.models import Attendance, Cohort, Enrollment, enrollment_active_access_q
from courses.models import Course, Lesson
from users.models import CustomUser, Notification

logger = logging.getLogger(__name__)

GUEST_DEMO_QUESTION_LIMIT = 5


def is_active_staff(user):
    """Bot admin huquqi uchun yagona tekshiruv.

    O'chirilgan (deaktivatsiya qilingan) staff hisob admin sifatida
    qabul qilinmaydi — aks holda bloklangan xodim hali ham buyruq bera
    olardi.
    """
    return bool(user and user.is_active and (user.is_staff or user.is_superuser))


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
    # Ismli ro'yxatlar: {"present": [...], "partial": [...], "absent": [...]}
    # har element: {"name", "telegram_id", "telegram_username", "user_id"}
    details: dict | None = None


@dataclass
class SessionStatusResult(ActionResult):
    session: TelegramLessonSession | None = None
    checkin_count: int = 0
    checkin_names: list | None = None


def student_display_name(user):
    full = f"{user.first_name} {user.last_name}".strip()
    return full or user.username


def get_user_role(telegram_id):
    user = CustomUser.objects.filter(telegram_id=telegram_id).first()
    if not user:
        return "Mehmon"
    if is_active_staff(user):
        return "Admin"
    is_student = Enrollment.objects.filter(enrollment_active_access_q(), student=user).exists()
    if is_student:
        return "Talaba"
    return "Mehmon"


def link_user_from_start_token(token, telegram_user_id, telegram_username=""):
    if not token:
        return ActionResult(ok=False, code="missing_token", message="Bog'lash tokeni topilmadi.")

    from users.models import TelegramLinkToken

    link_token = TelegramLinkToken.objects.select_related("user").filter(token=token).first()
    if link_token is None:
        return ActionResult(ok=False, code="invalid_token", message="Xatolik: havola yaroqsiz yoki buzilgan!")
    if link_token.consumed_at is not None:
        return ActionResult(
            ok=False,
            code="used_token",
            message="Bu havola allaqachon ishlatilgan. Profil sahifasidan yangisini oling.",
        )
    if link_token.is_expired():
        return ActionResult(
            ok=False,
            code="expired_token",
            message="Havolaning muddati tugagan. Profil sahifasidan yangisini oling.",
        )
    user_id = link_token.user_id

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
            # Token bir martalik: muvaffaqiyatli ulanishdan keyin yopiladi.
            link_token.consume()

            Notification.objects.get_or_create(
                recipient=user,
                external_key=f"telegram-linked-{user.id}-{telegram_user_id}",
                defaults={
                    "title": "Telegram hisobi ulandi",
                    "message": "Profilingiz Telegram botiga muvaffaqiyatli bog'landi.",
                    "icon": "telegram",
                    "url": "/users/profile/",
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


def handle_telegram_auth_token(token, telegram_user_id, first_name="", last_name="", telegram_username=""):
    """Telegram orqali login/register qilish (Deep-link auth tokenini tasdiqlash)."""
    if not token or not token.startswith("auth_"):
        return ActionResult(ok=False, code="invalid_format", message="Noto'g'ri token formati.")

    auth_token = token[5:] # 'auth_' prefiksini olib tashlaymiz
    from users.models import TelegramAuthSession, CustomUser, Notification
    from django.db import transaction

    try:
        session = TelegramAuthSession.objects.get(token=auth_token)
    except TelegramAuthSession.DoesNotExist:
        return ActionResult(ok=False, code="not_found", message="Kirish sessiyasi topilmadi yoki eskirgan.")

    if not session.is_valid():
        return ActionResult(ok=False, code="expired", message="Sessiya vaqti tugagan. Iltimos, saytdan qayta urinib ko'ring.")

    try:
        with transaction.atomic():
            user = CustomUser.objects.filter(telegram_id=telegram_user_id).first()

            if user:
                # Login: user mavjud, sessiyaga ulaymiz
                session.user = user
                session.status = TelegramAuthSession.STATUS_AUTHENTICATED
                session.save(update_fields=['user', 'status'])
                return ActionResult(
                    ok=True,
                    code="login_success",
                    message="Tizimga kirish tasdiqlandi! Brauzeringizga qaytib, o'qishni davom ettiring 🚀"
                )
            else:
                # Register: yangi user yaratamiz
                email = f"tg_{telegram_user_id}@telegram.local"
                base_username = telegram_username or f"tg_{telegram_user_id}"
                username = base_username
                counter = 1
                while CustomUser.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1

                user = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    telegram_id=telegram_user_id,
                    telegram_username=telegram_username,
                )
                user.set_unusable_password()
                user.save()

                session.user = user
                session.status = TelegramAuthSession.STATUS_AUTHENTICATED
                session.save(update_fields=['user', 'status'])
                
                Notification.objects.create(
                    recipient=user,
                    external_key=f"telegram-auth-created-{user.id}",
                    title="Xush kelibsiz!",
                    message="Profilingiz Telegram orqali yaratildi va ulandi.",
                    icon="telegram",
                    url="/users/profile/",
                    category=Notification.CATEGORY_SYSTEM,
                )
                return ActionResult(
                    ok=True,
                    code="register_success",
                    message="Siz uchun yangi profil yaratildi va tizimga kirish tasdiqlandi! Brauzeringizga qayting 🚀"
                )
    except Exception as e:
        logger.exception("handle_telegram_auth_token xatosi: %s", str(e))
        return ActionResult(ok=False, code="server_error", message="Tizim xatoligi yuz berdi. Qayta urinib ko'ring.")



def can_manage_cohort(user, cohort):
    """Guruhni boshqarish huquqi — web bilan bir xil scope.

    Ilgari bu yerda `is_active_staff(user)` yetarli edi, ya'ni **har qanday
    faol staff har qanday guruhni** boshqara olardi: boshqa o'qituvchining
    davomat sessiyasini ocha va yopa, guruhini chatga bog'lay olardi.

    A0b/1 aynan shu default-allow'ni yopgan edi, lekin u yerda web paneli,
    `/guruhlarim` va `/baholash` ko'chirilgan — bu yordamchi esa eski
    qoidada qolib ketgan. Endi u ham `core/access.py` dagi canonical
    scope'ni chaqiradi: superuser hammasini, qolgan har kim faqat o'ziga
    instructor sifatida biriktirilgan kursning guruhini.
    """
    from core.access import teacher_cohort_queryset

    if not (user and user.is_active):
        return False
    return teacher_cohort_queryset(user).filter(pk=cohort.pk).exists()


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
    details = {
        Attendance.STATUS_PRESENT: [],
        Attendance.STATUS_PARTIAL: [],
        Attendance.STATUS_ABSENT: [],
    }

    # Butun yopish bitta tranzaksiyada: sikl o'rtasida uzilish yarim yozilgan
    # davomat va OPEN qolgan sessiyani qoldirardi — o'qituvchi "davomat
    # olindimi?" degan savolga javob topolmasdi.
    with transaction.atomic():
        # Ikkita bir vaqtdagi `/yopish` ni ketma-ketlashtiradi. `of=("self",)`
        # — faqat sessiya satri qulflanadi; `select_related` ichida nullable
        # bog'lanish paydo bo'lsa PostgreSQL yalang'och `FOR UPDATE` ni rad
        # etadi. SQLite'da bu no-op, ammo amallarning o'zi idempotent.
        locked_session = (
            TelegramLessonSession.objects.select_for_update(of=("self",))
            .filter(pk=session.pk, status=TelegramLessonSession.STATUS_OPEN)
            .first()
        )
        if locked_session is None:
            return CloseLessonResult(
                ok=False,
                code="session_missing",
                message="Bu sessiya allaqachon yopilgan.",
            )

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
            student = enrollment.student
            details[status].append(
                {
                    "name": student_display_name(student),
                    "telegram_id": student.telegram_id,
                    "telegram_username": student.telegram_username or "",
                    "user_id": student.id,
                }
            )

        session.status = TelegramLessonSession.STATUS_CLOSED
        session.closed_by = actor
        session.closed_at = timezone.now()
        session.save(update_fields=["status", "closed_by", "closed_at"])

        # Bildirishnoma ham shu yerda: yopilish qaytarilsa "darsni
        # qoldirdingiz" xabari ham qolmasligi kerak. Telegram'ga yuborish
        # baribir outbox orqali, ya'ni commitdan keyin.
        _notify_absent_students(session, details[Attendance.STATUS_ABSENT])

    return CloseLessonResult(
        ok=True,
        code="session_closed",
        message="Davomat sessiyasi yopildi va attendance yozildi.",
        session=session,
        summary=summary,
        details=details,
    )


def _notify_absent_students(session, absent_items):
    """Kelmaganlarga platforma-bildirishnoma (sayt qo'ng'irog'i). DM alohida — handler yuboradi."""
    lesson_url = f"/courses/{session.cohort.course_id}/lesson/{session.lesson_id}/"
    for item in absent_items:
        Notification.objects.get_or_create(
            recipient_id=item["user_id"],
            external_key=f"tg-absent-{session.id}",
            defaults={
                "title": "Darsni qoldirdingiz",
                "message": (
                    f"{session.attendance_date.strftime('%d.%m.%Y')} — "
                    f"\"{session.lesson.title}\" darsida davomatga belgilanmadingiz. "
                    f"Dars materialini ko'rib chiqing."
                ),
                "icon": "calendar-x",
                "url": lesson_url,
                "category": Notification.CATEGORY_SYSTEM,
            },
        )


def get_open_session_status(chat_id):
    """Guruhda /davomat — joriy ochiq sessiya holati."""
    session = (
        TelegramLessonSession.objects.select_related("cohort", "lesson")
        .filter(chat_id=chat_id, status=TelegramLessonSession.STATUS_OPEN)
        .first()
    )
    if not session:
        return SessionStatusResult(
            ok=False,
            code="session_missing",
            message="Hozir ochiq davomat sessiyasi yo'q. Boshlash: /dars <raqam>",
        )
    checkins = list(
        session.checkins.select_related("enrollment__student").order_by("checked_in_at")
    )
    names = [student_display_name(c.enrollment.student) for c in checkins]
    return SessionStatusResult(
        ok=True,
        code="session_open",
        message="Sessiya ochiq.",
        session=session,
        checkin_count=len(checkins),
        checkin_names=names,
    )


# ================================================================ F2: Onboarding (mehmon)

@dataclass
class GuestDemoResult(ActionResult):
    answer: str = ""
    remaining: int = 0


@dataclass
class PhoneRegisterResult(ActionResult):
    user: CustomUser | None = None
    created: bool = False


def list_public_courses():
    """Mehmonga ko'rsatiladigan faol kurslar (bot formatiga tayyor)."""
    level_labels = {"beginner": "Boshlang'ich", "intermediate": "O'rta", "advanced": "Yuqori"}
    items = []
    for course in Course.objects.filter(is_active=True).order_by("level", "title"):
        items.append(
            {
                "id": course.id,
                "title": course.title,
                "level": level_labels.get(course.level, course.level),
                "duration": course.duration,
                "price": int(course.price),
                "description": strip_tags(course.description or "")[:220].strip(),
            }
        )
    return items


def list_plans():
    """Faol tariflar + belgilangan xususiyatlar."""
    from subscriptions.catalog import purchase_plans

    items = []
    for plan in purchase_plans().prefetch_related("features"):
        items.append(
            {
                "id": plan.id,
                "name": plan.name,
                "price": int(plan.price),
                "is_popular": plan.is_popular,
                "features": [f.name for f in plan.features.all() if f.is_included][:6],
                "description": strip_tags(plan.description or "")[:160].strip(),
            }
        )
    return items


def _fmt_sum(value):
    return f"{value:,}".replace(",", " ")


def _build_demo_context():
    """AI demo uchun ixcham mahsulot-konteksti (kurslar + tariflar)."""
    course_lines = [
        f"- {c['title']} ({c['level']}, ~{c['duration']} soat, {_fmt_sum(c['price'])} so'm)"
        for c in list_public_courses()[:6]
    ]
    plan_lines = [f"- {p['name']}: {_fmt_sum(p['price'])} so'm/oy" for p in list_plans()[:4]]
    return (
        "Sen AzureLMS platformasining yordamchi konsultantisan. AzureLMS — o'zbek "
        "tilida turk tilini A1'dan C1'gacha o'rgatadigan onlayn platforma: video "
        "darslar, jonli guruh darslari, davomat, imtihonlar, sertifikat va AI repetitor bor.\n"
        + ("Kurslar:\n" + "\n".join(course_lines) + "\n" if course_lines else "")
        + ("Tariflar:\n" + "\n".join(plan_lines) + "\n" if plan_lines else "")
        + "Qoidalar: faqat o'zbekcha, qisqa (3-5 jumla), samimiy javob ber. Faqat platforma "
        "va turk tili o'rganish mavzusida gapir — boshqa mavzuga o'tma. Narx/kurs haqida "
        "yuqoridagi ma'lumotdan tashqarisini TO'QIMA; bilmasang ro'yxatdan o'tib aniqlashtirishni taklif qil."
    )


def guest_demo_answer(
    telegram_id,
    telegram_username,
    question,
    *,
    request_key=None,
    provider=None,
):
    """Mehmon uchun limitli AI savol-javob. Provider xatosi halol xabar bilan qaytadi."""
    question = (question or "").strip()
    if not question:
        return GuestDemoResult(ok=False, code="empty", message="Savol bo'sh.")
    if len(question) > 500:
        return GuestDemoResult(
            ok=False, code="too_long",
            message="Savol juda uzun — qisqaroq yozing (500 belgigacha).",
        )

    provider_injected = provider is not None
    if not provider_injected:
        from aicontrol.models import AISettings

        if not AISettings.load().guest_demo_enabled:
            return GuestDemoResult(
                ok=False,
                code="disabled",
                message=(
                    "AI demo hozircha o'chirilgan. Ro'yxatdan o'tib platformadagi "
                    "mavjud imkoniyatlardan foydalanishingiz mumkin."
                ),
            )

    guest, _ = BotGuest.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={"telegram_username": telegram_username or ""},
    )
    # Slot provider chaqiruvidan **oldin** band qilinadi va shartli `UPDATE`
    # bilan: `demo_questions_used < LIMIT` filtri faqat bitta so'rovda mos
    # keladi, ikkinchisi `0` qator yangilaydi.
    #
    # Ilgari bu yerda oddiy `if` bor edi va hisoblagich javobdan **keyin**
    # oshirilardi. Ikki savol bir vaqtda kelsa ikkalasi ham tekshiruvdan
    # o'tib, ikkalasiga ham javob berilardi — ya'ni mehmon chegaradan ortiq
    # bepul savol olardi. Tekshirish va band qilish bitta amalga birlashdi.
    from django.db.models import F

    claimed = BotGuest.objects.filter(
        pk=guest.pk, demo_questions_used__lt=GUEST_DEMO_QUESTION_LIMIT
    ).update(demo_questions_used=F("demo_questions_used") + 1)
    if not claimed:
        return GuestDemoResult(
            ok=False,
            code="limit_reached",
            message=(
                "Demo savollar tugadi. Ro'yxatdan o'tsangiz, AI repetitor bilan "
                "cheklovsiz suhbatlashasiz — /start bosib \"Ro'yxatdan o'tish\"ni tanlang."
            ),
        )
    guest.refresh_from_db(fields=["demo_questions_used"])

    prompt = f"{_build_demo_context()}\n\nMehmon savoli: {question}"
    try:
        if provider_injected:
            response = provider.generate(prompt=prompt)
        else:
            from ai.providers import get_chat_provider
            from aicontrol.models import AISupplyEvent
            from aicontrol.supply import execute_provider_call, fingerprint_request

            provider = get_chat_provider()
            response = execute_provider_call(
                provider,
                request_key=fingerprint_request(
                    "bot-guest",
                    request_key or question,
                    telegram_id,
                    guest.demo_questions_used,
                ),
                call_type=AISupplyEvent.CALL_BOT_GUEST,
                prompt=prompt,
                metadata={"guest_sequence": guest.demo_questions_used},
            )
        answer = (response.text or "").strip()
    except Exception:
        # Band qilingan slot qaytariladi: javob bermagan chaqiruv mehmonning
        # bepul savolini yeb qo'ymasligi kerak. `Greatest` bilan — bir vaqtda
        # kelgan boshqa bo'shatish hisoblagichni manfiyga tushirmasin.
        from django.db.models import Value
        from django.db.models.functions import Greatest

        BotGuest.objects.filter(pk=guest.pk).update(
            demo_questions_used=Greatest(F("demo_questions_used") - 1, Value(0))
        )
        return GuestDemoResult(
            ok=False,
            code="provider_error",
            message="Hozir javob bera olmadim — birozdan so'ng qayta urinib ko'ring.",
        )

    # Hisoblagich yuqorida, chaqiruvdan oldin oshirilgan — bu yerda faqat
    # profil ma'lumoti yangilanadi.
    if telegram_username and guest.telegram_username != telegram_username:
        guest.telegram_username = telegram_username
        guest.save(update_fields=["telegram_username", "updated_at"])

    return GuestDemoResult(
        ok=True,
        code="answered",
        message="OK",
        answer=answer,
        remaining=GUEST_DEMO_QUESTION_LIMIT - guest.demo_questions_used,
    )


def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:  # 901234567 → O'zbekiston raqami deb hisoblaymiz
        digits = "998" + digits
    return f"+{digits}" if digits else ""


def register_guest_via_phone(*, telegram_id, telegram_username, phone, first_name="", last_name=""):
    """Telefon-kontakt orqali ro'yxat: mavjud hisob bo'lsa bog'laydi, bo'lmasa yaratadi.

    Telefon Telegram tomonidan tasdiqlangan bo'lishi shart (handler
    contact.user_id == from_user.id ni tekshiradi).
    """
    phone = normalize_phone(phone)
    if not phone or len(phone) < 10:
        return PhoneRegisterResult(ok=False, code="bad_phone", message="Telefon raqam noto'g'ri ko'rinishda.")

    existing_tg = CustomUser.objects.filter(telegram_id=telegram_id).first()
    if existing_tg:
        return PhoneRegisterResult(
            ok=True, code="already_linked",
            message="Bu Telegram allaqachon hisobga ulangan.", user=existing_tg,
        )

    with transaction.atomic():
        user = CustomUser.objects.filter(phone_number=phone).first()
        if user:
            if user.telegram_id and user.telegram_id != telegram_id:
                return PhoneRegisterResult(
                    ok=False, code="phone_taken",
                    message="Bu raqamdagi hisob boshqa Telegram'ga ulangan. Yordam: /yordam",
                )
            user.telegram_id = telegram_id
            user.telegram_username = telegram_username or ""
            user.save(update_fields=["telegram_id", "telegram_username"])
            created = False
        else:
            base_username = f"user{phone.lstrip('+')}"
            username = base_username
            suffix = 1
            while CustomUser.objects.filter(username=username).exists():
                suffix += 1
                username = f"{base_username}-{suffix}"
            user = CustomUser.objects.create_user(
                username=username,
                # email unique=True — bo'sh qoldirib bo'lmaydi (ikkinchi ''-email
                # UNIQUE'ni buzadi). Username'dan deterministik placeholder;
                # user keyin sozlamalarda haqiqiy emailga almashtira oladi.
                email=f"{username}@telegram.azurelms.uz",
                phone_number=phone,
                first_name=(first_name or "")[:150],
                last_name=(last_name or "")[:150],
                telegram_id=telegram_id,
                telegram_username=telegram_username or "",
            )
            user.set_unusable_password()
            user.save(update_fields=["password"])
            created = True

    Notification.objects.create(
        recipient=user,
        title="Telegram orqali ro'yxatdan o'tdingiz" if created else "Telegram hisobi ulandi",
        message=(
            "AzureLMS'ga xush kelibsiz! Kurs tanlab o'qishni boshlashingiz mumkin."
            if created
            else "Telegram botingiz hisobingizga muvaffaqiyatli ulandi."
        ),
        icon="telegram",
        category=Notification.CATEGORY_SYSTEM,
    )
    return PhoneRegisterResult(
        ok=True,
        code="registered" if created else "linked",
        message="Ro'yxatdan o'tdingiz!" if created else "Hisobingiz ulandi!",
        user=user,
        created=created,
    )


# ================================================================ F3: O'quvchi workspace

TELEGRAM_AI_ROOM_NAME = "Telegram AI suhbati"

ATTENDANCE_STATUS_LABELS = {
    Attendance.STATUS_PRESENT: "✅ Keldi",
    Attendance.STATUS_PARTIAL: "🕒 Kech",
    Attendance.STATUS_ABSENT: "❌ Kelmadi",
}

ENROLLMENT_STATUS_LABELS = {
    "active": "Faol",
    "pending": "To'lov kutilmoqda",
    "frozen": "Muzlatilgan",
    "expired": "Muddati tugagan",
    "completed": "Tugallangan",
}


@dataclass
class TelegramAiResult(ActionResult):
    answer: str = ""


def student_overview(user):
    """Dashboard bilan BIR XIL hisob — users.views.build_student_enrollments qayta ishlatiladi."""
    from users.views import build_student_enrollments

    items = []
    for e in build_student_enrollments(user):
        items.append(
            {
                "course_id": e.cohort.course_id,
                "course": e.cohort.course.title,
                "cohort": e.cohort.name,
                "status": ENROLLMENT_STATUS_LABELS.get(
                    e.dashboard_effective_status, e.dashboard_effective_status
                ),
                "completed": e.dashboard_completed_lessons,
                "total": e.dashboard_total_lessons,
                "progress": e.dashboard_progress,
            }
        )
    return items


def student_recent_attendance(user, limit=10):
    records = (
        Attendance.objects.filter(enrollment__student=user)
        .select_related("lesson")
        .order_by("-date", "-id")[:limit]
    )
    return [
        {
            "date": r.date.strftime("%d.%m.%Y"),
            "lesson": r.lesson.title if r.lesson else "—",
            "status": ATTENDANCE_STATUS_LABELS.get(r.status, r.status),
        }
        for r in records
    ]


def student_payment_overview(user):
    items = []
    for e in user.enrollments.select_related("plan", "cohort__course").order_by("-joined_at"):
        items.append(
            {
                "course": e.cohort.course.title,
                "plan": e.plan.name if e.plan else "—",
                "status": ENROLLMENT_STATUS_LABELS.get(e.status, e.status),
                "last_payment": e.last_payment_date.strftime("%d.%m.%Y") if e.last_payment_date else "—",
                "next_deadline": (
                    e.next_payment_deadline.strftime("%d.%m.%Y") if e.next_payment_deadline else "—"
                ),
            }
        )
    return items


def get_or_create_telegram_ai_room(user):
    """Har userga bitta doimiy 'Telegram AI suhbati' xonasi.

    Nomi qat'iy — saytdagi AI suhbatlaridan ajralib turadi va lookup barqaror.
    """
    from messenger.models import ChatRoom

    room = (
        ChatRoom.objects.filter(
            room_type="ai", participants=user, name=TELEGRAM_AI_ROOM_NAME
        )
        .order_by("id")
        .first()
    )
    if room is None:
        from messenger.access import create_user_ai_room

        room = create_user_ai_room(user)
        room.name = TELEGRAM_AI_ROOM_NAME
        room.save(update_fields=["name"])
    return room


def telegram_ai_reply(user, text):
    """Bog'langan user matni → messenger AI engine (skills, xotira, kvota — hammasi).

    Sayt bilan bitta engine: generate_ai_response o'zi kvota tekshiradi
    (aicontrol, fail-open), xotira/RAG ishlatadi. Suhbat saytdagi messenger'da
    'Telegram AI suhbati' xonasi sifatida ko'rinadi.
    """
    text = (text or "").strip()
    if not text:
        return TelegramAiResult(ok=False, code="empty", message="Xabar bo'sh.")

    from messenger.models import Message
    from messenger.signals import suppress_ai_signal
    from messenger.tasks import generate_ai_response

    room = get_or_create_telegram_ai_room(user)
    with suppress_ai_signal():
        user_message = Message.objects.create(room=room, sender=user, text=text)

    try:
        ai_message_id = generate_ai_response.run(
            room_id=room.id,
            student_id=user.id,
            user_question=text,
            user_message_id=user_message.id,
        )
    except Exception:
        return TelegramAiResult(
            ok=False,
            code="engine_error",
            message="Hozir javob bera olmadim — birozdan so'ng qayta urinib ko'ring.",
        )

    ai_message = Message.objects.filter(id=ai_message_id).first() if ai_message_id else None
    if not ai_message or not (ai_message.text or "").strip():
        return TelegramAiResult(
            ok=False,
            code="empty_answer",
            message="Javob tayyorlanmadi — birozdan so'ng qayta urinib ko'ring.",
        )
    return TelegramAiResult(ok=True, code="answered", message="OK", answer=ai_message.text)


# ================================================================ F3.5: Kursga yozilish

@dataclass
class EnrollBeginResult(ActionResult):
    course_title: str = ""
    plan_name: str = ""
    amount: int = 0
    card_number: str = ""
    card_holder: str = ""
    period_start: str = ""
    period_end: str = ""


@dataclass
class ReceiptSubmitResult(ActionResult):
    receipt_id: int | None = None
    course_title: str = ""
    amount: int = 0


def _checkout_period(enrollment, today=None):
    """Eski adapter API; billing qoidasi canonical servisda."""
    from cohorts.checkout_service import checkout_period

    return checkout_period(enrollment, today=today)


def begin_course_enrollment(user, course_id, plan_id):
    """Kurs+tarif tanlandi → pending enrollment + to'lov rekvizitlari.

    Sayt bilan bitta servis: resolve_checkout_enrollment kohortni o'zi tanlaydi,
    mavjud enrollmentni qayta ishlatadi (dublikat ochilmaydi).
    """
    from cohorts.checkout_service import (
        CheckoutUnavailable,
        mark_checkout_started,
        resolve_checkout_enrollment,
    )
    from cohorts.models import PaymentReceipt, PendingReceiptExists
    from frontend.models import SiteSettings
    from subscriptions.models import Plan
    from subscriptions.catalog import purchase_plans
    from django.core.exceptions import ValidationError

    course = Course.objects.filter(id=course_id, is_active=True).first()
    if not course:
        return EnrollBeginResult(ok=False, code="course_missing", message="Kurs topilmadi yoki faol emas.")
    plan = purchase_plans(student=user, course=course).filter(id=plan_id).first()
    if not plan:
        return EnrollBeginResult(ok=False, code="plan_missing", message="Tarif topilmadi.")

    try:
        enrollment, _created, _cohort = resolve_checkout_enrollment(student=user, course=course, plan=plan)
    except (CheckoutUnavailable, ValidationError) as exc:
        return EnrollBeginResult(ok=False, code="unavailable", message=str(exc))

    if PaymentReceipt.objects.filter(enrollment=enrollment, is_verified=False).exists():
        return EnrollBeginResult(
            ok=False,
            code="pending_receipt",
            message=(
                "Sizda tasdiqlanmagan to'lov cheki bor — administrator ko'rib chiqishini kuting. "
                "Holat: /tolov"
            ),
        )

    try:
        mark_checkout_started(enrollment, plan=plan)
    except PendingReceiptExists:
        return EnrollBeginResult(ok=False, code="pending_receipt", message="Tasdiqlanmagan chek mavjud. Qarorni kuting.")
    except ValidationError as exc:
        return EnrollBeginResult(ok=False, code="unavailable", message=" ".join(exc.messages))

    start, end = _checkout_period(enrollment)
    site = SiteSettings.load()
    return EnrollBeginResult(
        ok=True,
        code="begun",
        message="Tarif tanlandi.",
        course_title=course.title,
        plan_name=plan.name,
        amount=int(plan.price),
        card_number=site.payment_card_number or "",
        card_holder=site.payment_card_holder or "",
        period_start=start.strftime("%d.%m.%Y"),
        period_end=end.strftime("%d.%m.%Y"),
    )


@transaction.atomic
def submit_payment_receipt(user, receipt_image):
    """Telegram'dan kelgan chek rasmi → PaymentReceipt (sayt bilan bitta servis).

    Nishon: tarifi tanlangan, tasdiqlanmagan cheki yo'q eng so'nggi enrollment
    (begin_course_enrollment'dan keyingi holat).
    """
    from cohorts.models import PendingReceiptExists
    from subscriptions.promo_service import create_checkout_receipt_with_promo
    from cohorts.delivery_service import lock_enrollment
    from django.core.exceptions import ValidationError

    # Nishon taxmin qilinmaydi: foydalanuvchi `/yozilish` da (yoki saytdagi
    # checkout formasida) qaysi enrollment uchun to'lov boshlaganini
    # `checkout_started_at` yozib qo'yadi. Ilgari bu yerda "eng oxirgi
    # qo'shilgan enrollment" olinardi va ikkita kursi bor o'quvchining puli
    # noto'g'ri kursga tushardi.
    enrollment = (
        user.enrollments.select_related("pending_plan", "cohort__course")
        .filter(pending_plan__isnull=False, checkout_started_at__isnull=False)
        .exclude(receipts__is_verified=False)
        .order_by("-checkout_started_at", "-id")
        .first()
    )
    if enrollment is None:
        has_pending = user.enrollments.filter(receipts__is_verified=False).exists()
        if has_pending:
            return ReceiptSubmitResult(
                ok=False,
                code="pending_receipt",
                message="Oldingi chekingiz hali tasdiqlanmagan — administrator ko'rib chiqishini kuting.",
            )
        return ReceiptSubmitResult(
            ok=False,
            code="no_target",
            message="Avval kurs va tarifni tanlang: /yozilish",
        )

    enrollment = lock_enrollment(enrollment.pk)
    if enrollment.pending_plan_id is None:
        return ReceiptSubmitResult(ok=False, code="no_target", message="Avval kurs va tarifni tanlang: /yozilish")
    start, end = _checkout_period(enrollment)
    try:
        receipt, _quote, _redemption = create_checkout_receipt_with_promo(
            enrollment=enrollment,
            plan=enrollment.pending_plan,
            receipt_image=receipt_image,
            period_start=start,
            period_end=end,
        )
    except PendingReceiptExists:
        # Yuqoridagi tanlov bilan yozuv orasida boshqa yuborish ulgurdi
        # (masalan ikkita rasm ketma-ket). Baza cheklovi ikkinchisini rad etdi.
        return ReceiptSubmitResult(
            ok=False,
            code="pending_receipt",
            message="Oldingi chekingiz hali tasdiqlanmagan — administrator ko'rib chiqishini kuting.",
        )
    except ValidationError as exc:
        return ReceiptSubmitResult(ok=False, code="unavailable", message=" ".join(exc.messages))
    return ReceiptSubmitResult(
        ok=True,
        code="submitted",
        message="Chek qabul qilindi.",
        receipt_id=receipt.id,
        course_title=enrollment.cohort.course.title,
        amount=int(receipt.amount),
    )


# ================================================================ F4: O'qituvchi / Admin

def teacher_cohorts_overview(user):
    """O'qituvchining guruhlari: o'quvchi soni, Telegram bog'lanishi, oxirgi sessiya."""
    # Scope canonical: `core.access.teacher_cohort_queryset()`. Ilgari bu yerda
    # teskari qoida turardi — har qanday active staff barcha guruhlarni ko'rardi
    # va faqat staff bo'lmagan instructor o'z kursi bilan cheklanardi (A0b).
    from core.access import teacher_cohort_queryset

    cohorts = (
        teacher_cohort_queryset(user)
        .filter(is_active=True)
        .select_related("course")
        .order_by("course__title", "name")
    )

    items = []
    for cohort in cohorts:
        last_session = (
            TelegramLessonSession.objects.filter(cohort=cohort)
            .order_by("-started_at")
            .first()
        )
        items.append(
            {
                "id": cohort.id,
                "name": cohort.name,
                "course": cohort.course.title,
                "students": Enrollment.objects.filter(
                    enrollment_active_access_q(), cohort=cohort
                ).count(),
                "tg_bound": bool(getattr(cohort, "telegram_chat_id", None)),
                "last_session": (
                    last_session.attendance_date.strftime("%d.%m.%Y") if last_session else None
                ),
            }
        )
    return items


def teacher_grading_queue(user, limit=8):
    """Baholash kutayotgan ishlar — canonical scope + teacher_views helper'lari."""
    from core.access import teacher_course_queryset
    from core.teacher_views import (
        _pending_assignment_submissions,
        _pending_exam_attempts,
    )

    courses = teacher_course_queryset(user)
    exams = list(_pending_exam_attempts(courses)[:limit])
    assignments = list(_pending_assignment_submissions(courses)[:limit])
    return {
        "exam_count": _pending_exam_attempts(courses).count(),
        "assignment_count": _pending_assignment_submissions(courses).count(),
        "exams": [
            {
                "student": student_display_name(a.student),
                "title": a.exam.title,
                "course": a.exam.course.title,
            }
            for a in exams
        ],
        "assignments": [
            {
                "student": student_display_name(s.student),
                "title": s.assignment.title,
                "course": s.assignment.lesson.module.course.title,
            }
            for s in assignments
        ],
    }


def admin_stats():
    from cohorts.models import PaymentReceipt

    today = timezone.localdate()
    return {
        "students": CustomUser.objects.filter(is_staff=False, is_superuser=False).count(),
        "active_enrollments": Enrollment.objects.filter(enrollment_active_access_q()).count(),
        "pending_enrollments": Enrollment.objects.filter(status=Enrollment.STATUS_PENDING).count(),
        "unverified_receipts": PaymentReceipt.objects.filter(is_verified=False).count(),
        "guests": BotGuest.objects.count(),
        "today_checkins": TelegramLessonCheckIn.objects.filter(
            checked_in_at__date=today
        ).count(),
    }


def pending_receipts(limit=5):
    from cohorts.models import PaymentReceipt

    receipts = (
        PaymentReceipt.objects.filter(is_verified=False)
        .select_related("enrollment__student", "enrollment__cohort__course", "enrollment__plan")
        .order_by("submitted_at")[:limit]
    )
    return [
        {
            "id": r.id,
            "student": student_display_name(r.enrollment.student),
            "course": r.enrollment.cohort.course.title,
            "plan": r.plan_label,
            "amount": int(r.amount),
            "submitted": r.submitted_at.strftime("%d.%m %H:%M"),
            "image_path": r.receipt_image.path if r.receipt_image else None,
        }
        for r in receipts
    ]


def verify_receipt(receipt_id, actor):
    """Telegram adapteri — qaror `cohorts/receipt_service.py` da.

    Ilgari butun mantiq shu yerda edi, ya'ni pulga tegadigan yagona qaror
    adapter ichida turardi va web tomonida umuman yo'q edi.
    """
    from aicontrol.models import SystemAuditEvent
    from cohorts.receipt_service import verify_receipt as _verify

    decision = _verify(receipt_id, actor, source=SystemAuditEvent.SOURCE_BOT)
    return ActionResult(ok=decision.ok, code=decision.code, message=decision.message)


def reject_receipt(receipt_id, actor):
    """Telegram adapteri — qaror `cohorts/receipt_service.py` da."""
    from aicontrol.models import SystemAuditEvent
    from cohorts.receipt_service import reject_receipt as _reject

    decision = _reject(receipt_id, actor, source=SystemAuditEvent.SOURCE_BOT)
    return ActionResult(ok=decision.ok, code=decision.code, message=decision.message)


# ================================================================ F8: Botda o'qish (dars-yetkazish)

import html as _html
import re as _re


def html_to_text(raw):
    """CKEditor HTML → Telegram uchun oddiy matn (abzatslar saqlanadi)."""
    text = raw or ""
    text = _re.sub(r"<\s*(br|/p|/li|/h[1-6]|/div)\s*/?\s*>", "\n", text, flags=_re.I)
    text = _re.sub(r"<\s*li[^>]*>", "• ", text, flags=_re.I)
    text = strip_tags(text)
    text = _html.unescape(text)
    text = _re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


@dataclass
class LessonOpenResult(ActionResult):
    lesson: dict | None = None


def _course_enrollment_and_access(user, course):
    from courses.views import _build_lesson_access_bundle, _get_active_enrollment_for_course

    enrollment = _get_active_enrollment_for_course(user, course)
    bundle = _build_lesson_access_bundle(course, user, enrollment)
    return enrollment, bundle


def student_course_map(user, course_id):
    """Kursning modul→dars xaritasi (✅ o'tilgan / 🔒 qulf holatlari bilan)."""
    from courses.models import LessonProgress

    course = Course.objects.filter(id=course_id, is_active=True).first()
    if not course:
        return None
    enrollment, bundle = _course_enrollment_and_access(user, course)

    completed_ids = set()
    if enrollment:
        completed_ids = set(
            LessonProgress.objects.filter(
                enrollment=enrollment, is_completed=True
            ).values_list("lesson_id", flat=True)
        )

    modules = {}
    for lesson in bundle["lessons"]:
        state = bundle["lesson_access_map"].get(lesson.id, {})
        modules.setdefault(lesson.module.title, []).append(
            {
                "id": lesson.id,
                "title": lesson.title,
                "completed": lesson.id in completed_ids,
                "locked": not state.get("is_accessible", True),
                "lock_reason": state.get("lock_reason", ""),
            }
        )
    return {"course_id": course.id, "course": course.title, "modules": modules}


def student_open_lesson(user, lesson_id):
    """Darsni botda ochish. Sayt bilan bir xil: ochish = LessonProgress completed.

    Qulf mantig'i ham sayt bilan bitta (_build_lesson_access_bundle).
    """
    from courses.views import _mark_lesson_progress_completed

    lesson = (
        Lesson.objects.select_related("module__course")
        .filter(id=lesson_id, module__course__is_active=True)
        .first()
    )
    if not lesson:
        return LessonOpenResult(ok=False, code="missing", message="Dars topilmadi.")
    course = lesson.module.course

    enrollment, bundle = _course_enrollment_and_access(user, course)
    state = bundle["lesson_access_map"].get(lesson.id, {})
    if not state.get("is_accessible", True):
        return LessonOpenResult(
            ok=False,
            code="locked",
            message=f"🔒 {state.get('lock_reason') or 'Bu dars hozircha yopiq.'}",
        )
    if not enrollment:
        return LessonOpenResult(
            ok=False, code="not_enrolled",
            message="Bu kursga faol obunangiz yo'q. Yozilish: /yozilish",
        )

    _mark_lesson_progress_completed(enrollment, lesson)

    return LessonOpenResult(
        ok=True,
        code="opened",
        message="OK",
        lesson={
            "id": lesson.id,
            "title": lesson.title,
            "module": lesson.module.title,
            "course_id": course.id,
            "course": course.title,
            "video_url": lesson.video_url or "",
            "content": html_to_text(lesson.content or ""),
            "assignments": lesson.assignments.count(),
            "quizzes": lesson.quizzes.count(),
        },
    )


# ---------------------------------------------------------------- F9: vazifa va quiz

@dataclass
class AssignmentPromptResult(ActionResult):
    assignment: dict | None = None


@dataclass
class QuizStepResult(ActionResult):
    question: dict | None = None
    finished: bool = False
    score: float = 0.0
    total_correct: int = 0
    total_questions: int = 0
    xp_earned: int = 0
    quiz_title: str = ""


def get_pending_action(user):
    from bot.models import BotPendingAction

    return BotPendingAction.objects.filter(user=user).first()


def clear_pending_action(user):
    from bot.models import BotPendingAction

    BotPendingAction.objects.filter(user=user).delete()


def _lesson_access_ok(user, lesson):
    """Dars ochiqmi? (sayt qulf mantig'i)"""
    course = lesson.module.course
    enrollment, bundle = _course_enrollment_and_access(user, course)
    state = bundle["lesson_access_map"].get(lesson.id, {})
    return enrollment is not None and state.get("is_accessible", True)


def lesson_assignments(user, lesson_id):
    """Dars vazifalari + har birining topshirish holati."""
    from courses.models import Assignment, AssignmentSubmission

    lesson = Lesson.objects.select_related("module__course").filter(id=lesson_id).first()
    if not lesson:
        return None
    submissions = {
        s.assignment_id: s
        for s in AssignmentSubmission.objects.filter(
            student=user, assignment__lesson_id=lesson_id
        )
    }
    status_labels = {
        AssignmentSubmission.STATUS_PENDING: "⏳ Tekshiruvda",
        AssignmentSubmission.STATUS_APPROVED: "✅ Tasdiqlangan",
        AssignmentSubmission.STATUS_NEEDS_REVISION: "🔁 Qayta ishlash kerak",
    }
    items = []
    for assignment in Assignment.objects.filter(lesson_id=lesson_id).order_by("id"):
        submission = submissions.get(assignment.id)
        items.append(
            {
                "id": assignment.id,
                "title": assignment.title,
                "max_xp": assignment.max_xp,
                "status": status_labels.get(submission.status) if submission else "",
                "feedback": submission.teacher_feedback if submission else "",
                "awarded_xp": submission.awarded_xp if submission else 0,
            }
        )
    return {"lesson": lesson.title, "lesson_id": lesson.id, "assignments": items}


def start_assignment_answer(user, assignment_id):
    """Vazifa shartini berib, javob kutish holatini yozadi."""
    from bot.models import BotPendingAction
    from courses.models import Assignment

    assignment = (
        Assignment.objects.select_related("lesson__module__course")
        .filter(id=assignment_id)
        .first()
    )
    if not assignment:
        return AssignmentPromptResult(ok=False, code="missing", message="Vazifa topilmadi.")
    if not _lesson_access_ok(user, assignment.lesson):
        return AssignmentPromptResult(
            ok=False, code="locked", message="Bu dars siz uchun ochiq emas."
        )

    BotPendingAction.objects.update_or_create(
        user=user,
        defaults={
            "kind": BotPendingAction.KIND_ASSIGNMENT,
            "target_id": assignment.id,
            "data": {},
        },
    )
    return AssignmentPromptResult(
        ok=True,
        code="prompt",
        message="OK",
        assignment={
            "id": assignment.id,
            "title": assignment.title,
            "description": html_to_text(assignment.description or ""),
            "max_xp": assignment.max_xp,
            "lesson_id": assignment.lesson_id,
        },
    )


def submit_assignment_answer(user, assignment_id, *, text="", attachment=None):
    """Javobni saqlash — sayt bilan bitta servis (courses.submission_service)."""
    from courses.models import Assignment
    from courses.submission_service import submit_assignment

    assignment = (
        Assignment.objects.select_related("lesson__module__course")
        .filter(id=assignment_id)
        .first()
    )
    if not assignment:
        return ActionResult(ok=False, code="missing", message="Vazifa topilmadi.")

    result = submit_assignment(
        user=user, assignment=assignment, answer_text=text, attachment=attachment
    )
    if result.ok:
        clear_pending_action(user)
        return ActionResult(
            ok=True,
            code="submitted",
            message=(
                f"✅ Vazifa yuborildi: <b>{assignment.title}</b>\n"
                f"O'qituvchi tekshirgach xabar beramiz. Holat: /darslarim"
            ),
        )
    return ActionResult(ok=False, code=result.code, message=result.message)


def _quiz_question_payload(quiz, index):
    questions = list(quiz.questions.prefetch_related("choices").order_by("id"))
    if index >= len(questions):
        return None
    question = questions[index]
    return {
        "index": index,
        "total": len(questions),
        "id": question.id,
        "text": question.text,
        "choices": [
            {"id": c.id, "text": c.text} for c in question.choices.all().order_by("id")
        ],
    }


def start_quiz(user, quiz_id):
    """Quizni boshlash — birinchi savolni beradi, holatni yozadi."""
    from bot.models import BotPendingAction
    from courses.models import Quiz

    quiz = (
        Quiz.objects.select_related("lesson__module__course")
        .filter(id=quiz_id, lesson__isnull=False)
        .first()
    )
    if not quiz:
        return QuizStepResult(ok=False, code="missing", message="Quiz topilmadi.")
    if not _lesson_access_ok(user, quiz.lesson):
        return QuizStepResult(ok=False, code="locked", message="Bu dars siz uchun ochiq emas.")

    payload = _quiz_question_payload(quiz, 0)
    if payload is None:
        return QuizStepResult(ok=False, code="empty", message="Bu quizda savollar yo'q.")

    BotPendingAction.objects.update_or_create(
        user=user,
        defaults={
            "kind": BotPendingAction.KIND_QUIZ,
            "target_id": quiz.id,
            "data": {"index": 0, "answers": {}},
        },
    )
    return QuizStepResult(
        ok=True, code="question", message="OK", question=payload, quiz_title=quiz.title
    )


def answer_quiz_question(user, quiz_id, question_id, choice_id):
    """Javobni yozib keyingi savolga o'tadi; oxirida grade_quiz bilan baholaydi."""
    from bot.models import BotPendingAction
    from courses.models import Quiz
    from courses.submission_service import grade_quiz

    pending = BotPendingAction.objects.filter(
        user=user, kind=BotPendingAction.KIND_QUIZ, target_id=quiz_id
    ).first()
    if not pending:
        return QuizStepResult(
            ok=False, code="no_session",
            message="Quiz sessiyasi topilmadi — qaytadan boshlang.",
        )
    quiz = Quiz.objects.select_related("lesson__module__course").filter(id=quiz_id).first()
    if not quiz:
        return QuizStepResult(ok=False, code="missing", message="Quiz topilmadi.")

    answers = dict(pending.data.get("answers") or {})
    answers[str(question_id)] = int(choice_id)
    next_index = int(pending.data.get("index") or 0) + 1

    payload = _quiz_question_payload(quiz, next_index)
    if payload is not None:
        pending.data = {"index": next_index, "answers": answers}
        pending.save(update_fields=["data", "updated_at"])
        return QuizStepResult(
            ok=True, code="question", message="OK", question=payload, quiz_title=quiz.title
        )

    # Oxirgi savol — baholash
    result = grade_quiz(user=user, quiz=quiz, answers=answers)
    clear_pending_action(user)
    if not result.ok:
        return QuizStepResult(ok=False, code=result.code, message=result.message)
    return QuizStepResult(
        ok=True,
        code="finished",
        message="OK",
        finished=True,
        score=result.score,
        total_correct=result.total_correct,
        total_questions=result.total_questions,
        xp_earned=result.xp_earned,
        quiz_title=quiz.title,
    )


def lesson_quizzes(user, lesson_id):
    from courses.models import Quiz

    return [
        {"id": q.id, "title": q.title, "xp": q.xp_reward, "questions": q.questions.count()}
        for q in Quiz.objects.filter(lesson_id=lesson_id).order_by("id")
    ]


def parse_start_payload(payload):
    """Deep-link payload: 'dars_12' → ("lesson", 12); aks holda ("token", payload)."""
    text = (payload or "").strip()
    match = _re.fullmatch(r"dars_(\d+)", text)
    if match:
        return ("lesson", int(match.group(1)))
    return ("token", text) if text else ("none", None)


# ================================================================ F6: Admin kengaytmasi

def _require_admin(actor):
    return is_active_staff(actor)


def admin_search_users(query, limit=5):
    """Ism/username/email/telefon/telegram bo'yicha qidiruv."""
    from django.db.models import Q

    query = (query or "").strip()
    if len(query) < 3:
        return []
    users = (
        CustomUser.objects.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone_number__icontains=query)
            | Q(telegram_username__icontains=query)
        )
        .order_by("-date_joined")[:limit]
    )
    return [admin_user_card(u) for u in users]


def admin_user_card(user):
    enrollments = [
        {
            "course": e.cohort.course.title,
            "status": ENROLLMENT_STATUS_LABELS.get(e.status, e.status),
            "next_deadline": (
                e.next_payment_deadline.strftime("%d.%m.%Y") if e.next_payment_deadline else "—"
            ),
        }
        for e in user.enrollments.select_related("cohort__course").order_by("-joined_at")[:4]
    ]
    if user.is_staff or user.is_superuser:
        role = "Admin"
    elif enrollments:
        role = "O'quvchi"
    else:
        role = "Foydalanuvchi"
    return {
        "id": user.id,
        "name": student_display_name(user),
        "username": user.username,
        "role": role,
        "email": user.email or "—",
        "phone": user.phone_number or "—",
        "telegram": f"@{user.telegram_username}" if user.telegram_username else (
            "ulangan" if user.telegram_id else "ulanmagan"
        ),
        "is_active": user.is_active,
        "xp": user.total_xp,
        "joined": user.date_joined.strftime("%d.%m.%Y"),
        "enrollments": enrollments,
        "ai": ai_user_status(user),
    }


def admin_toggle_user_active(user_id, actor):
    """Bloklash/faollashtirish. Himoya: o'zini va staff'ni bloklab bo'lmaydi."""
    if not _require_admin(actor):
        return ActionResult(ok=False, code="forbidden", message="Ruxsat yo'q.")
    user = CustomUser.objects.filter(id=user_id).first()
    if not user:
        return ActionResult(ok=False, code="missing", message="Foydalanuvchi topilmadi.")
    if user.id == actor.id:
        return ActionResult(ok=False, code="self", message="O'zingizni bloklay olmaysiz.")
    if user.is_staff or user.is_superuser:
        return ActionResult(ok=False, code="staff", message="Staff hisobni botdan bloklab bo'lmaydi.")

    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    label = "faollashtirildi ✅" if user.is_active else "bloklandi 🔒"
    return ActionResult(
        ok=True,
        code="toggled",
        message=f"{student_display_name(user)} {label}",
    )


def create_broadcast_draft(actor, text):
    from bot.models import BotBroadcastDraft

    text = (text or "").strip()
    if not _require_admin(actor):
        return None, "Ruxsat yo'q."
    if len(text) < 5:
        return None, "Matn juda qisqa. Foydalanish: /broadcast E'lon matni..."
    if len(text) > 3500:
        return None, "Matn juda uzun (3500 belgigacha)."
    # Eski qoralamalarni tozalaymiz — bitta faol qoralama yetarli
    BotBroadcastDraft.objects.filter(admin=actor).delete()
    draft = BotBroadcastDraft.objects.create(admin=actor, text=text)
    return draft, None


def broadcast_targets():
    """Nishonlar: hammaga (bog'langanlar soni bilan) + faol kohortlar."""
    all_count = CustomUser.objects.filter(is_active=True).count()
    tg_count = CustomUser.objects.filter(is_active=True, telegram_id__isnull=False).count()
    cohorts = [
        {
            "id": c.id,
            "name": c.name,
            "count": Enrollment.objects.filter(
                enrollment_active_access_q(), cohort=c
            ).count(),
        }
        for c in Cohort.objects.filter(is_active=True).order_by("name")[:8]
    ]
    return {"all_count": all_count, "tg_count": tg_count, "cohorts": cohorts}


def broadcast_recipient_count(target):
    qs = _broadcast_recipients_qs(target)
    return qs.count() if qs is not None else 0


def _broadcast_recipients_qs(target):
    if target == "all":
        return CustomUser.objects.filter(is_active=True)
    if str(target).isdigit():
        return CustomUser.objects.filter(
            is_active=True,
            enrollments__cohort_id=int(target),
        ).distinct()
    return None


def execute_broadcast(draft_id, target, actor):
    """Broadcast'ni yuborish: NotificationBroadcast yozuvi + har userga Notification.

    ATAYIN bitta-bitta create (bulk emas): post_save signali TelegramOutbox'ga
    yozsin — sayt qo'ng'irog'i + Telegram DM birga ketadi (outbox worker
    rate-limit bilan yuboradi).
    """
    from bot.models import BotBroadcastDraft
    from users.models import NotificationBroadcast

    if not _require_admin(actor):
        return ActionResult(ok=False, code="forbidden", message="Ruxsat yo'q.")
    draft = BotBroadcastDraft.objects.filter(id=draft_id, admin=actor).first()
    if not draft:
        return ActionResult(
            ok=False, code="draft_missing",
            message="Qoralama topilmadi — /broadcast bilan qaytadan boshlang.",
        )
    recipients = _broadcast_recipients_qs(target)
    if recipients is None:
        return ActionResult(ok=False, code="bad_target", message="Nishon noto'g'ri.")

    broadcast = NotificationBroadcast.objects.create(
        title="E'lon",
        message=draft.text,
        icon="megaphone",
        target_type=(
            NotificationBroadcast.TARGET_ALL if target == "all"
            else NotificationBroadcast.TARGET_COHORTS
        ),
        created_by=actor,
    )
    if target != "all":
        broadcast.cohorts.add(int(target))

    total = 0
    tg_total = 0
    for user in recipients.iterator():
        Notification.objects.create(
            recipient=user,
            title="E'lon 📢",
            message=draft.text,
            icon="megaphone",
            category=Notification.CATEGORY_MANUAL,
        )
        total += 1
        if user.telegram_id:
            tg_total += 1

    broadcast.is_sent = True
    broadcast.sent_at = timezone.now()
    broadcast.save(update_fields=["is_sent", "sent_at"])
    draft.delete()

    return ActionResult(
        ok=True,
        code="sent",
        message=(
            f"📢 E'lon {total} kishiga yozildi (saytda qo'ng'iroqcha), "
            f"shundan {tg_total} tasiga Telegram DM navbatga qo'yildi."
        ),
    )


# ================================================================ F7: AI nazorat (admin)

AI_WINDOW_LABELS = {"5h": "5 soatlik", "weekly": "Haftalik", "both": "Ikkala oyna"}


def ai_control_overview():
    """Global AI sozlamalari + tarif siyosatlari + so'nggi amallar."""
    from aicontrol.models import AIPlanPolicy, AISettings, AIUsageResetEvent

    s = AISettings.load()
    policies = [
        {
            "plan": p.plan.name,
            "limit_5h": p.token_limit_5h,
            "limit_weekly": p.token_limit_weekly,
            "active": p.is_active,
        }
        for p in AIPlanPolicy.objects.select_related("plan")
    ]
    recent = [
        {
            "kind": e.get_kind_display(),
            "scope": e.get_scope_display(),
            "window": e.get_window_display(),
            "count": e.affected_count,
            "when": e.created_at.strftime("%d.%m %H:%M"),
        }
        for e in AIUsageResetEvent.objects.all()[:5]
    ]
    return {
        "enforcement": s.enforcement_enabled,
        "exempt_staff": s.exempt_staff,
        "limit_5h": s.default_5h_token_limit,
        "limit_weekly": s.default_weekly_token_limit,
        "model": s.default_model or "(settings.py default)",
        "policies": policies,
        "recent": recent,
    }


def ai_toggle_enforcement(actor):
    from aicontrol.models import AISettings

    if not _require_admin(actor):
        return ActionResult(ok=False, code="forbidden", message="Ruxsat yo'q.")
    s = AISettings.load()
    s.enforcement_enabled = not s.enforcement_enabled
    s.updated_by = actor
    s.save(update_fields=["enforcement_enabled", "updated_by", "updated_at"])
    label = "yoqildi 🟢" if s.enforcement_enabled else "o'chirildi 🔴 (hech kim bloklanmaydi)"
    return ActionResult(ok=True, code="toggled", message=f"AI limitlari {label}")


def ai_set_global_limits(actor, limit_5h, limit_weekly):
    from aicontrol.models import AISettings

    if not _require_admin(actor):
        return ActionResult(ok=False, code="forbidden", message="Ruxsat yo'q.")
    try:
        limit_5h, limit_weekly = int(limit_5h), int(limit_weekly)
    except (TypeError, ValueError):
        return ActionResult(ok=False, code="bad_value", message="Foydalanish: /ai_limit 100000 1000000")
    if limit_5h <= 0 or limit_weekly <= 0 or limit_weekly < limit_5h:
        return ActionResult(
            ok=False, code="bad_value",
            message="Limitlar musbat bo'lishi va haftalik ≥ 5 soatlikdan bo'lishi kerak.",
        )
    s = AISettings.load()
    s.default_5h_token_limit = limit_5h
    s.default_weekly_token_limit = limit_weekly
    s.updated_by = actor
    s.save(update_fields=["default_5h_token_limit", "default_weekly_token_limit", "updated_by", "updated_at"])
    return ActionResult(
        ok=True, code="updated",
        message=f"Global limitlar: 5 soatlik {_fmt_sum(limit_5h)} · haftalik {_fmt_sum(limit_weekly)} token",
    )


def ai_plan_policies():
    """Barcha tariflar + AI siyosati holati (tahrirlash ro'yxati uchun)."""
    from aicontrol.models import AIPlanPolicy
    from subscriptions.models import Plan

    policies = {p.plan_id: p for p in AIPlanPolicy.objects.all()}
    items = []
    for plan in Plan.objects.order_by("order", "id"):
        policy = policies.get(plan.id)
        items.append(
            {
                "plan_id": plan.id,
                "name": plan.name,
                "price": int(plan.price),
                "policy": (
                    {
                        "limit_5h": policy.token_limit_5h,
                        "limit_weekly": policy.token_limit_weekly,
                        "active": policy.is_active,
                    }
                    if policy
                    else None
                ),
            }
        )
    return items


def ai_set_plan_policy(actor, plan_id, limit_5h, limit_weekly):
    """Tarif siyosatini o'rnatish/yangilash (is_active=True bilan)."""
    from aicontrol.models import AIPlanPolicy
    from subscriptions.models import Plan

    if not _require_admin(actor):
        return ActionResult(ok=False, code="forbidden", message="Ruxsat yo'q.")
    plan = Plan.objects.filter(id=plan_id).first()
    if not plan:
        return ActionResult(ok=False, code="plan_missing", message="Tarif topilmadi — /ai_tarif bilan ID'larni ko'ring.")
    try:
        limit_5h, limit_weekly = int(limit_5h), int(limit_weekly)
    except (TypeError, ValueError):
        return ActionResult(ok=False, code="bad_value", message="Limitlar butun son bo'lishi kerak.")
    if limit_5h <= 0 or limit_weekly <= 0 or limit_weekly < limit_5h:
        return ActionResult(
            ok=False, code="bad_value",
            message="Limitlar musbat bo'lishi va haftalik ≥ 5 soatlikdan bo'lishi kerak.",
        )
    AIPlanPolicy.objects.update_or_create(
        plan=plan,
        defaults={
            "token_limit_5h": limit_5h,
            "token_limit_weekly": limit_weekly,
            "is_active": True,
        },
    )
    return ActionResult(
        ok=True, code="updated",
        message=(
            f"✅ {plan.name}: 5 soatlik {_fmt_sum(limit_5h)} · "
            f"haftalik {_fmt_sum(limit_weekly)} token"
        ),
    )


def ai_disable_plan_policy(actor, plan_id):
    """Tarif siyosatini o'chirish — tarif global defaultga qaytadi."""
    from aicontrol.models import AIPlanPolicy

    if not _require_admin(actor):
        return ActionResult(ok=False, code="forbidden", message="Ruxsat yo'q.")
    policy = AIPlanPolicy.objects.filter(plan_id=plan_id).select_related("plan").first()
    if not policy:
        return ActionResult(ok=False, code="missing", message="Bu tarifda alohida siyosat yo'q.")
    policy.is_active = False
    policy.save(update_fields=["is_active", "updated_at"])
    return ActionResult(
        ok=True, code="disabled",
        message=f"🔕 {policy.plan.name} siyosati o'chirildi — global default amal qiladi.",
    )


def ai_action_scopes():
    """Reset/bonus nishonlari: hammaga + faol kohortlar + tariflar."""
    from subscriptions.models import Plan

    cohorts = [
        {"id": c.id, "name": c.name}
        for c in Cohort.objects.filter(is_active=True).order_by("name")[:6]
    ]
    plans = [{"id": p.id, "name": p.name} for p in Plan.objects.order_by("order")[:6]]
    return {"cohorts": cohorts, "plans": plans}


def _build_ai_event(kind, amount, scope_type, scope_id):
    from aicontrol.models import AIUsageResetEvent

    scope_map = {
        "a": AIUsageResetEvent.SCOPE_ALL,
        "c": AIUsageResetEvent.SCOPE_COHORT,
        "p": AIUsageResetEvent.SCOPE_PLAN,
    }
    scope = scope_map.get(scope_type)
    if scope is None:
        return None
    event = AIUsageResetEvent(
        scope=scope,
        kind=AIUsageResetEvent.KIND_BONUS if kind == "b" else AIUsageResetEvent.KIND_RESET,
        bonus_tokens=int(amount or 0),
    )
    if scope == AIUsageResetEvent.SCOPE_COHORT:
        event.cohort_id = int(scope_id)
    elif scope == AIUsageResetEvent.SCOPE_PLAN:
        event.plan_id = int(scope_id)
    return event


def ai_action_preview(kind, amount, scope_type, scope_id, window):
    """Amal qamraydigan foydalanuvchilar soni (saqlamasdan)."""
    from aicontrol.service import WINDOW_WEEK, _scope_users

    event = _build_ai_event(kind, amount, scope_type, scope_id)
    if event is None:
        return None
    event.window = window
    return _scope_users(event, active_since=timezone.now() - WINDOW_WEEK).count()


def ai_execute_action(actor, kind, amount, scope_type, scope_id, window):
    """Reset/bonus'ni qo'llash — mavjud apply_reset_event servisi orqali (audit bilan)."""
    from aicontrol.service import apply_reset_event

    if not _require_admin(actor):
        return ActionResult(ok=False, code="forbidden", message="Ruxsat yo'q.")
    if kind == "b" and int(amount or 0) <= 0:
        return ActionResult(ok=False, code="bad_amount", message="Bonus miqdori noto'g'ri.")
    event = _build_ai_event(kind, amount, scope_type, scope_id)
    if event is None or window not in AI_WINDOW_LABELS:
        return ActionResult(ok=False, code="bad_target", message="Nishon yoki oyna noto'g'ri.")
    event.window = window
    event.reason = "Telegram bot orqali"
    event.created_by = actor
    event.save()
    count = apply_reset_event(event)
    kind_label = f"Bonus +{_fmt_sum(int(amount))} token" if kind == "b" else "Reset"
    return ActionResult(
        ok=True,
        code="applied",
        message=f"✅ {kind_label} · {AI_WINDOW_LABELS[window]} — {count} foydalanuvchiga qo'llandi.",
    )


def ai_user_status(user):
    """Qidiruv kartasi uchun user AI holati."""
    from aicontrol.service import build_usage_panel, get_allowance

    panel = build_usage_panel(user)
    allowance = get_allowance(user)
    return {
        "blocked": allowance.is_blocked,
        "unlimited": panel["unlimited"],
        "pct_5h": panel["session"]["percent"],
        "pct_weekly": panel["weekly"]["percent"],
    }


def ai_toggle_user_block(user_id, actor):
    from aicontrol.service import get_allowance

    if not _require_admin(actor):
        return ActionResult(ok=False, code="forbidden", message="Ruxsat yo'q.")
    user = CustomUser.objects.filter(id=user_id).first()
    if not user:
        return ActionResult(ok=False, code="missing", message="Foydalanuvchi topilmadi.")
    allowance = get_allowance(user)
    allowance.is_blocked = not allowance.is_blocked
    allowance.save(update_fields=["is_blocked", "updated_at"])
    label = "AI bloklandi 🚫" if allowance.is_blocked else "AI ochildi ✅"
    return ActionResult(ok=True, code="toggled", message=f"{student_display_name(user)}: {label}")


def admin_ai_usage():
    """AI sarfi: bugun/7 kun, muvaffaqiyat, top-5 token yeyuvchi."""
    from django.db.models import Count, Sum

    from messenger.models import AIResponseRun

    now = timezone.now()
    today_qs = AIResponseRun.objects.filter(created_at__date=timezone.localdate())
    week_qs = AIResponseRun.objects.filter(created_at__gte=now - datetime.timedelta(days=7))

    def _agg(qs):
        data = qs.aggregate(runs=Count("id"), tokens=Sum("total_tokens"))
        return {"runs": data["runs"] or 0, "tokens": int(data["tokens"] or 0)}

    top = (
        week_qs.values("student__username", "student__first_name", "student__last_name")
        .annotate(tokens=Sum("total_tokens"), runs=Count("id"))
        .order_by("-tokens")[:5]
    )
    top_users = [
        {
            "name": (f"{t['student__first_name']} {t['student__last_name']}".strip()
                     or t["student__username"]),
            "tokens": int(t["tokens"] or 0),
            "runs": t["runs"],
        }
        for t in top
    ]
    failed_week = week_qs.filter(status=AIResponseRun.STATUS_FAILED).count()
    return {
        "today": _agg(today_qs),
        "week": _agg(week_qs),
        "failed_week": failed_week,
        "top_users": top_users,
    }
