from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.contrib import messages
from .forms import CustomUserCreationForm

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

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import UpdateView, TemplateView
from .models import CustomUser

class ProfileView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    template_name = 'users/profile.html'
    fields = ['first_name', 'last_name', 'phone_number', 'bio', 'avatar']
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Profil muvaffaqiyatli yangilandi.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Xatolik yuz berdi. Iltimos, ma'lumotlarni tekshiring.")
        return super().form_invalid(form)

from django.views.generic import TemplateView

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
