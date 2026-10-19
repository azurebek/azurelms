"""Presentation-only V1 selection; domain context and access stay in the views."""

from django.contrib.auth.views import LoginView
from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import patch_cache_control
from django.utils.functional import cached_property

from core.flags import flag_enabled


class FrontendV1Mixin:
    frontend_v1_template = None
    frontend_v1_title = ""
    frontend_v1_flag = "frontend_v1_learning"

    @cached_property
    def frontend_v1_enabled(self):
        return flag_enabled(self.frontend_v1_flag)

    def get_template_names(self):
        if self.frontend_v1_enabled:
            return [self.frontend_v1_template]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.frontend_v1_enabled:
            context["frontend_v1_title"] = self.frontend_v1_title
            context["frontend_v1_records_ready"] = flag_enabled("frontend_v1_records")
            context["frontend_v1_checkout_ready"] = flag_enabled("frontend_v1_checkout")
            context["frontend_v1_exam_attempt_ready"] = flag_enabled("frontend_v1_exam_attempt")
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
            if flag_enabled("frontend_v1_messenger"):
                context["frontend_v1_nav"].append(dict(url=reverse("messenger:group"), name="messenger:group", label="Xabarlar", icon="message"))
                for item in context["frontend_v1_legacy_nav"]:
                    if item["url"] == reverse("messenger:ai"):
                        item["label"] = "Azure AI"
            if flag_enabled("frontend_v1_ai_messenger"):
                context["frontend_v1_nav"].append(dict(url=reverse("messenger:ai"), name="messenger:ai", label="Azure AI", icon="message"))
                context["frontend_v1_legacy_nav"] = [item for item in context["frontend_v1_legacy_nav"] if item["url"] != reverse("messenger:ai")]
            if context["frontend_v1_records_ready"]:
                records = {reverse(name): name for name in ("certificates", "leaderboard", "attendance_calendar", "subscriptions", "help_center")}
                context["frontend_v1_nav"].extend(dict(item, name=records[item["url"]]) for item in context["frontend_v1_legacy_nav"] if item["url"] in records)
                context["frontend_v1_legacy_nav"] = [item for item in context["frontend_v1_legacy_nav"] if item["url"] not in records]
            if flag_enabled("frontend_v1_exams"):
                exam_url = reverse("exam_center")
                context["frontend_v1_nav"].append(dict(url=exam_url, name="exam_center", label="Imtihonlar", icon="exam"))
                context["frontend_v1_legacy_nav"] = [item for item in context["frontend_v1_legacy_nav"] if item["url"] != exam_url]
            if flag_enabled("frontend_v1_classbook_live"):
                live_url = reverse("classbook:live_home")
                context["frontend_v1_nav"].append(dict(url=live_url, name="classbook:live_home", label="Jonli dars", icon="live"))
                context["frontend_v1_legacy_nav"] = [item for item in context["frontend_v1_legacy_nav"] if item["url"] != live_url]
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

    @cached_property
    def frontend_v1_enabled(self):
        return flag_enabled('frontend_v1_learning') or flag_enabled('frontend_v1_auth')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context.get("form")
        if form is not None and form.is_bound and form.errors:
            # Xato bilan qaytgan sahifada fokus birinchi xatoga o'tadi (PUB1.4b), nomga emas.
            form.fields["username"].widget.attrs.pop("autofocus", None)
        from frontend import public_intent

        context["auth_intent"] = public_intent.describe(context.get("next", ""))
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # O'zbekcha xatolar ikkala renderer'da (PUB1.4b): legacy ilgari Django'ning
        # inglizcha «Please enter a correct username and password…» matnini ko'rsatardi.
        form.error_messages = {
            **form.error_messages,
            "invalid_login": "Email yoki username va parol mos kelmadi. Qayta tekshiring.",
            "inactive": "Bu hisob faol emas. Yordam xizmatiga murojaat qiling.",
        }
        for field in form.fields.values():
            field.error_messages["required"] = "Bu maydonni to‘ldiring."
            if self.frontend_v1_enabled:
                field.widget.attrs["class"] = "c-field"
        return form

    # --- urinishlar cheklovi (PUB1.0c) ------------------------------------- #
    # Blok tekshiruvi parol tekshiruvidan OLDIN: bloklangan so'rov `authenticate`
    # ga yetmaydi, ya'ni javob vaqti ham parol to'g'riligini oshkor qilmaydi.

    def post(self, request, *args, **kwargs):
        from users import auth_abuse

        identifier = request.POST.get("username", "")
        decision = auth_abuse.login_blocked(request, identifier)
        if not decision.allowed:
            # Bog'lanmagan forma: bog'langan forma `errors`da authenticate qilardi.
            # `get_form()` orqali — V1 uslubi va xabarlari saqlanadi.
            self._auth_throttled = True
            form = self.get_form()
            # Bog'lanmagan formada `add_error` `cleaned_data`ni kutadi; validatsiya
            # esa aynan chetlab o'tilayotgan `authenticate` bo'lardi.
            form.cleaned_data = {}
            form.add_error(None, decision.message)
            response = self.render_to_response(self.get_context_data(form=form))
            return auth_abuse.apply_throttle_headers(response, decision)
        return super().post(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if getattr(self, "_auth_throttled", False):
            kwargs.pop("data", None)
            kwargs.pop("files", None)
            # Kiritilgan login saqlanadi (niyat yo'qolmaydi), parol esa yo'q.
            kwargs["initial"] = {**kwargs.get("initial", {}), "username": self.request.POST.get("username", "")[:254]}
        return kwargs

    def form_invalid(self, form):
        from users import auth_abuse

        auth_abuse.record_login_failure(self.request, self.request.POST.get("username", ""))
        return super().form_invalid(form)

    def form_valid(self, form):
        from users import auth_abuse

        auth_abuse.record_login_success(self.request, self.request.POST.get("username", ""))
        return super().form_valid(form)


def teacher_v1_navigation(active_nav):
    """One teacher navigation definition, including the conversation mode."""
    pages = (
        ("teacher_dashboard", "Bosh sahifa", "home"),
        ("teacher_release", "Darslarni ochish", "book"),
        ("teacher_grading", "Tekshiruv navbati", "exam"),
        ("teacher_cohorts", "Guruhlar", "users"),
        ("teacher_students", "O‘quvchilar", "users"),
        ("teacher_courses", "Kurslar", "book"),
        ("teacher_attendance", "Davomat", "calendar"),
    )
    legacy = (
        ("classbook:teacher_home", "Classbook", "live"),
    )
    if flag_enabled("frontend_v1_classbook_preparation"):
        pages += legacy
        legacy = ()
    if flag_enabled("frontend_v1_messenger"):
        pages += (("messenger:group", "Xabarlar", "message"),)
    if flag_enabled("frontend_v1_ai_messenger"):
        pages += (("messenger:ai", "Azure AI", "message"),)
    records_ready = flag_enabled("frontend_v1_records")
    if flag_enabled("frontend_v1_library"):
        pages += (("library_backoffice:resources", "Kutubxona", "book"),)
    if flag_enabled("frontend_v1_editors"):
        pages += (("backoffice_courses", "Kurs muharriri", "book"),
                  ("backoffice_lessons", "Dars muharriri", "book"))
    if records_ready:
        pages += (("help_center", "Yordam", "bulb"),)
    return dict(
        frontend_v1_records_ready=records_ready,
        frontend_v1_title=dict((name, label) for name, label, _ in pages)[active_nav],
        frontend_v1_workspace="Ustoz maydoni",
        frontend_v1_tagline="Darslar va o‘quvchilar",
        frontend_v1_home=reverse("teacher_dashboard"),
        frontend_v1_nav=[dict(url=reverse(name), name=name, label=label, icon=icon) for name, label, icon in pages],
        frontend_v1_legacy_nav=[dict(url=reverse(name), label=label, icon=icon) for name, label, icon in legacy],
    )


def render_teacher_v1(request, legacy_template, context, *, enabled=None, status=200):
    """Select presentation only; caller has already applied the teacher scope."""
    if enabled is None:
        enabled = flag_enabled("frontend_v1_teacher")
    if not enabled:
        return render(request, legacy_template, context, status=status)
    context.update(teacher_v1_navigation(context["active_nav"]))
    response = render(request, f"frontend_v1/{legacy_template}", context, status=status)
    patch_cache_control(response, private=True, no_store=True)
    return response
