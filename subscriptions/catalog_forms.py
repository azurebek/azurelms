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
        fields = ("name", "price", "description", "is_available_for_purchase", "is_popular", "button_text", "order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        self.fields["capacity"].help_text = "Bo'sh qoldirilsa tarif chegarasi olinadi. Uni kamaytirish mumkin, oshirish mumkin emas."
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "brand-input"
