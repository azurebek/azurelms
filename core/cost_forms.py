"""AI narx snapshot'ini kiritish formasi (A2).

Boshqa owner mutation'lari bilan bir xil: majburiy sabab va majburiy tasdiq.
Narx **manba izohi** bilan kiritiladi — raqamni keyin tekshirish mumkin bo'lsin.
"""

from django import forms


class AIModelPriceForm(forms.Form):
    provider = forms.CharField(max_length=32, initial="gemini")
    model_name = forms.CharField(max_length=80, label="Model nomi")
    input_per_million = forms.DecimalField(
        max_digits=12, decimal_places=6, min_value=0, label="Kirish (1M token uchun)"
    )
    output_per_million = forms.DecimalField(
        max_digits=12, decimal_places=6, min_value=0, label="Chiqish (1M token uchun)"
    )
    currency = forms.CharField(max_length=8, initial="USD", label="Valyuta")
    effective_from = forms.DateField(
        label="Qaysi sanadan amal qiladi",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    note = forms.CharField(
        max_length=200, required=False, label="Manba",
        help_text="Raqam qayerdan olindi — keyin tekshirish uchun.",
    )
    change_reason = forms.CharField(
        label="Sabab", max_length=240,
        widget=forms.Textarea(attrs={"rows": 2, "class": "brand-input"}),
    )
    confirm_change = forms.BooleanField(label="Narxni yozishni tasdiqlayman", required=True)
