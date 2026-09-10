from django import forms
from django.core.exceptions import ValidationError

from core.upload_validation import validate_upload
from courses.models import Lesson

from .grading import author_definition, parse_author_definition
from .models import Exercise, LessonPlaybook


HELP_BY_KIND = {
    "single_choice": "Har qator — variant. To'g'ri bittasini * bilan boshlang.",
    "multiple_choice": "Har qator — variant. Barcha to'g'ri variantlarni * bilan boshlang.",
    "true_false": "Faqat `ha` yoki `yo'q` yozing.",
    "short_answer": "Har qator — qabul qilinadigan javob varianti.",
    "fill_blank": "Har qator — qabul qilinadigan javob varianti.",
    "matching": "Har qator `chap = o'ng` ko'rinishida.",
    "ordering": "Elementlarni to'g'ri tartibda, har birini yangi qatorga yozing.",
    "categorization": "Har qator `Kategoriya: element, element` ko'rinishida.",
    "unscramble": "So'z yoki bo'laklarni to'g'ri tartibda, har birini yangi qatorga yozing.",
    "poll": "Har qator — bitta variant. * ishlatmang.",
}


class ExerciseForm(forms.ModelForm):
    definition = forms.CharField(
        label="Variantlar va javob kaliti",
        widget=forms.Textarea(attrs={"rows": 9, "spellcheck": "false"}),
        help_text="Mashq turiga qarab pastdagi ko'rsatma o'zgaradi.",
    )

    class Meta:
        model = Exercise
        fields = [
            "course", "lesson", "title", "kind", "prompt", "instructions", "definition",
            "explanation", "media", "media_kind", "time_limit_seconds", "max_points", "speed_bonus_percent",
        ]
        widgets = {
            "prompt": forms.Textarea(attrs={"rows": 4}),
            "instructions": forms.TextInput(),
            "explanation": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.teacher = teacher
        from core.access import teacher_course_queryset

        courses = teacher_course_queryset(teacher) if teacher else self.fields["course"].queryset.none()
        self.fields["course"].queryset = courses.order_by("title")
        self.fields["lesson"].queryset = Lesson.objects.filter(module__course__in=courses).select_related("module")
        self.fields["lesson"].required = False
        self.fields["media_kind"].required = False
        self.fields["media"].required = False
        self.fields["kind"].widget.attrs["data-exercise-kind"] = ""
        self.fields["definition"].widget.attrs["data-exercise-definition"] = ""
        if self.instance and self.instance.pk:
            self.fields["definition"].initial = author_definition(
                self.instance.kind, self.instance.config, self.instance.answer_key
            )

    def clean_media(self):
        upload = self.cleaned_data.get("media")
        if upload and (hasattr(upload, "temporary_file_path") or getattr(upload, "content_type", None)):
            requested = self.data.get("media_kind") or self.cleaned_data.get("media_kind")
            profile = "audio" if requested == "audio" else "image"
            validate_upload(upload, profile=profile, field_label="Mashq media fayli")
        return upload

    def clean(self):
        cleaned = super().clean()
        course = cleaned.get("course")
        lesson = cleaned.get("lesson")
        if course and lesson and lesson.module.course_id != course.id:
            self.add_error("lesson", "Dars tanlangan kursga tegishli emas.")
        kind = cleaned.get("kind")
        definition = cleaned.get("definition")
        if kind and definition:
            try:
                cleaned["parsed_definition"] = parse_author_definition(kind, definition)
            except ValidationError as exc:
                self.add_error("definition", exc)
        return cleaned

    def save(self, commit=True):
        exercise = super().save(commit=False)
        parsed = self.cleaned_data.get("parsed_definition")
        if parsed:
            exercise.config, exercise.answer_key = parsed
        upload = self.cleaned_data.get("media")
        if upload and getattr(upload, "content_type", None):
            exercise.media_content_type = upload.content_type[:120]
        if not exercise.media:
            exercise.media_kind = ""
            exercise.media_content_type = ""
        if commit:
            exercise.full_clean()
            exercise.save()
        return exercise


class LessonPlaybookForm(forms.ModelForm):
    class Meta:
        model = LessonPlaybook
        fields = [
            "status", "opening_message", "materials_message", "homework_message",
            "late_after_minutes", "auto_release_lesson", "announce_names",
        ]
        widgets = {
            "opening_message": forms.Textarea(attrs={"rows": 3}),
            "materials_message": forms.Textarea(attrs={"rows": 4}),
            "homework_message": forms.Textarea(attrs={"rows": 4}),
        }
