import base64
import datetime
import re
from dataclasses import dataclass

from django.core.signing import BadSignature, Signer
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.html import strip_tags

from bot.models import BotGuest, TelegramLessonCheckIn, TelegramLessonSession
from cohorts.attendance_service import upsert_attendance_and_xp
from cohorts.models import Attendance, Cohort, Enrollment, enrollment_active_access_q
from courses.models import Course, Lesson
from users.models import CustomUser, Notification

GUEST_DEMO_QUESTION_LIMIT = 5


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
    details = {
        Attendance.STATUS_PRESENT: [],
        Attendance.STATUS_PARTIAL: [],
        Attendance.STATUS_ABSENT: [],
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
    from subscriptions.models import Plan

    items = []
    for plan in Plan.objects.prefetch_related("features").order_by("order"):
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


def guest_demo_answer(telegram_id, telegram_username, question, *, provider=None):
    """Mehmon uchun limitli AI savol-javob. Provider xatosi halol xabar bilan qaytadi."""
    question = (question or "").strip()
    if not question:
        return GuestDemoResult(ok=False, code="empty", message="Savol bo'sh.")
    if len(question) > 500:
        return GuestDemoResult(
            ok=False, code="too_long",
            message="Savol juda uzun — qisqaroq yozing (500 belgigacha).",
        )

    guest, _ = BotGuest.objects.get_or_create(
        telegram_id=telegram_id,
        defaults={"telegram_username": telegram_username or ""},
    )
    if guest.demo_questions_used >= GUEST_DEMO_QUESTION_LIMIT:
        return GuestDemoResult(
            ok=False,
            code="limit_reached",
            message=(
                "Demo savollar tugadi. Ro'yxatdan o'tsangiz, AI repetitor bilan "
                "cheklovsiz suhbatlashasiz — /start bosib \"Ro'yxatdan o'tish\"ni tanlang."
            ),
        )

    if provider is None:
        from ai.providers import get_chat_provider

        provider = get_chat_provider()

    prompt = f"{_build_demo_context()}\n\nMehmon savoli: {question}"
    try:
        response = provider.generate(prompt=prompt)
        answer = (response.text or "").strip()
    except Exception:
        return GuestDemoResult(
            ok=False,
            code="provider_error",
            message="Hozir javob bera olmadim — birozdan so'ng qayta urinib ko'ring.",
        )

    guest.demo_questions_used += 1
    if telegram_username and guest.telegram_username != telegram_username:
        guest.telegram_username = telegram_username
    guest.save(update_fields=["demo_questions_used", "telegram_username", "updated_at"])

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
    """Sayt checkout'i bilan BIR XIL davr hisobi (cohorts/views.checkout_view)."""
    today = today or timezone.localdate()
    if (
        enrollment.status == Enrollment.STATUS_ACTIVE
        and enrollment.next_payment_deadline
        and enrollment.next_payment_deadline > today
    ):
        start = enrollment.next_payment_deadline
    else:
        start = today
    return start, start + datetime.timedelta(days=30)


def begin_course_enrollment(user, course_id, plan_id):
    """Kurs+tarif tanlandi → pending enrollment + to'lov rekvizitlari.

    Sayt bilan bitta servis: resolve_checkout_enrollment kohortni o'zi tanlaydi,
    mavjud enrollmentni qayta ishlatadi (dublikat ochilmaydi).
    """
    from cohorts.checkout_service import CheckoutUnavailable, resolve_checkout_enrollment
    from cohorts.models import PaymentReceipt
    from frontend.models import SiteSettings
    from subscriptions.models import Plan

    course = Course.objects.filter(id=course_id, is_active=True).first()
    if not course:
        return EnrollBeginResult(ok=False, code="course_missing", message="Kurs topilmadi yoki faol emas.")
    plan = Plan.objects.filter(id=plan_id).first()
    if not plan:
        return EnrollBeginResult(ok=False, code="plan_missing", message="Tarif topilmadi.")

    try:
        enrollment, _created, _cohort = resolve_checkout_enrollment(student=user, course=course)
    except CheckoutUnavailable as exc:
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

    if enrollment.plan_id != plan.id:
        enrollment.plan = plan
        enrollment.save(update_fields=["plan"])

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


def submit_payment_receipt(user, receipt_image):
    """Telegram'dan kelgan chek rasmi → PaymentReceipt (sayt bilan bitta servis).

    Nishon: tarifi tanlangan, tasdiqlanmagan cheki yo'q eng so'nggi enrollment
    (begin_course_enrollment'dan keyingi holat).
    """
    from subscriptions.promo_service import create_checkout_receipt_with_promo

    enrollment = (
        user.enrollments.select_related("plan", "cohort__course")
        .filter(plan__isnull=False)
        .exclude(receipts__is_verified=False)
        .order_by("-joined_at", "-id")
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

    start, end = _checkout_period(enrollment)
    receipt, _quote, _redemption = create_checkout_receipt_with_promo(
        enrollment=enrollment,
        plan=enrollment.plan,
        receipt_image=receipt_image,
        period_start=start,
        period_end=end,
    )
    return ReceiptSubmitResult(
        ok=True,
        code="submitted",
        message="Chek qabul qilindi.",
        receipt_id=receipt.id,
        course_title=enrollment.cohort.course.title,
        amount=int(receipt.amount),
    )
