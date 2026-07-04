"""TeacherShell — o'qituvchi paneli view'lari.

Proto: azurelms-proto/teacher/*. Kirish huquqi backoffice bilan bir xil
(is_staff/superuser), lekin ma'lumot ko'lami o'qituvchining O'Z kurslari
bilan cheklanadi: superuser hammasini ko'radi; staff instructor bo'lgan
kurslarini; agar staff'ga hech qanday kurs biriktirilmagan bo'lsa (kichik
markaz rejimi) — barcha kurslar ko'rinadi, aks holda panel bo'sh qolardi.
"""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from cohorts.models import Attendance, Cohort, Enrollment, enrollment_active_access_q
from courses.models import (
    AssignmentSubmission,
    Course,
    ExamAttempt,
    Lesson,
    LessonProgress,
)


def _is_teacher(user):
    return user.is_staff or user.is_superuser


def _teacher_courses(user):
    if user.is_superuser:
        return Course.objects.all()
    own = Course.objects.filter(instructor=user)
    if own.exists():
        return own
    return Course.objects.all()


def _pending_exam_attempts(courses):
    return (
        ExamAttempt.objects.filter(
            exam__course__in=courses,
            is_completed=True,
            is_reviewed=False,
        )
        .select_related("student", "exam", "exam__course")
        .order_by("completed_time")
    )


def _pending_assignment_submissions(courses):
    return (
        AssignmentSubmission.objects.filter(
            assignment__lesson__module__course__in=courses,
            status=AssignmentSubmission.STATUS_PENDING,
        )
        .select_related("student", "assignment", "assignment__lesson__module__course")
        .order_by("submitted_at")
    )


def _base_context(user, active_nav):
    """Har bir teacher sahifasi uchun umumiy kontekst (nav + tekshirish badge)."""
    courses = _teacher_courses(user)
    return {
        "active_nav": active_nav,
        "teacher_courses": courses,
        "grading_pending_count": _pending_exam_attempts(courses).count()
        + _pending_assignment_submissions(courses).count(),
    }


# ---------------------------------------------------------------- dashboard


@login_required
@user_passes_test(_is_teacher)
def teacher_dashboard(request):
    context = _base_context(request.user, "teacher_dashboard")
    courses = context["teacher_courses"]

    cohorts = (
        Cohort.objects.filter(course__in=courses, is_active=True)
        .select_related("course")
        .annotate(
            members_count=Count(
                "members",
                filter=enrollment_active_access_q(prefix="members__"),
                distinct=True,
            )
        )
        .order_by("-start_date")
    )
    students_count = (
        Enrollment.objects.filter(enrollment_active_access_q(), cohort__course__in=courses)
        .values("student_id")
        .distinct()
        .count()
    )

    pending_exams = _pending_exam_attempts(courses)
    pending_assignments = _pending_assignment_submissions(courses)

    context.update(
        {
            "kpis": {
                "cohorts": cohorts.count(),
                "students": students_count,
                "pending_exams": pending_exams.count(),
                "pending_assignments": pending_assignments.count(),
            },
            "cohorts": cohorts[:6],
            "queue_exams": pending_exams[:5],
            "queue_assignments": pending_assignments[:5],
        }
    )
    return render(request, "teacher/dashboard.html", context)


# ---------------------------------------------------------------- guruhlar


@login_required
@user_passes_test(_is_teacher)
def teacher_cohorts(request):
    context = _base_context(request.user, "teacher_cohorts")
    cohorts = (
        Cohort.objects.filter(course__in=context["teacher_courses"])
        .select_related("course")
        .annotate(
            members_count=Count(
                "members",
                filter=enrollment_active_access_q(prefix="members__"),
                distinct=True,
            ),
            pending_count=Count(
                "members",
                filter=Q(members__status=Enrollment.STATUS_PENDING),
                distinct=True,
            ),
        )
        .order_by("-is_active", "-start_date")
    )
    context["cohorts"] = cohorts
    return render(request, "teacher/cohorts.html", context)


# ---------------------------------------------------------------- o'quvchilar


@login_required
@user_passes_test(_is_teacher)
def teacher_students(request):
    context = _base_context(request.user, "teacher_students")
    courses = context["teacher_courses"]

    enrollments = (
        Enrollment.objects.filter(cohort__course__in=courses)
        .select_related("student", "cohort", "cohort__course")
        .annotate(
            completed_lessons=Count(
                "lesson_progress",
                filter=Q(lesson_progress__is_completed=True),
                distinct=True,
            ),
            last_activity=Max("lesson_progress__last_accessed_at"),
        )
        .order_by("-joined_at")
    )

    cohort_id = request.GET.get("cohort")
    if cohort_id and cohort_id.isdigit():
        enrollments = enrollments.filter(cohort_id=int(cohort_id))
        context["selected_cohort_id"] = int(cohort_id)

    query = (request.GET.get("q") or "").strip()
    if query:
        enrollments = enrollments.filter(
            Q(student__first_name__icontains=query)
            | Q(student__last_name__icontains=query)
            | Q(student__username__icontains=query)
            | Q(student__email__icontains=query)
        )
        context["search_query"] = query

    lessons_by_course = {
        row["module__course"]: row["total"]
        for row in Lesson.objects.filter(module__course__in=courses)
        .values("module__course")
        .annotate(total=Count("id"))
    }
    enrollments = list(enrollments)
    for enrollment in enrollments:
        total = lessons_by_course.get(enrollment.cohort.course_id, 0)
        enrollment.total_lessons = total
        enrollment.progress_percent = (
            int(round(enrollment.completed_lessons / total * 100)) if total else 0
        )

    paginator = Paginator(enrollments, 25)
    context["page_obj"] = paginator.get_page(request.GET.get("page"))
    context["cohort_choices"] = Cohort.objects.filter(course__in=courses).select_related("course").order_by("-start_date")
    context["total_count"] = paginator.count
    return render(request, "teacher/students.html", context)


# ---------------------------------------------------------------- kontent


@login_required
@user_passes_test(_is_teacher)
def teacher_courses_view(request):
    context = _base_context(request.user, "teacher_courses")
    # NB: lessons_count/students_count Course modelida property — annotate nomi boshqa
    courses = (
        context["teacher_courses"]
        .annotate(
            lessons_total=Count("modules__lessons", distinct=True),
            students_total=Count(
                "cohorts__members",
                filter=enrollment_active_access_q(prefix="cohorts__members__"),
                distinct=True,
            ),
            exams_total=Count("exams", distinct=True),
        )
        .order_by("-is_active", "title")
    )
    context["courses"] = courses
    return render(request, "teacher/courses.html", context)


# ---------------------------------------------------------------- tekshirish


@login_required
@user_passes_test(_is_teacher)
def teacher_grading(request):
    context = _base_context(request.user, "teacher_grading")
    courses = context["teacher_courses"]
    context["pending_exams"] = _pending_exam_attempts(courses)
    context["pending_assignments"] = _pending_assignment_submissions(courses)
    context["recently_reviewed"] = (
        ExamAttempt.objects.filter(exam__course__in=courses, is_reviewed=True)
        .select_related("student", "exam")
        .order_by("-reviewed_at")[:5]
    )
    return render(request, "teacher/grading.html", context)


def _clamp_score(raw, maximum):
    try:
        value = Decimal(str(raw).replace(",", "."))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if value < 0:
        value = Decimal("0")
    if value > maximum:
        value = Decimal(maximum)
    return value


@login_required
@user_passes_test(_is_teacher)
def teacher_grade_exam(request, attempt_id):
    context = _base_context(request.user, "teacher_grading")
    attempt = get_object_or_404(
        ExamAttempt.objects.select_related("student", "exam", "exam__course"),
        id=attempt_id,
        exam__course__in=context["teacher_courses"],
        is_completed=True,
    )
    attempt.ensure_section_reviews()

    if request.method == "POST":
        # 1) Javob ballari + per-javob izohlar (writing/speaking va h.k.)
        for answer in attempt.answers.select_related("question"):
            score_raw = request.POST.get(f"answer_score_{answer.id}")
            feedback_raw = request.POST.get(f"answer_feedback_{answer.id}")
            changed = []
            if score_raw not in (None, ""):
                score = _clamp_score(score_raw, answer.question.points)
                if score is not None and score != answer.awarded_score:
                    answer.awarded_score = score
                    answer.is_graded = True
                    changed += ["awarded_score", "is_graded"]
            if feedback_raw is not None and feedback_raw != answer.grader_feedback:
                answer.grader_feedback = feedback_raw
                changed.append("grader_feedback")
            if changed:
                answer.save(update_fields=changed + ["updated_at"])

        # 2) Bo'lim ballari + izohlari
        for review in attempt.section_reviews.select_related("section"):
            score_raw = request.POST.get(f"section_score_{review.id}")
            feedback_raw = request.POST.get(f"section_feedback_{review.id}")
            changed = []
            if score_raw not in (None, ""):
                score = _clamp_score(score_raw, review.section.max_score)
                if score is not None and score != review.awarded_score:
                    review.awarded_score = score
                    changed.append("awarded_score")
            if feedback_raw is not None and feedback_raw != review.feedback:
                review.feedback = feedback_raw
                changed.append("feedback")
            if changed:
                review.save(update_fields=changed + ["updated_at"])

        # 3) Yakuniy izoh
        review_notes = request.POST.get("review_notes")
        if review_notes is not None and review_notes != attempt.review_notes:
            attempt.review_notes = review_notes
            attempt.save(update_fields=["review_notes"])

        if request.POST.get("action") == "finalize":
            certificate, created = attempt.finalize_review(reviewed_by=request.user)
            attempt.refresh_from_db()
            note = f"Natija tasdiqlandi: {attempt.score}% — {'o‘tdi' if attempt.passed else 'o‘tmadi'}."
            if created and certificate:
                note += " Sertifikat berildi."
            messages.success(request, note)
            return redirect("teacher_grading")

        messages.success(request, "Baholar saqlandi (hali tasdiqlanmadi).")
        return redirect("teacher_grade_exam", attempt_id=attempt.id)

    # GET — bo'limma-bo'lim ma'lumot yig'ish
    reviews = {review.section_id: review for review in attempt.section_reviews.select_related("section")}
    answers_by_section = {}
    for answer in attempt.answers.select_related("question", "selected_choice", "question__exam_section"):
        answers_by_section.setdefault(answer.question.exam_section_id, []).append(answer)
    reading_totals = {
        row["item__task__section"]: row["total"]
        for row in attempt.reading_responses.values("item__task__section").annotate(total=Sum("awarded_score"))
    }

    sections = []
    for section in attempt.exam.sections.all().order_by("order"):
        review = reviews.get(section.id)
        section_answers = answers_by_section.get(section.id, [])
        manual = section.section_type in {"writing", "speaking"}
        sections.append(
            {
                "section": section,
                "review": review,
                "answers": section_answers,
                "manual": manual,
                "reading_total": reading_totals.get(section.id),
                "has_rich": section.id in reading_totals,
            }
        )

    exam_max = sum(section.max_score for section in attempt.exam.sections.all())
    section_total = attempt.section_reviews.aggregate(total=Sum("awarded_score"))["total"] or 0
    context.update(
        {
            "attempt": attempt,
            "sections": sections,
            "exam_max": exam_max,
            "section_total": section_total,
            "projected_percent": round(section_total / exam_max * 100, 1) if exam_max else 0,
        }
    )
    return render(request, "teacher/grade_exam.html", context)


@login_required
@user_passes_test(_is_teacher)
def teacher_grade_assignment(request, submission_id):
    context = _base_context(request.user, "teacher_grading")
    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related(
            "student", "assignment", "assignment__lesson", "assignment__lesson__module__course"
        ),
        id=submission_id,
        assignment__lesson__module__course__in=context["teacher_courses"],
    )

    if request.method == "POST":
        submission.teacher_feedback = request.POST.get("teacher_feedback", submission.teacher_feedback)
        xp_raw = request.POST.get("awarded_xp")
        if xp_raw not in (None, ""):
            try:
                submission.awarded_xp = max(0, min(int(xp_raw), submission.assignment.max_xp))
            except (TypeError, ValueError):
                pass

        action = request.POST.get("action")
        if action == "approve":
            submission.status = AssignmentSubmission.STATUS_APPROVED
        elif action == "revision":
            submission.status = AssignmentSubmission.STATUS_NEEDS_REVISION
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.save()
        messages.success(
            request,
            "Tasdiqlandi — keyingi dars ochildi." if action == "approve" else "Qayta ishlashga qaytarildi.",
        )
        return redirect("teacher_grading")

    context["submission"] = submission
    return render(request, "teacher/grade_assignment.html", context)


# ---------------------------------------------------------------- davomat


@login_required
@user_passes_test(_is_teacher)
def teacher_attendance(request):
    context = _base_context(request.user, "teacher_attendance")
    courses = context["teacher_courses"]

    cohorts = list(
        Cohort.objects.filter(course__in=courses, is_active=True)
        .select_related("course")
        .order_by("-start_date")
    )
    context["cohorts"] = cohorts

    cohort = None
    cohort_id = request.GET.get("cohort") or request.POST.get("cohort")
    if cohort_id and str(cohort_id).isdigit():
        cohort = next((c for c in cohorts if c.id == int(cohort_id)), None)
    if cohort is None and cohorts:
        cohort = cohorts[0]
    context["cohort"] = cohort
    if cohort is None:
        return render(request, "teacher/attendance.html", context)

    lessons = list(
        Lesson.objects.filter(module__course=cohort.course)
        .select_related("module")
        .order_by("module__order", "order")
    )
    context["lessons"] = lessons

    lesson = None
    lesson_id = request.GET.get("lesson") or request.POST.get("lesson")
    if lesson_id and str(lesson_id).isdigit():
        lesson = next((l for l in lessons if l.id == int(lesson_id)), None)
    if lesson is None and lessons:
        lesson = lessons[0]
    context["lesson"] = lesson

    enrollments = list(
        Enrollment.objects.filter(enrollment_active_access_q(), cohort=cohort)
        .select_related("student")
        .order_by("student__first_name", "student__username")
    )

    if request.method == "POST" and lesson:
        valid = dict(Attendance.STATUS_CHOICES)
        marked = 0
        for enrollment in enrollments:
            status = request.POST.get(f"att_{enrollment.id}")
            if status not in valid:
                continue
            record = Attendance.objects.filter(enrollment=enrollment, lesson=lesson).first()
            if record:
                if record.status != status:
                    record.status = status
                    record.marked_by = request.user
                    record.save(update_fields=["status", "marked_by", "marked_at"])
            else:
                Attendance.objects.create(
                    enrollment=enrollment,
                    lesson=lesson,
                    status=status,
                    marked_by=request.user,
                )
            marked += 1
        messages.success(request, f"Davomat saqlandi ({marked} o'quvchi).")
        return redirect(f"{request.path}?cohort={cohort.id}&lesson={lesson.id}")

    current = {}
    if lesson:
        current = {
            record.enrollment_id: record.status
            for record in Attendance.objects.filter(enrollment__in=enrollments, lesson=lesson)
        }

    # Har bir o'quvchining kurs bo'yicha umumiy davomati (belgilanganlar ichida)
    stats = {
        row["enrollment"]: row
        for row in Attendance.objects.filter(enrollment__in=enrollments)
        .values("enrollment")
        .annotate(
            total=Count("id"),
            present=Count("id", filter=Q(status__in=[Attendance.STATUS_PRESENT, Attendance.STATUS_PARTIAL])),
        )
    }
    rows = []
    for enrollment in enrollments:
        stat = stats.get(enrollment.id)
        percent = int(round(stat["present"] / stat["total"] * 100)) if stat and stat["total"] else None
        rows.append(
            {
                "enrollment": enrollment,
                "status": current.get(enrollment.id, ""),
                "percent": percent,
            }
        )
    context["rows"] = rows
    return render(request, "teacher/attendance.html", context)
