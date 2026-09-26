"""Frozen auth presentation; Django retains form/token/session semantics."""
from django.contrib.auth import views as auth_views

from core.frontend_v1 import FrontendV1Mixin
from .forms import UzbekSetPasswordForm


class AuthV1Mixin(FrontendV1Mixin):
    frontend_v1_flag = 'frontend_v1_auth'
    auth_intro = ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.frontend_v1_enabled:
            context['auth_intro'] = self.auth_intro
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.frontend_v1_enabled:
            labels = {'first_name': 'Ism', 'last_name': 'Familiya (ixtiyoriy)',
                      'email': 'Email', 'password1': 'Parol', 'password2': 'Parolni tasdiqlang'}
            autocomplete = {'first_name': 'given-name', 'last_name': 'family-name', 'email': 'email'}
            for name, field in form.fields.items():
                field.label = labels.get(name, field.label)
                field.widget.attrs['class'] = 'c-field'
                field.error_messages['required'] = 'Bu maydonni to‘ldiring.'
                if name in autocomplete:
                    field.widget.attrs['autocomplete'] = autocomplete[name]
                if field.widget.input_type == 'password':
                    field.widget.attrs.update({'autocomplete': 'new-password', 'data-auth-password': ''})
                if name == 'email':
                    field.error_messages['invalid'] = 'To‘g‘ri email manzilini kiriting.'
                if name in ('password2', 'new_password2'):
                    field.help_text = 'Tekshirish uchun yuqoridagi parolni qayta kiriting.'
        return form


class PasswordResetView(AuthV1Mixin, auth_views.PasswordResetView):
    frontend_v1_template = 'frontend_v1/auth_reset.html'
    frontend_v1_title = 'Parolni tiklash'
    auth_intro = 'Hisobingiz emailini kiriting. Tiklash ko‘rsatmasi shu manzilga yuborilishi mumkin.'


class PasswordResetDoneView(AuthV1Mixin, auth_views.PasswordResetDoneView):
    frontend_v1_template = 'frontend_v1/auth_reset_done.html'
    frontend_v1_title = 'Emailingizni tekshiring'
    auth_intro = 'Agar email faol hisobga tegishli bo‘lsa, tiklash ko‘rsatmasi yuboriladi.'


class PasswordResetConfirmView(AuthV1Mixin, auth_views.PasswordResetConfirmView):
    form_class = UzbekSetPasswordForm
    frontend_v1_template = 'frontend_v1/auth_reset_confirm.html'
    frontend_v1_title = 'Yangi parol'
    auth_intro = 'Yangi parolingizni ikki marta kiriting.'

    def form_valid(self, form):
        response = super().form_valid(form)
        # Presentation-only, one-use success notice; never a reset credential.
        self.request.session['frontend_v1_reset_completed'] = True
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.frontend_v1_enabled and not self.validlink:
            context.update(frontend_v1_title='Havola yaroqsiz', auth_intro='Havola ishlatilgan, muddati tugagan yoki noto‘g‘ri.')
        return context


class PasswordResetCompleteView(AuthV1Mixin, auth_views.PasswordResetCompleteView):
    frontend_v1_template = 'frontend_v1/auth_reset_complete.html'
    frontend_v1_title = 'Hisobga kirish'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        completed = self.request.session.pop('frontend_v1_reset_completed', False)
        if self.frontend_v1_enabled:
            context['auth_reset_completed'] = completed
            if completed:
                context['frontend_v1_title'] = 'Parol yangilandi'
        return context
