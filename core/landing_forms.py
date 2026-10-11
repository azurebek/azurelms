from django import forms

from frontend.models import LandingPage


# Landing bo'limlari — template shu tuzilma bo'yicha panellarni render qiladi.
# `anchor` bosh sahifadagi (`/`) mos bo'lim id'siga havola (bo'sh bo'lsa faqat "/").
LANDING_SECTIONS = [
    {
        "key": "rail",
        "number": "01",
        "title": "Yon panel",
        "desc": "Sahifaning chap tomonidagi qisqa matnlar.",
        "anchor": "top",
        "fields": ["rail_tagline", "rail_footer_line_one", "rail_footer_line_two"],
    },
    {
        "key": "hero",
        "number": "02",
        "title": "Birinchi ekran",
        "desc": "Eng yuqoridagi sarlavha, kichik matn va tugmalar.",
        "anchor": "top",
        "fields": [
            "hero_kicker_left", "hero_kicker_right",
            "hero_title_start", "hero_title_highlight", "hero_title_end",
            "hero_subtitle", "hero_primary_label", "hero_secondary_label",
        ],
    },
    {
        "key": "demo",
        "number": "03",
        "title": "O‘quvchi kabineti namunasi",
        "desc": "Saytdagi namuna kartasi matnlari. Haqiqiy kurs yoki o‘quvchi natijalari o‘zgarmaydi.",
        "anchor": "top",
        "fields": [
            "demo_url", "demo_course_kicker", "demo_course_name", "demo_progress",
            "demo_next_title", "demo_next_time", "demo_next_badge",
            "demo_stat_one_value", "demo_stat_one_label",
            "demo_stat_two_value", "demo_stat_two_label",
            "demo_stat_three_value", "demo_stat_three_label",
        ],
    },
    {
        "key": "how",
        "number": "04",
        "title": "Jarayon (Qanday ishlaydi?)",
        "desc": "Jarayonni tushuntiradigan bo‘lim sarlavhasi va tavsifi.",
        "anchor": "how",
        "fields": ["process_section_kicker", "how_it_works_title", "how_it_works_subtitle"],
    },
    {
        "key": "path",
        "number": "05",
        "title": "Daraja yo'li",
        "desc": "Til darajalari bo‘limining sarlavhasi va tavsifi.",
        "anchor": "path",
        "fields": ["path_kicker", "path_title", "path_subtitle"],
    },
    {
        "key": "ai",
        "number": "06",
        "title": "AI repetitor",
        "desc": "Bo‘lim sarlavhasi va suhbat namunasi. Bu yerda faqat saytda ko‘rinadigan matnlar o‘zgaradi.",
        "anchor": "ai",
        "fields": [
            "ai_kicker", "ai_title", "ai_subtitle",
            "ai_demo_session_label", "ai_demo_question", "ai_demo_answer",
            "ai_demo_input_placeholder",
        ],
    },
    {
        "key": "exam",
        "number": "07",
        "title": "Imtihon muhiti",
        "desc": "Imtihonlar haqida bo‘lim sarlavhasi va tavsifi.",
        "anchor": "exam",
        "fields": ["exam_kicker", "exam_title", "exam_subtitle"],
    },
    {
        "key": "cert",
        "number": "08",
        "title": "Sertifikat",
        "desc": "Bo'lim matni va namuna sertifikat kartasi.",
        "anchor": "cert",
        "fields": [
            "cert_kicker", "cert_title", "cert_text", "cert_cta_label",
            "cert_sample_number", "cert_sample_label", "cert_sample_course",
            "cert_sample_name", "cert_sample_score", "cert_sample_date",
            "cert_sample_location",
        ],
    },
    {
        "key": "footer",
        "number": "09",
        "title": "Sahifa oxiri",
        "desc": "Sahifa oxiridagi sarlavha, tugmalar va ma’lumotlar.",
        "anchor": "",
        "fields": [
            "final_cta_title", "cta_primary_label", "final_cta_secondary_label",
            "footer_tagline", "footer_col_platform_title", "footer_col_company_title",
            "footer_col_legal_title", "footer_col_contact_title", "footer_copyright",
        ],
    },
]

# Barcha tahrirlanadigan maydonlar (bo'limlardan yig'iladi).
_EDITABLE_FIELDS = tuple(name for section in LANDING_SECTIONS for name in section["fields"])

# Uzunroq matnlar uchun textarea.
_TEXTAREA_FIELDS = {"hero_subtitle", "ai_subtitle", "ai_demo_answer", "cert_text", "how_it_works_subtitle"}


class LandingPageForm(forms.ModelForm):
    """Bosh sahifa singleton matnlari uchun owner editori (brend paneli pattern'ida)."""

    change_reason = forms.CharField(
        label="O'zgartirish sababi",
        max_length=240,
        help_text="O‘zgarishlar tarixida saqlanadi. Masalan: bosh sarlavha yangilandi.",
        widget=forms.Textarea(attrs={"rows": 3, "class": "lc-input"}),
    )
    confirm_change = forms.BooleanField(
        label="Bosh sahifa jonli o'zgarishini tasdiqlayman",
        required=True,
    )

    class Meta:
        model = LandingPage
        fields = _EDITABLE_FIELDS
        labels = {
            "rail_tagline": "Yon paneldagi tavsif",
            "rail_footer_line_one": "Yon panel oxiridagi 1-qator",
            "rail_footer_line_two": "Yon panel oxiridagi 2-qator",
            "hero_kicker_left": "Sarlavha ustidagi chap yozuv",
            "hero_kicker_right": "Sarlavha ustidagi o‘ng yozuv",
            "hero_primary_label": "Asosiy tugma matni",
            "hero_secondary_label": "Ikkinchi tugma matni",
            "demo_url": "Namunada ko‘rinadigan sayt manzili",
            "demo_course_kicker": "Kurs ustidagi yozuv",
            "demo_course_name": "Namunadagi kurs nomi",
            "demo_progress": "Namunadagi bajarilish foizi",
            "demo_next_title": "Namunadagi keyingi dars nomi",
            "demo_next_time": "Namunadagi keyingi dars vaqti",
            "demo_next_badge": "Keyingi dars belgisi matni",
            "demo_stat_one_value": "Birinchi ko‘rsatkich qiymati",
            "demo_stat_one_label": "Birinchi ko‘rsatkich nomi",
            "demo_stat_two_value": "Ikkinchi ko‘rsatkich qiymati",
            "demo_stat_two_label": "Ikkinchi ko‘rsatkich nomi",
            "demo_stat_three_value": "Uchinchi ko‘rsatkich qiymati",
            "demo_stat_three_label": "Uchinchi ko‘rsatkich nomi",
            "process_section_kicker": "Sarlavha ustidagi yozuv",
            "path_kicker": "Sarlavha ustidagi yozuv",
            "ai_kicker": "Sarlavha ustidagi yozuv",
            "ai_demo_session_label": "Suhbat namunasi nomi",
            "ai_demo_question": "Namunadagi savol",
            "ai_demo_answer": "Namunadagi javob",
            "ai_demo_input_placeholder": "Savol maydonidagi ko‘rsatma",
            "exam_kicker": "Sarlavha ustidagi yozuv",
            "cert_kicker": "Sarlavha ustidagi yozuv",
            "cert_cta_label": "Sertifikat tugmasi matni",
            "final_cta_title": "Sahifa oxiridagi sarlavha",
            "cta_primary_label": "Sahifa oxiridagi asosiy tugma matni",
            "final_cta_secondary_label": "Sahifa oxiridagi ikkinchi tugma matni",
            "footer_tagline": "Platforma haqida qisqa matn",
            "footer_col_platform_title": "Platforma havolalari sarlavhasi",
            "footer_col_company_title": "Kompaniya havolalari sarlavhasi",
            "footer_col_legal_title": "Huquqiy havolalar sarlavhasi",
            "footer_col_contact_title": "Aloqa ma’lumotlari sarlavhasi",
            "footer_copyright": "Mualliflik huquqi yozuvi",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in ("change_reason", "confirm_change"):
                continue
            if name in _TEXTAREA_FIELDS:
                field.widget = forms.Textarea(attrs={"rows": 3})
            widget = field.widget
            if isinstance(widget, (forms.TextInput, forms.Textarea, forms.NumberInput)):
                css = widget.attrs.get("class", "")
                widget.attrs["class"] = (css + " lc-input").strip()

    @property
    def changed_landing_fields(self):
        return [name for name in self.changed_data if name in self._meta.fields]

    @property
    def sections(self):
        """Template uchun: har bo'lim + unga tegishli bound field'lar."""
        result = []
        for section in LANDING_SECTIONS:
            bound_fields = [self[name] for name in section["fields"]]
            result.append({
                "key": section["key"],
                "number": section["number"],
                "title": section["title"],
                "desc": section["desc"],
                "anchor": section["anchor"],
                "fields": bound_fields,
                "has_error": any(bf.errors for bf in bound_fields),
            })
        return result
