from django.db import models
from django.conf import settings
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
    # Yutuqlar (Masalan: "Birinchi qon!", "7 kun qatorasiga dars qildi", "100% test ishladi")
    name = models.CharField(max_length=100, verbose_name="Yutuq nomi")
    description = models.TextField(verbose_name="Ta'rifi (Qanday olinadi?)")
    icon = models.ImageField(upload_to='badges/', verbose_name="Yutuq rasmi (Ikonka)")

    class Meta:
        verbose_name = "Nishon (Badge)"
        verbose_name_plural = "Nishonlar"

    def __str__(self):
        return self.name

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