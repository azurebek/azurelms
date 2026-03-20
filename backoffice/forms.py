from django import forms

from cohorts.models import Cohort
from frontend.models import AuthPageSettings, LegalPage, SiteSettings
from subscriptions.models import Plan, PlanFeature
from users.models import CustomUser, NotificationBroadcast


class BackofficeUserUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "telegram_id",
            "telegram_username",
            "total_xp",
            "is_active",
            "is_staff",
        )
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "telegram_id": forms.NumberInput(attrs={"class": "form-control"}),
            "telegram_username": forms.TextInput(attrs={"class": "form-control"}),
            "total_xp": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_staff": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_total_xp(self):
        value = self.cleaned_data.get("total_xp")
        return max(value or 0, 0)


class BackofficeBroadcastForm(forms.ModelForm):
    recipients = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(is_active=True).order_by("username"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "6"}),
    )
    cohorts = forms.ModelMultipleChoiceField(
        queryset=Cohort.objects.select_related("course").filter(is_active=True).order_by("name"),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": "6"}),
    )

    class Meta:
        model = NotificationBroadcast
        fields = ("title", "message", "icon", "url", "target_type", "recipients", "cohorts")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Masalan: Platforma yangilandi"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Bildirishnoma matni"}),
            "icon": forms.TextInput(attrs={"class": "form-control", "placeholder": "megaphone"}),
            "url": forms.TextInput(attrs={"class": "form-control", "placeholder": "/users/dashboard/"}),
            "target_type": forms.Select(attrs={"class": "form-select", "id": "id_target_type"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        target_type = cleaned_data.get("target_type")
        recipients = cleaned_data.get("recipients")
        cohorts = cleaned_data.get("cohorts")

        if target_type == NotificationBroadcast.TARGET_USERS and not recipients:
            self.add_error("recipients", "Tanlangan foydalanuvchilar ro'yxati bo'sh bo'lmasligi kerak.")
        if target_type == NotificationBroadcast.TARGET_COHORTS and not cohorts:
            self.add_error("cohorts", "Tanlangan cohortlar ro'yxati bo'sh bo'lmasligi kerak.")
        return cleaned_data


class BackofficePlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ("name", "price", "description", "is_popular", "button_text", "order")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "is_popular": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "button_text": forms.TextInput(attrs={"class": "form-control"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class BackofficePlanFeatureForm(forms.ModelForm):
    class Meta:
        model = PlanFeature
        fields = ("name", "is_included", "order")
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Masalan: Barcha darslarga kirish"}),
            "is_included": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
        }


class BackofficeSiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = (
            "company_description",
            "contact_phone",
            "contact_email",
            "contact_address",
            "support_url",
            "payment_card_number",
            "payment_card_holder",
            "payment_provider_label",
            "payment_instruction",
            "telegram_url",
            "instagram_url",
            "youtube_url",
            "facebook_url",
        )
        widgets = {
            "company_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "contact_phone": forms.TextInput(attrs={"class": "form-control"}),
            "contact_email": forms.EmailInput(attrs={"class": "form-control"}),
            "contact_address": forms.TextInput(attrs={"class": "form-control"}),
            "support_url": forms.URLInput(attrs={"class": "form-control"}),
            "payment_card_number": forms.TextInput(attrs={"class": "form-control"}),
            "payment_card_holder": forms.TextInput(attrs={"class": "form-control"}),
            "payment_provider_label": forms.TextInput(attrs={"class": "form-control"}),
            "payment_instruction": forms.TextInput(attrs={"class": "form-control"}),
            "telegram_url": forms.URLInput(attrs={"class": "form-control"}),
            "instagram_url": forms.URLInput(attrs={"class": "form-control"}),
            "youtube_url": forms.URLInput(attrs={"class": "form-control"}),
            "facebook_url": forms.URLInput(attrs={"class": "form-control"}),
        }


class BackofficeAuthPageSettingsForm(forms.ModelForm):
    class Meta:
        model = AuthPageSettings
        fields = (
            "meta_description",
            "topbar_back_label",
            "help_prompt",
            "help_link_label",
            "login_visual_kicker",
            "login_visual_title",
            "login_visual_description",
            "login_panel_badge",
            "login_panel_heading",
            "login_panel_intro",
            "login_footer_prompt",
            "login_footer_link_label",
            "register_visual_kicker",
            "register_visual_title",
            "register_visual_description",
            "register_panel_badge",
            "register_panel_heading",
            "register_panel_intro",
            "register_footer_prompt",
            "register_footer_link_label",
        )
        widgets = {
            "meta_description": forms.TextInput(attrs={"class": "form-control"}),
            "topbar_back_label": forms.TextInput(attrs={"class": "form-control"}),
            "help_prompt": forms.TextInput(attrs={"class": "form-control"}),
            "help_link_label": forms.TextInput(attrs={"class": "form-control"}),
            "login_visual_kicker": forms.TextInput(attrs={"class": "form-control"}),
            "login_visual_title": forms.TextInput(attrs={"class": "form-control"}),
            "login_visual_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "login_panel_badge": forms.TextInput(attrs={"class": "form-control"}),
            "login_panel_heading": forms.TextInput(attrs={"class": "form-control"}),
            "login_panel_intro": forms.TextInput(attrs={"class": "form-control"}),
            "login_footer_prompt": forms.TextInput(attrs={"class": "form-control"}),
            "login_footer_link_label": forms.TextInput(attrs={"class": "form-control"}),
            "register_visual_kicker": forms.TextInput(attrs={"class": "form-control"}),
            "register_visual_title": forms.TextInput(attrs={"class": "form-control"}),
            "register_visual_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "register_panel_badge": forms.TextInput(attrs={"class": "form-control"}),
            "register_panel_heading": forms.TextInput(attrs={"class": "form-control"}),
            "register_panel_intro": forms.TextInput(attrs={"class": "form-control"}),
            "register_footer_prompt": forms.TextInput(attrs={"class": "form-control"}),
            "register_footer_link_label": forms.TextInput(attrs={"class": "form-control"}),
        }


class BackofficeLegalPageForm(forms.ModelForm):
    class Meta:
        model = LegalPage
        fields = ("title", "content")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 12}),
        }
