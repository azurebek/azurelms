"""AI circuit breaker cooldown'ini tozalash formasi (A2).

Kill switch, brend va landing muharrirlaridagi bir xil mutation patterni:
majburiy sabab, majburiy tasdiqlash va o'zgarish bo'lmasa hech narsa
yozmaydigan no-op yo'l.
"""

from django import forms


class AICircuitResetForm(forms.Form):
    change_reason = forms.CharField(
        label="Tozalash sababi",
        max_length=240,
        help_text=(
            "Audit tarixida saqlanadi. Circuit'ni sabab bartaraf etilgandan "
            "keyin tozalang — masalan: model sozlamasi tuzatildi."
        ),
        widget=forms.Textarea(attrs={"rows": 3, "class": "brand-input"}),
    )
    confirm_change = forms.BooleanField(
        label="Cooldown'ni tozalashni tasdiqlayman",
        required=True,
    )
