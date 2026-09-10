import csv
import datetime
import json
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Count, Max
from django.db.models.fields.files import FieldFile
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from bot.models import TelegramLessonSession
from cohorts.models import Enrollment, enrollment_active_access_q
from core.access import teacher_cohort_queryset, teacher_course_queryset
from core.private_media_views import serve_private_file
from courses.models import Lesson

from .access import active_enrollment_for, can_join_session, can_manage_cohort
from .forms import ExerciseForm, HELP_BY_KIND, LessonPlaybookForm
from .models import ActivityRun, Exercise, LessonPlaybook, PlaybookExercise, StudentResponse
from .services import (
    activity_leaderboard,
    close_activity,
    current_activity_for_session,
    finish_class_session,
    next_activity_for_session,
    open_activity,
    response_breakdown,
    session_leaderboard,
    start_class_session,
    submit_response,
)


def _is_teacher(user):
    return bool(user.is_authenticated and user.is_active and (user.is_staff or user.is_superuser))


def _teacher_context(user, active_nav="classbook"):
    courses = teacher_course_queryset(user)
    from core.teacher_views import _pending_assignment_submissions, _pending_exam_attempts
    return {
        "active_nav": active_nav,
        "teacher_courses": courses,
        "grading_pending_count": _pending_exam_attempts(courses).count()
        + _pending_assignment_submissions(courses).count(),
    }


def _teacher_session(user, session_id):
    return get_object_or_404(
        TelegramLessonSession.objects.select_related("cohort", "cohort__course", "lesson", "lesson__module"),
        pk=session_id,
        cohort__in=teacher_cohort_queryset(user),
    )


def _teacher_activity(user, activity_id):
    return get_object_or_404(
        ActivityRun.objects.select_related(
            "session__cohort", "session__cohort__course", "session__lesson", "exercise"
        ),
        pk=activity_id,
        session__cohort__in=teacher_cohort_queryset(user),
    )


@login_required
@user_passes_test(_is_teacher)
def teacher_home(request):
    context = _teacher_context(request.user)
    cohorts = list(
        teacher_cohort_queryset(request.user)
        .filter(is_active=True)
        .select_related("course")
        .annotate(
            active_members=Count("members", filter=enrollment_active_access_q(prefix="members__"), distinct=True)
        )
        .order_by("name")
    )
    for cohort in cohorts:
        cohort.classbook_lessons = list(
            Lesson.objects.filter(module__course=cohort.course)
            .select_related("module")
            .prefetch_related("classbook_playbooks")
            .order_by("module__order", "order")
        )
        playbooks = {
            item.lesson_id: item
            for item in LessonPlaybook.objects.filter(cohort=cohort).annotate(step_count=Count("exercise_steps"))
        }
        for lesson in cohort.classbook_lessons:
            lesson.classbook_playbook = playbooks.get(lesson.id)
    context.update({
        "cohorts": cohorts,
        "open_sessions": TelegramLessonSession.objects.filter(
            cohort__in=teacher_cohort_queryset(request.user), status=TelegramLessonSession.STATUS_OPEN
        ).select_related("cohort", "lesson"),
        "exercise_count": Exercise.objects.filter(course__in=context["teacher_courses"], is_active=True).count(),
    })
    return render(request, "classbook/teacher_home.html", context)


@login_required
@user_passes_test(_is_teacher)
def exercise_list(request):
    context = _teacher_context(request.user)
    context["exercises"] = (
        Exercise.objects.filter(course__in=context["teacher_courses"])
        .select_related("course", "lesson")
        .order_by("course__title", "-updated_at")
    )
    return render(request, "classbook/exercise_list.html", context)


@login_required
@user_passes_test(_is_teacher)
def exercise_edit(request, exercise_id=None):
    courses = teacher_course_queryset(request.user)
    exercise = None
    if exercise_id:
        exercise = get_object_or_404(Exercise, pk=exercise_id, course__in=courses)
    form = ExerciseForm(request.POST or None, request.FILES or None, instance=exercise, teacher=request.user)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        if not item.created_by_id:
            item.created_by = request.user
        item.full_clean()
        item.save()
        messages.success(request, "Mashq saqlandi.")
        return redirect("classbook:exercise_list")
    context = _teacher_context(request.user)
    context.update({"form": form, "exercise": exercise, "help_by_kind": HELP_BY_KIND})
    return render(request, "classbook/exercise_form.html", context)


@login_required
@user_passes_test(_is_teacher)
def playbook_edit(request, cohort_id, lesson_id):
    cohort = get_object_or_404(teacher_cohort_queryset(request.user).select_related("course"), pk=cohort_id)
    lesson = get_object_or_404(
        Lesson.objects.select_related("module", "module__course"), pk=lesson_id, module__course=cohort.course
    )
    playbook, _ = LessonPlaybook.objects.get_or_create(
        cohort=cohort, lesson=lesson, defaults={"created_by": request.user}
    )
    form = LessonPlaybookForm(request.POST or None, instance=playbook)
    if request.method == "POST" and request.POST.get("action") == "save" and form.is_valid():
        playbook = form.save(commit=False)
        playbook.full_clean()
        playbook.save()
        messages.success(request, "Dars playbook'i saqlandi.")
        return redirect("classbook:playbook_edit", cohort_id=cohort.id, lesson_id=lesson.id)

    context = _teacher_context(request.user)
    context.update({
        "cohort": cohort,
        "lesson": lesson,
        "playbook": playbook,
        "form": form,
        "steps": playbook.exercise_steps.select_related("exercise").order_by("order", "id"),
        "available_exercises": Exercise.objects.filter(course=cohort.course, is_active=True).order_by("title"),
    })
    return render(request, "classbook/playbook_form.html", context)


@login_required
@user_passes_test(_is_teacher)
@require_POST
@transaction.atomic
def playbook_add_exercise(request, playbook_id):
    playbook = get_object_or_404(
        LessonPlaybook.objects.select_for_update().select_related("cohort"),
        pk=playbook_id,
        cohort__in=teacher_cohort_queryset(request.user),
    )
    exercise = get_object_or_404(
        Exercise,
        pk=request.POST.get("exercise_id"),
        course=playbook.cohort.course,
        is_active=True,
    )
    next_order = (playbook.exercise_steps.aggregate(value=Max("order"))["value"] or 0) + 1
    step = PlaybookExercise(playbook=playbook, exercise=exercise, order=next_order)
    step.full_clean()
    step.save()
    messages.success(request, f"{exercise.title} playbook'ga qo'shildi.")
    return redirect("classbook:playbook_edit", cohort_id=playbook.cohort_id, lesson_id=playbook.lesson_id)


@login_required
@user_passes_test(_is_teacher)
@require_POST
@transaction.atomic
def playbook_remove_exercise(request, step_id):
    step = get_object_or_404(
        PlaybookExercise.objects.select_for_update().select_related("playbook__cohort"),
        pk=step_id,
        playbook__cohort__in=teacher_cohort_queryset(request.user),
    )
    destination = (step.playbook.cohort_id, step.playbook.lesson_id)
    siblings = list(
        PlaybookExercise.objects.select_for_update()
        .filter(playbook_id=step.playbook_id)
        .exclude(pk=step.pk)
        .order_by("order", "id")
    )
    step.delete()
    # Qolgan step'larni 1..N ko'rinishiga qaytaramiz.
    for order, item in enumerate(siblings, 1):
        if item.order != order:
            PlaybookExercise.objects.filter(pk=item.pk).update(order=order)
    messages.success(request, "Mashq playbook'dan olib tashlandi.")
    return redirect("classbook:playbook_edit", cohort_id=destination[0], lesson_id=destination[1])


@login_required
@user_passes_test(_is_teacher)
@require_POST
def playbook_move_exercise(request, step_id, direction):
    if direction not in {"up", "down"}:
        raise Http404
    with transaction.atomic():
        step = get_object_or_404(
            PlaybookExercise.objects.select_for_update().select_related("playbook__cohort"),
            pk=step_id,
            playbook__cohort__in=teacher_cohort_queryset(request.user),
        )
        steps = list(
            PlaybookExercise.objects.select_for_update()
            .filter(playbook_id=step.playbook_id)
            .order_by("order", "id")
        )
        index = next(position for position, item in enumerate(steps) if item.id == step.id)
        target_index = index - 1 if direction == "up" else index + 1
        if 0 <= target_index < len(steps):
            neighbor = steps[target_index]
            step_order, neighbor_order = step.order, neighbor.order
            temporary_order = max(item.order for item in steps) + 1
            PlaybookExercise.objects.filter(pk=neighbor.pk).update(order=temporary_order)
            PlaybookExercise.objects.filter(pk=step.pk).update(order=neighbor_order)
            PlaybookExercise.objects.filter(pk=neighbor.pk).update(order=step_order)
    return redirect("classbook:playbook_edit", cohort_id=step.playbook.cohort_id, lesson_id=step.playbook.lesson_id)


@login_required
@user_passes_test(_is_teacher)
@require_POST
def session_start(request, cohort_id, lesson_id):
    cohort = get_object_or_404(teacher_cohort_queryset(request.user).select_related("course"), pk=cohort_id)
    lesson = get_object_or_404(Lesson.objects.select_related("module"), pk=lesson_id, module__course=cohort.course)
    result = start_class_session(actor=request.user, cohort=cohort, lesson=lesson)
    if not result.ok:
        messages.error(request, result.message)
        return redirect("classbook:playbook_edit", cohort_id=cohort.id, lesson_id=lesson.id)
    messages.success(request, result.message)
    return redirect("classbook:teacher_session", session_id=result.session.id)


def _session_context(session):
    current = current_activity_for_session(session)
    delivery_counts = {
        row["status"]: row["total"]
        for row in session.classbook_group_deliveries.values("status").annotate(total=Count("id"))
    }
    delivery_counts["queued"] = delivery_counts.get("pending", 0) + delivery_counts.get("sending", 0)
    return {
        "session": session,
        "activities": session.classbook_activities.select_related("exercise").annotate(
            response_count=Count("responses")
        ).order_by("order", "id"),
        "current_activity": current,
        "next_activity": next_activity_for_session(session),
        "attendance_count": session.checkins.count(),
        "roster_count": Enrollment.objects.filter(enrollment_active_access_q(), cohort=session.cohort).count(),
        "leaderboard": session_leaderboard(session, limit=10),
        "delivery_counts": delivery_counts,
    }


@login_required
@user_passes_test(_is_teacher)
def teacher_session(request, session_id):
    session = _teacher_session(request.user, session_id)
    context = _teacher_context(request.user)
    context.update(_session_context(session))
    return render(request, "classbook/teacher_session.html", context)


def _csv_safe(value):
    """Excel formulasi sifatida bajarilishi mumkin bo'lgan qiymatlarni zararsizlantiradi."""
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{text}"
    return text


def _csv_response(filename):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    return response


@login_required
@user_passes_test(_is_teacher)
def teacher_session_export(request, session_id):
    session = _teacher_session(request.user, session_id)
    activities = list(session.classbook_activities.select_related("exercise").order_by("order", "id"))
    enrollments = list(
        Enrollment.objects.filter(enrollment_active_access_q(), cohort=session.cohort)
        .select_related("student")
        .order_by("student__first_name", "student__last_name", "student__username")
    )
    response_map = {
        (item.enrollment_id, item.activity_id): item
        for item in StudentResponse.objects.filter(activity__session=session)
    }
    checkins = {item.enrollment_id: item for item in session.checkins.all()}
    ranking = {row["student"].id: row for row in session_leaderboard(session)}
    late_cutoff = session.started_at + datetime.timedelta(minutes=session.late_after_minutes)

    response = _csv_response(
        f"classbook-{slugify(session.cohort.name) or session.cohort_id}-{session.attendance_date}.csv"
    )
    writer = csv.writer(response)
    writer.writerow([
        "Ism",
        "Username",
        "Email",
        "Davomat",
        "O'rin",
        "Jami ball",
        "Maksimal ball",
        *[f"{item.order}. {item.snapshot.get('title', item.exercise.title)}" for item in activities],
    ])
    for enrollment in enrollments:
        checkin = checkins.get(enrollment.id)
        attendance = "Kelmadi" if not checkin else ("Kech" if checkin.checked_in_at > late_cutoff else "Keldi")
        leader = ranking.get(enrollment.student_id)
        scores = []
        for activity in activities:
            item = response_map.get((enrollment.id, activity.id))
            scores.append(f"{item.score}/{item.max_score}" if item else "")
        writer.writerow([
            _csv_safe(enrollment.student.get_full_name() or enrollment.student.username),
            _csv_safe(enrollment.student.username),
            _csv_safe(enrollment.student.email),
            attendance,
            leader["rank"] if leader else "",
            leader["score"] if leader else 0,
            leader["max_score"] if leader else 0,
            *scores,
        ])
    return response


@login_required
@user_passes_test(_is_teacher)
def teacher_session_state(request, session_id):
    session = _teacher_session(request.user, session_id)
    data = _session_context(session)
    activities = [{
        "id": item.id,
        "status": item.status,
        "responses": item.response_count,
    } for item in data["activities"]]
    return JsonResponse({
        "status": session.status,
        "attendance_count": data["attendance_count"],
        "roster_count": data["roster_count"],
        "activities": activities,
        "current_activity_id": data["current_activity"].id if data["current_activity"] else None,
        "leaderboard": [{
            "rank": row["rank"], "name": row["student"].get_full_name() or row["student"].username,
            "score": str(row["score"]), "max_score": str(row["max_score"]),
        } for row in data["leaderboard"]],
        "deliveries": data["delivery_counts"],
    })


@login_required
@user_passes_test(_is_teacher)
@require_POST
def activity_open(request, activity_id):
    activity = get_object_or_404(
        ActivityRun.objects.select_related("session__cohort"),
        pk=activity_id,
        session__cohort__in=teacher_cohort_queryset(request.user),
    )
    result = open_activity(actor=request.user, activity=activity)
    (messages.success if result.ok else messages.error)(request, result.message)
    return redirect("classbook:teacher_session", session_id=activity.session_id)


@login_required
@user_passes_test(_is_teacher)
@require_POST
def activity_close(request, activity_id):
    activity = get_object_or_404(
        ActivityRun.objects.select_related("session__cohort"),
        pk=activity_id,
        session__cohort__in=teacher_cohort_queryset(request.user),
    )
    result = close_activity(actor=request.user, activity=activity, publish=True)
    (messages.success if result.ok else messages.error)(request, result.message)
    return redirect("classbook:teacher_session", session_id=activity.session_id)


@login_required
@user_passes_test(_is_teacher)
def teacher_activity_result(request, activity_id):
    activity = _teacher_activity(request.user, activity_id)
    rows = activity_leaderboard(activity)
    for row in rows:
        row["breakdown"] = response_breakdown(activity, row["response"])
    context = _teacher_context(request.user)
    context.update({"activity": activity, "rows": rows})
    return render(request, "classbook/teacher_activity_result.html", context)


@login_required
@user_passes_test(_is_teacher)
def teacher_activity_export(request, activity_id):
    activity = _teacher_activity(request.user, activity_id)
    response = _csv_response(
        f"classbook-{activity.id}-{slugify(activity.snapshot.get('title', activity.exercise.title)) or 'natija'}.csv"
    )
    writer = csv.writer(response)
    writer.writerow([
        "O'rin",
        "Ism",
        "Username",
        "Email",
        "Ball",
        "Maksimal ball",
        "Aniqlik %",
        "Tezlik bonusi",
        "Javob vaqti (ms)",
        "Yuborilgan vaqt",
        "Javob",
        "To'g'ri javob",
    ])
    for row in activity_leaderboard(activity):
        item = row["response"]
        breakdown = response_breakdown(activity, item)
        writer.writerow([
            row["rank"],
            _csv_safe(row["student"].get_full_name() or row["student"].username),
            _csv_safe(row["student"].username),
            _csv_safe(row["student"].email),
            item.score,
            item.max_score,
            item.accuracy_percent,
            item.speed_bonus,
            item.response_ms,
            timezone.localtime(item.submitted_at).isoformat(timespec="seconds"),
            _csv_safe(breakdown["submitted"]),
            _csv_safe(breakdown["correct"]),
        ])
    return response


@login_required
@user_passes_test(_is_teacher)
@require_POST
def session_finish(request, session_id):
    session = _teacher_session(request.user, session_id)
    result = finish_class_session(actor=request.user, session=session)
    (messages.success if result.ok else messages.error)(request, result.message)
    return redirect("classbook:teacher_session", session_id=session.id)


def _student_session(request, session_id):
    session = get_object_or_404(
        TelegramLessonSession.objects.select_related("cohort", "lesson"), pk=session_id
    )
    if not can_join_session(request.user, session):
        raise Http404
    return session


def _shuffle_activity_config(activity, user):
    payload = activity.public_snapshot
    config = json.loads(json.dumps(payload.get("config", {})))
    rng = random.Random(f"classbook:{activity.id}:{user.id}")
    kind = payload.get("kind")
    if kind in {"single_choice", "multiple_choice", "poll"}:
        rng.shuffle(config.get("options", []))
    elif kind == "matching":
        rng.shuffle(config.get("right", []))
    elif kind in {"ordering", "unscramble"}:
        items = config.get("items", [])
        rng.shuffle(items)
        expected = activity.snapshot.get("answer_key", {}).get("order", [])
        if len(items) > 1 and [item["id"] for item in items] == expected:
            items.append(items.pop(0))
    elif kind == "categorization":
        rng.shuffle(config.get("items", []))
    payload["config"] = config
    payload["activity_id"] = activity.id
    payload["status"] = activity.status
    payload["closes_at"] = activity.closes_at.isoformat() if activity.closes_at else None
    return payload


@login_required
def live_home(request):
    active_cohort_ids = request.user.enrollments.filter(
        enrollment_active_access_q()
    ).values_list("cohort_id", flat=True)
    sessions = list(
        TelegramLessonSession.objects.filter(
            cohort_id__in=active_cohort_ids, status=TelegramLessonSession.STATUS_OPEN
        ).select_related("cohort", "lesson")
    )
    if len(sessions) == 1:
        return redirect("classbook:live_session", session_id=sessions[0].id)
    return render(request, "classbook/live_home.html", {"active_nav": "classbook_live", "sessions": sessions})


@login_required
def live_session(request, session_id):
    session = _student_session(request, session_id)
    current = current_activity_for_session(session)
    full_leaderboard = session_leaderboard(session, revealed_only=True)
    leaderboard = full_leaderboard[:10]
    my_rank = next((row for row in full_leaderboard if row["student"].id == request.user.id), None)
    return render(request, "classbook/live_session.html", {
        "active_nav": "classbook_live",
        "session": session,
        "current_activity": current,
        "leaderboard": leaderboard,
        "my_rank": my_rank,
    })


@login_required
def live_session_state(request, session_id):
    session = _student_session(request, session_id)
    current = current_activity_for_session(session)
    return JsonResponse({
        "status": session.status,
        "current_activity_id": current.id if current else None,
        "current_activity_url": (
            f"/classbook/live/activity/{current.id}/" if current else ""
        ),
    })


@login_required
def live_activity(request, activity_id):
    activity = get_object_or_404(
        ActivityRun.objects.select_related("session__cohort", "session__lesson", "exercise"), pk=activity_id
    )
    enrollment = active_enrollment_for(request.user, activity.session.cohort)
    if not enrollment:
        raise Http404
    if activity.status == ActivityRun.STATUS_REVEALED:
        return redirect("classbook:activity_result", activity_id=activity.id)
    if activity.status != ActivityRun.STATUS_OPEN:
        raise Http404
    response = StudentResponse.objects.filter(activity=activity, enrollment=enrollment).first()
    return render(request, "classbook/live_activity.html", {
        "active_nav": "classbook_live",
        "activity": activity,
        "exercise_payload": _shuffle_activity_config(activity, request.user),
        "response": response,
    })


@login_required
def live_activity_state(request, activity_id):
    activity = get_object_or_404(ActivityRun.objects.select_related("session__cohort"), pk=activity_id)
    enrollment = active_enrollment_for(request.user, activity.session.cohort)
    if not enrollment:
        raise Http404
    if activity.status not in {ActivityRun.STATUS_OPEN, ActivityRun.STATUS_REVEALED}:
        raise Http404
    return JsonResponse({
        "status": activity.status,
        "submitted": StudentResponse.objects.filter(activity=activity, enrollment=enrollment).exists(),
    })


@login_required
@require_POST
def live_activity_submit(request, activity_id):
    activity = get_object_or_404(ActivityRun.objects.select_related("session__cohort"), pk=activity_id)
    if not active_enrollment_for(request.user, activity.session.cohort):
        raise Http404
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "message": "Javob formati noto'g'ri."}, status=400)
    result = submit_response(user=request.user, activity=activity, answer=payload.get("answer"))
    status = 200 if result.ok else (403 if result.code == "no_access" else 400)
    return JsonResponse({"ok": result.ok, "code": result.code, "message": result.message}, status=status)


@login_required
def activity_result(request, activity_id):
    activity = get_object_or_404(
        ActivityRun.objects.select_related("session__cohort", "session__lesson", "exercise"), pk=activity_id
    )
    enrollment = active_enrollment_for(request.user, activity.session.cohort)
    teacher = can_manage_cohort(request.user, activity.session.cohort)
    if not enrollment and not teacher:
        raise Http404
    # Xodim cohortda test learner sifatida ham turgan bo'lishi mumkin. Teacher
    # havolasi baribir boshqaruv natijasiga olib borishi kerak.
    if teacher:
        return redirect("classbook:teacher_activity_result", activity_id=activity.id)
    if activity.status != ActivityRun.STATUS_REVEALED and not teacher:
        raise Http404
    response = None
    breakdown = None
    if enrollment:
        response = StudentResponse.objects.filter(activity=activity, enrollment=enrollment).first()
        if response:
            breakdown = response_breakdown(activity, response)
    return render(request, "classbook/activity_result.html", {
        "active_nav": "classbook_live",
        "activity": activity,
        "response": response,
        "breakdown": breakdown,
        "leaderboard": activity_leaderboard(activity, limit=10),
    })


@login_required
def activity_media(request, activity_id):
    activity = get_object_or_404(
        ActivityRun.objects.select_related("exercise", "session__cohort"), pk=activity_id
    )
    allowed = can_manage_cohort(request.user, activity.session.cohort)
    if not allowed and activity.status in {ActivityRun.STATUS_OPEN, ActivityRun.STATUS_REVEALED}:
        allowed = active_enrollment_for(request.user, activity.session.cohort) is not None
    media_name = (activity.snapshot or {}).get("media_name", "")
    if not allowed or not media_name:
        raise Http404
    field = Exercise._meta.get_field("media")
    snapshotted_file = FieldFile(activity.exercise, field, media_name)
    return serve_private_file(request, snapshotted_file)
