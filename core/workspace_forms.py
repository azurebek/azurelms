"""Small authoring forms reusing the existing canonical validation."""
from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from core.backoffice_forms import CourseBackofficeForm, LessonBackofficeForm
from library.backoffice_forms import LibraryResourceForm


def rich_widget():
    widget = CKEditor5Widget()
    widget.config['toolbar'] = ['heading', '|', 'bold', 'italic', 'link',
                                'bulletedList', 'numberedList', '|', 'undo', 'redo']
    return widget


class WorkspaceCourseForm(CourseBackofficeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].widget = rich_widget()
        self.fields['is_active'].label = 'Katalogda ko‘rinsin'
        self.fields['duration'].label = 'Davomiylik (soat)'
        if not self.instance.pk:
            self.initial.update(is_active=False, duration=1, price=0)


class WorkspaceLessonForm(LessonBackofficeForm):
    def __init__(self, *args, course, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['module'].queryset = self.fields['module'].queryset.filter(course=course)
        self.fields['content'].widget = rich_widget()
        for key, label in {'title': 'Dars nomi', 'module': 'Modul', 'content': 'Dars matni',
                           'video_url': 'Video havolasi', 'order': 'Moduldagi tartib',
                           'xp_reward': 'Dars uchun ball'}.items():
            self.fields[key].label = label


class WorkspaceModuleForm(forms.Form):
    title = forms.CharField(max_length=200, label='Modul nomi')


class WorkspaceUploadForm(LibraryResourceForm):
    def __init__(self, *args, **kwargs):
        # Initialize the canonical form before reducing the visible fields.
        kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for name in list(self.fields):
            if name not in {'title', 'file', 'is_teacher_only'}:
                self.fields.pop(name)
        self.fields['title'].label = 'Material nomi'
        self.fields['is_teacher_only'].label = 'Faqat ustoz uchun'
