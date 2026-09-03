"""To'lov cheki bo'yicha qaror formasi (A2 mutation patterni).

Kill switch, circuit reset, brend va landing muharrirlaridagi bir xil naqsh:
majburiy sabab va majburiy tasdiqlash. Farqi bitta — bu yerda qaror **pulga**
tegadi, shuning uchun sabab tasdiqlashda ham, rad etishda ham talab qilinadi:
audit tarixida "nega tasdiqlandi/rad etildi" savoli keyinroq beriladi.
"""

from django import forms


class ReceiptDecisionForm(forms.Form):
    ACTION_VERIFY = "verify"
    ACTION_REJECT = "reject"
    ACTION_CHOICES = (
        (ACTION_VERIFY, "Tasdiqlash"),
        (ACTION_REJECT, "Rad etish"),
    )

    receipt_id = forms.IntegerField(widget=forms.HiddenInput)
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.HiddenInput)
    change_reason = forms.CharField(
        label="Qaror sababi",
        max_length=240,
        widget=forms.Textarea(attrs={"rows": 2, "class": "brand-input"}),
        help_text=(
            "Audit tarixida saqlanadi. Masalan: “bank ko'chirmasi mos keladi” "
            "yoki “summa yetarli emas”."
        ),
    )
    confirm_change = forms.BooleanField(
        label="Qarorni tasdiqlayman",
        required=True,
    )
