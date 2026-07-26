from django import forms

from frontend.models import LandingPage


# Landing bo'limlari — template shu tuzilma bo'yicha panellarni render qiladi.
# `anchor` bosh sahifadagi (`/`) mos bo'lim id'siga havola (bo'sh bo'lsa faqat "/").
LANDING_SECTIONS = [
    {
        "key": "rail",
        "number": "01",
        "title": "Yon panel (rail)",
        "desc": "Chap tomondagi qat'iy panel matnlari.",
        "anchor": "top",
        "fields": ["rail_tagline", "rail_footer_line_one", "rail_footer_line_two"],
    },
    {
        "key": "hero",
        "number": "02",
        "title": "Hero (bosh ekran)",
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
        "title": "Demo dashboard",
        "desc": "Hero ostidagi ko'rgazma dashboard kartasi.",
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
        "desc": "Bo'lim sarlavhasi. Qadamlar alohida ro'yxatda (keyingi bosqich).",
        "anchor": "how",
        "fields": ["process_section_kicker", "how_it_works_title", "how_it_works_subtitle"],
    },
    {
        "key": "path",
        "number": "05",
        "title": "Daraja yo'li",
        "desc": "Bo'lim sarlavhasi. Bosqichlar alohida ro'yxatda (keyingi bosqich).",
        "anchor": "path",
        "fields": ["path_kicker", "path_title", "path_subtitle"],
    },
    {
        "key": "ai",
        "number": "06",
        "title": "AI repetitor",
        "desc": "Bo'lim sarlavhasi va chat demo matni. Xususiyatlar alohida ro'yxatda (keyingi bosqich).",
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
        "desc": "Bo'lim sarlavhasi. Ko'nikma kartalari alohida ro'yxatda (keyingi bosqich).",
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
        "title": "Pastki CTA va footer",
        "desc": "Sahifa oxiridagi chaqiruv va footer matnlari. Footer havolalari navigatsiya menejerida (keyingi bosqich).",
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
        help_text="Audit tarixida saqlanadi. Masalan: hero sarlavhasi yangilandi.",
        widget=forms.Textarea(attrs={"rows": 3, "class": "lc-input"}),
    )
    confirm_change = forms.BooleanField(
        label="Bosh sahifa jonli o'zgarishini tasdiqlayman",
        required=True,
    )

    class Meta:
        model = LandingPage
        fields = _EDITABLE_FIELDS

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
            result.append({
                "number": section["number"],
                "title": section["title"],
                "desc": section["desc"],
                "anchor": section["anchor"],
                "fields": [self[name] for name in section["fields"]],
            })
        return result
