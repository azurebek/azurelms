from django import forms

from cohorts.models import Cohort
from .models import Plan


class CatalogPlanForm(forms.ModelForm):
    description = forms.CharField(label="Qisqa izoh", widget=forms.Textarea(attrs={"rows": 3}))
    features_text = forms.CharField(
        label="Marketing imkoniyatlari", required=False, max_length=10000,
        help_text="Har qatorda bitta imkoniyat. Kiritilmagan imkoniyat oldiga - yozing. Faqat real ishlayotgan xizmatni va'da qiling.",
        widget=forms.Textarea(attrs={"rows": 8}),
    )
    change_reason = forms.CharField(label="O'zgartirish sababi", max_length=240)
    confirm_change = forms.BooleanField(label="Narx va sotuv holati o'zgarishini tasdiqlayman")

    class Meta:
        model = Plan
        fields = ("name", "price", "cohort_capacity_limit", "description", "is_available_for_purchase", "is_popular", "button_text", "order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.cohort_capacity_limit is None:
            # Legacy tarifda delivery turkumi yo'q va uni keyin qo'shib
            # bo'lmaydi (`Plan.clean`), shuning uchun maydon ko'rsatilmaydi.
            self.fields.pop("cohort_capacity_limit")
        else:
            capacity = self.fields["cohort_capacity_limit"]
            capacity.required = True
            capacity.label = "Guruhning standart sig'imi"
            capacity.help_text = (
                "Yangi guruhlar shu sondan boshlanadi va sotuv sahifasida shu va'da "
                "qilinadi. Uni keyin o'zgartirish mumkin — mavjud guruhlar o'z "
                "sig'imini saqlaydi. Bitta guruhga istisno qilish uchun o'sha "
                "guruhning sig'imini o'zgartiring."
            )
        if self.instance.pk:
            self.fields["features_text"].initial = "\n".join(
                ("" if f.is_included else "- ") + f.name for f in self.instance.features.order_by("order", "id")
            )
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "brand-input"

    def clean_features_text(self):
        lines = [line.strip() for line in self.cleaned_data["features_text"].splitlines() if line.strip()]
        if len(lines) > 40 or any(len(line.removeprefix("- ")) > 200 for line in lines):
            raise forms.ValidationError("40 tagacha imkoniyat, har biri 200 belgigacha bo'lishi kerak.")
        return "\n".join(lines)

    def clean(self):
        data = super().clean()
        if (data.get("is_available_for_purchase") and self.instance.cohort_capacity_limit
                and not self.instance.delivery_cohorts.filter(is_active=True, course__is_active=True).exists()):
            self.add_error("is_available_for_purchase", "Avval shu tarifga mos faol guruh yarating.")
        return data


class SeatDecisionForm(forms.Form):
    """Joy bo'yicha qaror — chek qarori bilan bir xil naqsh: sabab + tasdiq."""

    ACTION_RELEASE = "release"
    ACTION_RESTORE = "restore"
    ACTION_CHOICES = ((ACTION_RELEASE, "Joyni bo'shatish"), (ACTION_RESTORE, "Qaytarish"))

    enrollment_id = forms.IntegerField(widget=forms.HiddenInput)
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.HiddenInput)
    change_reason = forms.CharField(
        label="Qaror sababi", max_length=240,
        widget=forms.Textarea(attrs={"rows": 2, "class": "brand-input"}),
        help_text="Audit tarixida saqlanadi. Masalan: “yarim yildan beri to’lamayapti”.",
    )
    confirm_change = forms.BooleanField(label="Qarorni tasdiqlayman", required=True)


class MemberTransferForm(forms.Form):
    """Boshqa guruhga ko'chirish — tarif almashsa alohida tasdiq so'raladi."""

    enrollment_id = forms.IntegerField(widget=forms.HiddenInput)
    target_cohort = forms.ModelChoiceField(
        queryset=Cohort.objects.none(), label="Yangi guruh", empty_label="Guruhni tanlang",
    )
    change_reason = forms.CharField(
        label="Ko'chirish sababi", max_length=240,
        widget=forms.Textarea(attrs={"rows": 2, "class": "brand-input"}),
    )
    confirm_change = forms.BooleanField(label="Ko'chirishni tasdiqlayman", required=True)
    allow_tier_change = forms.BooleanField(
        label="Tarif ham o'zgarishini tasdiqlayman", required=False,
        help_text=(
            "Boshqa tarifdagi guruhga ko'chirilsa kerak. Tizim narx farqini "
            "hisoblamaydi — yangi tarif joriy davr oxirigacha ishlaydi, farqni "
            "odatdagi to'lov oqimi orqali olasiz."
        ),
    )

    def __init__(self, *args, targets=None, **kwargs):
        super().__init__(*args, **kwargs)
        if targets is not None:
            self.fields["target_cohort"].queryset = targets
        self.fields["target_cohort"].widget.attrs["class"] = "brand-input"


class DeliveryCohortForm(forms.ModelForm):
    change_reason = forms.CharField(label="O'zgartirish sababi", max_length=240)
    confirm_change = forms.BooleanField(label="Guruh sozlamalarini tasdiqlayman")

    class Meta:
        model = Cohort
        fields = ("name", "course", "plan", "capacity", "start_date", "is_active", "is_checkout_default", "telegram_group_link")
        widgets = {"start_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plan"].queryset = Plan.objects.filter(cohort_capacity_limit__isnull=False)
        self.fields["plan"].required = not self.instance.pk or self.instance.plan_id is not None
        self.fields["capacity"].help_text = (
            "Bo'sh qoldirilsa tarifning standart sig'imi olinadi. Kamaytirish ham, "
            "oshirish ham mumkin — bu guruh uchun istisno qilsangiz katalogda "
            "ko'rinib turadi. Band joylar sonidan kam bo'la olmaydi."
        )
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "brand-input"
