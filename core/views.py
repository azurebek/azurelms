from datetime import timedelta

from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timesince import timesince
from django.utils import timezone

from blog.models import BlogPost
from cohorts.models import Cohort, Enrollment, PaymentReceipt
from courses.models import Course, Exam, ExamSection, Lesson, LessonProgress, Module
from messenger.rag import get_rag_index_status
from subscriptions.models import PromoCode

from .backoffice_forms import (
    CourseBackofficeForm,
    ExamBackofficeForm,
    ExamSectionBackofficeForm,
    LessonBackofficeForm,
)


def _is_backoffice_user(user):
    return user.is_staff or user.is_superuser


def _backoffice_counts():
    User = get_user_model()
    pending_receipts_count = PaymentReceipt.objects.filter(is_verified=False).count()
    pending_posts_count = BlogPost.objects.exclude(status=BlogPost.STATUS_PUBLISHED).count()
    students_count = User.objects.filter(is_staff=False, is_superuser=False).count()
    teachers_count = User.objects.filter(is_staff=True, is_superuser=False).count()
    admins_count = User.objects.filter(is_superuser=True).count()
    return {
        "users": students_count + teachers_count + admins_count,
        "students": students_count,
        "teachers": teachers_count,
        "admins": admins_count,
        "courses": Course.objects.count(),
        "lessons": Lesson.objects.count(),
        "exams": Exam.objects.count(),
        "cohorts": Cohort.objects.count(),
        "pending_receipts": pending_receipts_count,
        "pending_posts": pending_posts_count,
        "promo_codes": PromoCode.objects.count(),
        "completed_lessons": LessonProgress.objects.filter(is_completed=True).count(),
    }


def _backoffice_context(active):
    return {
        "active_nav": "backoffice",
        "bo_active": active,
        "counts": _backoffice_counts(),
    }


def page_not_found(request, exception=None):
    return render(request, "errors/404.html", status=404)


def permission_denied(request, exception=None):
    return render(request, "errors/403.html", status=403)


def server_error(request):
    return render(request, "errors/500.html", status=500)


def maintenance(request):
    return render(request, "errors/maintenance.html", status=503)


def offline(request):
    return render(request, "errors/offline.html")


@login_required
@user_passes_test(_is_backoffice_user)
def backoffice_dashboard(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=6)
    User = get_user_model()

    active_enrollments = Enrollment.objects.with_active_access()
    total_enrollments = Enrollment.objects.count()
    completed_enrollments = Enrollment.objects.filter(
        completion_state=Enrollment.COMPLETION_STATE_COMPLETED,
    ).count()
    completion_rate = round((completed_enrollments / total_enrollments) * 100) if total_enrollments else 0

    pending_receipts = PaymentReceipt.objects.filter(is_verified=False).select_related(
        "enrollment__student",
        "enrollment__cohort__course",
    ).order_by("submitted_at")
    recent_users = User.objects.filter(is_staff=False, is_superuser=False).order_by("-date_joined")[:5]
    weekly_revenue = (
        PaymentReceipt.objects.filter(is_verified=True, submitted_at__date__gte=week_start)
        .aggregate(total=Sum("amount"))
        .get("total")
        or 0
    )
    today_revenue = (
        PaymentReceipt.objects.filter(is_verified=True, submitted_at__date=today)
        .aggregate(total=Sum("amount"))
        .get("total")
        or 0
    )
    pending_receipts_count = pending_receipts.count()
    pending_posts_count = BlogPost.objects.exclude(status=BlogPost.STATUS_PUBLISHED).count()
    rag_status = get_rag_index_status()

    context = {
        "active_nav": "backoffice",
        "today": today,
        "kpis": {
            "active_students": active_enrollments.values("student").distinct().count(),
            "today_revenue": today_revenue,
            "new_signups": User.objects.filter(date_joined__date=today, is_staff=False, is_superuser=False).count(),
            "completion_rate": completion_rate,
        },
        "counts": {
            "students": User.objects.filter(is_staff=False, is_superuser=False).count(),
            "teachers": User.objects.filter(is_staff=True, is_superuser=False).count(),
            "admins": User.objects.filter(is_superuser=True).count(),
            "courses": Course.objects.count(),
            "lessons": Lesson.objects.count(),
            "exams": Exam.objects.count(),
            "cohorts": Cohort.objects.count(),
            "pending_receipts": pending_receipts_count,
            "pending_posts": pending_posts_count,
            "promo_codes": PromoCode.objects.count(),
            "completed_lessons": LessonProgress.objects.filter(is_completed=True).count(),
        },
        "attention_count": pending_receipts_count + pending_posts_count,
        "pending_receipts": pending_receipts[:4],
        "recent_users": recent_users,
        "active_cohorts": Cohort.objects.filter(is_active=True).select_related("course").order_by("start_date")[:4],
        "weekly_revenue": weekly_revenue,
        "sparkline": [38, 52, 44, 68, 60, 78, 92],
        "rag_status": rag_status,
    }
    return render(request, "backoffice/dashboard.html", context)


@login_required
@user_passes_test(_is_backoffice_user)
def backoffice_course_editor(request, course_id=None):
    course = get_object_or_404(Course, pk=course_id) if course_id else None
    form = CourseBackofficeForm(request.POST or None, instance=course)
    if not course and not form.initial.get("instructor"):
        form.initial["instructor"] = request.user.pk

    if request.method == "POST" and form.is_valid():
        course = form.save(commit=False)
        if "save_draft" in request.POST:
            course.is_active = False
        if not course.instructor_id:
            course.instructor = request.user
        course.save()
        if not course.modules.exists():
            Module.objects.create(course=course, title="1. Boshlanish", order=1)
        messages.success(request, "Kurs saqlandi.")
        return redirect("backoffice_course_edit", course_id=course.pk)

    modules = (
        course.modules.prefetch_related("lessons").order_by("order")
        if course
        else Module.objects.none()
    )
    lessons_count = Lesson.objects.filter(module__course=course).count() if course else 0
    students_count = (
        Enrollment.objects.with_active_access()
        .filter(cohort__course=course)
        .values("student")
        .distinct()
        .count()
        if course
        else 0
    )
    context = {
        **_backoffice_context("courses"),
        "course": course,
        "form": form,
        "modules": modules,
        "lessons_count": lessons_count,
        "students_count": students_count,
    }
    return render(request, "backoffice/course_form.html", context)


@login_required
@user_passes_test(_is_backoffice_user)
def backoffice_lesson_editor(request, lesson_id=None):
    lesson = (
        get_object_or_404(Lesson.objects.select_related("module__course"), pk=lesson_id)
        if lesson_id
        else Lesson.objects.select_related("module__course").order_by("module__course__title", "module__order", "order").first()
    )
    form = LessonBackofficeForm(request.POST or None, instance=lesson)

    if request.method == "POST" and form.is_valid():
        lesson = form.save()
        messages.success(request, "Dars saqlandi.")
        return redirect("backoffice_lesson_edit", lesson_id=lesson.pk)

    courses = Course.objects.prefetch_related("modules__lessons").order_by("title")
    assignments = list(lesson.assignments.all()) if lesson else []
    quizzes = list(lesson.quizzes.all()) if lesson else []
    context = {
        **_backoffice_context("lessons"),
        "lesson": lesson,
        "form": form,
        "courses": courses,
        "assignments": assignments,
        "quizzes": quizzes,
    }
    return render(request, "backoffice/lesson_form.html", context)


@login_required
@user_passes_test(_is_backoffice_user)
def backoffice_exam_editor(request, exam_id=None):
    exam = (
        get_object_or_404(Exam.objects.select_related("course"), pk=exam_id)
        if exam_id
        else Exam.objects.select_related("course").order_by("course__title", "title").first()
    )
    section = exam.sections.order_by("order").first() if exam else None
    exam_form = ExamBackofficeForm(request.POST or None, instance=exam)
    section_form = ExamSectionBackofficeForm(request.POST or None, instance=section, prefix="section")

    if request.method == "POST" and exam_form.is_valid() and section_form.is_valid():
        exam = exam_form.save()
        section = section_form.save(commit=False)
        section.exam = exam
        section.save()
        messages.success(request, "Imtihon saqlandi.")
        return redirect("backoffice_exam_edit", exam_id=exam.pk)

    sections = exam.sections.order_by("order") if exam else ExamSection.objects.none()
    total_score = sections.aggregate(total=Sum("max_score")).get("total") or 0
    total_time = sections.aggregate(total=Sum("time_limit_minutes")).get("total") or 0
    questions_count = section.questions.count() if section else 0
    context = {
        **_backoffice_context("exams"),
        "exam": exam,
        "section": section,
        "sections": sections,
        "section_types": ExamSection.SECTION_TYPES,
        "exam_form": exam_form,
        "section_form": section_form,
        "total_score": total_score,
        "total_time": total_time,
        "questions_count": questions_count,
    }
    return render(request, "backoffice/exam_form.html", context)


def _user_role_data(user):
    if user.is_superuser:
        return "Admin", "role-admin", "bi-shield-lock-fill"
    if user.is_staff:
        return "O'qituvchi", "role-teacher", "bi-person-video3"
    return "Talaba", "role-student", "bi-mortarboard-fill"


def _user_initials(user):
    first = (user.first_name or "").strip()
    last = (user.last_name or "").strip()
    if first:
        return f"{first[:1]}{last[:1]}".upper()
    return (user.username or user.email or "U")[:2].upper()


@login_required
@user_passes_test(_is_backoffice_user)
def backoffice_users(request):
    User = get_user_model()
    role = request.GET.get("role", "all")
    status = request.GET.get("status", "all")
    query = request.GET.get("q", "").strip()

    users_qs = User.objects.annotate(
        course_count=Count("enrollments__cohort__course", distinct=True),
    ).order_by("-date_joined")

    if query:
        users_qs = users_qs.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(phone_number__icontains=query)
        )
    if role == "students":
        users_qs = users_qs.filter(is_staff=False, is_superuser=False)
    elif role == "teachers":
        users_qs = users_qs.filter(is_staff=True, is_superuser=False)
    elif role == "admins":
        users_qs = users_qs.filter(is_superuser=True)
    if status == "active":
        users_qs = users_qs.filter(is_active=True)
    elif status == "blocked":
        users_qs = users_qs.filter(is_active=False)

    page_obj = Paginator(users_qs, 12).get_page(request.GET.get("page"))
    user_rows = []
    user_rows_json = []
    for user in page_obj.object_list:
        role_label, role_class, role_icon = _user_role_data(user)
        status_label = "Faol" if user.is_active else "Bloklangan"
        status_class = "status-active" if user.is_active else "status-banned"
        name = user.get_full_name().strip() or user.username
        row = {
            "id": user.pk,
            "dom_id": f"user-{user.pk}",
            "name": name,
            "email": user.email or "-",
            "phone": user.phone_number or "",
            "initials": _user_initials(user),
            "role_label": role_label,
            "role_class": role_class,
            "role_icon": role_icon,
            "status_label": status_label,
            "status_class": status_class,
            "course_count": user.course_count,
            "date_joined": user.date_joined,
            "last_login": user.last_login,
        }
        user_rows.append(row)
        user_rows_json.append(
            {
                **row,
                "joined_display": timezone.localtime(user.date_joined).strftime("%d.%m.%Y"),
                "last_login_display": (
                    f"{timesince(user.last_login)} oldin" if user.last_login else "Kirmagan"
                ),
            }
        )

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    week_start = timezone.now() - timedelta(days=7)
    context = {
        **_backoffice_context("users"),
        "filters": {"q": query, "role": role, "status": status},
        "page_obj": page_obj,
        "user_rows": user_rows,
        "user_rows_json": user_rows_json,
        "user_stats": {
            "total": total_users,
            "active": active_users,
            "blocked": User.objects.filter(is_active=False).count(),
            "new_this_week": User.objects.filter(date_joined__gte=week_start).count(),
            "active_percent": round((active_users / total_users) * 100, 1) if total_users else 0,
        },
    }
    return render(request, "backoffice/users.html", context)
