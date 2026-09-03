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


class ProfileFieldsForm(forms.ModelForm):
    """Foydalanuvchi o'zi tahrirlaydigan profil maydonlari — yagona manba.

    Profil sahifasidagi joyida tahrirlash ham, Sozlamalar > Hisob ham shu
    formani ishlatadi. `username` va `email` ataylab yo'q: ular login
    identifikatori va ularni bu yerdan tekshiruvsiz o'zgartirib bo'lmaydi.
    """

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone_number', 'bio']
        labels = {
            'first_name': 'Ism',
            'last_name': 'Familiya',
            'phone_number': 'Telefon',
            'bio': 'Haqida (bio)',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'autocomplete': 'family-name'}),
            'phone_number': forms.TextInput(attrs={'autocomplete': 'tel'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
        }

    def save(self, commit=True):
        """Faqat shu formadagi maydonlarni yozadi.

        `ModelForm.save()` odatiy holda `instance.save()` ni argumentsiz
        chaqiradi, ya'ni `CustomUser` ning **butun qatorini** formaga yuklangan
        (eskirgan) qiymatlar bilan qayta yozadi. O'sha qatorda profilga aloqasi
        yo'q, lekin boshqa yo'llardan yangilanadigan maydonlar bor:

        * `total_xp` — `users/xp.py::award_xp` (davomat, quiz, vazifa bahosi);
        * `ai_tone`, `ai_model`, `ai_skill`, `ai_memory_enabled`,
          `ai_web_search_effort` — `/users/settings/ai-*` endpointlari.

        Ya'ni bir tabda AI ohangini o'zgartirib, boshqasida profilni saqlash
        ohangni eskisiga qaytarardi; profil saqlanayotgan lahzada berilgan XP
        esa yo'qolardi. Ikkalasi ham jim sodir bo'lardi.
        """
        instance = super().save(commit=False)
        if commit:
            instance.save(update_fields=list(self.Meta.fields))
        return instance
