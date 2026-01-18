from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.urls import reverse

from .models import CustomUser, Profile


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
    now = timezone.localtime()
    if now.hour < 12:
        greeting = "Xayrli tong"
    elif now.hour < 18:
        greeting = "Xayrli kun"
    else:
        greeting = "Xayrli kech"
    return render(
        request,
        "users/dashboard/student_dashboard.html",
        {
            "greeting": greeting,
        },
    )


def check_email_view(request):
    email = (request.GET.get("email") or "").strip().lower()
    if not email:
        return HttpResponse("")
    if CustomUser.objects.filter(email=email).exists():
        return HttpResponse('<div class="text-danger small mt-1">Bu email band.</div>')
    return HttpResponse('<div class="text-success small mt-1">Email bo‘sh.</div>')
