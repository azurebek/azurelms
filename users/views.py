from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.urls import reverse

from .models import CustomUser, Profile
from education.models import Enrollment, LessonProgress
from billing.models import BillingAccount


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("users:dashboard")

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""

        if not email or not password:
            messages.error(request, "Email va parol majburiy.")
            return render(request, "users/auth/signup.html")

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Bu email band.")
            return render(request, "users/auth/signup.html")

        with transaction.atomic():
            user = CustomUser.objects.create_user(email=email, password=password)
            # profile signal bilan yaratilgan bo'ladi

        user = authenticate(request, email=email, password=password)
        login(request, user)
        return redirect("users:onboarding")

    return render(request, "users/auth/signup.html")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("users:dashboard")

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        password = request.POST.get("password") or ""
        remember_me = request.POST.get("remember_me") == "on"
        user = authenticate(request, email=email, password=password)
        if user is None:
            messages.error(request, "Email yoki parol noto‘g‘ri.")
            return render(request, "users/auth/login.html")
        login(request, user)
        if not remember_me:
            request.session.set_expiry(0)
        return redirect("users:dashboard")

    return render(request, "users/auth/login.html")


def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect("users:dashboard")

    if request.method == "POST":
        messages.success(
            request,
            "Agar bu email mavjud bo‘lsa, tiklash havolasi yuborildi.",
        )
        return render(request, "users/auth/forgot_password.html")

    return render(request, "users/auth/forgot_password.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("users:login")


@login_required
def onboarding_view(request):
    profile: Profile = request.user.profile

    if profile.is_onboarded:
        return redirect("users:dashboard")

    if request.method == "POST":
        # step'lar hammasini bitta POSTda qabul qilamiz (tez MVP)
        display_name = (request.POST.get("display_name") or "").strip()
        goal = request.POST.get("goal") or ""
        level = request.POST.get("level") or ""
        daily_commitment = request.POST.get("daily_commitment") or ""

        if display_name:
            profile.display_name = display_name[:50]
        profile.goal = goal
        profile.level = level
        try:
            profile.daily_commitment = int(daily_commitment) if daily_commitment else None
        except ValueError:
            profile.daily_commitment = None

        profile.is_onboarded = True
        profile.save()

        return redirect("users:dashboard")

    return render(request, "users/auth/onboarding_wizard.html")


@login_required
def dashboard_view(request):
    """
    Hozircha MVP:
    - agar userda Enrollment yo'q bo'lsa -> sales dashboard
    - bo'lsa -> student dashboard
    """
    has_enrollment = request.user.enrollments.exists()
    if not has_enrollment:
        return render(request, "users/dashboard/sales_dashboard.html")

    billing_account, _ = BillingAccount.objects.get_or_create(user=request.user)
    if billing_account.status == BillingAccount.FROZEN:
        return render(
            request,
            "users/dashboard/frozen_dashboard.html",
            {"account": billing_account},
        )
    now = timezone.localtime()
    grace_days_left = None
    if billing_account.status == BillingAccount.GRACE and billing_account.next_due_date:
        grace_end = billing_account.next_due_date + timedelta(days=3)
        grace_days_left = max(0, (grace_end - now.date()).days)
    if now.hour < 12:
        greeting = "Xayrli tong"
    elif now.hour < 18:
        greeting = "Xayrli kun"
    else:
        greeting = "Xayrli kech"
    active_enrollment = (
        Enrollment.objects.filter(user=request.user, is_active=True)
        .select_related("batch__course")
        .order_by("-created_at")
        .first()
    )
    latest_progress = None
    if active_enrollment:
        latest_progress = (
            LessonProgress.objects.filter(enrollment=active_enrollment)
            .select_related("lesson__module__course", "enrollment__batch")
            .order_by("-updated_at")
            .first()
        )
    resume_lesson = latest_progress.lesson if latest_progress else None
    resume_batch = active_enrollment.batch if active_enrollment else None
    daily_goals = []
    if latest_progress:
        quiz_done = True
        if latest_progress.lesson.quiz_required:
            quiz_done = latest_progress.quiz_score >= latest_progress.lesson.quiz_pass_score
        daily_goals = [
            {"label": "Video dars", "done": latest_progress.is_video_watched},
            {"label": "Quiz", "done": quiz_done},
            {"label": "Uy vazifa", "done": latest_progress.assignment_status == LessonProgress.APPROVED},
        ]
    daily_goal_total = len(daily_goals)
    daily_goal_completed = sum(1 for goal in daily_goals if goal["done"])
    return render(
        request,
        "users/dashboard/student_dashboard.html",
        {
            "greeting": greeting,
            "billing_account": billing_account,
            "grace_days_left": grace_days_left,
            "resume_lesson": resume_lesson,
            "resume_batch": resume_batch,
            "daily_goals": daily_goals,
            "daily_goal_total": daily_goal_total,
            "daily_goal_completed": daily_goal_completed,
        },
    )


@login_required
def profile_view(request):
    return render(request, "users/profile/view.html")


@login_required
def profile_edit(request):
    profile = request.user.profile
    if request.method == "POST":
        full_name = (request.POST.get("full_name") or "").strip()
        bio = (request.POST.get("bio") or "").strip()
        avatar = request.FILES.get("avatar")

        if full_name:
            name_parts = full_name.split(maxsplit=1)
            request.user.first_name = name_parts[0]
            request.user.last_name = name_parts[1] if len(name_parts) > 1 else ""
            if not profile.display_name:
                profile.display_name = full_name
            request.user.save(update_fields=["first_name", "last_name"])

        profile.bio = bio
        if avatar:
            profile.avatar = avatar
        profile.save()
        messages.success(request, "Profil ma'lumotlari yangilandi.")
        return redirect("users:profile_view")

    return render(request, "users/profile/edit.html", {"profile": profile})


def check_email_view(request):
    email = (request.GET.get("email") or "").strip().lower()
    if not email:
        return HttpResponse("")
    if CustomUser.objects.filter(email=email).exists():
        return HttpResponse('<div class="text-danger small mt-1">Bu email band.</div>')
    return HttpResponse('<div class="text-success small mt-1">Email bo‘sh.</div>')
