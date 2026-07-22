from django import forms

from frontend.models import SiteSettings


class BrandSettingsForm(forms.ModelForm):
    MAX_IMAGE_BYTES = 5 * 1024 * 1024
    IMAGE_FIELDS = ("logo_image", "logo_dark_image", "logo_mark_image", "favicon_image")

    change_reason = forms.CharField(
        label="O'zgartirish sababi",
        max_length=240,
        help_text="Audit tarixida saqlanadi. Masalan: yangi kurs brendi tasdiqlandi.",
        widget=forms.Textarea(attrs={"rows": 3, "class": "brand-input"}),
    )
    confirm_change = forms.BooleanField(
        label="Barcha logo yuzalari yangilanishini tasdiqlayman",
        required=True,
    )

    class Meta:
        model = SiteSettings
        fields = (
            "brand_name",
            "brand_tagline",
            "logo_mark_text",
            "logo_image",
            "logo_dark_image",
            "logo_mark_image",
            "favicon_image",
        )
        widgets = {
            "brand_name": forms.TextInput(attrs={"class": "brand-input"}),
            "brand_tagline": forms.TextInput(attrs={"class": "brand-input"}),
            "logo_mark_text": forms.TextInput(attrs={"class": "brand-input", "maxlength": 8}),
            "logo_image": forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
            "logo_dark_image": forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
            "logo_mark_image": forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
            "favicon_image": forms.ClearableFileInput(attrs={"accept": "image/png,image/jpeg,image/webp"}),
        }

    @property
    def changed_brand_fields(self):
        return [name for name in self.changed_data if name in self._meta.fields]

    def clean(self):
        cleaned_data = super().clean()
        for field_name in self.IMAGE_FIELDS:
            uploaded_file = self.files.get(field_name)
            if uploaded_file and uploaded_file.size > self.MAX_IMAGE_BYTES:
                self.add_error(field_name, "Rasm hajmi 5 MB dan oshmasligi kerak.")
        return cleaned_data
