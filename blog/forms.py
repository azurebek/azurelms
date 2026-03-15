from django import forms
from django.utils import timezone

from .models import BlogComment, BlogPost, BlogTag


class BlogPostForm(forms.ModelForm):
    tag_names = forms.CharField(
        required=False,
        help_text="Teglarni vergul bilan ajrating. Masalan: product, mindset, notes",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "strategy, turk tili, founder notes",
            }
        ),
    )

    class Meta:
        model = BlogPost
        fields = [
            "title",
            "cover_image",
            "cover_alt_text",
            "excerpt",
            "featured_quote",
            "body",
            "tag_names",
            "featured",
            "allow_comments",
            "status",
            "published_at",
            "seo_title",
            "meta_description",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Sarlavha"}),
            "cover_image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "cover_alt_text": forms.TextInput(attrs={"class": "form-control", "placeholder": "Cover rasm tavsifi"}),
            "excerpt": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "Qisqa kirish yoki teaser matni"}
            ),
            "featured_quote": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Article ichida highlight bo'ladigan qisqa fikr"}
            ),
            "published_at": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "seo_title": forms.TextInput(attrs={"class": "form-control", "placeholder": "SEO sarlavha"}),
            "meta_description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "placeholder": "Share preview uchun qisqa tavsif"}
            ),
            "featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "allow_comments": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["tag_names"].initial = ", ".join(self.instance.tags.values_list("name", flat=True))
            if self.instance.published_at:
                self.initial["published_at"] = timezone.localtime(self.instance.published_at).strftime("%Y-%m-%dT%H:%M")

    def save(self, commit=True):
        post = super().save(commit=commit)
        if commit:
            self._save_tags(post)
        return post

    def save_m2m(self):
        super().save_m2m()
        if self.instance.pk:
            self._save_tags(self.instance)

    def _save_tags(self, post):
        raw_tags = self.cleaned_data.get("tag_names", "")
        names = []
        for item in raw_tags.split(","):
            name = item.strip()
            if name and name.lower() not in {existing.lower() for existing in names}:
                names.append(name)

        tags = [BlogTag.objects.get_or_create(name=name)[0] for name in names]
        post.tags.set(tags)


class BlogCommentForm(forms.ModelForm):
    class Meta:
        model = BlogComment
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control blog-comment-input",
                    "rows": 4,
                    "placeholder": "Fikringizni yozing...",
                    "maxlength": 2000,
                }
            )
        }
