from django.db import models
from django.conf import settings
from django.utils import timezone
import datetime
from courses.models import Course, Lesson


class Cohort(models.Model):
    # Guruhlar (Masalan: "Mart A1 - Kechki")
    name = models.CharField(max_length=200, verbose_name="Guruh nomi")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='cohorts')
    start_date = models.DateField(verbose_name="Boshlanish sanasi")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")

    # Telegram guruh linki (O'quvchi to'lov qilgach ko'rinadi)
    telegram_group_link = models.URLField(blank=True, null=True, verbose_name="Telegram guruh havolasi")
    telegram_chat_id = models.BigIntegerField(blank=True, null=True, unique=True, verbose_name="Telegram chat ID")
    telegram_chat_title = models.CharField(max_length=255, blank=True, default="", verbose_name="Telegram chat nomi")

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
    plan = models.ForeignKey(
        "subscriptions.Plan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrollments",
        verbose_name="Tarif",
    )
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
    
    from core.utils import validate_file_size, validate_image_extension
    receipt_image = models.ImageField(
        upload_to='receipts/%Y/%m/', 
        verbose_name="Chek rasmi",
        validators=[validate_file_size, validate_image_extension]
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="To'lov summasi")
    
    # Qaysi oy (interval) uchun to'lov qilinayotgani
    period_start = models.DateField(null=True, blank=True, verbose_name="To'lov davri boshlanishi")
    period_end = models.DateField(null=True, blank=True, verbose_name="To'lov davri tugashi")
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False, verbose_name="Tasdiqlandi")

    def __str__(self):
        return f"Chek: {self.enrollment.student.username} - {self.amount} UZS"

    def save(self, *args, **kwargs):
        is_new_verification = False
        if self.pk:
            old_receipt = PaymentReceipt.objects.get(pk=self.pk)
            if not old_receipt.is_verified and self.is_verified:
                is_new_verification = True
        elif self.is_verified:
            is_new_verification = True
            
        super().save(*args, **kwargs)
        
        if is_new_verification:
            enrollment = self.enrollment
            enrollment.status = 'active'
            enrollment.last_payment_date = timezone.localdate()
            if self.period_end:
                 enrollment.next_payment_deadline = self.period_end
            else:
                 enrollment.next_payment_deadline = timezone.localdate() + datetime.timedelta(days=30)
            enrollment.save()

    class Meta:
        verbose_name = "To'lov cheki"
        verbose_name_plural = "To'lov cheklari"


class Attendance(models.Model):
    # Davomat (manual yoki integratsiya orqali to'ldiriladi)
    STATUS_PRESENT = 'present'
    STATUS_ABSENT = 'absent'
    STATUS_PARTIAL = 'partial'
    STATUS_CHOICES = (
        (STATUS_PRESENT, "Keldi"),
        (STATUS_ABSENT, "Kelmadi"),
        (STATUS_PARTIAL, "Qisman kirdi"),
    )

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, verbose_name="O'quvchi")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, verbose_name="Dars")
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PRESENT, verbose_name="Davomat holati")
    xp_awarded = models.PositiveIntegerField(default=0, verbose_name="Berilgan XP")
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendance_records',
        verbose_name="Belgilagan xodim",
    )
    marked_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.enrollment.student.username} - {self.lesson.title} - {self.get_status_display()}"

    @property
    def is_present(self):
        return self.status in {self.STATUS_PRESENT, self.STATUS_PARTIAL}

    class Meta:
        verbose_name = "Davomat"
        verbose_name_plural = "Davomatlar"
        unique_together = ('enrollment', 'lesson', 'date')
