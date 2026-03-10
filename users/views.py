from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, TemplateView, ListView, View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
import datetime
import base64
from .forms import CustomUserCreationForm
from .models import CustomUser
from django.shortcuts import redirect, render
from cohorts.models import Enrollment
from courses.models import Certificate as CourseCertificate
from gamification.models import EarnedBadge
from django.core.signing import TimestampSigner
from django.conf import settings
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


class ProfileView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    template_name = 'users/profile.html'
    fields = ['first_name', 'last_name', 'phone_number', 'bio']
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return self.request.user

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
        return redirect('profile')

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
            return redirect('profile')
        if new_pass1 != new_pass2:
            messages.error(request, "Yangi parollar mos kelmadi.")
            return redirect('profile')
            
        try:
            validate_password(new_pass1, user)
        except ValidationError as e:
            messages.error(request, f"Parol juda oddiy: {' '.join(e.messages)}")
            return redirect('profile')
            
        user.set_password(new_pass1)
        user.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Parol muvaffaqiyatli o'zgartirildi.")
        return redirect('profile')

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
        
        # Haqiqiy obunalarni bazadan olish (using updated statuses)
        context['active_enrollments'] = user.enrollments.select_related('cohort', 'cohort__course').all().order_by('-joined_at')
        
        from courses.models import ExamAttempt
        
        # Calculate real dynamic statistics
        passed_exams_count = ExamAttempt.objects.filter(student=user, passed=True).count()
        context['completed_lessons'] = passed_exams_count # Masalan, nechta dars/imtihon yakunlaganini bildiradi
        context['streak_days'] = user.streak_days if hasattr(user, 'streak_days') else 0
        context['study_hours'] = passed_exams_count * 2 # Taxminan har bir dars 2 soat
        context['xp_points'] = user.total_xp if hasattr(user, 'total_xp') else passed_exams_count * 50
        
        from gamification.models import EarnedBadge
        context['achievements_count'] = EarnedBadge.objects.filter(student=user).count()

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

class SubscriptionHistoryView(LoginRequiredMixin, ListView):
    model = Enrollment
    template_name = 'users/subscriptions.html'
    context_object_name = 'enrollments'
    
    def get_queryset(self):
        return self.request.user.enrollments.all().order_by('-joined_at')

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
