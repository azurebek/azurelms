from django.db import models
from django.conf import settings
from courses.models import Course, Lesson


class Cohort(models.Model):
    # Guruhlar (Masalan: "Mart A1 - Kechki")
    name = models.CharField(max_length=200, verbose_name="Guruh nomi")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='cohorts')
    start_date = models.DateField(verbose_name="Boshlanish sanasi")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")

    # Telegram guruh linki (O'quvchi to'lov qilgach ko'rinadi)
    telegram_group_link = models.URLField(blank=True, null=True, verbose_name="Telegram guruh havolasi")

    def __str__(self):
        return f"{self.name} ({self.course.title})"

    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"


class Enrollment(models.Model):
    # O'quvchini guruhga a'zo qilish va to'lov holati
    STATUS_CHOICES = (
        ('active', 'Faol (To\'lov qilingan)'),
        ('pending', 'To\'lov kutilmoqda'),
        ('expired', 'Muddati tugagan (Bloklangan)'),
        ('frozen', 'Muzlatilgan'),
    )

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='enrollments',
                                verbose_name="O'quvchi")
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='members', verbose_name="Guruh")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="Holati")

    joined_at = models.DateTimeField(auto_now_add=True)
    last_payment_date = models.DateField(null=True, blank=True, verbose_name="So'nggi to'lov sanasi")
    next_payment_deadline = models.DateField(null=True, blank=True, help_text="Navbatdagi to'lov oxirgi muddati")

    def __str__(self):
        return f"{self.student.username} -> {self.cohort.name}"

    class Meta:
        unique_together = ('student', 'cohort')  # Bir o'quvchi bitta guruhga faqat bir marta a'zo bo'la oladi
        verbose_name = "Obuna (A'zolik)"
        verbose_name_plural = "Obunalar"


class PaymentReceipt(models.Model):
    # To'lov cheklarini saqlash
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='receipts',
                                   verbose_name="O'quvchi obunasi")
    receipt_image = models.ImageField(upload_to='receipts/%Y/%m/', verbose_name="Chek rasmi")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="To'lov summasi")
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False, verbose_name="Tasdiqlandi")

    def __str__(self):
        return f"Chek: {self.enrollment.student.username} - {self.amount} UZS"

    def save(self, *args, **kwargs):
        # Agar to'lov cheki admin tomonidan tasdiqlansa, avtomatik ravishda obunani FAOL holatiga o'tkazamiz
        super().save(*args, **kwargs)
        if self.is_verified and self.enrollment.status != 'active':
            self.enrollment.status = 'active'
            self.enrollment.save()

    class Meta:
        verbose_name = "To'lov cheki"
        verbose_name_plural = "To'lov cheklari"


class Attendance(models.Model):
    # Davomat (Bot orqali avtomat to'ldiriladi)
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, verbose_name="O'quvchi")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, verbose_name="Dars")
    date = models.DateField(auto_now_add=True)
    is_present = models.BooleanField(default=True, verbose_name="Qatnashdi")

    def __str__(self):
        return f"{self.enrollment.student.username} - {self.lesson.title}"

    class Meta:
        verbose_name = "Davomat"
        verbose_name_plural = "Davomatlar"