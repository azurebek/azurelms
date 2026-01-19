from django import forms
from .models import LessonProgress


class LessonAssignmentForm(forms.ModelForm):
    class Meta:
        model = LessonProgress
        fields = ["assignment_file", "assignment_text"]
        widgets = {
            "assignment_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "assignment_text": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Vazifa matnini kiriting",
                    "class": "form-control",
                }
            ),
        }
