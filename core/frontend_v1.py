"""Presentation-only V1 selection; domain context and access stay in the views."""

from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.utils.cache import patch_cache_control
from django.utils.functional import cached_property

from core.flags import flag_enabled


class FrontendV1Mixin:
    frontend_v1_template = None
    frontend_v1_title = ""

    @cached_property
    def frontend_v1_enabled(self):
        return flag_enabled("frontend_v1_learning")

    def get_template_names(self):
        if self.frontend_v1_enabled:
            return [self.frontend_v1_template]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.frontend_v1_enabled:
            context["frontend_v1_title"] = self.frontend_v1_title
            context["frontend_v1_nav"] = [
                {"url": reverse(name), "name": name, "label": label, "icon": icon}
                for name, label, icon in (
                    ("dashboard", "Bosh sahifa", "home"),
                    ("my_courses", "Kurslarim", "book"),
                )
            ]
            context["frontend_v1_legacy_nav"] = [
                {"url": reverse(name), "label": label, "icon": icon}
                for name, label, icon in (
                    ("classbook:live_home", "Jonli dars", "live"),
                    ("messenger:ai", "Xabarlar", "message"),
                    ("exam_center", "Imtihonlar", "exam"),
                    ("certificates", "Sertifikatlar", "award"),
                    ("leaderboard", "Reyting", "sprout"),
                    ("attendance_calendar", "Davomat", "calendar"),
                    ("subscriptions", "To‘lovlar", "book"),
                    ("blog:list", "Blog", "book"),
                    ("sit:home", "Turkiyada o‘qish", "users"),
                    ("help_center", "Yordam", "bulb"),
                )
            ]
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        if self.frontend_v1_enabled:
            patch_cache_control(response, private=True, no_store=True)
        return response


class FrontendLoginView(FrontendV1Mixin, LoginView):
    """Django still owns authentication, validation, CSRF and safe-next."""

    frontend_v1_template = "frontend_v1/login.html"
    frontend_v1_title = "Hisobga kirish"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if self.frontend_v1_enabled:
            form.error_messages = {
                **form.error_messages,
                "invalid_login": "Email yoki username va parol mos kelmadi. Qayta tekshiring.",
                "inactive": "Bu hisob faol emas. Yordam xizmatiga murojaat qiling.",
            }
            for field in form.fields.values():
                field.widget.attrs["class"] = "c-field"
                field.error_messages["required"] = "Bu maydonni to‘ldiring."
        return form
