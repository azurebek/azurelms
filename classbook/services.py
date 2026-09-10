from __future__ import annotations

import datetime
import html
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from bot.models import TelegramLessonCheckIn, TelegramLessonSession
from cohorts.attendance_service import upsert_attendance_and_xp
from cohorts.models import Attendance, Enrollment, enrollment_active_access_q
from courses.release_service import set_lesson_release
from users.models import Notification

from .access import active_enrollment_for, can_manage_cohort
from .delivery import queue_group_delivery
from .grading import grade_answer, points_for_grade
from .models import ActivityRun, LessonPlaybook, StudentResponse, TelegramGroupDelivery
from .realtime import broadcast_after_commit


@dataclass
class ServiceResult:
    ok: bool
    code: str
    message: str
    session: TelegramLessonSession | None = None
    activity: ActivityRun | None = None
    response: StudentResponse | None = None
    summary: dict | None = None
    details: dict | None = None


def display_name(user):
    return user.get_full_name().strip() or user.username


def _plain_for_telegram(value, max_escaped_length):
    """Telegram HTML limitini buzmasdan plain matnni xavfsiz qisqartiradi."""
    value = str(value or "")
    if len(html.escape(value)) <= max_escaped_length:
        return value
    low, high = 0, len(value)
    while low < high:
        middle = (low + high + 1) // 2
        if len(html.escape(value[:middle])) <= max_escaped_length - 1:
            low = middle
        else:
            high = middle - 1
    return f"{value[:low]}…"


def _escape_for_telegram(value, max_escaped_length):
    return html.escape(_plain_for_telegram(value, max_escaped_length))


def _join_names_for_telegram(items, max_escaped_length=950):
    names = []
    used = 0
    for item in items:
        name = _escape_for_telegram(item["name"], 120)
        addition = len(name) + (2 if names else 0)
        if used + addition > max_escaped_length:
            names.append("…")
            break
        names.append(name)
        used += addition
    return ", ".join(names)


def _labels(items):
    return {str(item["id"]): item["text"] for item in items}


def correct_answer_text(activity):
    snapshot = activity.snapshot
    config = snapshot.get("config", {})
    answer_key = snapshot.get("answer_key", {})
    kind = snapshot.get("kind")
    if kind in {"single_choice", "multiple_choice"}:
        labels = _labels(config.get("options", []))
        return ", ".join(labels.get(str(key), str(key)) for key in answer_key.get("correct", []))
    if kind == "true_false":
        return "To'g'ri" if answer_key.get("correct") else "Noto'g'ri"
    if kind in {"short_answer", "fill_blank"}:
        return ", ".join(answer_key.get("accepted", []))
    if kind == "matching":
        left, right = _labels(config.get("left", [])), _labels(config.get("right", []))
        return "; ".join(
            f"{left.get(str(a), a)} → {right.get(str(b), b)}"
            for a, b in answer_key.get("pairs", {}).items()
        )
    if kind in {"ordering", "unscramble"}:
        labels = _labels(config.get("items", []))
        return " → ".join(labels.get(str(value), str(value)) for value in answer_key.get("order", []))
    if kind == "categorization":
        items, categories = _labels(config.get("items", [])), _labels(config.get("categories", []))
        return "; ".join(
            f"{items.get(str(a), a)} → {categories.get(str(b), b)}"
            for a, b in answer_key.get("assignments", {}).items()
        )
    return "Poll baholanmaydi"


def response_breakdown(activity, response):
    snapshot = activity.snapshot
    config = snapshot.get("config", {})
    details = response.grading_details
    kind = snapshot.get("kind")
    correct = correct_answer_text(activity)
    if kind in {"single_choice", "multiple_choice"}:
        labels = _labels(config.get("options", []))
        submitted = ", ".join(labels.get(str(key), str(key)) for key in details.get("selected", []))
    elif kind == "true_false":
        submitted = "To'g'ri" if details.get("selected") else "Noto'g'ri"
    elif kind in {"short_answer", "fill_blank"}:
        submitted = details.get("selected", "")
    elif kind == "matching":
        left, right = _labels(config.get("left", [])), _labels(config.get("right", []))
        submitted = "; ".join(
            f"{left.get(str(a), a)} → {right.get(str(b), b)}"
            for a, b in details.get("selected", {}).items()
        )
    elif kind in {"ordering", "unscramble"}:
        labels = _labels(config.get("items", []))
        submitted = " → ".join(
            labels.get(str(value), str(value)) for value in details.get("selected", [])
        )
    elif kind == "categorization":
        items, categories = _labels(config.get("items", [])), _labels(config.get("categories", []))
        submitted = "; ".join(
            f"{items.get(str(a), a)} → {categories.get(str(b), b)}"
            for a, b in details.get("selected", {}).items()
        )
    else:
        labels = _labels(config.get("options", []))
        selected = details.get("selected")
        submitted = labels.get(str(selected), str(selected or "Ovoz berildi"))
    return {"submitted": submitted, "correct": correct}


def _attendance_open_text(session):
    return (
        "📋 <b>Bugungi dars boshlandi</b>\n"
        f"Guruh: <b>{_escape_for_telegram(session.cohort.name, 500)}</b>\n"
        f"Dars: <b>{_escape_for_telegram(session.lesson.title, 500)}</b>\n\n"
        "Davomatga belgilanish uchun tugmani bosing 👇"
    )


def _material_text(session, playbook):
    lines = [f"📚 <b>{_escape_for_telegram(session.lesson.title, 500)}</b>"]
    if playbook.opening_message:
        lines.extend(["", _escape_for_telegram(playbook.opening_message, 1400)])
    if playbook.materials_message:
        lines.extend(["", "<b>Bugungi materiallar</b>", _escape_for_telegram(playbook.materials_message, 1400)])
    return "\n".join(lines)


def _ensure_activity_runs(session, playbook):
    existing_orders = set(session.classbook_activities.values_list("order", flat=True))
    runs = [
        ActivityRun(
            session=session,
            playbook_step=step,
            exercise=step.exercise,
            order=step.order,
            snapshot=step.exercise.snapshot(),
        )
        for step in playbook.exercise_steps.select_related("exercise").order_by("order", "id")
        if step.order not in existing_orders
    ]
    if runs:
        ActivityRun.objects.bulk_create(runs)
    return len(runs)


@transaction.atomic
def start_class_session(*, actor, cohort, lesson, require_telegram=True, queue_attendance=True):
    cohort = type(cohort).objects.select_for_update().select_related("course").get(pk=cohort.pk)
    if not can_manage_cohort(actor, cohort):
        return ServiceResult(False, "permission_denied", "Bu guruh darsini boshlash huquqi sizda yo'q.")
    if lesson.module.course_id != cohort.course_id:
        return ServiceResult(False, "wrong_lesson", "Tanlangan dars bu guruh kursiga tegishli emas.")
    if require_telegram and not cohort.telegram_chat_id:
        return ServiceResult(False, "telegram_missing", "Avval cohortni Telegram guruhiga bog'lang.")

    playbook = LessonPlaybook.objects.filter(cohort=cohort, lesson=lesson).first()
    if not playbook:
        return ServiceResult(False, "playbook_missing", "Bu dars uchun Classbook playbook tayyorlanmagan.")
    if playbook.status != LessonPlaybook.STATUS_READY:
        return ServiceResult(False, "playbook_not_ready", "Playbook hali `Darsga tayyor` holatida emas.")

    existing = (
        TelegramLessonSession.objects.select_related("cohort", "lesson")
        .filter(cohort=cohort, status=TelegramLessonSession.STATUS_OPEN)
        .first()
    )
    if existing:
        if existing.lesson_id != lesson.id:
            return ServiceResult(
                False,
                "another_lesson_open",
                f"Avval ochiq {existing.lesson.title} darsini yakunlang.",
                session=existing,
            )
        _ensure_activity_runs(existing, playbook)
        if queue_attendance and not existing.attendance_message_id:
            queue_group_delivery(
                session=existing,
                external_key=f"classbook-session-{existing.id}-attendance-open",
                text=_attendance_open_text(existing),
                kind=TelegramGroupDelivery.KIND_ATTENDANCE,
            )
        if playbook.opening_message or playbook.materials_message:
            queue_group_delivery(
                session=existing,
                external_key=f"classbook-session-{existing.id}-materials",
                text=_material_text(existing, playbook),
            )
        return ServiceResult(True, "already_open", "Ochiq dars Classbook'da davom ettirildi.", session=existing)

    try:
        # IntegrityError tashqi atomic blokni "broken" qilmasin: unique-open
        # poygasini ichki savepoint ushlaydi, so'ng g'olib yozuvni o'qiymiz.
        with transaction.atomic():
            session = TelegramLessonSession.objects.create(
                cohort=cohort,
                lesson=lesson,
                chat_id=cohort.telegram_chat_id or 0,
                chat_title=cohort.telegram_chat_title or cohort.name,
                attendance_date=timezone.localdate(),
                late_after_minutes=playbook.late_after_minutes,
                started_by=actor,
            )
    except IntegrityError:
        existing = TelegramLessonSession.objects.filter(
            chat_id=cohort.telegram_chat_id, status=TelegramLessonSession.STATUS_OPEN
        ).first()
        return ServiceResult(True, "already_open", "Ochiq dars davom ettirildi.", session=existing)

    run_count = _ensure_activity_runs(session, playbook)

    if queue_attendance:
        queue_group_delivery(
            session=session,
            external_key=f"classbook-session-{session.id}-attendance-open",
            text=_attendance_open_text(session),
            kind=TelegramGroupDelivery.KIND_ATTENDANCE,
        )
    if playbook.opening_message or playbook.materials_message:
        queue_group_delivery(
            session=session,
            external_key=f"classbook-session-{session.id}-materials",
            text=_material_text(session, playbook),
        )

    from core.audit import record_audit_event
    record_audit_event(
        action="classbook.session.start",
        actor=actor,
        target=session,
        target_label=f"{cohort.name} → {lesson.title}",
        after={"status": session.status, "activities": run_count},
    )
    broadcast_after_commit(session.id, "session_started", {"lesson": lesson.title})
    return ServiceResult(True, "started", "Dars boshlandi; davomat va materiallar navbatga qo'yildi.", session=session)


def _activity_link(activity):
    return f"/classbook/live/activity/{activity.id}/"


@transaction.atomic
def open_activity(*, actor, activity):
    activity = (
        ActivityRun.objects.select_for_update()
        .select_related("session__cohort", "session__lesson", "exercise")
        .get(pk=activity.pk)
    )
    if not can_manage_cohort(actor, activity.session.cohort):
        return ServiceResult(False, "permission_denied", "Mashqni ochish huquqi sizda yo'q.", activity=activity)
    if activity.session.status != TelegramLessonSession.STATUS_OPEN:
        return ServiceResult(False, "session_closed", "Dars sessiyasi yopilgan.", activity=activity)
    if activity.status != ActivityRun.STATUS_QUEUED:
        return ServiceResult(False, "wrong_state", "Bu mashq navbatda emas.", activity=activity)
    if ActivityRun.objects.filter(session=activity.session, status=ActivityRun.STATUS_OPEN).exists():
        return ServiceResult(False, "another_open", "Avval ochiq mashqni yakunlang.", activity=activity)

    now = timezone.now()
    seconds = int(activity.snapshot.get("time_limit_seconds") or activity.exercise.time_limit_seconds)
    activity.status = ActivityRun.STATUS_OPEN
    activity.opened_by = actor
    activity.opened_at = now
    activity.closes_at = now + datetime.timedelta(seconds=seconds)
    activity.save(update_fields=["status", "opened_by", "opened_at", "closes_at"])

    queue_group_delivery(
        session=activity.session,
        activity=activity,
        external_key=f"classbook-activity-{activity.id}-open",
        kind=TelegramGroupDelivery.KIND_LINK,
        text=(
            f"⚡ <b>{_escape_for_telegram(activity.snapshot.get('title', activity.exercise.title), 600)}</b>\n"
            f"{_escape_for_telegram(activity.snapshot.get('instructions') or 'Havolani ochib mashqni bajaring.', 1800)}\n"
            f"⏱ {seconds} soniya"
        ),
        button_text="⚡ Mashqni bajarish",
        button_path=_activity_link(activity),
    )
    broadcast_after_commit(activity.session_id, "activity_opened", {
        "activity_id": activity.id,
        "title": activity.snapshot.get("title", activity.exercise.title),
        "closes_at": activity.closes_at.isoformat(),
    })
    return ServiceResult(True, "opened", "Mashq ochildi va guruhga yuborish navbatiga qo'yildi.", activity=activity)


@transaction.atomic
def submit_response(*, user, activity, answer):
    # Bitta activity qatori qisqa muddatga qulflanadi: yopilish bilan javob
    # qabul qilish orasida race bo'lmasin. Grader pure va tez; 50 foydalanuvchi
    # uchun bu keyingi load testda alohida o'lchanadi.
    activity = (
        ActivityRun.objects.select_for_update()
        .select_related("session__cohort", "exercise")
        .get(pk=activity.pk)
    )
    enrollment = active_enrollment_for(user, activity.session.cohort)
    if not enrollment:
        return ServiceResult(False, "no_access", "Siz bu jonli dars guruhiga kirmaysiz.", activity=activity)
    existing = StudentResponse.objects.filter(activity=activity, enrollment=enrollment).first()
    if existing:
        return ServiceResult(True, "already_submitted", "Javobingiz avval qabul qilingan.", activity=activity, response=existing)
    if activity.session.status != TelegramLessonSession.STATUS_OPEN:
        return ServiceResult(False, "session_closed", "Dars yakunlangan.", activity=activity)
    if activity.status != ActivityRun.STATUS_OPEN:
        return ServiceResult(False, "activity_closed", "Mashq hozir javob qabul qilmayapti.", activity=activity)
    now = timezone.now()
    if activity.closes_at and now > activity.closes_at:
        return ServiceResult(False, "deadline", "Mashq vaqti tugadi.", activity=activity)

    snapshot = activity.snapshot
    try:
        grade = grade_answer(snapshot["kind"], snapshot["config"], snapshot["answer_key"], answer)
    except (ValidationError, KeyError) as exc:
        message = "; ".join(exc.messages) if isinstance(exc, ValidationError) else "Mashq konfiguratsiyasi buzilgan."
        return ServiceResult(False, "invalid_answer", message, activity=activity)

    elapsed_ms = max(0, int((now - activity.opened_at).total_seconds() * 1000))
    score, max_score, bonus = points_for_grade(
        grade=grade,
        max_points=snapshot.get("max_points", 100),
        speed_bonus_percent=snapshot.get("speed_bonus_percent", 0),
        elapsed_ms=elapsed_ms,
        time_limit_seconds=snapshot.get("time_limit_seconds", 0),
    )
    if snapshot["kind"] == "poll":
        score = max_score = bonus = Decimal("0")

    try:
        # Duplicate request poygasi tashqi tranzaksiyani broken qilmasin.
        # Ichki savepoint unique constraint xatosini yutadi, keyin mavjud
        # javobni xavfsiz o'qiymiz.
        with transaction.atomic():
            response = StudentResponse.objects.create(
                activity=activity,
                enrollment=enrollment,
                answer=answer,
                score=score,
                max_score=max_score,
                accuracy=grade.fraction,
                speed_bonus=bonus,
                is_correct=grade.is_correct,
                grading_details=grade.details,
                response_ms=elapsed_ms,
            )
    except IntegrityError:
        response = StudentResponse.objects.get(activity=activity, enrollment=enrollment)
        return ServiceResult(True, "already_submitted", "Javobingiz avval qabul qilingan.", activity=activity, response=response)

    # Telegram check-in va web mashq ishtiroki bir xil davomat signaliga aylanadi.
    TelegramLessonCheckIn.objects.get_or_create(
        session=activity.session,
        enrollment=enrollment,
        defaults={
            "telegram_user_id": user.telegram_id or 0,
            "telegram_username": user.telegram_username or "",
        },
    )
    from users.streak import record_activity
    record_activity(user)
    response_count = StudentResponse.objects.filter(activity=activity).count()
    broadcast_after_commit(activity.session_id, "response_received", {
        "activity_id": activity.id,
        "response_count": response_count,
    })
    return ServiceResult(True, "submitted", "Javobingiz qabul qilindi.", activity=activity, response=response)


def activity_leaderboard(activity, limit=None):
    rows = list(
        activity.responses.select_related("enrollment__student")
        .order_by("-score", "response_ms", "submitted_at", "id")
    )
    result = []
    previous_key = None
    previous_rank = 0
    for position, response in enumerate(rows, 1):
        key = (response.score, response.response_ms)
        rank = previous_rank if key == previous_key else position
        result.append({
            "rank": rank,
            "response": response,
            "student": response.enrollment.student,
            "score": response.score,
            "max_score": response.max_score,
        })
        previous_key, previous_rank = key, rank
        if limit and len(result) >= limit:
            break
    return result


def session_leaderboard(session, limit=None, *, revealed_only=False):
    aggregates = {}
    responses = (
        StudentResponse.objects.filter(activity__session=session)
        .exclude(activity__snapshot__kind="poll")
        .select_related("enrollment__student")
    )
    if revealed_only:
        responses = responses.filter(activity__status=ActivityRun.STATUS_REVEALED)
    for response in responses:
        row = aggregates.setdefault(response.enrollment_id, {
            "student": response.enrollment.student,
            "score": Decimal("0"),
            "max_score": Decimal("0"),
            "response_ms": 0,
        })
        row["score"] += response.score
        row["max_score"] += response.max_score
        row["response_ms"] += response.response_ms
    ordered = sorted(
        aggregates.values(), key=lambda row: (-row["score"], row["response_ms"], row["student"].id)
    )
    for rank, row in enumerate(ordered, 1):
        row["rank"] = rank
    return ordered[:limit] if limit else ordered


def _publish_activity_notifications(activity):
    title = activity.snapshot.get("title", activity.exercise.title)
    url = f"/classbook/live/activity/{activity.id}/result/"
    responses = {item.enrollment_id: item for item in activity.responses.all()}
    enrollments = Enrollment.objects.filter(
        enrollment_active_access_q(), cohort=activity.session.cohort
    ).select_related("student")
    for enrollment in enrollments:
        response = responses.get(enrollment.id)
        explanation = _plain_for_telegram((activity.snapshot.get("explanation") or "").strip(), 800)
        if response:
            verdict = "To'g'ri" if response.is_correct else "Tekshirib chiqing"
            breakdown = response_breakdown(activity, response)
            message = (
                f"{verdict}: {response.score}/{response.max_score} ball. "
                f"Javobingiz: {_plain_for_telegram(breakdown['submitted'] or '—', 650)}. "
                f"To'g'ri javob: {_plain_for_telegram(breakdown['correct'] or '—', 650)}."
            )
        else:
            message = (
                "Bu mashqda javob yubormadingiz. "
                f"To'g'ri javob: {_plain_for_telegram(correct_answer_text(activity) or '—', 900)}."
            )
        if explanation:
            message += f" {explanation}"
        Notification.objects.get_or_create(
            recipient=enrollment.student,
            external_key=f"classbook-activity-result-{activity.id}",
            defaults={
                "title": f"Mashq natijasi: {title}",
                "message": message[:3000],
                "icon": "lightning",
                "url": url,
                "category": Notification.CATEGORY_SYSTEM,
            },
        )


@transaction.atomic
def close_activity(*, actor, activity, publish=True):
    activity = (
        ActivityRun.objects.select_for_update()
        .select_related("session__cohort", "exercise")
        .get(pk=activity.pk)
    )
    if not can_manage_cohort(actor, activity.session.cohort):
        return ServiceResult(False, "permission_denied", "Mashqni yopish huquqi sizda yo'q.", activity=activity)
    if activity.status not in {ActivityRun.STATUS_OPEN, ActivityRun.STATUS_CLOSED}:
        return ServiceResult(False, "wrong_state", "Bu mashqni hozir yopib bo'lmaydi.", activity=activity)
    if activity.status == ActivityRun.STATUS_OPEN:
        activity.status = ActivityRun.STATUS_CLOSED
        activity.closed_at = timezone.now()
        activity.save(update_fields=["status", "closed_at"])
    if publish and activity.status == ActivityRun.STATUS_CLOSED:
        activity.status = ActivityRun.STATUS_REVEALED
        activity.revealed_at = timezone.now()
        activity.save(update_fields=["status", "revealed_at"])
        leaders = activity_leaderboard(activity, limit=5)
        lines = [
            f"🏁 <b>{_escape_for_telegram(activity.snapshot.get('title', activity.exercise.title), 600)} — natija</b>",
            f"Javob berdi: <b>{activity.responses.count()}</b>",
        ]
        if activity.snapshot.get("kind") != "poll" and leaders:
            lines.append("")
            for row in leaders:
                lines.append(
                    f"{row['rank']}. {_escape_for_telegram(display_name(row['student']), 350)} — {row['score']} ball"
                )
        queue_group_delivery(
            session=activity.session,
            activity=activity,
            external_key=f"classbook-activity-{activity.id}-result",
            text="\n".join(lines),
        )
        _publish_activity_notifications(activity)

    broadcast_after_commit(activity.session_id, "activity_closed", {
        "activity_id": activity.id,
        "response_count": activity.responses.count(),
        "published": publish,
    })
    return ServiceResult(True, "closed", "Mashq yopildi va natijalar e'lon qilindi.", activity=activity)


def _attendance_details(enrollments, checkins, late_cutoff):
    summary = {"present": 0, "partial": 0, "absent": 0, "total": len(enrollments)}
    details = {"present": [], "partial": [], "absent": []}
    for enrollment in enrollments:
        checkin = checkins.get(enrollment.id)
        if not checkin:
            status = Attendance.STATUS_ABSENT
        elif checkin.checked_in_at > late_cutoff:
            status = Attendance.STATUS_PARTIAL
        else:
            status = Attendance.STATUS_PRESENT
        summary[status] += 1
        details[status].append({
            "enrollment": enrollment,
            "student": enrollment.student,
            "name": display_name(enrollment.student),
        })
    return summary, details


def _attendance_close_text(session, summary, details, announce_names=False):
    lines = [
        "📋 <b>Davomat yakunlandi</b>",
        f"Dars: <b>{html.escape(session.lesson.title)}</b>",
        "",
        f"✅ Keldi: <b>{summary['present']}</b>",
        f"🕒 Kech: <b>{summary['partial']}</b>",
        f"❌ Kelmadi: <b>{summary['absent']}</b>",
    ]
    if announce_names:
        for status, icon, label in (("present", "✅", "Keldi"), ("partial", "🕒", "Kech"), ("absent", "❌", "Kelmadi")):
            if details[status]:
                names = _join_names_for_telegram(details[status][:60])
                lines.extend(["", f"{icon} <b>{label}:</b> {names}"])
    return "\n".join(lines)


@transaction.atomic
def finish_class_session(*, actor, session, queue_attendance_summary=True):
    session = (
        TelegramLessonSession.objects.select_for_update(of=("self",))
        .select_related("cohort", "cohort__course", "lesson")
        .filter(pk=session.pk)
        .first()
    )
    if not session:
        return ServiceResult(False, "missing", "Dars sessiyasi topilmadi.")
    if not can_manage_cohort(actor, session.cohort):
        return ServiceResult(False, "permission_denied", "Darsni yakunlash huquqi sizda yo'q.", session=session)
    if session.status != TelegramLessonSession.STATUS_OPEN:
        return ServiceResult(False, "already_closed", "Dars allaqachon yakunlangan.", session=session)

    open_activity = session.classbook_activities.filter(status=ActivityRun.STATUS_OPEN).first()
    if open_activity:
        close_activity(actor=actor, activity=open_activity, publish=True)

    enrollments = list(
        Enrollment.objects.select_related("student")
        .filter(enrollment_active_access_q(), cohort=session.cohort)
        .order_by("student__first_name", "student__last_name", "student__username")
    )
    checkins = {row.enrollment_id: row for row in session.checkins.all()}
    late_cutoff = session.started_at + datetime.timedelta(minutes=session.late_after_minutes)
    summary, details = _attendance_details(enrollments, checkins, late_cutoff)

    for status, items in details.items():
        for item in items:
            upsert_attendance_and_xp(
                enrollment=item["enrollment"],
                lesson=session.lesson,
                date=session.attendance_date,
                status=status,
                marked_by=actor,
            )

    session.status = TelegramLessonSession.STATUS_CLOSED
    session.closed_by = actor
    session.closed_at = timezone.now()
    session.save(update_fields=["status", "closed_by", "closed_at"])

    playbook = LessonPlaybook.objects.filter(cohort=session.cohort, lesson=session.lesson).first()
    if playbook and playbook.auto_release_lesson:
        set_lesson_release(
            cohort=session.cohort,
            lesson=session.lesson,
            released=True,
            actor=actor,
            note=f"Classbook sessiyasi #{session.id} yakunlandi",
        )

    if queue_attendance_summary:
        queue_group_delivery(
            session=session,
            external_key=f"classbook-session-{session.id}-attendance-close",
            text=_attendance_close_text(
                session, summary, details, announce_names=bool(playbook and playbook.announce_names)
            ),
        )
    if playbook and playbook.homework_message:
        queue_group_delivery(
            session=session,
            external_key=f"classbook-session-{session.id}-homework",
            kind=TelegramGroupDelivery.KIND_LINK,
            text=f"📝 <b>Uyga vazifa</b>\n{_escape_for_telegram(playbook.homework_message, 3200)}",
            button_text="📚 Dars va vazifani ochish",
            button_path=f"/courses/{session.cohort.course_id}/lesson/{session.lesson_id}/",
        )

    for item in details["absent"]:
        Notification.objects.get_or_create(
            recipient=item["student"],
            external_key=f"classbook-absent-{session.id}",
            defaults={
                "title": "Bugungi darsda ko'rishmadik",
                "message": (
                    f"{session.lesson.title} darsida davomatga belgilanmadingiz. "
                    "Ochilgan materialni ko'rib, uyga vazifani bajaring."
                ),
                "icon": "calendar-x",
                "url": f"/courses/{session.cohort.course_id}/lesson/{session.lesson_id}/",
                "category": Notification.CATEGORY_SYSTEM,
            },
        )

    from core.audit import record_audit_event
    record_audit_event(
        action="classbook.session.finish",
        actor=actor,
        target=session,
        target_label=f"{session.cohort.name} → {session.lesson.title}",
        before={"status": TelegramLessonSession.STATUS_OPEN},
        after={"status": session.status, "attendance": summary},
    )
    broadcast_after_commit(session.id, "session_finished", summary)
    public_details = {
        key: [{"name": item["name"], "student_id": item["student"].id} for item in value]
        for key, value in details.items()
    }
    return ServiceResult(
        True, "finished", "Dars, davomat, access va uyga vazifa oqimi yakunlandi.",
        session=session, summary=summary, details=public_details,
    )


def next_activity_for_session(session):
    return session.classbook_activities.filter(status=ActivityRun.STATUS_QUEUED).order_by("order", "id").first()


def current_activity_for_session(session):
    return session.classbook_activities.filter(status=ActivityRun.STATUS_OPEN).first()
