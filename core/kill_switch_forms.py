"""AI kill switch formasi — owner uchun shoshilinch to'xtatish tugmasi (A2).

Brend va landing muharrirlaridagi bir xil mutation patterni: majburiy sabab,
majburiy tasdiqlash va o'zgarish bo'lmasa hech narsa yozmaydigan no-op yo'l.
"""

from django import forms

from aicontrol.models import AISettings


class AIKillSwitchForm(forms.ModelForm):
    change_reason = forms.CharField(
        label="O'zgartirish sababi",
        max_length=240,
        help_text="Audit tarixida saqlanadi. Masalan: kvota tugab qoldi, tekshirgunimcha to'xtatildi.",
        widget=forms.Textarea(attrs={"rows": 3, "class": "brand-input"}),
    )
    confirm_change = forms.BooleanField(
        label="AI holatini o'zgartirishni tasdiqlayman",
        required=True,
    )

    class Meta:
        model = AISettings
        fields = ("ai_remote_calls_enabled",)

    @property
    def switch_changed(self):
        return "ai_remote_calls_enabled" in self.changed_data
