from django import forms
from django.forms import inlineformset_factory, modelformset_factory

from .models import (
    Announcement,
    KnowledgeArticle,
    University,
    UniversityDocument,
    UniversityFaculty,
    UniversityMedia,
    UniversityPreparationCourse,
    UniversityProgram,
    UniversityRequirement,
    UniversityServiceItem,
)


def _style_form_fields(form):
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs["class"] = "sit-bo-check"
            continue
        css = widget.attrs.get("class", "")
        widget.attrs["class"] = f"{css} sit-bo-input".strip()
        if isinstance(widget, forms.DateInput):
            widget.attrs["type"] = "date"


class AuditModelForm(forms.ModelForm):
    change_reason = forms.CharField(
        label="O'zgartirish sababi",
        max_length=240,
        help_text="Audit jurnalida saqlanadi.",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Masalan: 2026 kuzgi qabul ma'lumotlari yangilandi.",
            }
        ),
    )
    confirm_change = forms.BooleanField(
        label="O'zgarishlarni saqlashni tasdiqlayman",
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_form_fields(self)

    @property
    def changed_model_fields(self):
        return [name for name in self.changed_data if name in self._meta.fields]


class UniversityBackofficeForm(AuditModelForm):
    FIELD_GROUPS = (
        (
            "Asosiy ma'lumot",
            "Universitet identifikatsiyasi va joylashuvi.",
            (
                "name",
                "short_name",
                "city",
                "location_detail",
                "university_type",
                "description",
                "founded_year",
                "student_count",
            ),
        ),
        (
            "Qabul va kontrakt",
            "Public katalogdagi qabul holati, muddat va boshlang'ich narx.",
            (
                "admission_status",
                "admission_deadline",
                "academic_year",
                "tuition_from",
                "tuition_currency",
            ),
        ),
        (
            "Ariza yordami",
            "Universitet detail sahifasidagi yordam CTA sozlamalari.",
            (
                "application_help_enabled",
                "application_help_fee",
            ),
        ),
        (
            "Manba va dolzarblik",
            "Nashr uchun rasmiy manba va oxirgi tekshirilgan sana majburiy.",
            (
                "official_website",
                "source_url",
                "last_verified_on",
            ),
        ),
        (
            "Ko'rinish va nashr",
            "Bosh sahifa, muqova va public ko'rinish nazorati.",
            (
                "cover_theme",
                "cover_image",
                "logo_image",
                "is_featured",
                "is_published",
                "order",
            ),
        ),
    )

    class Meta:
        model = University
        fields = (
            "name",
            "short_name",
            "city",
            "location_detail",
            "university_type",
            "description",
            "founded_year",
            "student_count",
            "admission_status",
            "admission_deadline",
            "academic_year",
            "tuition_from",
            "tuition_currency",
            "application_help_enabled",
            "application_help_fee",
            "official_website",
            "source_url",
            "last_verified_on",
            "cover_theme",
            "cover_image",
            "logo_image",
            "is_featured",
            "is_published",
            "order",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "admission_deadline": forms.DateInput(),
            "last_verified_on": forms.DateInput(),
            "tuition_from": forms.NumberInput(attrs={"min": 0}),
            "application_help_fee": forms.NumberInput(attrs={"min": 0, "step": 1000}),
            "order": forms.NumberInput(attrs={"min": 0}),
        }

    @property
    def sections(self):
        return [
            {
                "title": title,
                "description": description,
                "fields": [self[name] for name in names],
                "has_error": any(self[name].errors for name in names),
            }
            for title, description, names in self.FIELD_GROUPS
        ]


class AnnouncementBackofficeForm(AuditModelForm):
    class Meta:
        model = Announcement
        fields = (
            "title",
            "university",
            "category",
            "published_on",
            "external_url",
            "show_on_home",
            "is_published",
            "order",
        )
        widgets = {
            "published_on": forms.DateInput(),
            "order": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["university"].queryset = University.objects.order_by("name")


class KnowledgeArticleBackofficeForm(AuditModelForm):
    class Meta:
        model = KnowledgeArticle
        fields = (
            "title",
            "category",
            "excerpt",
            "body",
            "cover_image",
            "published_on",
            "source_url",
            "last_verified_on",
            "is_featured",
            "is_published",
            "order",
        )
        widgets = {
            "excerpt": forms.Textarea(attrs={"rows": 3}),
            "published_on": forms.DateInput(),
            "last_verified_on": forms.DateInput(),
            "order": forms.NumberInput(attrs={"min": 0}),
        }


class StyledModelForm(forms.ModelForm):
    empty_sentinel_fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_form_fields(self)

    def has_changed(self):
        if not self.instance.pk and self.is_bound and self.empty_sentinel_fields:
            has_sentinel_value = any(
                self.data.get(self.add_prefix(name))
                or self.files.get(self.add_prefix(name))
                for name in self.empty_sentinel_fields
            )
            if not has_sentinel_value:
                return False
        return super().has_changed()


class UniversityFacultyBackofficeForm(StyledModelForm):
    empty_sentinel_fields = ("name",)

    class Meta:
        model = UniversityFaculty
        fields = ("name", "is_active", "order")


class UniversityProgramBackofficeForm(StyledModelForm):
    empty_sentinel_fields = ("name",)

    class Meta:
        model = UniversityProgram
        fields = (
            "faculty",
            "name",
            "degree_level",
            "language",
            "duration",
            "tuition_fee",
            "tuition_currency",
            "is_active",
            "order",
        )

    def __init__(self, *args, university=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = UniversityFaculty.objects.none()
        if university and university.pk:
            queryset = university.faculties.order_by("order", "name")
        self.fields["faculty"].queryset = queryset


class UniversityPreparationCourseBackofficeForm(StyledModelForm):
    empty_sentinel_fields = ("language",)

    class Meta:
        model = UniversityPreparationCourse
        fields = (
            "language",
            "duration",
            "tuition_fee",
            "tuition_currency",
            "is_active",
            "order",
        )


class UniversityRequirementBackofficeForm(StyledModelForm):
    empty_sentinel_fields = ("text",)

    class Meta:
        model = UniversityRequirement
        fields = ("text", "is_active", "order")


class UniversityDocumentBackofficeForm(StyledModelForm):
    empty_sentinel_fields = ("text",)

    class Meta:
        model = UniversityDocument
        fields = ("text", "is_active", "order")


class UniversityServiceItemBackofficeForm(StyledModelForm):
    empty_sentinel_fields = ("text",)

    class Meta:
        model = UniversityServiceItem
        fields = ("text", "is_active", "order")


class UniversityMediaBackofficeForm(StyledModelForm):
    empty_sentinel_fields = ("image", "video_url", "caption")

    class Meta:
        model = UniversityMedia
        fields = (
            "media_type",
            "image",
            "video_url",
            "caption",
            "is_active",
            "order",
        )


UniversityFacultyFormSet = inlineformset_factory(
    University,
    UniversityFaculty,
    form=UniversityFacultyBackofficeForm,
    extra=1,
    can_delete=False,
)
UniversityProgramFormSet = modelformset_factory(
    UniversityProgram,
    form=UniversityProgramBackofficeForm,
    extra=1,
    can_delete=False,
)
UniversityPreparationCourseFormSet = inlineformset_factory(
    University,
    UniversityPreparationCourse,
    form=UniversityPreparationCourseBackofficeForm,
    extra=1,
    can_delete=False,
)
UniversityRequirementFormSet = inlineformset_factory(
    University,
    UniversityRequirement,
    form=UniversityRequirementBackofficeForm,
    extra=1,
    can_delete=False,
)
UniversityDocumentFormSet = inlineformset_factory(
    University,
    UniversityDocument,
    form=UniversityDocumentBackofficeForm,
    extra=1,
    can_delete=False,
)
UniversityServiceItemFormSet = inlineformset_factory(
    University,
    UniversityServiceItem,
    form=UniversityServiceItemBackofficeForm,
    extra=1,
    can_delete=False,
)
UniversityMediaFormSet = inlineformset_factory(
    University,
    UniversityMedia,
    form=UniversityMediaBackofficeForm,
    extra=1,
    can_delete=False,
)
