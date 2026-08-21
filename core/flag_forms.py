"""Feature flag o'zgartirish formasi (A2).

Kill switch va circuit reset bilan bir xil mutation patterni: majburiy sabab,
majburiy tasdiq. Qo'shimcha shart — slug **registrda** bo'lishi kerak, aks
holda DB'da hech narsani boshqarmaydigan yetim qator paydo bo'lardi.
"""

from django import forms

from core.flags import FLAG_REGISTRY


class FeatureFlagForm(forms.Form):
    slug = forms.ChoiceField(
        choices=[(flag.slug, flag.label) for flag in FLAG_REGISTRY],
        widget=forms.HiddenInput,
    )
    enabled = forms.BooleanField(required=False)
    change_reason = forms.CharField(
        label="O'zgartirish sababi",
        max_length=240,
        widget=forms.Textarea(attrs={"rows": 2, "class": "brand-input"}),
    )
    confirm_change = forms.BooleanField(
        label="O'zgartirishni tasdiqlayman",
        required=True,
    )
