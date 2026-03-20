from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, TemplateView, ListView, View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q
import datetime
import base64
import calendar
from .forms import CustomUserCreationForm
from .models import CustomUser, Notification
from django.shortcuts import redirect, render, get_object_or_404
from cohorts.models import Enrollment, Attendance, Cohort
from courses.models import Certificate as CourseCertificate
from courses.models import Course
from gamification.models import EarnedBadge
from frontend.models import LegalPage
from django.core.signing import TimestampSigner
from django.conf import settings
from courses.models import Lesson
from .notification_service import ensure_subscription_notifications_for_user
import os
import uuid

def home_view(request):
    """
    Renders the landing page for guests.
    Redirects authenticated users straight to the dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')


class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Muvaffaqiyatli ro'yxatdan o'tdingiz! Iltimos tizimga kiring.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Xatolik yuz berdi. Iltimos, ma'lumotlarni tekshirib qaytadan kiriting.")
        return super().form_invalid(form)


class SettingsView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    template_name = 'users/settings.html'
    fields = ['first_name', 'last_name', 'phone_number', 'bio']
    success_url = reverse_lazy('settings')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['active_nav'] = 'settings'
        context['active_courses_count'] = user.enrollments.filter(status='active').count()
        context['certificates_count'] = CourseCertificate.objects.filter(student=user).count()
        passed_lessons_count = Attendance.objects.filter(
            enrollment__student=user,
            status__in=[Attendance.STATUS_PRESENT, Attendance.STATUS_PARTIAL],
        ).count()
        context['total_hours'] = passed_lessons_count * 2
        return context

    def form_valid(self, form):
        messages.success(self.request, "Profil ma'lumotlari muvaffaqiyatli yangilandi.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Xatolik yuz berdi. Iltimos, barcha maydonlarni tekshiring.")
        return super().form_invalid(form)

class AvatarUpdateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        if 'avatar' in request.FILES:
            avatar_file = request.FILES['avatar']
            old_avatar_name = user.avatar.name if user.avatar else None

            # Cache muammosini oldini olish uchun har safar yangi, unikal fayl nomi beramiz.
            ext = os.path.splitext(avatar_file.name)[1].lower() or '.jpg'
            avatar_file.name = f'user_{user.id}_{uuid.uuid4().hex}{ext}'

            user.avatar = avatar_file
            user.save(update_fields=['avatar'])

            # Yangi avatar saqlangandan keyin eski faylni tozalash (agar mavjud bo'lsa)
            if old_avatar_name and old_avatar_name != user.avatar.name:
                user.avatar.storage.delete(old_avatar_name)

            messages.success(request, "Profil rasmi muvaffaqiyatli yangilandi.")
        else:
            messages.error(request, "Rasm tanlanmadi.")
        return redirect('settings')

class PasswordUpdateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        user = request.user
        old_pass = request.POST.get('old_password')
        new_pass1 = request.POST.get('new_password1')
        new_pass2 = request.POST.get('new_password2')
        
        if not user.check_password(old_pass):
            messages.error(request, "Joriy parol noto'g'ri.")
            return redirect('settings')
        if new_pass1 != new_pass2:
            messages.error(request, "Yangi parollar mos kelmadi.")
            return redirect('settings')
            
        try:
            validate_password(new_pass1, user)
        except ValidationError as e:
            messages.error(request, f"Parol juda oddiy: {' '.join(e.messages)}")
            return redirect('settings')
            
        user.set_password(new_pass1)
        user.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Parol muvaffaqiyatli o'zgartirildi.")
        return redirect('settings')

    def form_valid(self, form):
        messages.success(self.request, "Profil ma'lumotlari yordamida muvaffaqiyatli yangilandi.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Xatolik yuz berdi. Iltimos, barcha maydonlarni tekshiring.")
        return super().form_invalid(form)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'users/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['active_nav'] = 'dashboard'
        
        # --- Grace Period Check Logging ---
        today = timezone.now().date()
        grace_limit = today - datetime.timedelta(days=2)
        
        # Find all active enrollments where deadline passed grace limit
        expired_enrollments = user.enrollments.filter(
            status='active',
            next_payment_deadline__lt=grace_limit
        )
        
        # Optimize: Avoid N+1 query by doing a single bulk update
        if expired_enrollments.exists():
            expired_enrollments.update(status='expired')
        
        enrollments = list(
            user.enrollments.select_related(
                'cohort',
                'cohort__course',
                'cohort__course__instructor',
                'plan',
            ).annotate(
                total_lessons_count=Count('cohort__course__modules__lessons', distinct=True),
                completed_attendance_count=Count(
                    'attendance__lesson',
                    filter=Q(attendance__status__in=[Attendance.STATUS_PRESENT, Attendance.STATUS_PARTIAL]),
                    distinct=True,
                ),
                completed_progress_count=Count(
                    'lesson_progress',
                    filter=Q(lesson_progress__is_completed=True),
                    distinct=True,
                ),
            )
        )

        status_priority = {'active': 0, 'pending': 1, 'frozen': 2, 'expired': 3}
        enrollments.sort(
            key=lambda item: (
                status_priority.get(item.status, 9),
                -item.joined_at.timestamp(),
            )
        )

        for enrollment in enrollments:
            total_lessons = enrollment.total_lessons_count or 0
            completed_lessons = max(
                enrollment.completed_attendance_count or 0,
                enrollment.completed_progress_count or 0,
            )
            enrollment.dashboard_total_lessons = total_lessons
            enrollment.dashboard_completed_lessons = completed_lessons
            enrollment.dashboard_progress = (
                int(round((completed_lessons / total_lessons) * 100))
                if total_lessons
                else 0
            )
            enrollment.dashboard_status_label = enrollment.get_status_display()
            enrollment.dashboard_status_tone = {
                'active': 'success',
                'pending': 'warning',
                'expired': 'danger',
                'frozen': 'secondary',
            }.get(enrollment.status, 'secondary')
            enrollment.dashboard_days_left = None
            if enrollment.next_payment_deadline:
                enrollment.dashboard_days_left = (
                    enrollment.next_payment_deadline - today
                ).days

        context['active_enrollments'] = enrollments
        active_enrollment_qs = user.enrollments.filter(status='active')
        context['active_courses_count'] = active_enrollment_qs.count()

        # Dashboard metriclar: o'tilgan darslar soni attendance va LMS lesson progress asosida hisoblanadi.
        attendance_lessons_count = Attendance.objects.filter(
            enrollment__student=user,
            status__in=[Attendance.STATUS_PRESENT, Attendance.STATUS_PARTIAL],
        ).values('lesson_id').distinct().count()
        progress_lessons_count = user.enrollments.filter(
            status='active',
        ).aggregate(
            total=Count(
                'lesson_progress',
                filter=Q(lesson_progress__is_completed=True),
                distinct=True,
            )
        )['total'] or 0
        passed_lessons_count = max(attendance_lessons_count, progress_lessons_count)
        context['completed_lessons_count'] = passed_lessons_count
        context['completed_lessons'] = passed_lessons_count
        context['average_progress'] = passed_lessons_count
        context['total_hours'] = passed_lessons_count * 2
        context['study_hours'] = context['total_hours']
        context['xp_points'] = user.total_xp if hasattr(user, 'total_xp') else 0
        context['streak_days'] = user.streak_days if hasattr(user, 'streak_days') else 0

        context['achievements_count'] = EarnedBadge.objects.filter(student=user).count()
        context['certificates_count'] = CourseCertificate.objects.filter(student=user).count()
        context.update(get_cohort_leaderboard_context(user))

        profile_checks = [
            bool(user.first_name),
            bool(user.last_name),
            bool(user.phone_number),
            bool(user.avatar),
            bool(user.bio),
        ]
        context['profile_completion'] = int(round((sum(profile_checks) / len(profile_checks)) * 100))

        context['primary_enrollment'] = next(
            (item for item in enrollments if item.status == 'active'),
            enrollments[0] if enrollments else None,
        )
        context['current_plan'] = (
            context['primary_enrollment'].plan
            if context['primary_enrollment'] and context['primary_enrollment'].plan_id
            else next((item.plan for item in enrollments if item.plan_id), None)
        )

        enrolled_course_ids = {item.cohort.course_id for item in enrollments}
        context['recommended_courses'] = (
            Course.objects.filter(is_active=True)
            .exclude(id__in=enrolled_course_ids)
            .select_related('instructor')
            .annotate(
                annotated_lessons_count=Count('modules__lessons', distinct=True),
                annotated_students_count=Count(
                    'cohorts__members',
                    filter=Q(cohorts__members__status='active'),
                    distinct=True,
                ),
            )
            .order_by('-annotated_students_count', '-created_at')[:3]
        )

        # O'quvchining joriy telegram holati
        if user.telegram_id:
            context['telegram_linked'] = True
            context['telegram_username'] = user.telegram_username
        else:
            # Token generate for telegram bot binding
            # Use standard Signer because TimestampSigner produces too large a payload for Base64ing 64-chars Telegram limit
            from django.core.signing import Signer
            import base64
            
            signer = Signer()
            raw_token = signer.sign(str(user.id))
            token = base64.urlsafe_b64encode(raw_token.encode()).decode().rstrip('=')
            
            context['telegram_linked'] = False
            # Construct the deep link URL format: https://t.me/BOT_USERNAME?start=PAYLOAD
            bot_username = getattr(settings, 'BOT_USERNAME', '')
            if bot_username:
                context['telegram_bot_link'] = f"https://t.me/{bot_username.strip('@')}?start={token}"
            else:
                context['telegram_bot_link'] = f"https://t.me/lmsazurebot?start={token}"
            
        return context


def get_cohort_leaderboard_context(user):
    context = {
        'leaderboard_cohort': None,
        'leaderboard_top': [],
        'leaderboard_my_row': None,
    }

    current_active_enrollment = (
        user.enrollments.filter(status='active')
        .select_related('cohort')
        .order_by('-joined_at')
        .first()
    )
    context['leaderboard_cohort'] = current_active_enrollment.cohort if current_active_enrollment else None

    if not current_active_enrollment:
        return context

    leaderboard_qs = (
        Enrollment.objects.filter(
            cohort=current_active_enrollment.cohort,
            status='active',
        )
        .select_related('student')
        .order_by('-student__total_xp', 'joined_at', 'student__id')
    )

    for rank, enrollment in enumerate(leaderboard_qs, start=1):
        row = {
            'rank': rank,
            'student': enrollment.student,
            'xp': enrollment.student.total_xp,
            'is_me': enrollment.student_id == user.id,
        }
        if rank <= 10:
            context['leaderboard_top'].append(row)
        if row['is_me']:
            context['leaderboard_my_row'] = row
        if rank > 10 and context['leaderboard_my_row']:
            break

    return context


class LeaderboardView(LoginRequiredMixin, TemplateView):
    template_name = 'users/leaderboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_nav'] = 'leaderboard'
        context.update(get_cohort_leaderboard_context(self.request.user))
        return context


class NotificationCenterView(LoginRequiredMixin, TemplateView):
    template_name = "users/notifications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ensure_subscription_notifications_for_user(self.request.user)
        all_notifications = Notification.objects.filter(recipient=self.request.user).order_by("-created_at")
        context["active_nav"] = "notifications"
        context["unread_notifications"] = all_notifications.filter(is_read=False)
        context["read_notifications"] = all_notifications.filter(is_read=True)[:50]
        return context


class NotificationOpenView(LoginRequiredMixin, View):
    def get(self, request, notification_id):
        notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
        notification.mark_read()
        return redirect(notification.url or "notifications")


class NotificationReadAllView(LoginRequiredMixin, View):
    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(
            is_read=True,
            read_at=timezone.now(),
        )
        return redirect("notifications")


class HelpCenterView(LoginRequiredMixin, TemplateView):
    template_name = "users/help_center.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_nav"] = "help_center"
        for page_type in [LegalPage.PAGE_PRIVACY, LegalPage.PAGE_TERMS, LegalPage.PAGE_FAQ]:
            defaults = LegalPage.defaults_for(page_type)
            LegalPage.objects.get_or_create(page_type=page_type, defaults=defaults)
        return context


class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        current_plan_enrollment = (
            user.enrollments.filter(status='active', plan__isnull=False)
            .select_related('plan')
            .order_by('-joined_at')
            .first()
        )
        if not current_plan_enrollment:
            current_plan_enrollment = (
                user.enrollments.filter(plan__isnull=False)
                .select_related('plan')
                .order_by('-joined_at')
                .first()
            )
        context['active_nav'] = 'profile'
        context['earned_badges'] = EarnedBadge.objects.filter(student=user).order_by('-earned_at')
        context['course_certificates'] = CourseCertificate.objects.filter(student=user).order_by('-issued_at')
        context['current_plan'] = current_plan_enrollment.plan if current_plan_enrollment else None
        return context


def attendance_xp_for_status(base_xp, status):
    multipliers = {
        Attendance.STATUS_PRESENT: 1.0,
        Attendance.STATUS_PARTIAL: 0.3,
        Attendance.STATUS_ABSENT: 0.0,
    }
    return round(base_xp * multipliers.get(status, 0.0))


@transaction.atomic
def upsert_attendance_and_xp(*, enrollment, lesson, date, status, marked_by):
    attendance, _ = Attendance.objects.select_for_update().get_or_create(
        enrollment=enrollment,
        lesson=lesson,
        date=date,
        defaults={
            'status': status,
            'xp_awarded': 0,
            'marked_by': marked_by,
        },
    )

    old_xp = attendance.xp_awarded
    new_xp = attendance_xp_for_status(lesson.xp_reward, status)
    xp_diff = new_xp - old_xp

    if xp_diff != 0:
        student = enrollment.student
        student.total_xp = max(0, student.total_xp + xp_diff)
        student.save(update_fields=['total_xp'])

    attendance.status = status
    attendance.xp_awarded = new_xp
    attendance.marked_by = marked_by
    attendance.save(update_fields=['status', 'xp_awarded', 'marked_by', 'marked_at'])
    return attendance


class AttendanceCalendarView(LoginRequiredMixin, TemplateView):
    template_name = 'users/attendance_calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['active_nav'] = 'attendance_calendar'

        today = timezone.localdate()
        try:
            year = int(self.request.GET.get('year', today.year))
            month = int(self.request.GET.get('month', today.month))
            datetime.date(year, month, 1)
        except (ValueError, TypeError):
            year = today.year
            month = today.month

        selected_month = datetime.date(year, month, 1)
        prev_month = (selected_month.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
        next_month = (selected_month.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)

        active_enrollment = (
            user.enrollments.filter(status='active')
            .select_related('cohort')
            .order_by('-joined_at')
            .first()
        )

        context['selected_month'] = selected_month
        context['prev_month'] = prev_month
        context['next_month'] = next_month
        context['attendance_cohort'] = active_enrollment.cohort if active_enrollment else None
        raw_weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
        context['calendar_weeks'] = [[{'day': day, 'status': None} for day in week] for week in raw_weeks]
        context['attendance_day_status'] = {}
        context['attendance_summary'] = {'present': 0, 'partial': 0, 'absent': 0}

        if not active_enrollment:
            return context

        records = Attendance.objects.filter(
            enrollment=active_enrollment,
            date__year=year,
            date__month=month,
        ).order_by('date')

        day_status = {}
        for item in records:
            day = item.date.day
            current = day_status.get(day)
            if current == Attendance.STATUS_PRESENT:
                continue
            if item.status == Attendance.STATUS_PRESENT:
                day_status[day] = Attendance.STATUS_PRESENT
            elif item.status == Attendance.STATUS_PARTIAL:
                day_status[day] = Attendance.STATUS_PARTIAL
            elif current is None:
                day_status[day] = Attendance.STATUS_ABSENT

        for status in day_status.values():
            context['attendance_summary'][status] += 1

        context['attendance_day_status'] = day_status
        context['calendar_weeks'] = [
            [
                {'day': day, 'status': day_status.get(day) if day else None}
                for day in week
            ]
            for week in raw_weeks
        ]
        return context


class AttendanceManageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'users/attendance_manage.html'

    def test_func(self):
        user = self.request.user
        return user.is_staff or user.is_superuser

    def get_allowed_cohorts(self):
        if self.request.user.is_superuser:
            return Cohort.objects.filter(is_active=True).select_related('course').order_by('name')
        return Cohort.objects.filter(
            is_active=True,
            course__instructor=self.request.user,
        ).select_related('course').order_by('name')

    def _safe_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def build_context(self):
        context = {
            'active_nav': 'attendance_manage',
        }

        cohorts = self.get_allowed_cohorts()
        context['cohorts'] = cohorts

        selected_cohort_id = self._safe_int(self.request.GET.get('cohort_id'))
        selected_lesson_id = self._safe_int(self.request.GET.get('lesson_id'))
        selected_date_raw = self.request.GET.get('date')

        selected_cohort = cohorts.filter(id=selected_cohort_id).first() if selected_cohort_id else cohorts.first()
        context['selected_cohort'] = selected_cohort

        lessons = Lesson.objects.none()
        members = Enrollment.objects.none()
        selected_lesson = None
        selected_date = timezone.localdate()

        if selected_date_raw:
            try:
                selected_date = datetime.date.fromisoformat(selected_date_raw)
            except ValueError:
                selected_date = timezone.localdate()

        if selected_cohort:
            lessons = Lesson.objects.filter(module__course=selected_cohort.course).order_by('module__order', 'order')
            members = Enrollment.objects.filter(cohort=selected_cohort, status='active').select_related('student').order_by(
                'student__first_name', 'student__last_name', 'student__username'
            )
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
                    'enrollment': enrollment,
                    'status': existing.status if existing else Attendance.STATUS_ABSENT,
                }
            )

        context['lessons'] = lessons
        context['members'] = members
        context['member_rows'] = member_rows
        context['selected_lesson'] = selected_lesson
        context['selected_date'] = selected_date
        context['existing_attendance_map'] = existing_map
        context['status_choices'] = Attendance.STATUS_CHOICES
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.build_context())
        return context

    def post(self, request, *args, **kwargs):
        context = self.build_context()
        selected_lesson = context.get('selected_lesson')
        selected_date = context.get('selected_date')
        members = context.get('members')

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

class SubscriptionHistoryView(LoginRequiredMixin, ListView):
    model = Enrollment
    template_name = 'users/subscriptions.html'
    context_object_name = 'enrollments'
    
    def get_queryset(self):
        return (
            self.request.user.enrollments.select_related('cohort', 'cohort__course', 'plan')
            .order_by('-joined_at')
        )

class CertificateListView(LoginRequiredMixin, TemplateView):
    template_name = 'users/certificates.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['active_nav'] = 'certificates'
        
        # Gamification badges
        context['earned_badges'] = EarnedBadge.objects.filter(student=user).order_by('-earned_at')
        
        # Course Completion Certificates
        context['course_certificates'] = CourseCertificate.objects.filter(student=user).order_by('-issued_at')
        
        return context
