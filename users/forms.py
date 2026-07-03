import re
import uuid

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import CustomUser, UserOnboarding


def _generate_unique_username(email: str) -> str:
    """Email prefiksidan unique username yaratamiz (foydalanuvchi ko'rmaydi)."""
    base = re.sub(r"[^a-zA-Z0-9_.-]", "", (email or "").split("@", 1)[0]).lower() or "user"
    base = base[:140]
    candidate = base
    suffix = 0
    while CustomUser.objects.filter(username=candidate).exists():
        suffix += 1
        candidate = f"{base}{suffix}"
        if suffix > 50:
            candidate = f"{base}{uuid.uuid4().hex[:6]}"
            break
    return candidate


class CustomUserCreationForm(UserCreationForm):
    """Multi-step wizard registratsiya formasi.

    - Username avtomatik email prefiksidan generatsiya qilinadi.
    - Onboarding maydonlari (goal, current_level) shu yerda qabul qilinadi va
      save() chaqirilganda UserOnboarding modeliga yoziladi.
    """

    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # UserCreationForm.Meta.fields'da `username` qo'shilib qoladi — uni olib tashlaymiz.
        self.fields.pop("username", None)

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu email allaqachon ro'yxatdan o'tgan.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data.get("last_name", "")
        user.username = _generate_unique_username(user.email)
        if commit:
            user.save()
        return user
