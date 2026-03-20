from django import forms

from cohorts.models import Cohort
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
