from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, TemplateView
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import update_session_auth_hash
from .forms import CustomUserCreationForm
from .models import CustomUser
from django.shortcuts import redirect, render

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
        
    def post(self, request, *args, **kwargs):
        # 1. Avatar Update
        if 'update_avatar' in request.POST:
            user = self.get_object()
            if 'avatar' in request.FILES:
                user.avatar = request.FILES['avatar']
                user.save()
                messages.success(request, "Profil rasmi muvaffaqiyatli yangilandi.")
            else:
                messages.error(request, "Rasm tanlanmadi.")
            return redirect(self.success_url)
            
        # 2. Password Change
        if 'change_password' in request.POST:
            user = self.get_object()
            old_pass = request.POST.get('old_password')
            new_pass1 = request.POST.get('new_password1')
            new_pass2 = request.POST.get('new_password2')
            
            if not user.check_password(old_pass):
                messages.error(request, "Joriy parol noto'g'ri.")
                return redirect(self.success_url)
            if new_pass1 != new_pass2:
                messages.error(request, "Yangi parollar mos kelmadi.")
                return redirect(self.success_url)
                
            user.set_password(new_pass1)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Parol muvaffaqiyatli o'zgartirildi.")
            return redirect(self.success_url)

        # 3. Default Profile Information Update
        return super().post(request, *args, **kwargs)

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
        # Hozircha statik ma'lumotlar bilan ta'minlaymiz, keyin bazadan olinadigan qilinishi mumkin
        context['streak_days'] = 5
        context['completed_lessons'] = 12
        context['study_hours'] = 85
        context['xp_points'] = self.request.user.total_xp if hasattr(self.request.user, 'total_xp') else 1250
        context['achievements_count'] = 3
        return context
