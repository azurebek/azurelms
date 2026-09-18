"""Kutubxona backoffice formalari.

Uslub mavjud backoffice formalaridan olingan (`core/backoffice_forms.py`):
`field-input` / `field-textarea` klasslari, o'zbekcha label va help text.

Fayl validatsiyasi shu yerda **ham** chaqiriladi, chunki forma foydalanuvchiga
xatoni maydon ostida ko'rsatishi kerak; yozuv yo'li esa `library/services.py`
dagi `apply_upload()` orqali boradi — u ayni tekshiruvni takrorlaydi, ya'ni
formani chetlab o'tgan chaqiruv ham himoyalangan.
"""

from django import forms
from django.core.files.uploadedfile import UploadedFile
from django.db import models

from core.access import teacher_course_queryset
from core.upload_validation import validate_upload

from .models import LessonMaterial, LibraryResource, LibrarySettings, MaterialAudience
from .services import tags_as_text


class LibraryResourceForm(forms.ModelForm):
    """Material yuklash va metadatasini tahrirlash."""

    tags_text = forms.CharField(
        required=False,
        label="Teglar",
        help_text="Vergul bilan ajrating: a1, speaking, tanishuv.",
        widget=forms.TextInput(
            attrs={"class": "field-input", "placeholder": "a1, speaking, tanishuv"}
        ),
    )

    class Meta:
        model = LibraryResource
        fields = [
            "title",
            "description",
            "resource_type",
            "language",
            "level",
            "topic",
            "course",
            "is_teacher_only",
            "file",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "field-input", "placeholder": "Masalan: A1 tanishuv taqdimoti"}
            ),
            "description": forms.Textarea(attrs={"class": "field-textarea", "rows": 4}),
            "resource_type": forms.Select(attrs={"class": "field-input"}),
            "language": forms.Select(attrs={"class": "field-input"}),
            "level": forms.Select(attrs={"class": "field-input"}),
            "topic": forms.TextInput(
                attrs={"class": "field-input", "placeholder": "tanishuv, kelasi zamon..."}
            ),
            "course": forms.Select(attrs={"class": "field-input"}),
            # `ClearableFileInput` emas: u mavjud faylni ko'rsatish uchun
            # `value.url` ni chaqiradi, private storage esa ataylab URL
            # bermaydi (`core/private_storage.py`) va sahifa yiqilardi.
            # Joriy fayl yon paneldagi kartada, ruxsat tekshiradigan havola
            # bilan ko'rsatiladi.
            "file": forms.FileInput(attrs={"class": "field-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        courses = teacher_course_queryset(user) if user is not None else None
        if courses is not None:
            # Manbaning joriy kursi o'qituvchi scope'idan tashqarida bo'lishi
            # mumkin (kutubxona staff uchun umumiy). Uni ro'yxatdan chiqarib
            # tashlasak, boshqa maydonni tahrirlash "noto'g'ri tanlov" xatosi
            # bilan yiqilardi va bog'lanish jim yo'qolardi.
            current = self.instance.course_id
            if current and not courses.filter(pk=current).exists():
                courses = courses.model.objects.filter(
                    models.Q(pk__in=courses.values("pk")) | models.Q(pk=current)
                )
            self.fields["course"].queryset = courses.order_by("title")
        self.fields["course"].empty_label = "Kursga bog'lanmagan"
        limit_mb = LibrarySettings.max_upload_bytes() // (1024 * 1024)
        if self.instance.pk:
            self.fields["file"].required = False
            self.fields["file"].help_text = (
                f"Yangi fayl tanlansa eskisi almashtiriladi va versiya oshadi. "
                f"Chegara: {limit_mb} MB."
            )
        else:
            self.fields["file"].help_text = f"Chegara: {limit_mb} MB."
        if self.instance.pk and not self.is_bound:
            self.fields["tags_text"].initial = tags_as_text(self.instance)

    @property
    def uploaded_file(self):
        """Formada **yangi** fayl kelgan bo'lsa o'shani qaytaradi."""
        value = self.cleaned_data.get("file") if hasattr(self, "cleaned_data") else None
        return value if isinstance(value, UploadedFile) else None

    def clean_file(self):
        value = self.cleaned_data.get("file")
        if isinstance(value, UploadedFile):
            validate_upload(
                value,
                profile="library",
                field_label="Fayl",
                max_bytes=LibrarySettings.max_upload_bytes(),
            )
        return value


class LessonMaterialForm(forms.ModelForm):
    """Biriktirmaning darsga xos sozlamasi (manbaning o'zi o'zgarmaydi)."""

    class Meta:
        model = LessonMaterial
        # `order` ataylab yo'q: tartib bitta «Tartibni saqlash» formasida
        # boshqariladi (`material_reorder`), ya'ni bitta manba.
        fields = [
            "display_title",
            "audience",
            "is_visible",
            "is_downloadable",
            "is_required",
            "available_from",
        ]
        widgets = {
            "display_title": forms.TextInput(
                attrs={"class": "field-input", "placeholder": "Bo'sh bo'lsa material nomi"}
            ),
            "audience": forms.Select(attrs={"class": "field-input"}),
            "available_from": forms.DateTimeInput(
                attrs={"class": "field-input", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["available_from"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S"]
        if self.instance.resource_id and self.instance.resource.is_teacher_only:
            # Manba ustoz uchun belgilangan bo'lsa tanlov ham yopiladi:
            # forma darajasida ko'rsatib, model `clean()` da majburlaymiz.
            self.fields["audience"].choices = [
                (MaterialAudience.TEACHER, MaterialAudience.TEACHER.label)
            ]
            self.fields["audience"].help_text = (
                "Manba «faqat ustoz uchun» — o'quvchiga ochib bo'lmaydi."
            )
