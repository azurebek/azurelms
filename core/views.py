from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Max, OuterRef, Q, Subquery, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timesince import timesince
from django.utils import timezone

from blog.models import BlogPost
from cohorts.models import Cohort, Enrollment, PaymentReceipt
from courses.models import Course, Exam, ExamSection, Lesson, LessonProgress, Module
from messenger.models import ChatRoom, Message
from messenger.rag import get_rag_index_status
from subscriptions.models import PromoCode
from frontend.models import LandingPage, SiteSettings

from .backoffice_forms import (
    CourseBackofficeForm,
    ExamBackofficeForm,
    ExamSectionBackofficeForm,
    LessonBackofficeForm,
)
from .brand_forms import BrandSettingsForm
from .landing_forms import LandingPageForm
from .control_center import build_control_center_snapshot


def _is_backoffice_user(user):
    return user.is_staff or user.is_superuser


def _is_control_center_owner(user):
    return user.is_active and user.is_superuser


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
        "chat_rooms": ChatRoom.objects.count(),
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
@user_passes_test(_is_control_center_owner)
def backoffice_control(request):
    """Owner-only, read-only operational control-plane snapshot."""
    context = {
        "active_nav": "backoffice",
        "bo_active": "control",
        "counts": {},
        "snapshot": build_control_center_snapshot(),
    }
    return render(request, "backoffice/control_center.html", context)


@login_required
@user_passes_test(_is_control_center_owner)
def backoffice_brand(request):
    """Owner-only canonical brand and logo control surface."""
    brand_settings = SiteSettings.load()
    if request.method == "POST":
        form = BrandSettingsForm(request.POST, request.FILES, instance=brand_settings)
        if form.is_valid():
            changed_fields = form.changed_brand_fields
            if changed_fields:
                with transaction.atomic():
                    brand_settings = form.save()
                    field_labels = [form.fields[name].label for name in changed_fields]
                    reason = form.cleaned_data["change_reason"].strip()
                    LogEntry.objects.log_actions(
                        user_id=request.user.pk,
                        queryset=SiteSettings.objects.filter(pk=brand_settings.pk),
                        action_flag=CHANGE,
                        change_message=(
                            f"Markaziy brend yangilandi: {', '.join(field_labels)}. "
                            f"Sabab: {reason}"
                        ),
                        single_object=True,
                    )
                messages.success(request, "Brend yangilandi. Barcha ulangan logo yuzalari endi shu qiymatni oladi.")
            else:
                messages.info(request, "Brend qiymatlarida o'zgarish topilmadi; hech narsa yozilmadi.")
            return redirect("backoffice_brand")
    else:
        form = BrandSettingsForm(instance=brand_settings)

    content_type = ContentType.objects.get_for_model(SiteSettings)
    context = {
        "active_nav": "backoffice",
        "bo_active": "brand",
        "counts": {},
        "form": form,
        "brand_settings": brand_settings,
        "recent_brand_changes": LogEntry.objects.filter(
            content_type=content_type,
            object_id=str(brand_settings.pk),
            action_flag=CHANGE,
        ).select_related("user")[:8],
    }
    return render(request, "backoffice/brand_control.html", context)


@login_required
@user_passes_test(_is_control_center_owner)
def backoffice_landing(request):
    """Owner-only bosh sahifa (landing) matn editori."""
    landing = LandingPage.load()
    if request.method == "POST":
        form = LandingPageForm(request.POST, instance=landing)
        if form.is_valid():
            changed_fields = form.changed_landing_fields
            if changed_fields:
                with transaction.atomic():
                    landing = form.save()
                    field_labels = [form.fields[name].label for name in changed_fields]
                    reason = form.cleaned_data["change_reason"].strip()
                    LogEntry.objects.log_actions(
                        user_id=request.user.pk,
                        queryset=LandingPage.objects.filter(pk=landing.pk),
                        action_flag=CHANGE,
                        change_message=(
                            f"Bosh sahifa yangilandi: {', '.join(field_labels)}. "
                            f"Sabab: {reason}"
                        ),
                        single_object=True,
                    )
                messages.success(request, "Bosh sahifa yangilandi. O'zgarishlar saytda darhol ko'rinadi.")
            else:
                messages.info(request, "Bosh sahifa qiymatlarida o'zgarish topilmadi; hech narsa yozilmadi.")
            return redirect("backoffice_landing")
    else:
        form = LandingPageForm(instance=landing)

    content_type = ContentType.objects.get_for_model(LandingPage)
    context = {
        "active_nav": "backoffice",
        "bo_active": "landing",
        "counts": {},
        "form": form,
        "recent_landing_changes": LogEntry.objects.filter(
            content_type=content_type,
            object_id=str(landing.pk),
            action_flag=CHANGE,
        ).select_related("user")[:8],
    }
    return render(request, "backoffice/landing_editor.html", context)


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
            "chat_rooms": ChatRoom.objects.count(),
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
def backoffice_chats(request):
    query = request.GET.get("q", "").strip()
    room_type = request.GET.get("type", "all")
    latest_message = Message.objects.filter(room=OuterRef("pk")).order_by("-created_at")

    rooms_qs = (
        ChatRoom.objects.select_related("cohort", "cohort__course")
        .prefetch_related("participants")
        .annotate(
            message_count=Count("messages", distinct=True),
            participant_count=Count("participants", distinct=True),
            last_message_at=Max("messages__created_at"),
            last_message_text=Subquery(latest_message.values("text")[:1]),
            last_sender_name=Subquery(
                latest_message.values("sender__username")[:1],
            ),
        )
    )
    if room_type in {"ai", "group", "private"}:
        rooms_qs = rooms_qs.filter(room_type=room_type)
    if query:
        rooms_qs = rooms_qs.filter(
            Q(name__icontains=query)
            | Q(messages__text__icontains=query)
            | Q(participants__username__icontains=query)
            | Q(participants__email__icontains=query)
            | Q(cohort__name__icontains=query)
            | Q(cohort__course__title__icontains=query)
        ).distinct()

    page_obj = Paginator(rooms_qs.order_by("-last_message_at", "-created_at"), 12).get_page(request.GET.get("page"))
    today = timezone.localdate()
    context = {
        **_backoffice_context("chats"),
        "filters": {"q": query, "type": room_type},
        "page_obj": page_obj,
        "room_type_choices": (
            ("all", "Barcha chatlar"),
            ("ai", "AI suhbatlar"),
            ("group", "Guruh chatlari"),
            ("private", "Tutor/private"),
        ),
        "chat_stats": {
            "total": ChatRoom.objects.count(),
            "ai": ChatRoom.objects.filter(room_type="ai").count(),
            "group": ChatRoom.objects.filter(room_type="group").count(),
            "private": ChatRoom.objects.filter(room_type="private").count(),
            "messages_today": Message.objects.filter(created_at__date=today).count(),
            "attachments": Message.objects.filter(attachment__isnull=False).exclude(attachment="").count(),
        },
    }
    return render(request, "backoffice/chats.html", context)


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


@login_required
@user_passes_test(_is_backoffice_user)
def backoffice_ai_control(request):
    """AI boshqaruv markazi — global limitlar, tarif siyosatlari, usage, reset/bonus."""
    from aicontrol.models import AISettings, AIPlanPolicy, AIUsageResetEvent, AIUserAllowance
    from aicontrol.service import apply_reset_event
    from messenger.models import AIResponseRun
    from subscriptions.models import Plan

    ai_settings = AISettings.load()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "save_settings":
            ai_settings.enforcement_enabled = "enforcement_enabled" in request.POST
            ai_settings.exempt_staff = "exempt_staff" in request.POST
            ai_settings.default_5h_token_limit = _safe_int(request.POST.get("default_5h_token_limit")) or 0
            ai_settings.default_weekly_token_limit = _safe_int(request.POST.get("default_weekly_token_limit")) or 0
            ai_settings.default_model = (request.POST.get("default_model") or "").strip()[:80]
            ai_settings.default_effort = (request.POST.get("default_effort") or "").strip()[:20]
            ai_settings.updated_by = request.user
            ai_settings.save()
            messages.success(request, "AI global sozlamalari saqlandi.")
            return redirect("backoffice_ai_control")

        if action == "save_policy":
            plan = Plan.objects.filter(id=request.POST.get("plan_id")).first()
            if plan:
                AIPlanPolicy.objects.update_or_create(
                    plan=plan,
                    defaults={
                        "token_limit_5h": _safe_int(request.POST.get("token_limit_5h")) or 0,
                        "token_limit_weekly": _safe_int(request.POST.get("token_limit_weekly")) or 0,
                        "is_active": "is_active" in request.POST,
                    },
                )
                messages.success(request, f"{plan.name} tarif limiti saqlandi.")
            return redirect("backoffice_ai_control")

        if action == "apply_event":
            scope = request.POST.get("scope")
            kind = request.POST.get("kind")
            window = request.POST.get("window") or AIUsageResetEvent.WINDOW_BOTH
            event = AIUsageResetEvent(
                scope=scope,
                kind=kind,
                window=window,
                bonus_tokens=_safe_int(request.POST.get("bonus_tokens")) or 0,
                reason=(request.POST.get("reason") or "").strip()[:200],
                created_by=request.user,
            )
            if scope == AIUsageResetEvent.SCOPE_COHORT:
                event.cohort = Cohort.objects.filter(id=request.POST.get("cohort_id")).first()
            elif scope == AIUsageResetEvent.SCOPE_PLAN:
                event.plan = Plan.objects.filter(id=request.POST.get("plan_id")).first()
            event.save()
            count = apply_reset_event(event)
            verb = "Reset" if kind == AIUsageResetEvent.KIND_RESET else "Bonus"
            messages.success(request, f"{verb} qo'llandi — {count} foydalanuvchiga ta'sir qildi.")
            return redirect("backoffice_ai_control")

    # --- GET: usage overview ---
    now = timezone.now()
    week_start = now - timedelta(days=7)
    hour5 = now - timedelta(hours=5)

    week_runs = AIResponseRun.objects.filter(created_at__gte=week_start)
    tokens_week = week_runs.aggregate(t=Sum("total_tokens"))["t"] or 0
    tokens_5h = (
        AIResponseRun.objects.filter(created_at__gte=hour5).aggregate(t=Sum("total_tokens"))["t"] or 0
    )
    active_ai_users = week_runs.values("student").distinct().count()
    blocked_count = AIUserAllowance.objects.filter(is_blocked=True).count()

    top_users = list(
        week_runs.values("student__id", "student__username", "student__first_name", "student__last_name")
        .annotate(tokens=Sum("total_tokens"), runs=Count("id"))
        .order_by("-tokens")[:10]
    )

    # Tarif siyosatlari (mavjud + hali yo'q tariflar)
    policies = {p.plan_id: p for p in AIPlanPolicy.objects.select_related("plan")}
    plan_rows = []
    for plan in Plan.objects.order_by("order", "price"):
        policy = policies.get(plan.id)
        plan_rows.append({"plan": plan, "policy": policy})

    context = {
        **_backoffice_context("ai_control"),
        "ai_settings": ai_settings,
        "plan_rows": plan_rows,
        "cohorts": Cohort.objects.select_related("course").order_by("-start_date")[:100],
        "all_plans": Plan.objects.order_by("order", "price"),
        "usage": {
            "tokens_week": tokens_week,
            "tokens_5h": tokens_5h,
            "active_users": active_ai_users,
            "blocked": blocked_count,
        },
        "top_users": top_users,
        "recent_events": AIUsageResetEvent.objects.select_related("cohort", "plan", "created_by")[:8],
    }
    return render(request, "backoffice/ai_control.html", context)
