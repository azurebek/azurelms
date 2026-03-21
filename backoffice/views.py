import datetime
import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView

from cohorts.models import Attendance, Cohort, Enrollment, PaymentReceipt
from courses.models import (
    Assignment,
    AssignmentSubmission,
    CohortLessonRelease,
    Course,
    ExamAttempt,
    Lesson,
    LessonProgress,
    Module,
)
from blog.models import (
    BlogComment,
    BlogCommentLike,
    BlogHomeSettings,
    BlogPost,
    BlogPostClap,
    BlogPostRead,
    BlogTag,
)
from frontend.models import (
    AboutPage,
    AboutStatistic,
    AuthPageSettings,
    LandingNavItem,
    LandingPage,
    LegalPage,
    SiteSettings,
    Statistic,
    TeamMember,
    Testimonial,
)
from gamification.models import Badge, Certificate as GamificationCertificate, EarnedBadge, Level
from messenger.models import ChatRoom, LessonRAGChunk, Message
from subscriptions.models import Plan, PlanFeature
from users.models import Notification, NotificationBroadcast
from users.notification_service import send_broadcast
from users.views import upsert_attendance_and_xp
from .forms import (
    BackofficeAboutPageForm,
    BackofficeAboutStatisticForm,
    BackofficeCohortForm,
    BackofficeAuthPageSettingsForm,
    BackofficeBadgeForm,
    BackofficeBlogHomeSettingsForm,
    BackofficeBlogTagForm,
    BackofficeBroadcastForm,
    BackofficeChatRoomForm,
    BackofficeCourseForm,
    BackofficeEnrollmentCreateForm,
    BackofficeGamificationCertificateForm,
    BackofficeLandingNavItemForm,
    BackofficeLandingPageForm,
    BackofficeLegalPageForm,
    BackofficeLevelForm,
    BackofficeMessageCreateForm,
    BackofficeModuleForm,
    BackofficeLessonForm,
    BackofficeAssignmentForm,
    BackofficePlanFeatureForm,
    BackofficePlanForm,
    BackofficeSiteSettingsForm,
    BackofficeStatisticForm,
    BackofficeTeamMemberForm,
    BackofficeTestimonialForm,
    BackofficeUserUpdateForm,
)


User = get_user_model()


class BackofficeLoginView(LoginView):
    template_name = "backoffice/login.html"
    redirect_authenticated_user = True

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Backoffice faqat staff/admin foydalanuvchilar uchun.")
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        return reverse_lazy("backoffice:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            logout(self.request)
            messages.error(self.request, "Sizda backoffice panelga kirish huquqi yo'q.")
            return redirect("backoffice:login")
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["next_target"] = self.request.GET.get("next") or self.request.POST.get("next")
        return context


class BackofficeAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = "backoffice:login"

    def test_func(self):
        user = self.request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Backoffice faqat staff/admin uchun ochiq.")
            return redirect("dashboard")
        return super().handle_no_permission()


def _last_n_dates(days):
    today = timezone.localdate()
    return [today - datetime.timedelta(days=offset) for offset in reversed(range(days))]


def _series_from_rows(dates, rows):
    mapping = {row["day"]: float(row["total"] or 0) for row in rows}
    return [mapping.get(day, 0.0) for day in dates]


def _ensure_landing_nav_items():
    existing_keys = set(LandingNavItem.objects.values_list("key", flat=True))
    missing_items = [
        item
        for item in LandingNavItem.default_items()
        if item["key"] not in existing_keys
    ]
    for item in missing_items:
        LandingNavItem.objects.create(
            key=item["key"],
            label=item["label"],
            is_visible=item["is_visible"],
            order=item["order"],
        )


class BackofficeDashboardView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        window_days = 14
        from_date = timezone.localdate() - datetime.timedelta(days=window_days - 1)

        student_qs = User.objects.filter(is_staff=False, is_superuser=False)
        active_enrollment_qs = Enrollment.objects.filter(status="active")

        total_students = student_qs.count()
        active_students = active_enrollment_qs.values("student_id").distinct().count()
        active_courses = Course.objects.filter(is_active=True).count()
        active_cohorts = Cohort.objects.filter(is_active=True).count()

        revenue_30d = (
            PaymentReceipt.objects.filter(
                is_verified=True,
                submitted_at__gte=now - datetime.timedelta(days=30),
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )
        pending_receipts = PaymentReceipt.objects.filter(is_verified=False).count()

        progress_qs = LessonProgress.objects.filter(enrollment__status="active")
        total_progress = progress_qs.count()
        completed_progress = progress_qs.filter(is_completed=True).count()
        completion_rate = round((completed_progress / total_progress) * 100, 1) if total_progress else 0.0

        exam_qs = ExamAttempt.objects.filter(is_completed=True)
        exam_total = exam_qs.count()
        exam_pass_rate = round((exam_qs.filter(passed=True).count() / exam_total) * 100, 1) if exam_total else 0.0

        ai_replies_24h = Message.objects.filter(
            is_ai_response=True,
            created_at__gte=now - datetime.timedelta(hours=24),
        ).count()
        rag_chunks_total = LessonRAGChunk.objects.count()

        recent_payments = PaymentReceipt.objects.select_related(
            "enrollment__student",
            "enrollment__cohort__course",
        ).order_by("-submitted_at")[:8]

        top_courses = (
            Course.objects.filter(is_active=True)
            .annotate(
                active_students=Count(
                    "cohorts__members",
                    filter=Q(cohorts__members__status="active"),
                    distinct=True,
                ),
                lessons_total=Count("modules__lessons", distinct=True),
            )
            .order_by("-active_students", "title")[:6]
        )

        dates = _last_n_dates(window_days)
        labels = [d.strftime("%d %b") for d in dates]

        enrollment_rows = (
            Enrollment.objects.filter(joined_at__date__gte=from_date)
            .annotate(day=TruncDate("joined_at"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )
        payment_rows = (
            PaymentReceipt.objects.filter(is_verified=True, submitted_at__date__gte=from_date)
            .annotate(day=TruncDate("submitted_at"))
            .values("day")
            .annotate(total=Sum("amount"))
            .order_by("day")
        )
        message_rows = (
            Message.objects.filter(created_at__date__gte=from_date)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )

        chat_rooms_rows = (
            ChatRoom.objects.values("room_type")
            .annotate(total=Count("id"))
            .order_by("room_type")
        )
        room_type_labels = {
            "group": "Guruh",
            "private": "Tutor",
            "ai": "Azure AI",
        }
        chat_room_labels = [room_type_labels.get(row["room_type"], row["room_type"]) for row in chat_rooms_rows]
        chat_room_totals = [row["total"] for row in chat_rooms_rows]

        context.update(
            {
                "kpi": {
                    "total_students": total_students,
                    "active_students": active_students,
                    "active_courses": active_courses,
                    "active_cohorts": active_cohorts,
                    "revenue_30d": revenue_30d,
                    "pending_receipts": pending_receipts,
                    "completion_rate": completion_rate,
                    "exam_pass_rate": exam_pass_rate,
                    "ai_replies_24h": ai_replies_24h,
                    "rag_chunks_total": rag_chunks_total,
                },
                "recent_payments": recent_payments,
                "top_courses": top_courses,
                "chart_labels": labels,
                "chart_enrollments": _series_from_rows(dates, enrollment_rows),
                "chart_revenue": _series_from_rows(dates, payment_rows),
                "chart_messages": _series_from_rows(dates, message_rows),
                "chart_chat_room_labels": chat_room_labels,
                "chart_chat_room_totals": chat_room_totals,
            }
        )
        return context


class BackofficeStudentsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/students.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = (self.request.GET.get("q") or "").strip()

        students = User.objects.filter(is_staff=False, is_superuser=False)
        if query:
            students = students.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
            )

        students = (
            students.annotate(
                active_enrollments=Count("enrollments", filter=Q(enrollments__status="active"), distinct=True),
                pending_enrollments=Count("enrollments", filter=Q(enrollments__status="pending"), distinct=True),
                total_enrollments=Count("enrollments", distinct=True),
                last_joined=Max("enrollments__joined_at"),
            )
            .order_by("-date_joined")[:120]
        )

        context.update(
            {
                "students": students,
                "search_query": query,
                "total_students": User.objects.filter(is_staff=False, is_superuser=False).count(),
                "active_students": Enrollment.objects.filter(status="active").values("student_id").distinct().count(),
            }
        )
        return context


class BackofficeUsersView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/users.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = (self.request.GET.get("q") or "").strip()
        role = (self.request.GET.get("role") or "all").strip().lower()
        status = (self.request.GET.get("status") or "all").strip().lower()

        users = User.objects.all()
        if query:
            users = users.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(telegram_username__icontains=query)
            )

        if role == "students":
            users = users.filter(is_staff=False, is_superuser=False)
        elif role == "staff":
            users = users.filter(Q(is_staff=True) | Q(is_superuser=True))
        else:
            role = "all"

        if status == "active":
            users = users.filter(is_active=True)
        elif status == "inactive":
            users = users.filter(is_active=False)
        else:
            status = "all"

        users = (
            users.annotate(
                active_enrollments=Count("enrollments", filter=Q(enrollments__status="active"), distinct=True),
                unread_notifications=Count("notifications", filter=Q(notifications__is_read=False), distinct=True),
            )
            .order_by("-date_joined")[:200]
        )

        context.update(
            {
                "users": users,
                "search_query": query,
                "selected_role": role,
                "selected_status": status,
                "summary_total": User.objects.count(),
                "summary_active": User.objects.filter(is_active=True).count(),
                "summary_staff": User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).count(),
            }
        )
        return context


class BackofficeUserDetailView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/user_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.target_user = get_object_or_404(User, id=kwargs["user_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = kwargs.get("form") or BackofficeUserUpdateForm(instance=self.target_user)
        recent_enrollments = (
            self.target_user.enrollments.select_related("cohort", "cohort__course", "plan")
            .order_by("-joined_at")[:8]
        )
        recent_notifications = self.target_user.notifications.order_by("-created_at")[:10]
        context.update(
            {
                "target_user": self.target_user,
                "form": form,
                "recent_enrollments": recent_enrollments,
                "recent_notifications": recent_notifications,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        form = BackofficeUserUpdateForm(request.POST, instance=self.target_user)
        if form.is_valid():
            form.save()
            messages.success(request, "Foydalanuvchi ma'lumotlari yangilandi.")
            return redirect("backoffice:user_detail", user_id=self.target_user.id)
        messages.error(request, "Forma xatolik bilan to'ldirilgan. Iltimos, tekshiring.")
        return self.render_to_response(self.get_context_data(form=form))


class BackofficeSubscriptionsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/subscriptions.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plans = Plan.objects.prefetch_related("features").order_by("order", "id")
        context.update(
            {
                "plans": plans,
                "plan_form": kwargs.get("plan_form") or BackofficePlanForm(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        form = BackofficePlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f"Tarif yaratildi: {plan.name}.")
            return redirect("backoffice:subscription_plan_detail", plan_id=plan.id)
        messages.error(request, "Tarif formasi xatolik bilan to'ldirilgan.")
        return self.render_to_response(self.get_context_data(plan_form=form))


class BackofficeSubscriptionPlanDetailView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/subscription_plan_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.plan = get_object_or_404(Plan, id=kwargs["plan_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "plan": self.plan,
                "features": self.plan.features.order_by("order", "id"),
                "plan_form": kwargs.get("plan_form") or BackofficePlanForm(instance=self.plan),
                "feature_form": kwargs.get("feature_form") or BackofficePlanFeatureForm(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()

        if action == "update_plan":
            plan_form = BackofficePlanForm(request.POST, instance=self.plan)
            if plan_form.is_valid():
                plan_form.save()
                messages.success(request, "Tarif yangilandi.")
                return redirect("backoffice:subscription_plan_detail", plan_id=self.plan.id)
            messages.error(request, "Tarifni yangilashda xatolik bor.")
            return self.render_to_response(self.get_context_data(plan_form=plan_form))

        if action == "add_feature":
            feature_form = BackofficePlanFeatureForm(request.POST)
            if feature_form.is_valid():
                feature = feature_form.save(commit=False)
                feature.plan = self.plan
                feature.save()
                messages.success(request, "Imkoniyat qo'shildi.")
                return redirect("backoffice:subscription_plan_detail", plan_id=self.plan.id)
            messages.error(request, "Imkoniyat qo'shishda xatolik bor.")
            return self.render_to_response(self.get_context_data(feature_form=feature_form))

        if action == "delete_feature":
            feature_id = request.POST.get("feature_id")
            feature = self.plan.features.filter(id=feature_id).first()
            if feature:
                feature.delete()
                messages.success(request, "Imkoniyat o'chirildi.")
            else:
                messages.error(request, "Imkoniyat topilmadi.")
            return redirect("backoffice:subscription_plan_detail", plan_id=self.plan.id)

        messages.error(request, "Noma'lum amal.")
        return redirect("backoffice:subscription_plan_detail", plan_id=self.plan.id)


class BackofficePaymentsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/payments.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = (self.request.GET.get("status") or "all").strip().lower()

        receipts = PaymentReceipt.objects.select_related(
            "enrollment__student",
            "enrollment__cohort__course",
        )

        if status == "verified":
            receipts = receipts.filter(is_verified=True)
        elif status == "pending":
            receipts = receipts.filter(is_verified=False)
        else:
            status = "all"

        receipts = receipts.order_by("-submitted_at")[:120]

        context.update(
            {
                "receipts": receipts,
                "selected_status": status,
                "summary_all": PaymentReceipt.objects.count(),
                "summary_verified": PaymentReceipt.objects.filter(is_verified=True).count(),
                "summary_pending": PaymentReceipt.objects.filter(is_verified=False).count(),
                "summary_verified_amount": PaymentReceipt.objects.filter(is_verified=True).aggregate(total=Sum("amount"))[
                    "total"
                ]
                or Decimal("0"),
            }
        )
        return context


class BackofficeCohortsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/cohorts.html"

    def _safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _queryset(self):
        query = (self.request.GET.get("q") or "").strip()
        course_id = self._safe_int(self.request.GET.get("course_id"))
        status = (self.request.GET.get("status") or "active").strip().lower()

        cohorts = Cohort.objects.select_related("course").annotate(
            active_members=Count("members", filter=Q(members__status="active"), distinct=True),
            pending_members=Count("members", filter=Q(members__status="pending"), distinct=True),
            total_members=Count("members", distinct=True),
        )

        if query:
            cohorts = cohorts.filter(
                Q(name__icontains=query)
                | Q(course__title__icontains=query)
                | Q(telegram_group_link__icontains=query)
            )

        if course_id:
            cohorts = cohorts.filter(course_id=course_id)

        if status == "active":
            cohorts = cohorts.filter(is_active=True)
        elif status in {"archived", "inactive"}:
            cohorts = cohorts.filter(is_active=False)
            status = "archived"
        else:
            status = "all"

        return cohorts.order_by("-is_active", "course__title", "name")[:220], query, course_id, status

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cohorts, query, course_id, status = self._queryset()

        context.update(
            {
                "courses": Course.objects.filter(is_active=True).order_by("title"),
                "cohorts": cohorts,
                "search_query": query,
                "selected_course_id": course_id,
                "selected_status": status,
                "create_form": kwargs.get("create_form") or BackofficeCohortForm(),
                "summary_active": Cohort.objects.filter(is_active=True).count(),
                "summary_total": Cohort.objects.count(),
                "summary_total_students": Enrollment.objects.values("student_id").distinct().count(),
                "summary_active_students": Enrollment.objects.filter(status="active").values("student_id").distinct().count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()

        if action == "create_cohort":
            create_form = BackofficeCohortForm(request.POST)
            if create_form.is_valid():
                cohort = create_form.save()
                messages.success(request, f"Yangi cohort yaratildi: {cohort.name}.")
                return redirect("backoffice:cohort_detail", cohort_id=cohort.id)
            messages.error(request, "Cohort yaratish formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(create_form=create_form))

        ids = request.POST.getlist("cohort_ids")
        queryset = Cohort.objects.filter(id__in=ids)
        if not queryset.exists():
            messages.error(request, "Kamida bitta cohort tanlang.")
            return redirect(request.get_full_path())

        if action == "activate_selected":
            updated = queryset.update(is_active=True)
            messages.success(request, f"{updated} ta cohort faollashtirildi.")
            return redirect(request.get_full_path())

        if action == "archive_selected":
            updated = queryset.update(is_active=False)
            messages.success(request, f"{updated} ta cohort arxiv holatiga o'tdi.")
            return redirect(request.get_full_path())

        if action == "delete_selected":
            deleted, _ = queryset.delete()
            messages.success(request, f"{deleted} ta cohort yozuvi o'chirildi.")
            return redirect(request.get_full_path())

        messages.error(request, "Noma'lum action.")
        return redirect(request.get_full_path())


class BackofficeCohortDetailView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/cohort_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.cohort = get_object_or_404(Cohort.objects.select_related("course"), id=kwargs["cohort_id"])
        return super().dispatch(request, *args, **kwargs)

    def _safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollments = (
            Enrollment.objects.filter(cohort=self.cohort)
            .select_related("student", "plan")
            .annotate(receipts_total=Count("receipts", distinct=True))
            .order_by("student__username")
        )
        context.update(
            {
                "cohort_obj": self.cohort,
                "cohort_form": kwargs.get("cohort_form") or BackofficeCohortForm(instance=self.cohort),
                "enrollment_form": kwargs.get("enrollment_form") or BackofficeEnrollmentCreateForm(),
                "enrollments": enrollments,
                "plans": Plan.objects.order_by("order", "id"),
                "status_choices": Enrollment.STATUS_CHOICES,
                "summary_total": enrollments.count(),
                "summary_active": enrollments.filter(status="active").count(),
                "summary_pending": enrollments.filter(status="pending").count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()
        valid_statuses = {choice[0] for choice in Enrollment.STATUS_CHOICES}

        if action == "update_cohort":
            cohort_form = BackofficeCohortForm(request.POST, instance=self.cohort)
            if cohort_form.is_valid():
                cohort_form.save()
                messages.success(request, "Cohort ma'lumotlari yangilandi.")
                return redirect("backoffice:cohort_detail", cohort_id=self.cohort.id)
            messages.error(request, "Cohort formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(cohort_form=cohort_form))

        if action == "add_enrollment":
            enrollment_form = BackofficeEnrollmentCreateForm(request.POST)
            if enrollment_form.is_valid():
                enrollment = enrollment_form.save(commit=False)
                enrollment.cohort = self.cohort
                if Enrollment.objects.filter(cohort=self.cohort, student=enrollment.student).exists():
                    enrollment_form.add_error("student", "Bu foydalanuvchi cohort ichida allaqachon mavjud.")
                    messages.error(request, "Enrollment qo'shishda xatolik bor.")
                    return self.render_to_response(self.get_context_data(enrollment_form=enrollment_form))
                enrollment.save()
                messages.success(request, "Cohortga yangi student qo'shildi.")
                return redirect("backoffice:cohort_detail", cohort_id=self.cohort.id)
            messages.error(request, "Enrollment formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(enrollment_form=enrollment_form))

        if action == "update_enrollment":
            enrollment = get_object_or_404(Enrollment, id=request.POST.get("enrollment_id"), cohort=self.cohort)
            status = (request.POST.get("status") or "").strip()
            if status in valid_statuses:
                enrollment.status = status

            plan_id = self._safe_int(request.POST.get("plan_id"))
            enrollment.plan = Plan.objects.filter(id=plan_id).first() if plan_id else None
            enrollment.last_payment_date = self._parse_date(request.POST.get("last_payment_date"))
            enrollment.next_payment_deadline = self._parse_date(request.POST.get("next_payment_deadline"))
            enrollment.save(
                update_fields=["status", "plan", "last_payment_date", "next_payment_deadline"]
            )
            messages.success(request, "Enrollment yangilandi.")
            return redirect("backoffice:cohort_detail", cohort_id=self.cohort.id)

        if action == "delete_enrollment":
            enrollment = get_object_or_404(Enrollment, id=request.POST.get("enrollment_id"), cohort=self.cohort)
            enrollment.delete()
            messages.success(request, "Enrollment o'chirildi.")
            return redirect("backoffice:cohort_detail", cohort_id=self.cohort.id)

        ids = request.POST.getlist("enrollment_ids")
        queryset = Enrollment.objects.filter(id__in=ids, cohort=self.cohort)
        if not queryset.exists():
            messages.error(request, "Kamida bitta enrollment tanlang.")
            return redirect("backoffice:cohort_detail", cohort_id=self.cohort.id)

        if action == "mark_active_selected":
            updated = queryset.update(status="active")
            messages.success(request, f"{updated} ta enrollment faol qilindi.")
            return redirect("backoffice:cohort_detail", cohort_id=self.cohort.id)

        if action == "mark_pending_selected":
            updated = queryset.update(status="pending")
            messages.success(request, f"{updated} ta enrollment pending holatga o'tdi.")
            return redirect("backoffice:cohort_detail", cohort_id=self.cohort.id)

        if action == "mark_frozen_selected":
            updated = queryset.update(status="frozen")
            messages.success(request, f"{updated} ta enrollment muzlatildi.")
            return redirect("backoffice:cohort_detail", cohort_id=self.cohort.id)

        if action == "mark_expired_selected":
            updated = queryset.update(status="expired")
            messages.success(request, f"{updated} ta enrollment muddati tugagan holatga o'tdi.")
            return redirect("backoffice:cohort_detail", cohort_id=self.cohort.id)

        if action == "delete_selected_enrollments":
            deleted, _ = queryset.delete()
            messages.success(request, f"{deleted} ta enrollment o'chirildi.")
            return redirect("backoffice:cohort_detail", cohort_id=self.cohort.id)

        messages.error(request, "Noma'lum action.")
        return redirect("backoffice:cohort_detail", cohort_id=self.cohort.id)


class BackofficeAttendanceView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/attendance.html"

    def _safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    def get_allowed_cohorts(self):
        return Cohort.objects.filter(is_active=True).select_related("course").order_by("name")

    def get(self, request, *args, **kwargs):
        if (request.GET.get("export") or "").strip().lower() == "csv":
            context = self.build_context()
            return self._export_csv(context)
        return super().get(request, *args, **kwargs)

    def _export_csv(self, context):
        selected_cohort = context.get("selected_cohort")
        selected_lesson = context.get("selected_lesson")
        range_start = context.get("range_start")
        range_end = context.get("range_end")

        if not selected_cohort:
            messages.error(self.request, "Export uchun cohort tanlanishi kerak.")
            return redirect("backoffice:attendance")

        records = Attendance.objects.filter(enrollment__cohort=selected_cohort).select_related(
            "enrollment__student",
            "enrollment__cohort__course",
            "lesson__module",
            "marked_by",
        )
        if selected_lesson:
            records = records.filter(lesson=selected_lesson)
        records = records.filter(date__gte=range_start, date__lte=range_end).order_by(
            "date",
            "lesson__module__order",
            "lesson__order",
            "enrollment__student__username",
        )

        lesson_label = selected_lesson.title if selected_lesson else "all_lessons"
        filename = (
            f"attendance_{selected_cohort.id}_{lesson_label}_{range_start.isoformat()}_{range_end.isoformat()}.csv"
        )
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Date",
                "Cohort",
                "Course",
                "Lesson",
                "Student Username",
                "Student Name",
                "Status",
                "XP Awarded",
                "Marked By",
                "Marked At",
            ]
        )
        for row in records:
            student = row.enrollment.student
            writer.writerow(
                [
                    row.date.isoformat(),
                    row.enrollment.cohort.name,
                    row.enrollment.cohort.course.title,
                    row.lesson.title,
                    student.username,
                    student.get_full_name() or student.username,
                    row.get_status_display(),
                    row.xp_awarded,
                    row.marked_by.username if row.marked_by else "",
                    timezone.localtime(row.marked_at).strftime("%Y-%m-%d %H:%M:%S") if row.marked_at else "",
                ]
            )
        return response

    def build_context(self):
        context = {}
        cohorts = self.get_allowed_cohorts()
        context["cohorts"] = cohorts

        selected_cohort_id = self._safe_int(self.request.GET.get("cohort_id"))
        selected_lesson_id = self._safe_int(self.request.GET.get("lesson_id"))
        selected_date = self._parse_date(self.request.GET.get("date")) or timezone.localdate()

        range_end = self._parse_date(self.request.GET.get("date_to")) or selected_date
        range_start = self._parse_date(self.request.GET.get("date_from")) or (range_end - datetime.timedelta(days=6))
        if range_start > range_end:
            range_start, range_end = range_end, range_start

        selected_cohort = cohorts.filter(id=selected_cohort_id).first() if selected_cohort_id else cohorts.first()

        lessons = Lesson.objects.none()
        members = Enrollment.objects.none()
        selected_lesson = None

        if selected_cohort:
            lessons = Lesson.objects.filter(module__course=selected_cohort.course).order_by("module__order", "order")
            members = Enrollment.objects.filter(
                cohort=selected_cohort,
                status="active",
            ).select_related("student").order_by("student__first_name", "student__last_name", "student__username")
            selected_lesson = lessons.filter(id=selected_lesson_id).first() if selected_lesson_id else lessons.first()

        existing_map = {}
        if selected_lesson and members.exists():
            existing_attendance = Attendance.objects.filter(
                enrollment__in=members,
                lesson=selected_lesson,
                date=selected_date,
            )
            existing_map = {row.enrollment_id: row for row in existing_attendance}

        member_rows = []
        for enrollment in members:
            existing = existing_map.get(enrollment.id)
            member_rows.append(
                {
                    "enrollment": enrollment,
                    "status": existing.status if existing else Attendance.STATUS_ABSENT,
                }
            )

        analytics_qs = Attendance.objects.none()
        if selected_cohort:
            analytics_qs = Attendance.objects.filter(
                enrollment__cohort=selected_cohort,
                date__gte=range_start,
                date__lte=range_end,
            )
            if selected_lesson:
                analytics_qs = analytics_qs.filter(lesson=selected_lesson)

        summary_total_records = analytics_qs.count()
        summary_present = analytics_qs.filter(status=Attendance.STATUS_PRESENT).count()
        summary_partial = analytics_qs.filter(status=Attendance.STATUS_PARTIAL).count()
        summary_absent = analytics_qs.filter(status=Attendance.STATUS_ABSENT).count()
        summary_xp = analytics_qs.aggregate(total=Sum("xp_awarded"))["total"] or 0
        summary_presence_rate = (
            round(((summary_present + summary_partial) / summary_total_records) * 100, 1)
            if summary_total_records
            else 0.0
        )
        summary_avg_xp = round(summary_xp / summary_total_records, 1) if summary_total_records else 0.0

        daily_rows = (
            analytics_qs.annotate(day=TruncDate("date"))
            .values("day")
            .annotate(
                present=Count("id", filter=Q(status=Attendance.STATUS_PRESENT)),
                partial=Count("id", filter=Q(status=Attendance.STATUS_PARTIAL)),
                absent=Count("id", filter=Q(status=Attendance.STATUS_ABSENT)),
                total=Count("id"),
                xp_total=Sum("xp_awarded"),
            )
            .order_by("day")
        )

        context.update(
            {
                "selected_cohort": selected_cohort,
                "selected_lesson": selected_lesson,
                "selected_date": selected_date,
                "range_start": range_start,
                "range_end": range_end,
                "lessons": lessons,
                "members": members,
                "member_rows": member_rows,
                "status_choices": Attendance.STATUS_CHOICES,
                "summary_total_records": summary_total_records,
                "summary_present": summary_present,
                "summary_partial": summary_partial,
                "summary_absent": summary_absent,
                "summary_xp": summary_xp,
                "summary_presence_rate": summary_presence_rate,
                "summary_avg_xp": summary_avg_xp,
                "daily_rows": daily_rows,
            }
        )
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.build_context())
        return context

    def post(self, request, *args, **kwargs):
        context = self.build_context()
        selected_lesson = context.get("selected_lesson")
        selected_date = context.get("selected_date")
        members = context.get("members")

        if not selected_lesson or not members.exists():
            messages.error(request, "Cohort va darsni to'g'ri tanlang.")
            return redirect(request.get_full_path())

        valid_statuses = {choice[0] for choice in Attendance.STATUS_CHOICES}
        updated = 0

        for enrollment in members:
            raw_status = request.POST.get(f"status_{enrollment.id}", "").strip()
            status = raw_status if raw_status in valid_statuses else Attendance.STATUS_ABSENT
            upsert_attendance_and_xp(
                enrollment=enrollment,
                lesson=selected_lesson,
                date=selected_date,
                status=status,
                marked_by=request.user,
            )
            updated += 1

        messages.success(request, f"Davomat saqlandi: {updated} ta o'quvchi.")
        return redirect(request.get_full_path())


class BackofficeNotificationsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/notifications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = (self.request.GET.get("category") or "all").strip().lower()
        read_state = (self.request.GET.get("read") or "all").strip().lower()

        notifications = Notification.objects.select_related("recipient")
        if category in {"manual", "subscription", "system"}:
            notifications = notifications.filter(category=category)
        else:
            category = "all"

        if read_state == "read":
            notifications = notifications.filter(is_read=True)
        elif read_state == "unread":
            notifications = notifications.filter(is_read=False)
        else:
            read_state = "all"

        notifications = notifications.order_by("-created_at")[:160]
        broadcasts = NotificationBroadcast.objects.select_related("created_by").order_by("-created_at")[:30]

        form = kwargs.get("broadcast_form") or BackofficeBroadcastForm()
        context.update(
            {
                "notifications": notifications,
                "broadcasts": broadcasts,
                "broadcast_form": form,
                "selected_category": category,
                "selected_read": read_state,
                "summary_total": Notification.objects.count(),
                "summary_unread": Notification.objects.filter(is_read=False).count(),
                "summary_broadcasts": NotificationBroadcast.objects.count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        form = BackofficeBroadcastForm(request.POST)
        if form.is_valid():
            broadcast = form.save(commit=False)
            broadcast.created_by = request.user
            broadcast.save()
            form.save_m2m()
            sent_count = send_broadcast(broadcast)
            messages.success(request, f"Broadcast yuborildi: {sent_count} ta foydalanuvchi.")
            return redirect("backoffice:notifications")
        messages.error(request, "Broadcast formasi xatolik bilan to'ldirilgan.")
        return self.render_to_response(self.get_context_data(broadcast_form=form))


class BackofficeLearningAssignmentsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/learning_assignments.html"

    def _queryset(self):
        query = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "all").strip().lower()
        course_id = self.request.GET.get("course_id")

        submissions = AssignmentSubmission.objects.select_related(
            "student",
            "assignment__lesson__module__course",
            "reviewed_by",
        )

        if query:
            submissions = submissions.filter(
                Q(student__username__icontains=query)
                | Q(student__email__icontains=query)
                | Q(assignment__title__icontains=query)
                | Q(assignment__lesson__title__icontains=query)
            )

        valid_statuses = {
            AssignmentSubmission.STATUS_PENDING,
            AssignmentSubmission.STATUS_APPROVED,
            AssignmentSubmission.STATUS_NEEDS_REVISION,
        }
        if status in valid_statuses:
            submissions = submissions.filter(status=status)
        else:
            status = "all"

        if course_id:
            try:
                submissions = submissions.filter(assignment__lesson__module__course_id=int(course_id))
            except (TypeError, ValueError):
                course_id = ""
        else:
            course_id = ""

        return submissions.order_by("-updated_at")[:220], query, status, course_id

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submissions, query, status, course_id = self._queryset()
        context.update(
            {
                "submissions": submissions,
                "search_query": query,
                "selected_status": status,
                "selected_course_id": int(course_id) if course_id else None,
                "courses": Course.objects.filter(is_active=True).order_by("title"),
                "summary_pending": AssignmentSubmission.objects.filter(
                    status=AssignmentSubmission.STATUS_PENDING
                ).count(),
                "summary_approved": AssignmentSubmission.objects.filter(
                    status=AssignmentSubmission.STATUS_APPROVED
                ).count(),
                "summary_revision": AssignmentSubmission.objects.filter(
                    status=AssignmentSubmission.STATUS_NEEDS_REVISION
                ).count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()
        ids = request.POST.getlist("submission_ids")
        queryset = AssignmentSubmission.objects.filter(id__in=ids)
        if not queryset.exists():
            messages.error(request, "Kamida bitta submission tanlang.")
            return redirect(request.get_full_path())

        now = timezone.now()
        if action == "mark_pending":
            updated = queryset.update(
                status=AssignmentSubmission.STATUS_PENDING,
                reviewed_by=None,
                reviewed_at=None,
            )
            messages.success(request, f"{updated} ta submission pending holatga o'tdi.")
            return redirect(request.get_full_path())

        if action == "mark_approved":
            updated = queryset.update(
                status=AssignmentSubmission.STATUS_APPROVED,
                reviewed_by=request.user,
                reviewed_at=now,
            )
            messages.success(request, f"{updated} ta submission tasdiqlandi.")
            return redirect(request.get_full_path())

        if action == "mark_needs_revision":
            updated = queryset.update(
                status=AssignmentSubmission.STATUS_NEEDS_REVISION,
                reviewed_by=request.user,
                reviewed_at=now,
            )
            messages.success(request, f"{updated} ta submission revision holatiga o'tdi.")
            return redirect(request.get_full_path())

        messages.error(request, "Noma'lum action.")
        return redirect(request.get_full_path())


class BackofficeLearningReleasesView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/learning_releases.html"

    def _queryset(self):
        course_id = self.request.GET.get("course_id")
        cohort_id = self.request.GET.get("cohort_id")
        state = (self.request.GET.get("state") or "all").strip().lower()

        releases = CohortLessonRelease.objects.select_related(
            "cohort",
            "lesson__module__course",
            "released_by",
        )

        if course_id:
            try:
                releases = releases.filter(lesson__module__course_id=int(course_id))
            except (TypeError, ValueError):
                course_id = ""
        else:
            course_id = ""

        if cohort_id:
            try:
                releases = releases.filter(cohort_id=int(cohort_id))
            except (TypeError, ValueError):
                cohort_id = ""
        else:
            cohort_id = ""

        if state == "released":
            releases = releases.filter(is_released=True)
        elif state == "locked":
            releases = releases.filter(is_released=False)
        else:
            state = "all"

        return releases.order_by("-updated_at")[:240], course_id, cohort_id, state

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        releases, course_id, cohort_id, state = self._queryset()
        context.update(
            {
                "releases": releases,
                "selected_course_id": int(course_id) if course_id else None,
                "selected_cohort_id": int(cohort_id) if cohort_id else None,
                "selected_state": state,
                "courses": Course.objects.filter(is_active=True).order_by("title"),
                "cohorts": Cohort.objects.select_related("course").filter(is_active=True).order_by("name"),
                "summary_total": CohortLessonRelease.objects.count(),
                "summary_released": CohortLessonRelease.objects.filter(is_released=True).count(),
                "summary_locked": CohortLessonRelease.objects.filter(is_released=False).count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()
        ids = request.POST.getlist("release_ids")
        queryset = CohortLessonRelease.objects.filter(id__in=ids)
        if not queryset.exists():
            messages.error(request, "Kamida bitta release tanlang.")
            return redirect(request.get_full_path())

        if action == "mark_released":
            updated = queryset.update(
                is_released=True,
                released_by=request.user,
                released_at=timezone.now(),
            )
            messages.success(request, f"{updated} ta dars ochildi.")
            return redirect(request.get_full_path())

        if action == "mark_locked":
            updated = queryset.update(is_released=False)
            messages.success(request, f"{updated} ta dars qulflandi.")
            return redirect(request.get_full_path())

        messages.error(request, "Noma'lum action.")
        return redirect(request.get_full_path())


class BackofficeLearningExamsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/learning_exams.html"

    def _queryset(self):
        query = (self.request.GET.get("q") or "").strip()
        course_id = self.request.GET.get("course_id")
        review_state = (self.request.GET.get("review_state") or "all").strip().lower()

        attempts = ExamAttempt.objects.select_related(
            "student",
            "exam",
            "exam__course",
            "reviewed_by",
        )

        if query:
            attempts = attempts.filter(
                Q(student__username__icontains=query)
                | Q(student__email__icontains=query)
                | Q(exam__title__icontains=query)
                | Q(exam__course__title__icontains=query)
            )

        if course_id:
            try:
                attempts = attempts.filter(exam__course_id=int(course_id))
            except (TypeError, ValueError):
                course_id = ""
        else:
            course_id = ""

        if review_state == "approved":
            attempts = attempts.filter(is_reviewed=True)
        elif review_state == "pending":
            attempts = attempts.filter(is_completed=True, is_reviewed=False)
        elif review_state == "in_progress":
            attempts = attempts.filter(is_completed=False)
        else:
            review_state = "all"

        return attempts.order_by("-start_time")[:220], query, course_id, review_state

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempts, query, course_id, review_state = self._queryset()
        context.update(
            {
                "attempts": attempts,
                "search_query": query,
                "selected_course_id": int(course_id) if course_id else None,
                "selected_review_state": review_state,
                "courses": Course.objects.filter(is_active=True).order_by("title"),
                "summary_total": ExamAttempt.objects.count(),
                "summary_pending_review": ExamAttempt.objects.filter(is_completed=True, is_reviewed=False).count(),
                "summary_approved": ExamAttempt.objects.filter(is_reviewed=True).count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()
        ids = request.POST.getlist("attempt_ids")
        queryset = ExamAttempt.objects.select_related("exam").filter(id__in=ids)
        if not queryset.exists():
            messages.error(request, "Kamida bitta exam attempt tanlang.")
            return redirect(request.get_full_path())

        if action == "prepare_reviews":
            count = 0
            for attempt in queryset:
                attempt.ensure_section_reviews()
                attempt.prefill_section_scores_from_answers()
                count += 1
            messages.success(request, f"{count} ta urinish uchun bo'lim ballari tayyorlandi.")
            return redirect(request.get_full_path())

        if action == "approve_selected_attempts":
            approved_count = 0
            certificate_count = 0
            for attempt in queryset:
                if not attempt.is_completed:
                    continue
                certificate, created = attempt.finalize_review(reviewed_by=request.user)
                approved_count += 1
                if created and certificate:
                    certificate_count += 1
            messages.success(
                request,
                f"{approved_count} ta urinish tasdiqlandi. {certificate_count} ta yangi sertifikat yaratildi.",
            )
            return redirect(request.get_full_path())

        if action == "recalculate_scores":
            count = 0
            for attempt in queryset:
                if attempt.is_reviewed:
                    attempt.finalize_review(reviewed_by=request.user)
                else:
                    attempt.prefill_section_scores_from_answers()
                count += 1
            messages.success(request, f"{count} ta urinish uchun ballar yangilandi.")
            return redirect(request.get_full_path())

        messages.error(request, "Noma'lum action.")
        return redirect(request.get_full_path())


class BackofficeCoursesCatalogView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/courses_catalog.html"

    def _safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _queryset(self):
        query = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "active").strip().lower()
        instructor_id = self._safe_int(self.request.GET.get("instructor_id"))

        courses = Course.objects.select_related("instructor").annotate(
            module_count=Count("modules", distinct=True),
            lesson_count=Count("modules__lessons", distinct=True),
        )

        if query:
            courses = courses.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(instructor__username__icontains=query)
                | Q(instructor__email__icontains=query)
            )

        if status == "active":
            courses = courses.filter(is_active=True)
        elif status == "inactive":
            courses = courses.filter(is_active=False)
        else:
            status = "all"

        if instructor_id:
            courses = courses.filter(instructor_id=instructor_id)

        return courses.order_by("-created_at")[:220], query, status, instructor_id

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        courses, query, status, instructor_id = self._queryset()
        context.update(
            {
                "courses": courses,
                "search_query": query,
                "selected_status": status,
                "selected_instructor_id": instructor_id,
                "instructors": User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).order_by("username"),
                "create_form": kwargs.get("create_form") or BackofficeCourseForm(),
                "summary_total": Course.objects.count(),
                "summary_active": Course.objects.filter(is_active=True).count(),
                "summary_inactive": Course.objects.filter(is_active=False).count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()

        if action == "create_course":
            create_form = BackofficeCourseForm(request.POST, request.FILES)
            if create_form.is_valid():
                course = create_form.save()
                messages.success(request, f"Kurs yaratildi: {course.title}.")
                return redirect("backoffice:course_structure", course_id=course.id)
            messages.error(request, "Kurs yaratish formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(create_form=create_form))

        ids = request.POST.getlist("course_ids")
        queryset = Course.objects.filter(id__in=ids)
        if not queryset.exists():
            messages.error(request, "Kamida bitta kurs tanlang.")
            return redirect(request.get_full_path())

        if action == "activate_selected":
            updated = queryset.update(is_active=True)
            messages.success(request, f"{updated} ta kurs faollashtirildi.")
            return redirect(request.get_full_path())

        if action == "deactivate_selected":
            updated = queryset.update(is_active=False)
            messages.success(request, f"{updated} ta kurs nofaol holatga o'tdi.")
            return redirect(request.get_full_path())

        if action == "delete_selected":
            deleted, _ = queryset.delete()
            messages.success(request, f"{deleted} ta kursga oid yozuv o'chirildi.")
            return redirect(request.get_full_path())

        messages.error(request, "Noma'lum action.")
        return redirect(request.get_full_path())


class BackofficeCourseStructureView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/course_structure.html"

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course.objects.select_related("instructor"), id=kwargs["course_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        modules = (
            Module.objects.filter(course=self.course)
            .prefetch_related("lessons__assignments")
            .order_by("order", "id")
        )
        context.update(
            {
                "course_obj": self.course,
                "course_form": kwargs.get("course_form") or BackofficeCourseForm(instance=self.course),
                "module_form": kwargs.get("module_form") or BackofficeModuleForm(),
                "lesson_form": kwargs.get("lesson_form") or BackofficeLessonForm(),
                "assignment_form": kwargs.get("assignment_form") or BackofficeAssignmentForm(),
                "modules": modules,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()

        if action == "update_course":
            course_form = BackofficeCourseForm(request.POST, request.FILES, instance=self.course)
            if course_form.is_valid():
                course_form.save()
                messages.success(request, "Kurs ma'lumotlari yangilandi.")
                return redirect("backoffice:course_structure", course_id=self.course.id)
            messages.error(request, "Kurs formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(course_form=course_form))

        if action == "create_module":
            module_form = BackofficeModuleForm(request.POST)
            if module_form.is_valid():
                module = module_form.save(commit=False)
                module.course = self.course
                module.save()
                messages.success(request, "Yangi modul qo'shildi.")
                return redirect("backoffice:course_structure", course_id=self.course.id)
            messages.error(request, "Modul formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(module_form=module_form))

        if action == "update_module":
            module = get_object_or_404(Module, id=request.POST.get("module_id"), course=self.course)
            module_form = BackofficeModuleForm(request.POST, instance=module)
            if module_form.is_valid():
                module_form.save()
                messages.success(request, "Modul yangilandi.")
            else:
                messages.error(request, "Modul yangilashda xatolik bor.")
            return redirect("backoffice:course_structure", course_id=self.course.id)

        if action == "delete_module":
            module = get_object_or_404(Module, id=request.POST.get("module_id"), course=self.course)
            module.delete()
            messages.success(request, "Modul o'chirildi.")
            return redirect("backoffice:course_structure", course_id=self.course.id)

        if action == "create_lesson":
            module = get_object_or_404(Module, id=request.POST.get("module_id"), course=self.course)
            lesson_form = BackofficeLessonForm(request.POST)
            if lesson_form.is_valid():
                lesson = lesson_form.save(commit=False)
                lesson.module = module
                lesson.save()
                messages.success(request, "Yangi dars qo'shildi.")
                return redirect("backoffice:course_structure", course_id=self.course.id)
            messages.error(request, "Dars formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(lesson_form=lesson_form))

        if action == "update_lesson":
            lesson = get_object_or_404(Lesson, id=request.POST.get("lesson_id"), module__course=self.course)
            lesson_form = BackofficeLessonForm(request.POST, instance=lesson)
            if lesson_form.is_valid():
                lesson_form.save()
                messages.success(request, "Dars yangilandi.")
            else:
                messages.error(request, "Dars yangilashda xatolik bor.")
            return redirect("backoffice:course_structure", course_id=self.course.id)

        if action == "delete_lesson":
            lesson = get_object_or_404(Lesson, id=request.POST.get("lesson_id"), module__course=self.course)
            lesson.delete()
            messages.success(request, "Dars o'chirildi.")
            return redirect("backoffice:course_structure", course_id=self.course.id)

        if action == "create_assignment":
            lesson = get_object_or_404(Lesson, id=request.POST.get("lesson_id"), module__course=self.course)
            assignment_form = BackofficeAssignmentForm(request.POST)
            if assignment_form.is_valid():
                assignment = assignment_form.save(commit=False)
                assignment.lesson = lesson
                assignment.save()
                messages.success(request, "Yangi vazifa qo'shildi.")
                return redirect("backoffice:course_structure", course_id=self.course.id)
            messages.error(request, "Vazifa formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(assignment_form=assignment_form))

        if action == "update_assignment":
            assignment = get_object_or_404(Assignment, id=request.POST.get("assignment_id"), lesson__module__course=self.course)
            assignment_form = BackofficeAssignmentForm(request.POST, instance=assignment)
            if assignment_form.is_valid():
                assignment_form.save()
                messages.success(request, "Vazifa yangilandi.")
            else:
                messages.error(request, "Vazifa yangilashda xatolik bor.")
            return redirect("backoffice:course_structure", course_id=self.course.id)

        if action == "delete_assignment":
            assignment = get_object_or_404(Assignment, id=request.POST.get("assignment_id"), lesson__module__course=self.course)
            assignment.delete()
            messages.success(request, "Vazifa o'chirildi.")
            return redirect("backoffice:course_structure", course_id=self.course.id)

        messages.error(request, "Noma'lum action.")
        return redirect("backoffice:course_structure", course_id=self.course.id)


class BackofficeContentSettingsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/content_settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        site_settings = SiteSettings.load()
        auth_settings = AuthPageSettings.load()
        context.update(
            {
                "site_form": kwargs.get("site_form") or BackofficeSiteSettingsForm(instance=site_settings, prefix="site"),
                "auth_form": kwargs.get("auth_form") or BackofficeAuthPageSettingsForm(instance=auth_settings, prefix="auth"),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()
        site_settings = SiteSettings.load()
        auth_settings = AuthPageSettings.load()

        if action == "update_site":
            site_form = BackofficeSiteSettingsForm(request.POST, instance=site_settings, prefix="site")
            if site_form.is_valid():
                site_form.save()
                messages.success(request, "Site settings yangilandi.")
                return redirect("backoffice:content_settings")
            messages.error(request, "Site settings formada xatolik bor.")
            return self.render_to_response(
                self.get_context_data(site_form=site_form, auth_form=BackofficeAuthPageSettingsForm(instance=auth_settings, prefix="auth"))
            )

        if action == "update_auth":
            auth_form = BackofficeAuthPageSettingsForm(request.POST, instance=auth_settings, prefix="auth")
            if auth_form.is_valid():
                auth_form.save()
                messages.success(request, "Auth page settings yangilandi.")
                return redirect("backoffice:content_settings")
            messages.error(request, "Auth settings formada xatolik bor.")
            return self.render_to_response(
                self.get_context_data(site_form=BackofficeSiteSettingsForm(instance=site_settings, prefix="site"), auth_form=auth_form)
            )

        messages.error(request, "Noma'lum action.")
        return redirect("backoffice:content_settings")


class BackofficeLandingPageView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/content_landing_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        landing_page = LandingPage.load()
        context.update(
            {
                "landing_page_obj": landing_page,
                "form": kwargs.get("form") or BackofficeLandingPageForm(instance=landing_page),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        landing_page = LandingPage.load()
        form = BackofficeLandingPageForm(request.POST, request.FILES, instance=landing_page)
        if form.is_valid():
            form.save()
            messages.success(request, "Landing page sozlamalari yangilandi.")
            return redirect("backoffice:content_landing_page")
        messages.error(request, "Landing page formasida xatolik bor.")
        return self.render_to_response(self.get_context_data(form=form))


class BackofficeLandingBlocksView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/content_landing_blocks.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "statistics": Statistic.objects.order_by("order", "id"),
                "testimonials": Testimonial.objects.order_by("-is_active", "name", "id"),
                "stat_form": kwargs.get("stat_form") or BackofficeStatisticForm(),
                "testimonial_form": kwargs.get("testimonial_form") or BackofficeTestimonialForm(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()

        if action == "create_statistic":
            stat_form = BackofficeStatisticForm(request.POST)
            if stat_form.is_valid():
                stat_form.save()
                messages.success(request, "Landing statistikasi qo'shildi.")
                return redirect("backoffice:content_landing_blocks")
            messages.error(request, "Statistic formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(stat_form=stat_form))

        if action == "update_statistic":
            statistic = get_object_or_404(Statistic, id=request.POST.get("statistic_id"))
            stat_form = BackofficeStatisticForm(request.POST, instance=statistic)
            if stat_form.is_valid():
                stat_form.save()
                messages.success(request, "Landing statistikasi yangilandi.")
            else:
                messages.error(request, "Statistic yangilashda xatolik bor.")
            return redirect("backoffice:content_landing_blocks")

        if action == "delete_statistic":
            statistic = get_object_or_404(Statistic, id=request.POST.get("statistic_id"))
            statistic.delete()
            messages.success(request, "Landing statistikasi o'chirildi.")
            return redirect("backoffice:content_landing_blocks")

        if action == "create_testimonial":
            testimonial_form = BackofficeTestimonialForm(request.POST, request.FILES)
            if testimonial_form.is_valid():
                testimonial_form.save()
                messages.success(request, "Fikr (testimonial) qo'shildi.")
                return redirect("backoffice:content_landing_blocks")
            messages.error(request, "Testimonial formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(testimonial_form=testimonial_form))

        if action == "delete_testimonial":
            testimonial = get_object_or_404(Testimonial, id=request.POST.get("testimonial_id"))
            testimonial.delete()
            messages.success(request, "Testimonial o'chirildi.")
            return redirect("backoffice:content_landing_blocks")

        messages.error(request, "Noma'lum action.")
        return redirect("backoffice:content_landing_blocks")


class BackofficeLandingTestimonialDetailView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/content_testimonial_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.testimonial = get_object_or_404(Testimonial, id=kwargs["testimonial_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "testimonial_obj": self.testimonial,
                "form": kwargs.get("form") or BackofficeTestimonialForm(instance=self.testimonial),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "update").strip()

        if action == "delete":
            self.testimonial.delete()
            messages.success(request, "Testimonial o'chirildi.")
            return redirect("backoffice:content_landing_blocks")

        form = BackofficeTestimonialForm(request.POST, request.FILES, instance=self.testimonial)
        if form.is_valid():
            form.save()
            messages.success(request, "Testimonial yangilandi.")
            return redirect("backoffice:content_testimonial_detail", testimonial_id=self.testimonial.id)
        messages.error(request, "Testimonial formasida xatolik bor.")
        return self.render_to_response(self.get_context_data(form=form))


class BackofficeAboutPageView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/content_about_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        about_page = AboutPage.load()
        context.update(
            {
                "about_page_obj": about_page,
                "form": kwargs.get("form") or BackofficeAboutPageForm(instance=about_page),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        about_page = AboutPage.load()
        form = BackofficeAboutPageForm(request.POST, instance=about_page)
        if form.is_valid():
            form.save()
            messages.success(request, "About page sozlamalari yangilandi.")
            return redirect("backoffice:content_about_page")
        messages.error(request, "About page formasida xatolik bor.")
        return self.render_to_response(self.get_context_data(form=form))


class BackofficeAboutBlocksView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/content_about_blocks.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "about_statistics": AboutStatistic.objects.order_by("order", "id"),
                "team_members": TeamMember.objects.order_by("order", "id"),
                "about_stat_form": kwargs.get("about_stat_form") or BackofficeAboutStatisticForm(),
                "team_form": kwargs.get("team_form") or BackofficeTeamMemberForm(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()

        if action == "create_about_statistic":
            about_stat_form = BackofficeAboutStatisticForm(request.POST)
            if about_stat_form.is_valid():
                about_stat_form.save()
                messages.success(request, "About statistikasi qo'shildi.")
                return redirect("backoffice:content_about_blocks")
            messages.error(request, "About statistic formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(about_stat_form=about_stat_form))

        if action == "update_about_statistic":
            statistic = get_object_or_404(AboutStatistic, id=request.POST.get("about_statistic_id"))
            about_stat_form = BackofficeAboutStatisticForm(request.POST, instance=statistic)
            if about_stat_form.is_valid():
                about_stat_form.save()
                messages.success(request, "About statistikasi yangilandi.")
            else:
                messages.error(request, "About statistic yangilashda xatolik bor.")
            return redirect("backoffice:content_about_blocks")

        if action == "delete_about_statistic":
            statistic = get_object_or_404(AboutStatistic, id=request.POST.get("about_statistic_id"))
            statistic.delete()
            messages.success(request, "About statistikasi o'chirildi.")
            return redirect("backoffice:content_about_blocks")

        if action == "create_team_member":
            team_form = BackofficeTeamMemberForm(request.POST, request.FILES)
            if team_form.is_valid():
                team_form.save()
                messages.success(request, "Jamoa a'zosi qo'shildi.")
                return redirect("backoffice:content_about_blocks")
            messages.error(request, "Team member formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(team_form=team_form))

        if action == "delete_team_member":
            member = get_object_or_404(TeamMember, id=request.POST.get("member_id"))
            member.delete()
            messages.success(request, "Jamoa a'zosi o'chirildi.")
            return redirect("backoffice:content_about_blocks")

        messages.error(request, "Noma'lum action.")
        return redirect("backoffice:content_about_blocks")


class BackofficeTeamMemberDetailView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/content_team_member_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.member = get_object_or_404(TeamMember, id=kwargs["member_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "member_obj": self.member,
                "form": kwargs.get("form") or BackofficeTeamMemberForm(instance=self.member),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "update").strip()

        if action == "delete":
            self.member.delete()
            messages.success(request, "Jamoa a'zosi o'chirildi.")
            return redirect("backoffice:content_about_blocks")

        form = BackofficeTeamMemberForm(request.POST, request.FILES, instance=self.member)
        if form.is_valid():
            form.save()
            messages.success(request, "Jamoa a'zosi yangilandi.")
            return redirect("backoffice:content_team_member_detail", member_id=self.member.id)
        messages.error(request, "Team member formasida xatolik bor.")
        return self.render_to_response(self.get_context_data(form=form))


class BackofficeLandingNavItemsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/content_landing_nav.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        _ensure_landing_nav_items()
        context.update(
            {
                "nav_items": LandingNavItem.objects.order_by("order", "id"),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        _ensure_landing_nav_items()
        action = (request.POST.get("action") or "").strip()

        if action == "update_nav_item":
            nav_item = get_object_or_404(LandingNavItem, id=request.POST.get("nav_item_id"))
            form = BackofficeLandingNavItemForm(request.POST, instance=nav_item)
            if form.is_valid():
                form.save()
                messages.success(request, "Navbar elementi yangilandi.")
            else:
                messages.error(request, "Navbar elementi formasida xatolik bor.")
            return redirect("backoffice:content_landing_nav")

        if action == "normalize_order":
            for index, item in enumerate(LandingNavItem.objects.order_by("order", "id"), start=1):
                if item.order != index:
                    item.order = index
                    item.save(update_fields=["order"])
            messages.success(request, "Navbar tartibi normalizatsiya qilindi.")
            return redirect("backoffice:content_landing_nav")

        messages.error(request, "Noma'lum action.")
        return redirect("backoffice:content_landing_nav")


class BackofficeBlogHomeSettingsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/content_blog_home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings_obj = BlogHomeSettings.load()
        context.update(
            {
                "settings_obj": settings_obj,
                "form": kwargs.get("form") or BackofficeBlogHomeSettingsForm(instance=settings_obj),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        settings_obj = BlogHomeSettings.load()
        form = BackofficeBlogHomeSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Blog home settings yangilandi.")
            return redirect("backoffice:content_blog_home")
        messages.error(request, "Blog home settings formasida xatolik bor.")
        return self.render_to_response(self.get_context_data(form=form))


class BackofficeBlogTagsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/content_blog_tags.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "tags": BlogTag.objects.order_by("name"),
                "create_form": kwargs.get("create_form") or BackofficeBlogTagForm(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()

        if action == "create_tag":
            create_form = BackofficeBlogTagForm(request.POST)
            if create_form.is_valid():
                create_form.save()
                messages.success(request, "Blog tegi qo'shildi.")
                return redirect("backoffice:content_blog_tags")
            messages.error(request, "Tag formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(create_form=create_form))

        if action == "update_tag":
            tag = get_object_or_404(BlogTag, id=request.POST.get("tag_id"))
            form = BackofficeBlogTagForm(request.POST, instance=tag)
            if form.is_valid():
                form.save()
                messages.success(request, "Blog tegi yangilandi.")
            else:
                messages.error(request, "Tag yangilashda xatolik bor.")
            return redirect("backoffice:content_blog_tags")

        if action == "delete_tag":
            tag = get_object_or_404(BlogTag, id=request.POST.get("tag_id"))
            tag.delete()
            messages.success(request, "Blog tegi o'chirildi.")
            return redirect("backoffice:content_blog_tags")

        messages.error(request, "Noma'lum action.")
        return redirect("backoffice:content_blog_tags")


class BackofficeBlogSignalsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/content_blog_signals.html"

    def _safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = (self.request.GET.get("q") or "").strip()
        selected_kind = (self.request.GET.get("kind") or "all").strip().lower()
        selected_post_id = self._safe_int(self.request.GET.get("post_id"))

        reads = BlogPostRead.objects.select_related("post", "user")
        claps = BlogPostClap.objects.select_related("post", "user")
        comment_likes = BlogCommentLike.objects.select_related("comment", "comment__post", "user")

        if query:
            reads = reads.filter(
                Q(post__title__icontains=query)
                | Q(viewer_key__icontains=query)
                | Q(user__username__icontains=query)
            )
            claps = claps.filter(
                Q(post__title__icontains=query)
                | Q(viewer_key__icontains=query)
                | Q(user__username__icontains=query)
            )
            comment_likes = comment_likes.filter(
                Q(comment__post__title__icontains=query)
                | Q(comment__content__icontains=query)
                | Q(user__username__icontains=query)
            )

        if selected_post_id:
            reads = reads.filter(post_id=selected_post_id)
            claps = claps.filter(post_id=selected_post_id)
            comment_likes = comment_likes.filter(comment__post_id=selected_post_id)

        if selected_kind not in {"all", "reads", "claps", "comment_likes"}:
            selected_kind = "all"

        context.update(
            {
                "search_query": query,
                "selected_kind": selected_kind,
                "selected_post_id": selected_post_id,
                "posts": BlogPost.objects.order_by("-updated_at")[:150],
                "reads": reads.order_by("-last_seen_at")[:220],
                "claps": claps.order_by("-updated_at")[:220],
                "comment_likes": comment_likes.order_by("-created_at")[:220],
                "summary_reads": BlogPostRead.objects.count(),
                "summary_claps": BlogPostClap.objects.count(),
                "summary_comment_likes": BlogCommentLike.objects.count(),
            }
        )
        return context


class BackofficeLegalPagesView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/legal_pages.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for page_type in [LegalPage.PAGE_PRIVACY, LegalPage.PAGE_TERMS, LegalPage.PAGE_FAQ]:
            defaults = LegalPage.defaults_for(page_type)
            LegalPage.objects.get_or_create(page_type=page_type, defaults=defaults)

        context.update(
            {
                "pages": LegalPage.objects.order_by("page_type"),
            }
        )
        return context


class BackofficeLegalPageDetailView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/legal_page_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.page = get_object_or_404(LegalPage, id=kwargs["page_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_obj": self.page,
                "form": kwargs.get("form") or BackofficeLegalPageForm(instance=self.page),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        form = BackofficeLegalPageForm(request.POST, instance=self.page)
        if form.is_valid():
            form.save()
            messages.success(request, "Legal page yangilandi.")
            return redirect("backoffice:legal_page_detail", page_id=self.page.id)
        messages.error(request, "Legal page formada xatolik bor.")
        return self.render_to_response(self.get_context_data(form=form))


class BackofficeBlogPostsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/blog_posts.html"

    def _queryset(self):
        query = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "all").strip().lower()
        featured = (self.request.GET.get("featured") or "all").strip().lower()
        posts = BlogPost.objects.select_related("author").prefetch_related("tags")

        if query:
            posts = posts.filter(
                Q(title__icontains=query)
                | Q(excerpt__icontains=query)
                | Q(body__icontains=query)
                | Q(author__username__icontains=query)
            )

        if status in {BlogPost.STATUS_DRAFT, BlogPost.STATUS_PUBLISHED}:
            posts = posts.filter(status=status)
        else:
            status = "all"

        if featured == "yes":
            posts = posts.filter(featured=True)
        elif featured == "no":
            posts = posts.filter(featured=False)
        else:
            featured = "all"

        return posts.order_by("-updated_at")[:220], query, status, featured

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        posts, query, status, featured = self._queryset()
        context.update(
            {
                "posts": posts,
                "search_query": query,
                "selected_status": status,
                "selected_featured": featured,
                "summary_total": BlogPost.objects.count(),
                "summary_published": BlogPost.objects.filter(status=BlogPost.STATUS_PUBLISHED).count(),
                "summary_draft": BlogPost.objects.filter(status=BlogPost.STATUS_DRAFT).count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()
        ids = request.POST.getlist("post_ids")
        queryset = BlogPost.objects.filter(id__in=ids)
        if not queryset.exists():
            messages.error(request, "Kamida bitta post tanlang.")
            return redirect(request.get_full_path())

        if action == "mark_draft":
            updated = queryset.update(status=BlogPost.STATUS_DRAFT)
            messages.success(request, f"{updated} ta post qoralama holatga o'tdi.")
            return redirect(request.get_full_path())

        if action == "mark_published":
            now = timezone.now()
            updated = queryset.update(status=BlogPost.STATUS_PUBLISHED, published_at=now)
            messages.success(request, f"{updated} ta post nashr qilindi.")
            return redirect(request.get_full_path())

        if action == "mark_featured_on":
            updated = queryset.update(featured=True)
            messages.success(request, f"{updated} ta post featured bo'ldi.")
            return redirect(request.get_full_path())

        if action == "mark_featured_off":
            updated = queryset.update(featured=False)
            messages.success(request, f"{updated} ta post featured holatdan olindi.")
            return redirect(request.get_full_path())

        messages.error(request, "Noma'lum action.")
        return redirect(request.get_full_path())


class BackofficeBlogCommentsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/blog_comments.html"

    def _queryset(self):
        query = (self.request.GET.get("q") or "").strip()
        deleted = (self.request.GET.get("deleted") or "all").strip().lower()
        comments = BlogComment.objects.select_related("post", "user", "parent")

        if query:
            comments = comments.filter(
                Q(content__icontains=query)
                | Q(post__title__icontains=query)
                | Q(user__username__icontains=query)
                | Q(user__email__icontains=query)
            )

        if deleted == "yes":
            comments = comments.filter(is_deleted=True)
        elif deleted == "no":
            comments = comments.filter(is_deleted=False)
        else:
            deleted = "all"

        return comments.order_by("-created_at")[:220], query, deleted

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comments, query, deleted = self._queryset()
        context.update(
            {
                "comments": comments,
                "search_query": query,
                "selected_deleted": deleted,
                "summary_total": BlogComment.objects.count(),
                "summary_deleted": BlogComment.objects.filter(is_deleted=True).count(),
                "summary_active": BlogComment.objects.filter(is_deleted=False).count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()
        ids = request.POST.getlist("comment_ids")
        queryset = BlogComment.objects.filter(id__in=ids)
        if not queryset.exists():
            messages.error(request, "Kamida bitta comment tanlang.")
            return redirect(request.get_full_path())

        if action == "mark_deleted":
            updated = queryset.update(is_deleted=True)
            messages.success(request, f"{updated} ta comment o'chirilgan holatga o'tdi.")
            return redirect(request.get_full_path())

        if action == "restore":
            updated = queryset.update(is_deleted=False)
            messages.success(request, f"{updated} ta comment tiklandi.")
            return redirect(request.get_full_path())

        messages.error(request, "Noma'lum action.")
        return redirect(request.get_full_path())


class BackofficeMessengerRoomsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/messenger_rooms.html"

    def _queryset(self):
        query = (self.request.GET.get("q") or "").strip()
        room_type = (self.request.GET.get("room_type") or "all").strip().lower()

        rooms = ChatRoom.objects.select_related("cohort", "cohort__course").prefetch_related("participants").annotate(
            message_count=Count("messages", distinct=True),
            participant_count=Count("participants", distinct=True),
        )

        if query:
            rooms = rooms.filter(
                Q(name__icontains=query)
                | Q(cohort__name__icontains=query)
                | Q(cohort__course__title__icontains=query)
                | Q(participants__username__icontains=query)
            ).distinct()

        if room_type in {"group", "private", "ai"}:
            rooms = rooms.filter(room_type=room_type)
        else:
            room_type = "all"

        return rooms.order_by("-created_at")[:220], query, room_type

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rooms, query, room_type = self._queryset()
        context.update(
            {
                "rooms": rooms,
                "search_query": query,
                "selected_room_type": room_type,
                "create_form": kwargs.get("create_form") or BackofficeChatRoomForm(),
                "summary_total": ChatRoom.objects.count(),
                "summary_group": ChatRoom.objects.filter(room_type="group").count(),
                "summary_private": ChatRoom.objects.filter(room_type="private").count(),
                "summary_ai": ChatRoom.objects.filter(room_type="ai").count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        form = BackofficeChatRoomForm(request.POST)
        if form.is_valid():
            room = form.save()
            messages.success(request, f"Yangi chat xona yaratildi: {room}.")
            return redirect("backoffice:messenger_room_detail", room_id=room.id)
        messages.error(request, "Chat xona formasida xatolik bor.")
        return self.render_to_response(self.get_context_data(create_form=form))


class BackofficeMessengerRoomDetailView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/messenger_room_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.room = get_object_or_404(
            ChatRoom.objects.select_related("cohort", "cohort__course").prefetch_related("participants"),
            id=kwargs["room_id"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "room": self.room,
                "room_form": kwargs.get("room_form") or BackofficeChatRoomForm(instance=self.room),
                "message_form": kwargs.get("message_form") or BackofficeMessageCreateForm(room=self.room),
                "messages_list": self.room.messages.select_related("sender", "context_lesson").order_by("-created_at")[:100],
                "participants": self.room.participants.order_by("username"),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()

        if action == "update_room":
            room_form = BackofficeChatRoomForm(request.POST, instance=self.room)
            if room_form.is_valid():
                room_form.save()
                messages.success(request, "Chat xona yangilandi.")
                return redirect("backoffice:messenger_room_detail", room_id=self.room.id)
            messages.error(request, "Chat xona yangilash formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(room_form=room_form))

        if action == "add_message":
            message_form = BackofficeMessageCreateForm(request.POST, room=self.room)
            if message_form.is_valid():
                new_message = message_form.save(commit=False)
                new_message.room = self.room
                new_message.save()
                messages.success(request, "Xabar qo'shildi.")
                return redirect("backoffice:messenger_room_detail", room_id=self.room.id)
            messages.error(request, "Xabar formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(message_form=message_form))

        if action == "mark_all_read":
            updated = self.room.messages.filter(is_read=False).update(is_read=True)
            messages.success(request, f"{updated} ta xabar o'qilgan deb belgilandi.")
            return redirect("backoffice:messenger_room_detail", room_id=self.room.id)

        if action == "clear_messages":
            deleted, _ = self.room.messages.all().delete()
            messages.success(request, f"{deleted} ta xabar o'chirildi.")
            return redirect("backoffice:messenger_room_detail", room_id=self.room.id)

        messages.error(request, "Noma'lum action.")
        return redirect("backoffice:messenger_room_detail", room_id=self.room.id)


class BackofficeMessengerMessagesView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/messenger_messages.html"

    def _queryset(self):
        query = (self.request.GET.get("q") or "").strip()
        room_type = (self.request.GET.get("room_type") or "all").strip().lower()
        unread = (self.request.GET.get("unread") or "all").strip().lower()
        ai_only = (self.request.GET.get("ai_only") or "all").strip().lower()

        messages_qs = Message.objects.select_related("room", "sender", "context_lesson")

        if query:
            messages_qs = messages_qs.filter(
                Q(text__icontains=query)
                | Q(sender__username__icontains=query)
                | Q(room__name__icontains=query)
                | Q(context_lesson__title__icontains=query)
            )

        if room_type in {"group", "private", "ai"}:
            messages_qs = messages_qs.filter(room__room_type=room_type)
        else:
            room_type = "all"

        if unread == "yes":
            messages_qs = messages_qs.filter(is_read=False)
        elif unread == "no":
            messages_qs = messages_qs.filter(is_read=True)
        else:
            unread = "all"

        if ai_only == "yes":
            messages_qs = messages_qs.filter(is_ai_response=True)
        elif ai_only == "no":
            messages_qs = messages_qs.filter(is_ai_response=False)
        else:
            ai_only = "all"

        return messages_qs.order_by("-created_at")[:260], query, room_type, unread, ai_only

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        messages_qs, query, room_type, unread, ai_only = self._queryset()
        context.update(
            {
                "messages_list": messages_qs,
                "search_query": query,
                "selected_room_type": room_type,
                "selected_unread": unread,
                "selected_ai_only": ai_only,
                "summary_total": Message.objects.count(),
                "summary_unread": Message.objects.filter(is_read=False).count(),
                "summary_ai": Message.objects.filter(is_ai_response=True).count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()
        ids = request.POST.getlist("message_ids")
        queryset = Message.objects.filter(id__in=ids)
        if not queryset.exists():
            messages.error(request, "Kamida bitta xabar tanlang.")
            return redirect(request.get_full_path())

        if action == "mark_read":
            updated = queryset.update(is_read=True)
            messages.success(request, f"{updated} ta xabar o'qilgan deb belgilandi.")
            return redirect(request.get_full_path())

        if action == "mark_unread":
            updated = queryset.update(is_read=False)
            messages.success(request, f"{updated} ta xabar o'qilmagan holatga qaytdi.")
            return redirect(request.get_full_path())

        if action == "delete_messages":
            deleted, _ = queryset.delete()
            messages.success(request, f"{deleted} ta xabar o'chirildi.")
            return redirect(request.get_full_path())

        messages.error(request, "Noma'lum action.")
        return redirect(request.get_full_path())


class BackofficeMessengerRAGChunksView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/messenger_rag_chunks.html"

    def _safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _queryset(self):
        query = (self.request.GET.get("q") or "").strip()
        course_id = self._safe_int(self.request.GET.get("course_id"))
        model_name = (self.request.GET.get("model") or "").strip()

        chunks = LessonRAGChunk.objects.select_related("course", "lesson")

        if query:
            chunks = chunks.filter(
                Q(chunk_text__icontains=query)
                | Q(lesson__title__icontains=query)
                | Q(course__title__icontains=query)
            )

        if course_id:
            chunks = chunks.filter(course_id=course_id)

        if model_name:
            chunks = chunks.filter(embedding_model=model_name)

        return chunks.order_by("-updated_at")[:280], query, course_id, model_name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chunks, query, course_id, model_name = self._queryset()
        context.update(
            {
                "chunks": chunks,
                "search_query": query,
                "selected_course_id": course_id,
                "selected_model": model_name,
                "courses": Course.objects.filter(is_active=True).order_by("title"),
                "models": LessonRAGChunk.objects.values_list("embedding_model", flat=True).distinct().order_by("embedding_model"),
                "summary_total": LessonRAGChunk.objects.count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()
        ids = request.POST.getlist("chunk_ids")
        queryset = LessonRAGChunk.objects.filter(id__in=ids)
        if not queryset.exists():
            messages.error(request, "Kamida bitta chunk tanlang.")
            return redirect(request.get_full_path())

        if action == "delete_chunks":
            deleted, _ = queryset.delete()
            messages.success(request, f"{deleted} ta chunk o'chirildi.")
            return redirect(request.get_full_path())

        messages.error(request, "Noma'lum action.")
        return redirect(request.get_full_path())


class BackofficeGamificationLevelsView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/gamification_levels.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "levels": Level.objects.order_by("min_xp", "id"),
                "create_form": kwargs.get("create_form") or BackofficeLevelForm(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()

        if action == "create_level":
            create_form = BackofficeLevelForm(request.POST, request.FILES)
            if create_form.is_valid():
                create_form.save()
                messages.success(request, "Yangi level qo'shildi.")
                return redirect("backoffice:gamification_levels")
            messages.error(request, "Level formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(create_form=create_form))

        if action == "update_level":
            level = get_object_or_404(Level, id=request.POST.get("level_id"))
            form = BackofficeLevelForm(request.POST, request.FILES, instance=level)
            if form.is_valid():
                form.save()
                messages.success(request, "Level yangilandi.")
            else:
                messages.error(request, "Level yangilashda xatolik bor.")
            return redirect("backoffice:gamification_levels")

        if action == "delete_level":
            level = get_object_or_404(Level, id=request.POST.get("level_id"))
            level.delete()
            messages.success(request, "Level o'chirildi.")
            return redirect("backoffice:gamification_levels")

        messages.error(request, "Noma'lum action.")
        return redirect("backoffice:gamification_levels")


class BackofficeGamificationBadgesView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/gamification_badges.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        badges = Badge.objects.annotate(earned_count=Count("earnedbadge")).order_by("name")
        context.update(
            {
                "badges": badges,
                "create_form": kwargs.get("create_form") or BackofficeBadgeForm(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()

        if action == "create_badge":
            create_form = BackofficeBadgeForm(request.POST, request.FILES)
            if create_form.is_valid():
                create_form.save()
                messages.success(request, "Yangi badge qo'shildi.")
                return redirect("backoffice:gamification_badges")
            messages.error(request, "Badge formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(create_form=create_form))

        if action == "delete_badge":
            badge = get_object_or_404(Badge, id=request.POST.get("badge_id"))
            badge.delete()
            messages.success(request, "Badge o'chirildi.")
            return redirect("backoffice:gamification_badges")

        messages.error(request, "Noma'lum action.")
        return redirect("backoffice:gamification_badges")


class BackofficeGamificationBadgeDetailView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/gamification_badge_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.badge = get_object_or_404(Badge, id=kwargs["badge_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "badge_obj": self.badge,
                "form": kwargs.get("form") or BackofficeBadgeForm(instance=self.badge),
                "recent_earned": EarnedBadge.objects.select_related("student").filter(badge=self.badge).order_by("-earned_at")[:80],
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "update").strip()
        if action == "delete":
            self.badge.delete()
            messages.success(request, "Badge o'chirildi.")
            return redirect("backoffice:gamification_badges")

        form = BackofficeBadgeForm(request.POST, request.FILES, instance=self.badge)
        if form.is_valid():
            form.save()
            messages.success(request, "Badge yangilandi.")
            return redirect("backoffice:gamification_badge_detail", badge_id=self.badge.id)
        messages.error(request, "Badge formasida xatolik bor.")
        return self.render_to_response(self.get_context_data(form=form))


class BackofficeGamificationEarnedBadgesView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/gamification_earned_badges.html"

    def _safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _queryset(self):
        query = (self.request.GET.get("q") or "").strip()
        badge_id = self._safe_int(self.request.GET.get("badge_id"))

        earned = EarnedBadge.objects.select_related("student", "badge")
        if query:
            earned = earned.filter(
                Q(student__username__icontains=query)
                | Q(student__email__icontains=query)
                | Q(badge__name__icontains=query)
            )
        if badge_id:
            earned = earned.filter(badge_id=badge_id)

        return earned.order_by("-earned_at")[:260], query, badge_id

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        earned, query, badge_id = self._queryset()
        context.update(
            {
                "earned_badges": earned,
                "search_query": query,
                "selected_badge_id": badge_id,
                "badges": Badge.objects.order_by("name"),
                "summary_total": EarnedBadge.objects.count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()
        ids = request.POST.getlist("earned_badge_ids")
        queryset = EarnedBadge.objects.filter(id__in=ids)
        if not queryset.exists():
            messages.error(request, "Kamida bitta yozuv tanlang.")
            return redirect(request.get_full_path())

        if action == "revoke_selected":
            deleted, _ = queryset.delete()
            messages.success(request, f"{deleted} ta earned badge yozuvi o'chirildi.")
            return redirect(request.get_full_path())

        messages.error(request, "Noma'lum action.")
        return redirect(request.get_full_path())


class BackofficeGamificationCertificatesView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/gamification_certificates.html"

    def _safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _queryset(self):
        query = (self.request.GET.get("q") or "").strip()
        course_id = self._safe_int(self.request.GET.get("course_id"))

        certificates = GamificationCertificate.objects.select_related("student", "course")
        if query:
            certificates = certificates.filter(
                Q(student__username__icontains=query)
                | Q(student__email__icontains=query)
                | Q(course__title__icontains=query)
                | Q(certificate_id__icontains=query)
            )
        if course_id:
            certificates = certificates.filter(course_id=course_id)

        return certificates.order_by("-issued_at")[:260], query, course_id

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        certificates, query, course_id = self._queryset()
        context.update(
            {
                "certificates": certificates,
                "search_query": query,
                "selected_course_id": course_id,
                "courses": Course.objects.filter(is_active=True).order_by("title"),
                "create_form": kwargs.get("create_form") or BackofficeGamificationCertificateForm(),
                "summary_total": GamificationCertificate.objects.count(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = (request.POST.get("action") or "").strip()

        if action == "create_certificate":
            create_form = BackofficeGamificationCertificateForm(request.POST, request.FILES)
            if create_form.is_valid():
                create_form.save()
                messages.success(request, "Sertifikat yozuvi yaratildi.")
                return redirect("backoffice:gamification_certificates")
            messages.error(request, "Sertifikat formasida xatolik bor.")
            return self.render_to_response(self.get_context_data(create_form=create_form))

        ids = request.POST.getlist("certificate_ids")
        queryset = GamificationCertificate.objects.filter(id__in=ids)
        if not queryset.exists():
            messages.error(request, "Kamida bitta sertifikat tanlang.")
            return redirect(request.get_full_path())

        if action == "delete_selected":
            deleted, _ = queryset.delete()
            messages.success(request, f"{deleted} ta sertifikat o'chirildi.")
            return redirect(request.get_full_path())

        messages.error(request, "Noma'lum action.")
        return redirect(request.get_full_path())
