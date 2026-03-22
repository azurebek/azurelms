from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from django.conf import settings
from django.core.exceptions import ValidationError
import uuid
from courses.models import Course
from .utils import generate_certificate_image

class Level(models.Model):
    # Darajalar (Masalan: 1-Daraja: Yangi boshlovchi, 10-Daraja: Poliglot)
    name = models.CharField(max_length=50, verbose_name="Daraja nomi")
    min_xp = models.PositiveIntegerField(verbose_name="Minimal XP (Shu darajaga o'tish uchun)")
    badge_image = models.ImageField(upload_to='levels/', blank=True, null=True, verbose_name="Daraja nishoni (Rasm)")

    class Meta:
        ordering = ['min_xp'] # Doim eng kichik darajadan boshlab tartiblaydi
        verbose_name = "Daraja (Level)"
        verbose_name_plural = "Darajalar"

    def __str__(self):
        return f"{self.name} ({self.min_xp} XP+)"

class Badge(models.Model):
    ICON_SOURCE_UPLOAD = "upload"
    ICON_SOURCE_GOOGLE = "google"
    ICON_SOURCE_CHOICES = (
        (ICON_SOURCE_UPLOAD, "Rasm yuklash"),
        (ICON_SOURCE_GOOGLE, "Google Icon"),
    )

    GOOGLE_STYLE_OUTLINED = "outlined"
    GOOGLE_STYLE_ROUNDED = "rounded"
    GOOGLE_STYLE_SHARP = "sharp"
    GOOGLE_STYLE_CHOICES = (
        (GOOGLE_STYLE_OUTLINED, "Outlined"),
        (GOOGLE_STYLE_ROUNDED, "Rounded"),
        (GOOGLE_STYLE_SHARP, "Sharp"),
    )

    # Yutuqlar (Masalan: "Birinchi qon!", "7 kun qatorasiga dars qildi", "100% test ishladi")
    name = models.CharField(max_length=100, verbose_name="Yutuq nomi")
    description = CKEditor5Field(verbose_name="Ta'rifi (Qanday olinadi?)", config_name='default')
    icon_source = models.CharField(
        max_length=12,
        choices=ICON_SOURCE_CHOICES,
        default=ICON_SOURCE_UPLOAD,
        verbose_name="Ikonka manbasi",
    )
    google_icon_name = models.CharField(
        max_length=80,
        blank=True,
        default="",
        verbose_name="Google icon nomi",
        help_text="Masalan: workspace_premium, military_tech, school.",
    )
    google_icon_style = models.CharField(
        max_length=12,
        choices=GOOGLE_STYLE_CHOICES,
        default=GOOGLE_STYLE_OUTLINED,
        verbose_name="Google icon uslubi",
    )
    icon = models.ImageField(
        upload_to='badges/',
        blank=True,
        null=True,
        verbose_name="Yutuq rasmi (Ikonka)",
    )

    class Meta:
        verbose_name = "Nishon (Badge)"
        verbose_name_plural = "Nishonlar"

    def __str__(self):
        return self.name

    @property
    def uses_google_icon(self):
        return self.icon_source == self.ICON_SOURCE_GOOGLE and bool(self.google_icon_name.strip())

    @property
    def material_symbol_class(self):
        return {
            self.GOOGLE_STYLE_OUTLINED: "material-symbols-outlined",
            self.GOOGLE_STYLE_ROUNDED: "material-symbols-rounded",
            self.GOOGLE_STYLE_SHARP: "material-symbols-sharp",
        }.get(self.google_icon_style, "material-symbols-outlined")

    @property
    def google_icon_slug(self):
        return self.google_icon_name.strip().replace(" ", "_")

    def clean(self):
        super().clean()
        if self.icon_source == self.ICON_SOURCE_GOOGLE:
            if not self.google_icon_name.strip():
                raise ValidationError({"google_icon_name": "Google icon nomini kiriting."})
            self.google_icon_name = self.google_icon_slug
        else:
            if not self.icon:
                raise ValidationError({"icon": "Rasm yuklang yoki ikonka manbasini Google Icon qiling."})

class EarnedBadge(models.Model):
    # Qaysi o'quvchi qaysi yutuqni oldi?
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='earned_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True, verbose_name="Olingan vaqti")

    class Meta:
        verbose_name = "Olingan nishon"
        verbose_name_plural = "Olingan nishonlar"
        unique_together = ('student', 'badge') # Bitta yutuqni bir marta olish mumkin

    def __str__(self):
        return f"{self.student.username} -> {self.badge.name}"


class Certificate(models.Model):
    # Sertifikatlar
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='certificates',
                                verbose_name="O'quvchi")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="Tugatgan kursi")

    # Har bir sertifikatning o'ziga xos takrorlanmas raqami bo'ladi (Masalan: tekshirish uchun)
    certificate_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Sertifikat ID")

    issued_at = models.DateTimeField(auto_now_add=True, verbose_name="Berilgan sana")

    # Agar tayyor PDF yoki rasm yuklasangiz (kelajakda buni avtomat PDF yasaydigan qilishimiz ham mumkin)
    file = models.FileField(upload_to='certificates/', blank=True, null=True,
                            verbose_name="Sertifikat fayli (PDF/Rasm)")

    class Meta:
        verbose_name = "Sertifikat"
        verbose_name_plural = "Sertifikatlar"
        unique_together = ('student', 'course')  # Bitta kurs uchun faqat bitta sertifikat beriladi

    def __str__(self):
        return f"{self.student.username} - {self.course.title} Sertifikati"
