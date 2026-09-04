from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, TemplateView, ListView, View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import update_session_auth_hash, login as auth_login
from django.utils import timezone
from django.db.models import Count, Prefetch, Q
import datetime
import calendar
from .forms import CustomUserCreationForm, ProfileFieldsForm
from django.utils.http import url_has_allowed_host_and_scheme
from .models import CustomUser, Notification
from django.shortcuts import redirect, render, get_object_or_404
from cohorts.models import Enrollment, Attendance, Cohort, PaymentReceipt, enrollment_active_access_q
from cohorts.attendance_service import upsert_attendance_and_xp
from courses.models import Certificate as CourseCertificate
from courses.models import Course, LessonProgress
from gamification.models import EarnedBadge
from frontend.models import LegalPage
from django.core.exceptions import ValidationError
from django.core.signing import TimestampSigner
from django.conf import settings
from django.http import HttpResponseBadRequest, JsonResponse
from courses.models import Lesson
import os

from core.upload_validation import validate_upload
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
    success_url = reverse_lazy('onboarding_choice')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        # Tekshiruv `dispatch` da: sahifani yashirish yetmaydi, formani
        # to'g'ridan-to'g'ri POST qilish mumkin. Mavjud foydalanuvchilar
        # kirishda davom etadi — yopilishi kerak bo'lgani ro'yxatdan o'tish.
        from core.flags import flag_enabled

        if not flag_enabled("public_registration"):
            return render(request, 'registration/register_closed.html', status=200)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        # Wizard yakunida darhol login qilamiz — onboardingdan keyin dashboardga.
        auth_login(self.request, self.object, backend='users.backends.EmailOrUsernameBackend')
        messages.success(self.request, "Xush kelibsiz! Hisobingiz tayyor.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        if not form.non_field_errors():
            messages.error(self.request, "Ma'lumotlarda xatolik bor. Iltimos qaytadan tekshiring.")
        return super().form_invalid(form)

class OnboardingChoiceView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/onboarding_choice.html'

class StartSmartOnboardingView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        from messenger.models import ChatRoom, Message, SmartFormSession

        # Bitta faol onboarding sessiyasi yetarli — qayta bosilsa o'sha xonaga qaytamiz
        existing = (
            SmartFormSession.objects.filter(
                chat_room__participants=request.user,
                schema_name='user_onboarding',
                status__in=SmartFormSession.ACTIVE_STATUSES,
            )
            .select_related('chat_room')
            .first()
        )
        if existing:
            return redirect('messenger:ai_room', room_id=existing.chat_room_id)

        room = ChatRoom.objects.create(room_type='ai', name='Azure AI Onboarding')
        room.participants.add(request.user)

        SmartFormSession.objects.create(
            chat_room=room,
            schema_name='user_onboarding',
        )
        # Xona bo'sh ochilmasin — AI birinchi savolni beradi
        # (is_ai_response=True bo'lgani uchun AI-signal qayta trigger bo'lmaydi)
        first_name = request.user.first_name or "do'stim"
        Message.objects.create(
            room=room,
            is_ai_response=True,
            text=(
                f"Salom, {first_name}! 👋 Men Azure AI man. "
                "Sizga mos o'quv rejasini tuzishim uchun bir-ikki savol beraman.\n\n"
                "Avvalo: turk tilini nima maqsadda o'rganmoqchisiz — ish, sayohat, "
                "imtihon yoki shaxsiy qiziqish uchunmi?"
            ),
        )

        return redirect('messenger:ai_room', room_id=room.id)


def _safe_next(request, fallback):
    """`next` faqat shu saytning ichki manzili bo'lsa qabul qilinadi.

    Aks holda tashqi saytga ochiq redirect bo'lib qolardi.
    """
    candidate = request.POST.get('next') or request.GET.get('next')
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return fallback


class SettingsSectionMixin(LoginRequiredMixin):
    """Sozlamalar bo'limlari uchun umumiy kontekst.

    Har bo'lim alohida sahifa; `settings_section` chap navigatsiyada
    qaysi element faol ekanini belgilaydi.
    """

    settings_section = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_nav'] = 'settings'
        context['settings_section'] = self.settings_section
        return context


class SettingsAccountView(SettingsSectionMixin, UpdateView):
    """Hisob — shaxsiy ma'lumotlar, avatar, parol va ko'rinish."""

    model = CustomUser
    template_name = 'users/settings/account.html'
    form_class = ProfileFieldsForm
    settings_section = 'account'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return _safe_next(self.request, reverse_lazy('settings_account'))

    def form_valid(self, form):
        messages.success(self.request, "Profil ma'lumotlari muvaffaqiyatli yangilandi.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Xatolik yuz berdi. Iltimos, barcha maydonlarni tekshiring.")
        return super().form_invalid(form)


class SettingsBillingView(SettingsSectionMixin, TemplateView):
    """To'lov — tarif va unga bog'liq AI foydalanish limiti."""

    template_name = 'users/settings/billing.html'
    settings_section = 'billing'

    def get_context_data(self, **kwargs):
        from aicontrol.service import build_usage_panel

        context = super().get_context_data(**kwargs)
        context['ai_usage'] = build_usage_panel(self.request.user)
        return context


class SettingsCapabilitiesView(SettingsSectionMixin, TemplateView):
    """Imkoniyatlar — AzureAI ohangi, modeli va web qidiruv rejimi."""

    template_name = 'users/settings/capabilities.html'
    settings_section = 'capabilities'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tone_choices'] = CustomUser.AI_TONE_CHOICES
        context['model_choices'] = CustomUser.effective_ai_model_choices()
        context['web_search_choices'] = CustomUser.effective_ai_web_search_effort_choices()
        context['ai_free_tier_mode'] = bool(getattr(settings, 'AI_FREE_TIER_MODE', False))
        return context

class AvatarUpdateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        if 'avatar' in request.FILES:
            avatar_file = request.FILES['avatar']
            # Baytlar bo'yicha tekshiruv: `user.save()` yo'lida model field
            # validatorlari ishga tushmaydi (A0b).
            try:
                validate_upload(avatar_file, profile='image', field_label='Profil rasmi')
            except ValidationError as exc:
                messages.error(request, exc.messages[0])
                return redirect(_safe_next(request, 'settings_account'))
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
        # Profil sahifasidan yuklansa o'sha yerga qaytadi.
        return redirect(_safe_next(request, 'settings_account'))

class AIToneUpdateView(LoginRequiredMixin, View):
    """Update only the AI tone preference for the AzureAI assistant."""

    def post(self, request, *args, **kwargs):
        tone = (request.POST.get('ai_tone') or '').strip()
        valid_tones = {choice for choice, _ in CustomUser.AI_TONE_CHOICES}
        wants_json = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        )

        if tone not in valid_tones:
            if wants_json:
                return JsonResponse({"status": "error", "message": "Noto'g'ri uslub tanlandi."}, status=400)
            messages.error(request, "Noto'g'ri uslub tanlandi.")
            return redirect('settings_capabilities')

        if request.user.ai_tone != tone:
            request.user.ai_tone = tone
            request.user.save(update_fields=['ai_tone'])
            messages.success(request, "AzureAI uslubi yangilandi.")
        if wants_json:
            label = dict(CustomUser.AI_TONE_CHOICES).get(tone, tone)
            return JsonResponse({"status": "success", "ai_tone": tone, "label": label})
        return redirect('settings_capabilities')


class AIModelUpdateView(LoginRequiredMixin, View):
    """Update only the Gemini model preference for the AzureAI assistant."""

    def post(self, request, *args, **kwargs):
        model = (request.POST.get('ai_model') or '').strip()
        model_choices = CustomUser.effective_ai_model_choices()
        valid_models = {choice for choice, _ in model_choices}
        wants_json = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        )

        if model not in valid_models:
            if wants_json:
                return JsonResponse({"status": "error", "message": "Noto'g'ri model tanlandi."}, status=400)
            return HttpResponseBadRequest("Noto'g'ri model tanlandi.")

        if request.user.ai_model != model:
            request.user.ai_model = model
            request.user.save(update_fields=['ai_model'])
            messages.success(request, "AzureAI modeli yangilandi.")
        if wants_json:
            label = dict(model_choices).get(model, model)
            return JsonResponse({"status": "success", "ai_model": model, "label": label})
        return redirect('settings_capabilities')


class AISkillUpdateView(LoginRequiredMixin, View):
    """Update only the AzureAI skill preference."""

    def post(self, request, *args, **kwargs):
        skill = (request.POST.get('ai_skill') or '').strip()
        skill_choices = CustomUser.effective_ai_skill_choices()
        valid_skills = {choice for choice, _ in skill_choices}
        wants_json = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        )

        if skill not in valid_skills:
            if wants_json:
                return JsonResponse({"status": "error", "message": "Noto'g'ri skill tanlandi."}, status=400)
            return HttpResponseBadRequest("Noto'g'ri skill tanlandi.")

        if request.user.ai_skill != skill:
            request.user.ai_skill = skill
            request.user.save(update_fields=['ai_skill'])
            messages.success(request, "AzureAI skilli yangilandi.")
        if wants_json:
            label = dict(skill_choices).get(skill, skill)
            return JsonResponse({"status": "success", "ai_skill": skill, "label": label})
        return redirect('settings_capabilities')


class AIWebSearchEffortUpdateView(LoginRequiredMixin, View):
    """Update only the AzureAI web-search effort preference."""

    def post(self, request, *args, **kwargs):
        effort = (request.POST.get('ai_web_search_effort') or '').strip()
        effort_choices = CustomUser.effective_ai_web_search_effort_choices()
        valid_efforts = {choice for choice, _ in effort_choices}
        wants_json = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        )

        if effort not in valid_efforts:
            if wants_json:
                return JsonResponse({"status": "error", "message": "Noto'g'ri qidiruv rejimi tanlandi."}, status=400)
            return HttpResponseBadRequest("Noto'g'ri qidiruv rejimi tanlandi.")

        if request.user.ai_web_search_effort != effort:
            request.user.ai_web_search_effort = effort
            request.user.save(update_fields=['ai_web_search_effort'])
            messages.success(request, "AzureAI web qidiruv rejimi yangilandi.")
        if wants_json:
            label = dict(effort_choices).get(effort, effort)
            return JsonResponse({"status": "success", "ai_web_search_effort": effort, "label": label})
        return redirect('settings_capabilities')


class AIMemoryToggleView(LoginRequiredMixin, View):
    """Toggle the user's AI long-term memory on/off."""

    def post(self, request, *args, **kwargs):
        raw = (request.POST.get('ai_memory_enabled') or '').strip().lower()
        enabled = raw in {'1', 'true', 'on', 'yes'}
        wants_json = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        )

        if request.user.ai_memory_enabled != enabled:
            request.user.ai_memory_enabled = enabled
            request.user.save(update_fields=['ai_memory_enabled'])
            label = "yoqildi" if enabled else "o'chirildi"
            messages.success(request, f"AzureAI xotirasi {label}.")
        if wants_json:
            return JsonResponse({"status": "success", "ai_memory_enabled": enabled})
        return redirect('settings_privacy')


class AIMemoryListView(SettingsSectionMixin, TemplateView):
    """Maxfiylik — AzureAI xotirasi.

    Avval alohida `/users/settings/ai-memory/` sahifasi edi; endi sozlamalar
    shell'ining Maxfiylik bo'limi. Eski URL shu yerga redirect qiladi.
    """

    template_name = 'users/settings/privacy.html'
    settings_section = 'privacy'

    def get_context_data(self, **kwargs):
        from messenger.models import AIMemoryFact, AIMemoryTrace, AILongTermMemory
        from ai.memory.repository import MemoryRepository

        context = super().get_context_data(**kwargs)
        user = self.request.user

        maintenance_report = MemoryRepository().maintain_user_memory(user=user)

        facts = list(
            AIMemoryFact.objects.filter(user=user, status=AIMemoryFact.STATUS_ACTIVE)
            .annotate(
                trace_count=Count("trace_events"),
                retrieval_count=Count(
                    "trace_events",
                    filter=Q(trace_events__event_type=AIMemoryTrace.EVENT_RETRIEVED),
                ),
            )
            .order_by('-updated_at')
        )
        fact_ids = [fact.id for fact in facts]
        latest_traces = {}
        trace_map: dict[int, list] = {}
        if fact_ids:
            traces = (
                AIMemoryTrace.objects.filter(user=user, fact_id__in=fact_ids)
                .order_by('fact_id', '-created_at')
            )
            for trace in traces:
                latest_traces.setdefault(trace.fact_id, trace)
                trace_map.setdefault(trace.fact_id, [])
                if len(trace_map[trace.fact_id]) < 3:
                    trace_map[trace.fact_id].append(trace)
        for fact in facts:
            fact.latest_trace = latest_traces.get(fact.id)
            fact.trace_items = trace_map.get(fact.id, [])
            fact.confidence_percent = round(max(0.0, min(float(fact.confidence or 0.0), 1.0)) * 100)
            fact.age_days = max(0, (timezone.now() - fact.created_at).days)
            fact.last_used_label = fact.last_used_at.strftime("%d-%b, %H:%M") if fact.last_used_at else "Hali ishlatilmagan"

        grouped: dict[str, list] = {}
        for fact in facts:
            grouped.setdefault(fact.category, []).append(fact)

        category_order = [
            AIMemoryFact.CATEGORY_PROFILE,
            AIMemoryFact.CATEGORY_LEARNING_GOAL,
            AIMemoryFact.CATEGORY_PREFERENCE,
            AIMemoryFact.CATEGORY_WEAK_TOPIC,
            AIMemoryFact.CATEGORY_SCHEDULE,
            AIMemoryFact.CATEGORY_OTHER,
        ]
        category_labels = dict(AIMemoryFact.CATEGORY_CHOICES)
        category_icons = {
            AIMemoryFact.CATEGORY_PROFILE: 'person-badge',
            AIMemoryFact.CATEGORY_LEARNING_GOAL: 'flag',
            AIMemoryFact.CATEGORY_PREFERENCE: 'sliders',
            AIMemoryFact.CATEGORY_WEAK_TOPIC: 'exclamation-triangle',
            AIMemoryFact.CATEGORY_SCHEDULE: 'calendar2-week',
            AIMemoryFact.CATEGORY_OTHER: 'bookmark',
        }

        context['memory_groups'] = [
            {
                'category': cat,
                'label': category_labels.get(cat, cat),
                'icon': category_icons.get(cat, 'bookmark'),
                'facts': grouped.get(cat, []),
            }
            for cat in category_order
            if grouped.get(cat)
        ]
        context['memory_total'] = len(facts)
        context['ai_memory_enabled'] = user.ai_memory_enabled
        status_counts = {
            row["status"]: row["total"]
            for row in AIMemoryFact.objects.filter(user=user).values("status").annotate(total=Count("id"))
        }
        trace_counts = {
            row["event_type"]: row["total"]
            for row in AIMemoryTrace.objects.filter(user=user).values("event_type").annotate(total=Count("id"))
        }
        context['memory_report'] = {
            "active": status_counts.get(AIMemoryFact.STATUS_ACTIVE, 0),
            "archived": status_counts.get(AIMemoryFact.STATUS_ARCHIVED, 0),
            "rejected": status_counts.get(AIMemoryFact.STATUS_REJECTED, 0),
            "saved": trace_counts.get(AIMemoryTrace.EVENT_SAVED, 0),
            "retrieved": trace_counts.get(AIMemoryTrace.EVENT_RETRIEVED, 0),
            "unused": sum(1 for fact in facts if not fact.last_used_at),
            "decayed": maintenance_report["decayed"],
            "auto_archived": maintenance_report["archived"],
        }
        context['recent_memory_traces'] = list(
            AIMemoryTrace.objects.filter(user=user)
            .select_related("fact")
            .order_by("-created_at")[:12]
        )
        legacy = AILongTermMemory.objects.filter(user=user).first()
        context['legacy_memory_text'] = (legacy.learned_facts or '').strip() if legacy else ''
        return context


class AIMemoryArchiveView(LoginRequiredMixin, View):
    """Soft-delete (archive) a single fact owned by the current user."""

    def post(self, request, fact_id, *args, **kwargs):
        from ai.memory.repository import MemoryRepository

        wants_json = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        )
        archived = MemoryRepository().archive_one(user=request.user, fact_id=fact_id)
        if archived:
            messages.success(request, "Xotira yozuvi o'chirildi.")
        else:
            messages.info(request, "Yozuv topilmadi yoki allaqachon arxivlangan.")
        if wants_json:
            return JsonResponse({"status": "success" if archived else "noop"})
        return redirect('settings_privacy')


class AIMemoryRejectView(LoginRequiredMixin, View):
    """Mark a memory fact as incorrect so it is no longer used by AI."""

    def post(self, request, fact_id, *args, **kwargs):
        from ai.memory.repository import MemoryRepository

        wants_json = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        )
        rejected = MemoryRepository().reject_one(user=request.user, fact_id=fact_id)
        if rejected:
            messages.success(request, "Xotira yozuvi noto'g'ri deb belgilandi.")
        else:
            messages.info(request, "Yozuv topilmadi yoki allaqachon faol emas.")
        if wants_json:
            return JsonResponse({"status": "success" if rejected else "noop"})
        return redirect('settings_privacy')


class AIMemoryClearAllView(LoginRequiredMixin, View):
    """Archive every active fact for the current user and clear legacy memory."""

    def post(self, request, *args, **kwargs):
        from ai.memory.repository import MemoryRepository

        wants_json = (
            request.headers.get("x-requested-with") == "XMLHttpRequest"
            or "application/json" in request.headers.get("accept", "")
        )
        archived_count = MemoryRepository().archive_all_for_user(user=request.user, clear_legacy=True)
        messages.success(request, "AzureAI xotirasi to'liq tozalandi.")
        if wants_json:
            return JsonResponse({"status": "success", "archived": archived_count})
        return redirect('settings_privacy')


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
            return redirect('settings_account')
        if new_pass1 != new_pass2:
            messages.error(request, "Yangi parollar mos kelmadi.")
            return redirect('settings_account')

        try:
            validate_password(new_pass1, user)
        except ValidationError as e:
            messages.error(request, f"Parol juda oddiy: {' '.join(e.messages)}")
            return redirect('settings_account')

        user.set_password(new_pass1)
        # Faqat parol yoziladi. `user.save()` argumentsiz butun qatorni
        # yozardi, ya'ni parol o'zgartirilayotgan lahzada boshqa yo'l bergan
        # XP (`users/xp.py::award_xp`) eskirgan nusxa bilan bosib ketilishi
        # mumkin edi.
        user.save(update_fields=["password"])
        update_session_auth_hash(request, user)
        messages.success(request, "Parol muvaffaqiyatli o'zgartirildi.")
        return redirect('settings_account')

    def form_valid(self, form):
        messages.success(self.request, "Profil ma'lumotlari yordamida muvaffaqiyatli yangilandi.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Xatolik yuz berdi. Iltimos, barcha maydonlarni tekshiring.")
        return super().form_invalid(form)


def build_student_enrollments(user, today=None):
    """O'quvchining enrollmentlarini progress/status metadata bilan tuzadi.

    Dashboard va "Mening kurslarim" sahifalari ulashadi. Har enrollment'ga
    `dashboard_*` atributlari qo'shiladi (progress %, status tone, days left).
    Ro'yxat status (active → pending → frozen → expired) va so'nggi qo'shilish
    bo'yicha saralanadi.
    """
    today = today or timezone.localdate()

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
            status_priority.get(item.get_effective_status(today=today), 9),
            -item.joined_at.timestamp(),
        )
    )

    for enrollment in enrollments:
        effective_status = enrollment.get_effective_status(today=today)
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
        enrollment.dashboard_effective_status = effective_status
        enrollment.dashboard_status_label = enrollment.get_effective_status_display(today=today)
        enrollment.dashboard_status_tone = {
            'active': 'success',
            'pending': 'warning',
            'expired': 'danger',
            'frozen': 'secondary',
        }.get(effective_status, 'secondary')
        enrollment.dashboard_days_left = None
        if enrollment.next_payment_deadline:
            enrollment.dashboard_days_left = (
                enrollment.next_payment_deadline - today
            ).days

    return enrollments


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'users/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['active_nav'] = 'dashboard'
        today = timezone.localdate()

        enrollments = build_student_enrollments(user, today)
        context['active_enrollments'] = enrollments
        active_enrollment_qs = user.enrollments.filter(enrollment_active_access_q())
        context['active_courses_count'] = active_enrollment_qs.count()

        # Dashboard metriclar: o'tilgan darslar soni attendance va LMS lesson progress asosida hisoblanadi.
        attendance_lessons_count = Attendance.objects.filter(
            enrollment__student=user,
            status__in=[Attendance.STATUS_PRESENT, Attendance.STATUS_PARTIAL],
        ).values('lesson_id').distinct().count()
        progress_lessons_count = user.enrollments.filter(enrollment_active_access_q()).aggregate(
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
        from aicontrol.service import build_usage_panel
        context['ai_usage'] = build_usage_panel(user)
        context['study_hours'] = context['total_hours']
        context['xp_points'] = user.total_xp if hasattr(user, 'total_xp') else 0
        from users.streak import streak_snapshot
        streak = streak_snapshot(user)
        context['streak'] = streak
        context['streak_days'] = streak['current']

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
            (item for item in enrollments if item.dashboard_effective_status == Enrollment.STATUS_ACTIVE),
            enrollments[0] if enrollments else None,
        )
        active_dashboard_enrollments = [
            item for item in enrollments if item.dashboard_effective_status == Enrollment.STATUS_ACTIVE
        ]
        context['active_dashboard_enrollments'] = active_dashboard_enrollments
        context['current_plan'] = (
            context['primary_enrollment'].active_plan()
            if context['primary_enrollment'] and context['primary_enrollment'].plan_id
            else next((item.active_plan() for item in enrollments if item.plan_id), None)
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
                    filter=enrollment_active_access_q(prefix='cohorts__members__'),
                    distinct=True,
                ),
            )
            .order_by('-annotated_students_count', '-created_at')[:3]
        )

        return context


class MyCoursesView(LoginRequiredMixin, TemplateView):
    """App-shell ichidagi "Mening kurslarim" — o'quvchi yozilgan kurslar.

    Public `/courses/` katalogidan farqli: bu app-shell oqimida qoladi va
    faqat foydalanuvchi enrollmentlarini progress bilan ko'rsatadi.
    """
    template_name = 'users/my_courses.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['active_nav'] = 'my_courses'

        enrollments = build_student_enrollments(user)
        context['enrollments'] = enrollments
        context['count_all'] = len(enrollments)
        context['count_active'] = sum(
            1 for e in enrollments if e.dashboard_effective_status == Enrollment.STATUS_ACTIVE
        )
        context['count_completed'] = sum(1 for e in enrollments if e.dashboard_progress >= 100)
        return context


def _build_telegram_link_context(user):
    """Telegram-bot ulash uchun deep-link va holat ma'lumotlari."""
    if user.telegram_id:
        return {
            'telegram_linked': True,
            'telegram_username': user.telegram_username,
        }

    # Qisqa, muddatli va bir martalik token. Imzolangan `user.id` ning
    # base64'i ikki sababdan yaroqsiz edi: muddati yo'q edi (havola sizib
    # chiqsa abadiy ishlardi) va `user.id >= 10000` da Telegram'ning 64
    # belgilik `start` chegarasidan oshib ketardi.
    from users.models import TelegramLinkToken

    token = TelegramLinkToken.issue(user).token

    bot_username = (getattr(settings, 'BOT_USERNAME', '') or 'lmsazurebot').strip('@')
    return {
        'telegram_linked': False,
        'telegram_bot_link': f"https://t.me/{bot_username}?start={token}",
    }


def get_cohort_leaderboard_context(user, cohort_id=None):
    context = {
        'leaderboard_cohort': None,
        'leaderboard_cohort_choices': [],
        'selected_leaderboard_cohort_id': None,
        'leaderboard_top': [],
        'leaderboard_my_row': None,
    }

    active_enrollments = list(
        user.enrollments.filter(enrollment_active_access_q())
        .select_related('cohort')
        .order_by('-joined_at', '-id')
    )
    context['leaderboard_cohort_choices'] = active_enrollments
    current_active_enrollment = next(
        (item for item in active_enrollments if item.cohort_id == cohort_id),
        active_enrollments[0] if active_enrollments else None,
    )
    context['selected_leaderboard_cohort_id'] = (
        current_active_enrollment.cohort_id if current_active_enrollment else None
    )
    context['leaderboard_cohort'] = current_active_enrollment.cohort if current_active_enrollment else None

    if not current_active_enrollment:
        return context

    leaderboard_qs = list(
        Enrollment.objects.filter(
            enrollment_active_access_q(),
            cohort=current_active_enrollment.cohort,
        )
        .select_related('student', 'student__streak')
        .prefetch_related(
            Prefetch(
                'lesson_progress',
                queryset=LessonProgress.objects.filter(is_completed=True).select_related('lesson'),
            ),
            Prefetch(
                'attendance_set',
                queryset=Attendance.objects.select_related('lesson'),
            ),
        )
    )

    def cohort_score(enrollment):
        lesson_scores = {}

        for progress in enrollment.lesson_progress.all():
            if not progress.is_completed:
                continue
            lesson_scores[progress.lesson_id] = max(
                lesson_scores.get(progress.lesson_id, 0),
                progress.lesson.xp_reward,
            )

        for attendance in enrollment.attendance_set.all():
            lesson_scores[attendance.lesson_id] = max(
                lesson_scores.get(attendance.lesson_id, 0),
                attendance.xp_awarded,
            )

        return sum(lesson_scores.values())

    leaderboard_rows = []
    for enrollment in leaderboard_qs:
        leaderboard_rows.append(
            {
                'student': enrollment.student,
                'cohort_score': cohort_score(enrollment),
                'is_me': enrollment.student_id == user.id,
                'joined_at': enrollment.joined_at,
                'student_id': enrollment.student_id,
            }
        )

    leaderboard_rows.sort(
        key=lambda row: (
            -row['cohort_score'],
            row['joined_at'],
            row['student_id'],
        )
    )

    for rank, row in enumerate(leaderboard_rows, start=1):
        row = {
            'rank': rank,
            'student': row['student'],
            'cohort_score': row['cohort_score'],
            'is_me': row['is_me'],
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
        try:
            selected_cohort_id = int(self.request.GET.get('cohort', '') or 0)
        except (TypeError, ValueError):
            selected_cohort_id = None
        context.update(get_cohort_leaderboard_context(self.request.user, selected_cohort_id))
        return context


class NotificationCenterView(LoginRequiredMixin, TemplateView):
    template_name = "users/notifications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
            page, _ = LegalPage.objects.get_or_create(page_type=page_type, defaults=defaults)
            context[f"page_{page_type}"] = page
        return context


class UserProfileView(LoginRequiredMixin, UpdateView):
    """Profil — ko'rish sahifasi, ism/telefon/bio esa joyida tahrirlanadi.

    Tahrirlash boshqa sahifaga olib o'tmaydi: forma shu sahifada ochiladi.
    Sozlamalar > Hisob bilan bitta `ProfileFieldsForm` ishlatiladi, shuning
    uchun ikki yuzada ikki xil validatsiya bo'lmaydi.
    """

    model = CustomUser
    template_name = 'users/profile.html'
    form_class = ProfileFieldsForm
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profil ma'lumotlari saqlandi.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Ma'lumotlarda xatolik bor. Iltimos tekshiring.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        current_plan_enrollment = (
            user.enrollments.filter(enrollment_active_access_q(), plan__isnull=False)
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
        context['current_plan'] = current_plan_enrollment.active_plan() if current_plan_enrollment else None

        passed_lessons_count = Attendance.objects.filter(
            enrollment__student=user,
            status__in=[Attendance.STATUS_PRESENT, Attendance.STATUS_PARTIAL],
        ).count()
        context['total_hours'] = passed_lessons_count * 2
        context.update(_build_telegram_link_context(user))
        return context


class AttendanceCalendarView(LoginRequiredMixin, TemplateView):
    template_name = 'users/attendance_calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['active_nav'] = 'attendance_calendar'
        context['weekday_labels'] = ['Du', 'Se', 'Cho', 'Pa', 'Ju', 'Sha', 'Ya']

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

        active_enrollments = list(
            user.enrollments.filter(enrollment_active_access_q())
            .select_related('cohort', 'cohort__course', 'plan')
            .order_by('-joined_at', '-id')
        )
        try:
            selected_cohort_id = int(self.request.GET.get('cohort', '') or 0)
        except (TypeError, ValueError):
            selected_cohort_id = 0

        selected_enrollment = next(
            (item for item in active_enrollments if item.cohort_id == selected_cohort_id),
            active_enrollments[0] if active_enrollments else None,
        )
        if selected_enrollment:
            selected_cohort_id = selected_enrollment.cohort_id

        context['selected_month'] = selected_month
        context['prev_month'] = prev_month
        context['next_month'] = next_month
        context['attendance_cohort_choices'] = active_enrollments
        context['selected_attendance_cohort_id'] = selected_cohort_id or None
        context['attendance_cohort'] = selected_enrollment.cohort if selected_enrollment else None
        raw_weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
        context['calendar_weeks'] = [[{'day': day, 'status': None} for day in week] for week in raw_weeks]
        context['attendance_day_status'] = {}
        context['attendance_summary'] = {'present': 0, 'partial': 0, 'absent': 0}

        if not selected_enrollment:
            return context

        records = Attendance.objects.filter(
            enrollment=selected_enrollment,
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
        # Scope canonical: `core.access.teacher_cohort_queryset()` — teacher
        # paneli va Telegram adapteri ham aynan shuni iste'mol qiladi (A0b).
        from core.access import teacher_cohort_queryset

        return (
            teacher_cohort_queryset(self.request.user)
            .filter(is_active=True)
            .select_related('course')
            .order_by('name')
        )

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
            members = Enrollment.objects.filter(
                enrollment_active_access_q(),
                cohort=selected_cohort,
            ).select_related('student').order_by(
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollments = list(context["enrollments"])
        context["active_nav"] = "subscriptions"
        context["active_subscription"] = next(
            (enrollment for enrollment in enrollments if enrollment.has_active_access()),
            enrollments[0] if enrollments else None,
        )
        context["payment_receipts"] = (
            PaymentReceipt.objects.filter(enrollment__student=self.request.user)
            .select_related("enrollment", "enrollment__cohort", "enrollment__cohort__course", "enrollment__plan")
            .order_by("-submitted_at", "-id")
        )
        return context

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


from django.http import JsonResponse
import secrets
from django.contrib.auth import login as django_login
from django.db import transaction
from django.utils.crypto import constant_time_compare
from users.models import TelegramAuthSession

TELEGRAM_AUTH_CLIENT_KEY = 'telegram_auth_client_key'


def telegram_auth_init(request):
    """Vaqtinchalik token va Telegram deep-linkini yaratadi (AJAX).

    Token shu brauzer sessiyasiga bog'lanadi — keyin faqat shu brauzer uni
    login uchun ishlata oladi. Bitta brauzerda bir vaqtda bitta oqim.
    """
    token = secrets.token_urlsafe(32)
    client_key = secrets.token_urlsafe(32)
    TelegramAuthSession.objects.create(token=token, client_key=client_key)
    request.session[TELEGRAM_AUTH_CLIENT_KEY] = client_key
    bot_username = (getattr(settings, 'BOT_USERNAME', '') or 'azureLMSbot').strip('@')
    bot_link = f"https://t.me/{bot_username}?start=auth_{token}"
    return JsonResponse({
        'ok': True,
        'token': token,
        'bot_link': bot_link
    })


def telegram_auth_status(request, token):
    """Token holatini tekshiradi va tasdiqlangan bo'lsa login qiladi (polling AJAX).

    Token bir martalik: olingandan keyin `used` bo'ladi. Boshqa brauzer
    tokenni bilsa ham login bo'lolmaydi — `client_key` mos kelmaydi.
    Mavjud emas va mos kelmagan holatlar bir xil javob beradi, aks holda
    token mavjudligini aniqlash mumkin bo'lardi.
    """
    unknown = JsonResponse({'ok': False, 'status': 'not_found', 'message': 'Sessiya topilmadi.'})
    client_key = request.session.get(TELEGRAM_AUTH_CLIENT_KEY) or ''
    if not client_key:
        return unknown

    with transaction.atomic():
        try:
            session = TelegramAuthSession.objects.select_for_update().get(token=token)
        except TelegramAuthSession.DoesNotExist:
            return unknown

        if not session.client_key or not constant_time_compare(session.client_key, client_key):
            return unknown

        # Muddati o'tgan sessiya (pending yoki authenticated) yopiladi —
        # aks holda frontend'ga 'authenticated' deb yolg'on javob ketardi.
        if session.status in (
            TelegramAuthSession.STATUS_PENDING,
            TelegramAuthSession.STATUS_AUTHENTICATED,
        ) and session.is_expired():
            session.status = TelegramAuthSession.STATUS_EXPIRED
            session.save(update_fields=['status'])

        if not session.is_claimable():
            return JsonResponse({'ok': True, 'status': session.status})

        # Bir martalik: tokenni login qilishdan OLDIN yopamiz, shunda
        # parallel so'rov ikkinchi marta ololmaydi.
        authenticated_user = session.user
        session.status = TelegramAuthSession.STATUS_USED
        session.consumed_at = timezone.now()
        session.save(update_fields=['status', 'consumed_at'])

    django_login(request, authenticated_user, backend='django.contrib.auth.backends.ModelBackend')
    request.session.pop(TELEGRAM_AUTH_CLIENT_KEY, None)
    return JsonResponse({
        'ok': True,
        'status': 'authenticated',
        'redirect_url': '/users/dashboard/'
    })

