"""Frozen auth presentation; Django retains form/token/session semantics."""
import logging

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect

from core.email_delivery import RESET_UNAVAILABLE_MESSAGE, reset_delivery_available
from core.frontend_v1 import FrontendV1Mixin
from .forms import UzbekPasswordResetForm, UzbekSetPasswordForm

logger = logging.getLogger(__name__)


class AfterResponseRedirect(HttpResponseRedirect):
    """Yo'naltirish; `after` javob mijozga to'liq yuborilgandan keyin ishlaydi.

    ASGI va WSGI server javob tanasini yuborib bo'lgach `close()`ni chaqiradi —
    ish shu yerda bajariladi, ya'ni uning davomiyligi javob vaqtiga qo'shilmaydi.
    Xato javobni buzmaydi (u allaqachon ketgan), faqat logga yoziladi.
    """

    def __init__(self, url, after):
        super().__init__(url)
        self._after = after

    def close(self):
        after, self._after = self._after, None
        if after is not None:
            try:
                after()
            except Exception:  # noqa: BLE001 — javob allaqachon yuborilgan
                logger.exception("Javobdan keyingi ish bajarilmadi")
        super().close()


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
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
            'html_email_template_name': self.html_email_template_name,
            'extra_email_context': self.extra_email_context,
        }
        # Hisobni qidirish, xatni chizish va yuborish — javob mijozga yetgandan
        # keyin (PUB1.4c). Aks holda mavjud email uchun javob SMTP vaqtiga
        # cho'zilib, qaysi email ro'yxatdan o'tgani javob vaqtidan bilinardi.
        return AfterResponseRedirect(self.get_success_url(), lambda: form.save(**opts))


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
        # `same-origin` — `no-referrer` yangi parol formasini `Origin: null` bilan
        # yuborib, CSRF tekshiruvida 403 qilardi.
        response = super().dispatch(*args, **kwargs)
        response['Referrer-Policy'] = 'same-origin'
        return response

    def form_valid(self, form):
        response = super().form_valid(form)
        # Presentation-only, one-use success notice; never a reset credential.
        self.request.session['frontend_v1_reset_completed'] = True
        # Begona odam xato parollar bilan hisobni yopib qo'ygan bo'lsa ham, emailga
        # ega egasi yangi parol bilan darhol kira oladi (PUB1.4c).
        from users import auth_abuse

        auth_abuse.record_password_recovered(form.user)
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
