import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Max, Q, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from cohorts.models import Attendance, Cohort, Enrollment, PaymentReceipt
from courses.models import Course, ExamAttempt, Lesson, LessonProgress
from messenger.models import ChatRoom, LessonRAGChunk, Message
from users.views import upsert_attendance_and_xp


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
