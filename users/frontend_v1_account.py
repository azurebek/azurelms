"""ACC-01 presentation; canonical profile form remains the only writer."""

import json

from django.db import transaction
from django.utils.crypto import constant_time_compare, salted_hmac

from core.flags import flag_enabled
from core.frontend_v1 import FrontendV1Mixin, teacher_v1_navigation
from .forms import ProfileFieldsForm
from .models import CustomUser


def profile_revision(user):
    """Opaque user-bound snapshot, excluding credentials, XP and preferences."""
    value = [user.pk, *[getattr(user, name) for name in ProfileFieldsForm.Meta.fields]]
    return salted_hmac("frontend-v1-profile", json.dumps(value), algorithm="sha256").hexdigest()


class AccountV1Mixin(FrontendV1Mixin):
    frontend_v1_flag = "frontend_v1_account"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Capture before ModelForm validation mutates its in-memory instance.
        self.initial_profile_revision = profile_revision(form.instance)
        if self.frontend_v1_enabled:
            for field in form.fields.values():
                field.widget.attrs["class"] = "c-field"
            form.fields["phone_number"].widget.input_type = "tel"
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.frontend_v1_enabled:
            if self.request.user.is_staff and flag_enabled("frontend_v1_teacher"):
                context.update(teacher_v1_navigation("teacher_dashboard"))
                context["frontend_v1_title"] = self.frontend_v1_title
            context["profile_revision"] = (
                self.request.POST.get("profile_revision", "")
                if self.request.method == "POST" else self.initial_profile_revision
            )
        return context

    def form_valid(self, form):
        revision = self.request.POST.get("profile_revision", "")
        if not self.frontend_v1_enabled and not revision:
            return super().form_valid(form)
        # Both V1 entry points serialize profile edits. Legacy field-only saves
        # and other writers still own their policies; this isn't a global version.
        with transaction.atomic():
            fresh = CustomUser.objects.select_for_update().get(pk=self.request.user.pk)
            if not constant_time_compare(revision, profile_revision(fresh)):
                form.add_error(None, "Profil boshqa oynada o‘zgargan yoki forma eskirgan. Matningizni saqlab oling va sahifani qayta oching.")
                return self.render_to_response(self.get_context_data(form=form), status=409)
            return super().form_valid(form)
