from django import forms
from django.contrib.auth import get_user_model

from courses.models import Course, Exam, ExamSection, Lesson, Module


class CourseBackofficeForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "instructor",
            "level",
            "duration",
            "price",
            "cover_mode",
            "gradient_preset",
            "gradient_cover_title",
            "gradient_cover_label",
            "is_active",
            "certificate_requires_all_assignments_approved",
            "certificate_min_lesson_completion_percent",
            "certificate_min_attendance_percent",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "field-input", "placeholder": "Kurs nomi..."}),
            "description": forms.Textarea(attrs={"class": "field-textarea", "rows": 4}),
            "instructor": forms.Select(attrs={"class": "field-input"}),
            "level": forms.Select(attrs={"class": "field-input"}),
            "duration": forms.NumberInput(attrs={"class": "field-input", "min": 1}),
            "price": forms.NumberInput(attrs={"class": "field-input", "min": 0, "step": "1000"}),
            "cover_mode": forms.Select(attrs={"class": "field-input"}),
            "gradient_preset": forms.Select(attrs={"class": "field-input"}),
            "gradient_cover_title": forms.TextInput(attrs={"class": "field-input"}),
            "gradient_cover_label": forms.TextInput(attrs={"class": "field-input"}),
            "certificate_min_lesson_completion_percent": forms.NumberInput(
                attrs={"class": "field-input", "min": 0, "max": 100}
            ),
            "certificate_min_attendance_percent": forms.NumberInput(
                attrs={"class": "field-input", "min": 0, "max": 100}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["instructor"].queryset = User.objects.filter(is_staff=True).order_by(
            "first_name",
            "last_name",
            "username",
        )


class LessonBackofficeForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["title", "module", "video_url", "content", "order", "xp_reward"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "field-input", "id": "lessonTitle"}),
            "module": forms.Select(attrs={"class": "field-input"}),
            "video_url": forms.URLInput(attrs={"class": "field-input", "placeholder": "https://youtube.com/watch?v=..."}),
            "content": forms.Textarea(attrs={"class": "field-textarea", "rows": 8}),
            "order": forms.NumberInput(attrs={"class": "field-input", "min": 0}),
            "xp_reward": forms.NumberInput(attrs={"class": "field-input", "min": 0, "id": "lessonXp"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["module"].queryset = Module.objects.select_related("course").order_by(
            "course__title",
            "order",
            "title",
        )


class ExamBackofficeForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = [
            "title",
            "course",
            "exam_type",
            "weight_percentage",
            "passing_score",
            "max_attempts",
            "prerequisite_exam",
            "requires_all_assignments_approved",
            "minimum_lesson_completion_percent",
            "minimum_attendance_percent",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "field-input"}),
            "course": forms.Select(attrs={"class": "field-input"}),
            "exam_type": forms.Select(attrs={"class": "field-input"}),
            "weight_percentage": forms.NumberInput(attrs={"class": "field-input", "min": 0, "max": 100}),
            "passing_score": forms.NumberInput(attrs={"class": "field-input", "min": 0, "max": 100}),
            "max_attempts": forms.NumberInput(attrs={"class": "field-input", "min": 1}),
            "prerequisite_exam": forms.Select(attrs={"class": "field-input"}),
            "minimum_lesson_completion_percent": forms.NumberInput(
                attrs={"class": "field-input", "min": 0, "max": 100}
            ),
            "minimum_attendance_percent": forms.NumberInput(
                attrs={"class": "field-input", "min": 0, "max": 100}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.order_by("title")
        prerequisite_qs = Exam.objects.select_related("course").order_by("course__title", "title")
        if self.instance and self.instance.pk:
            prerequisite_qs = prerequisite_qs.exclude(pk=self.instance.pk)
        self.fields["prerequisite_exam"].queryset = prerequisite_qs


class ExamSectionBackofficeForm(forms.ModelForm):
    class Meta:
        model = ExamSection
        fields = [
            "title",
            "section_type",
            "instructions",
            "reading_text",
            "media_url",
            "max_score",
            "time_limit_minutes",
            "order",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "field-input"}),
            "section_type": forms.Select(attrs={"class": "field-input"}),
            "instructions": forms.Textarea(attrs={"class": "field-textarea", "rows": 5}),
            "reading_text": forms.Textarea(attrs={"class": "field-textarea", "rows": 5}),
            "media_url": forms.URLInput(attrs={"class": "field-input", "placeholder": "https://..."}),
            "max_score": forms.NumberInput(attrs={"class": "field-input", "min": 0}),
            "time_limit_minutes": forms.NumberInput(attrs={"class": "field-input", "min": 1}),
            "order": forms.NumberInput(attrs={"class": "field-input", "min": 0}),
        }
