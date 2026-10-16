"""Frozen auth presentation; Django retains form/token/session semantics."""
from django.conf import settings
from django.contrib.auth import views as auth_views

from core.email_delivery import RESET_UNAVAILABLE_MESSAGE, reset_delivery_available
from core.frontend_v1 import FrontendV1Mixin
from .forms import UzbekPasswordResetForm, UzbekSetPasswordForm


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
    form_class = UzbekPasswordResetForm
    # O'zbekcha mavzu, oddiy matn va HTML (PUB1.0f). Django default'i inglizcha edi.
    subject_template_name = 'registration/password_reset_subject.txt'
    email_template_name = 'registration/password_reset_email.txt'
    html_email_template_name = 'registration/password_reset_email.html'
    frontend_v1_template = 'frontend_v1/auth_reset.html'
    frontend_v1_title = 'Parolni tiklash'
    auth_intro = 'Hisobingiz emailini kiriting. Tiklash ko‘rsatmasi shu manzilga yuborilishi mumkin.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        available = reset_delivery_available()
        context['reset_delivery_available'] = available
        if not available:
            context['reset_unavailable_message'] = RESET_UNAVAILABLE_MESSAGE
            if self.frontend_v1_enabled:
                context['auth_intro'] = ''
        return context

    def form_valid(self, form):
        # Xat yetib bormaydigan muhitda "yubordik" deyilmaydi: so'rov ochiq rad
        # etiladi, javob har qanday email uchun bir xil (PUB1.0f).
        if not reset_delivery_available():
            form.add_error(None, RESET_UNAVAILABLE_MESSAGE)
            response = self.form_invalid(form)
            response.status_code = 503
            return response
        # Har so'rov email yuboradi: email va IP bo'yicha cheklanadi (PUB1.0c).
        # Hisoblagich email mavjudligidan qat'i nazar yuradi — blok holati
        # enumeration signali bo'lmaydi.
        from users import auth_abuse

        decision = auth_abuse.consume_password_reset(self.request, form.cleaned_data.get('email', ''))
        if not decision.allowed:
            form.add_error(None, decision.message)
            return auth_abuse.apply_throttle_headers(self.form_invalid(form), decision)
        from frontend.models import SiteSettings

        self.extra_email_context = {
            'brand_name': SiteSettings.current().brand_name or 'AzureLMS',
            'reset_valid_hours': max(1, settings.PASSWORD_RESET_TIMEOUT // 3600),
        }
        return super().form_valid(form)


class PasswordResetDoneView(AuthV1Mixin, auth_views.PasswordResetDoneView):
    frontend_v1_template = 'frontend_v1/auth_reset_done.html'
    frontend_v1_title = 'Emailingizni tekshiring'
    auth_intro = 'Agar email faol hisobga tegishli bo‘lsa, tiklash ko‘rsatmasi yuboriladi.'


class PasswordResetConfirmView(AuthV1Mixin, auth_views.PasswordResetConfirmView):
    form_class = UzbekSetPasswordForm
    frontend_v1_template = 'frontend_v1/auth_reset_confirm.html'
    frontend_v1_title = 'Yangi parol'
    auth_intro = 'Yangi parolingizni ikki marta kiriting.'

    def dispatch(self, *args, **kwargs):
        # Tokenli havoladan boshqa saytga Referer sifatida token ketmasin (PUB1.0f).
        response = super().dispatch(*args, **kwargs)
        response['Referrer-Policy'] = 'no-referrer'
        return response

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
