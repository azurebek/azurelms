"""Dead-letter replay formasi — auditlangan mutation yuzasi (T6).

Kill switch, AI cooldown, brend va operatsion sozlamalardagi bir xil A2
patterni: majburiy sabab, majburiy tasdiqlash va o'zgarish bo'lmasa hech narsa
yozmaydigan no-op yo'l. Bu yerda ikki qo'shimcha shart bor va ikkisi ham
o'lchangan xavfdan kelib chiqadi:

1. **Tanlov sahifada ko'rsatilgan qatorlardan bo'lishi kerak.** `choices`
   sahifa qurilishida to'ldiriladi, ya'ni brauzerdan kelgan tasodifiy
   `dm:99999` qabul qilinmaydi. Sabab shakliy emas: owner ko'rmagan xabarni
   qaytarish «sabab bilan qaytarish» ta'rifiga to'g'ri kelmaydi.
2. **`permanent` turdagi qator uchun alohida tasdiq.** Bu tur — foydalanuvchi
   botni bloklagan, chat o'chirilgan yoki bot guruhdan chiqarilgan. Qayta
   urinish hech qachon yordam bermaydi va faqat rate budjetini yeydi. Baribir
   **taqiqlanmaydi**: blok yechilgan bo'lishi mumkin va buni faqat owner
   biladi. Shuning uchun to'siq emas, ikkinchi tasdiq.
"""

from django import forms
from django.core.exceptions import ValidationError

REASON_HELP = (
    "Audit tarixida saqlanadi. Masalan: token tuzatildi, tunda yiqilgan "
    "xabarlar qaytarildi."
)


class DeadLetterReplayForm(forms.Form):
    rows = forms.MultipleChoiceField(
        label="Qayta yuboriladigan xabarlar",
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Kamida bitta xabar tanlang."},
    )
    change_reason = forms.CharField(
        label="Qayta yuborish sababi",
        max_length=240,
        help_text=REASON_HELP,
        widget=forms.Textarea(attrs={"rows": 3, "class": "brand-input"}),
    )
    confirm_change = forms.BooleanField(
        label="Tanlangan xabarlarni navbatga qaytarishni tasdiqlayman",
        required=True,
    )
    acknowledge_permanent = forms.BooleanField(
        label=(
            "Tanlovda «hech qachon tuzalmaydi» turidagi xabar bor — "
            "baribir qaytarishni tasdiqlayman"
        ),
        required=False,
        help_text=(
            "Bu turdagi xabar foydalanuvchi botni bloklagani yoki bot guruhdan "
            "chiqarilgani uchun to'xtagan. Blok yechilmagan bo'lsa u yana "
            "o'sha xato bilan qaytadi."
        ),
    )

    def __init__(self, *args, available=(), limit=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.available = list(available)
        self.limit = limit
        self.permanent_selected = []
        self.fields["rows"].choices = [
            (row.key, row.short_label) for row in self.available
        ]

    def selectable_rows(self):
        """`(subwidget, row)` juftliklari — shablon ustun bo'yicha chizadi.

        `core/runtime_settings_forms.py::numeric_fields()` bilan bir xil
        naqsh: Django shablonida checkbox'ni o'z qatorining ma'lumotlari
        bilan yonma-yon qo'yishning boshqa yo'li yo'q, shuning uchun juftlik
        shu yerda tayyorlanadi. `self["rows"]` iteratsiyasi `choices` tartibida
        yuradi, ya'ni `available` bilan bir xil tartibda.
        """
        return zip(self["rows"], self.available)

    @property
    def permanent_available(self):
        return [row for row in self.available if row.is_permanent]

    def clean_rows(self):
        keys = self.cleaned_data["rows"]
        if self.limit is not None and len(keys) > int(self.limit):
            raise ValidationError(
                f"Bir amalda ko'pi bilan {self.limit} xabar qaytarilishi mumkin."
            )
        return keys

    def clean(self):
        cleaned = super().clean()
        by_key = {row.key: row for row in self.available}
        selected = [by_key[key] for key in cleaned.get("rows", ()) if key in by_key]
        self.permanent_selected = [row for row in selected if row.is_permanent]
        if self.permanent_selected and not cleaned.get("acknowledge_permanent"):
            self.add_error(
                "acknowledge_permanent",
                (
                    f"Tanlovda {len(self.permanent_selected)} ta «hech qachon "
                    "tuzalmaydi» turidagi xabar bor. Qaytarish uchun shu "
                    "tasdiqni ham belgilang."
                ),
            )
        return cleaned

    def selected_rows(self):
        """Tasdiqlangan tanlov — audit snapshot'i shundan quriladi."""
        by_key = {row.key: row for row in self.available}
        return [
            by_key[key] for key in self.cleaned_data.get("rows", ()) if key in by_key
        ]
