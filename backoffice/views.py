import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import TemplateView

from cohorts.models import Attendance, Cohort, Enrollment, PaymentReceipt
from courses.models import (
    AssignmentSubmission,
    CohortLessonRelease,
    Course,
    ExamAttempt,
    Lesson,
    LessonProgress,
)
from messenger.models import ChatRoom, LessonRAGChunk, Message
from subscriptions.models import Plan, PlanFeature
from users.models import Notification, NotificationBroadcast
from users.notification_service import send_broadcast
from users.views import upsert_attendance_and_xp
from .forms import (
    BackofficeBroadcastForm,
    BackofficePlanFeatureForm,
    BackofficePlanForm,
    BackofficeUserUpdateForm,
)


User = get_user_model()


class BackofficeAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = "login"

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self._safe_int(self.request.GET.get("course_id"))
        status = (self.request.GET.get("status") or "active").strip().lower()

        courses = Course.objects.filter(is_active=True).order_by("title")
        cohorts = Cohort.objects.select_related("course").annotate(
            active_members=Count("members", filter=Q(members__status="active"), distinct=True),
            pending_members=Count("members", filter=Q(members__status="pending"), distinct=True),
            total_members=Count("members", distinct=True),
        )

        if course_id:
            cohorts = cohorts.filter(course_id=course_id)

        if status == "archived":
            cohorts = cohorts.filter(is_active=False)
        else:
            status = "active"
            cohorts = cohorts.filter(is_active=True)

        cohorts = cohorts.order_by("course__title", "name")[:180]

        context.update(
            {
                "courses": courses,
                "cohorts": cohorts,
                "selected_course_id": course_id,
                "selected_status": status,
                "summary_active": Cohort.objects.filter(is_active=True).count(),
                "summary_total_students": Enrollment.objects.values("student_id").distinct().count(),
                "summary_active_students": Enrollment.objects.filter(status="active").values("student_id").distinct().count(),
            }
        )
        return context


class BackofficeAttendanceView(BackofficeAccessMixin, TemplateView):
    template_name = "backoffice/attendance.html"

    def _safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def get_allowed_cohorts(self):
        return Cohort.objects.filter(is_active=True).select_related("course").order_by("name")

    def build_context(self):
        context = {}
        cohorts = self.get_allowed_cohorts()
        context["cohorts"] = cohorts

        selected_cohort_id = self._safe_int(self.request.GET.get("cohort_id"))
        selected_lesson_id = self._safe_int(self.request.GET.get("lesson_id"))
        selected_date_raw = self.request.GET.get("date")

        selected_cohort = cohorts.filter(id=selected_cohort_id).first() if selected_cohort_id else cohorts.first()
        selected_date = timezone.localdate()
        if selected_date_raw:
            try:
                selected_date = datetime.date.fromisoformat(selected_date_raw)
            except ValueError:
                selected_date = timezone.localdate()

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

        context.update(
            {
                "selected_cohort": selected_cohort,
                "selected_lesson": selected_lesson,
                "selected_date": selected_date,
                "lessons": lessons,
                "members": members,
                "member_rows": member_rows,
                "status_choices": Attendance.STATUS_CHOICES,
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
