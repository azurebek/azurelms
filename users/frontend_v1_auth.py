"""Frozen auth presentation; Django retains form/token/session semantics."""
import logging

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect
from django.utils.functional import cached_property

from core.email_delivery import RESET_UNAVAILABLE_MESSAGE, reset_delivery_available
from core.flags import flags_enabled
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
    auth_aside_title = ''
    auth_aside_items = ()
    auth_aside_note = ''
    auth_aside_ordered = False

    @cached_property
    def auth_renderer_flags(self):
        """Auth V1 va editorial ramka ayni DB snapshot'idan tanlansin."""
        return flags_enabled('frontend_v1_auth', 'frontend_v1_public', 'public_editorial_v1')

    @cached_property
    def frontend_v1_enabled(self):
        return self.auth_renderer_flags['frontend_v1_auth']

    @cached_property
    def auth_editorial_enabled(self):
        flags = self.auth_renderer_flags
        return (
            flags['frontend_v1_auth']
            and flags['frontend_v1_public']
            and flags['public_editorial_v1']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.frontend_v1_enabled:
            context['auth_intro'] = self.auth_intro
        if self.auth_editorial_enabled:
            context.update(
                auth_base_template='frontend_v1/editorial/auth_base.html',
                auth_aside_title=self.auth_aside_title,
                auth_aside_items=self.auth_aside_items,
                auth_aside_note=self.auth_aside_note,
                auth_aside_ordered=self.auth_aside_ordered,
            )
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
    auth_aside_title = 'Tiklash qanday ishlaydi'
    auth_aside_items = (
        'Email faol hisobga tegishli bo‘lsa, unga havola keladi',
        'Havolani ochib, yangi parolni ikki marta kiritasiz',
        'Yangi parol bilan darhol kirasiz',
    )
    auth_aside_note = (
        'Telegram orqali kirgan bo‘lsangiz, parol shart emas — kirish sahifasida '
        'Telegram tugmasini bosing.'
    )
    auth_aside_ordered = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        available = reset_delivery_available()
        context['reset_delivery_available'] = available
        if not available:
            context['reset_unavailable_message'] = RESET_UNAVAILABLE_MESSAGE
            if self.frontend_v1_enabled:
                context['auth_intro'] = ''
            if self.auth_editorial_enabled:
                # Email ishlamayotganda odatiy "havola keladi" paneli yolg'on
                # bo'lardi; faqat hozir mavjud xavfsiz yo'llarni ko'rsatamiz.
                context.update(
                    auth_aside_title='Hozirgi variantlar',
                    auth_aside_items=(
                        'Telegrami ulangan hisob bilan Telegram orqali kiring',
                        'Yordam uchun administrator bilan bog‘laning',
                        'Parolingizni hech kimga yubormang',
                    ),
                    auth_aside_note='',
                    auth_aside_ordered=False,
                )
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
    auth_aside_title = 'Xat kelmasa'
    auth_aside_items = (
        'Email to‘g‘ri yozilganini tekshiring',
        'Spam va “Aksiyalar” papkasiga qarang',
        'Bir necha daqiqadan keyin qayta so‘rang',
    )


class PasswordResetConfirmView(AuthV1Mixin, auth_views.PasswordResetConfirmView):
    form_class = UzbekSetPasswordForm
    frontend_v1_template = 'frontend_v1/auth_reset_confirm.html'
    frontend_v1_title = 'Yangi parol'
    auth_intro = 'Yangi parolingizni ikki marta kiriting.'
    auth_aside_title = 'Yangi parol'
    auth_aside_items = (
        'Boshqa hisoblarda ishlatmaydigan parol tanlang',
        'Yangi parolni ikki marta bir xil kiriting',
        'Saqlagach, yangi parol bilan hisobga kiring',
    )

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
            if self.auth_editorial_enabled:
                context.update(
                    auth_aside_title='Yangi havola kerak',
                    auth_aside_items=(
                        'Tiklashni email manzilingiz bilan qayta boshlang',
                        'Faqat eng so‘nggi kelgan havolani oching',
                        'Havolani boshqa odamga yubormang',
                    ),
                )
        return context


class PasswordResetCompleteView(AuthV1Mixin, auth_views.PasswordResetCompleteView):
    frontend_v1_template = 'frontend_v1/auth_reset_complete.html'
    frontend_v1_title = 'Hisobga kirish'
    auth_aside_title = 'Keyingi qadam'
    auth_aside_items = (
        'Hisobga kirish sahifasiga o‘ting',
        'Yangi parolingizni kiriting',
        'Kurslaringizga qayting',
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        completed = self.request.session.pop('frontend_v1_reset_completed', False)
        if self.frontend_v1_enabled:
            context['auth_reset_completed'] = completed
            if completed:
                context['frontend_v1_title'] = 'Parol yangilandi'
        return context
