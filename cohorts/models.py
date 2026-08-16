from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.db.models import Q
from django.db import transaction
import datetime
from courses.models import Course, Lesson


ENROLLMENT_STATUS_ACTIVE = "active"
ENROLLMENT_STATUS_PENDING = "pending"
ENROLLMENT_STATUS_EXPIRED = "expired"
ENROLLMENT_STATUS_FROZEN = "frozen"
ENROLLMENT_ACCESS_GRACE_DAYS = 2


def enrollment_grace_limit(*, today=None, grace_days=ENROLLMENT_ACCESS_GRACE_DAYS):
    today = today or timezone.localdate()
    grace_days = ENROLLMENT_ACCESS_GRACE_DAYS if grace_days is None else grace_days
    return today - datetime.timedelta(days=grace_days)


def enrollment_active_access_q(*, today=None, grace_days=ENROLLMENT_ACCESS_GRACE_DAYS, prefix=""):
    deadline_field = f"{prefix}next_payment_deadline"
    return Q(**{f"{prefix}status": ENROLLMENT_STATUS_ACTIVE}) & (
        Q(**{f"{deadline_field}__isnull": True})
        | Q(**{f"{deadline_field}__gte": enrollment_grace_limit(today=today, grace_days=grace_days)})
    )


def enrollment_overdue_expiration_q(*, today=None, grace_days=ENROLLMENT_ACCESS_GRACE_DAYS, prefix=""):
    return Q(
        **{
            f"{prefix}status": ENROLLMENT_STATUS_ACTIVE,
            f"{prefix}next_payment_deadline__lt": enrollment_grace_limit(today=today, grace_days=grace_days),
        }
    )


class EnrollmentQuerySet(models.QuerySet):
    def with_active_access(self, *, today=None, grace_days=ENROLLMENT_ACCESS_GRACE_DAYS):
        return self.filter(enrollment_active_access_q(today=today, grace_days=grace_days))

    def overdue_for_expiration(self, *, today=None, grace_days=ENROLLMENT_ACCESS_GRACE_DAYS):
        return self.filter(enrollment_overdue_expiration_q(today=today, grace_days=grace_days))


class Cohort(models.Model):
    # Guruhlar (Masalan: "Mart A1 - Kechki")
    name = models.CharField(max_length=200, verbose_name="Guruh nomi")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='cohorts')
    start_date = models.DateField(verbose_name="Boshlanish sanasi")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")
    is_checkout_default = models.BooleanField(
        default=False,
        verbose_name="Checkout default cohort",
        help_text="Yangi checkout uchun aynan shu cohort birinchi tanlanadi.",
    )

    # Telegram guruh linki (O'quvchi to'lov qilgach ko'rinadi)
    telegram_group_link = models.URLField(blank=True, null=True, verbose_name="Telegram guruh havolasi")
    telegram_chat_id = models.BigIntegerField(blank=True, null=True, unique=True, verbose_name="Telegram chat ID")
    telegram_chat_title = models.CharField(max_length=255, blank=True, default="", verbose_name="Telegram chat nomi")

    def __str__(self):
        return f"{self.name} ({self.course.title})"

    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"
        constraints = [
            models.UniqueConstraint(
                fields=["course"],
                condition=Q(is_checkout_default=True),
                name="cohorts_one_checkout_default_per_course",
            ),
        ]


class Enrollment(models.Model):
    # O'quvchini guruhga a'zo qilish va to'lov holati
    STATUS_ACTIVE = ENROLLMENT_STATUS_ACTIVE
    STATUS_PENDING = ENROLLMENT_STATUS_PENDING
    STATUS_EXPIRED = ENROLLMENT_STATUS_EXPIRED
    STATUS_FROZEN = ENROLLMENT_STATUS_FROZEN
    ACCESS_GRACE_DAYS = ENROLLMENT_ACCESS_GRACE_DAYS

    STATUS_CHOICES = (
        (STATUS_ACTIVE, 'Faol (To\'lov qilingan)'),
        (STATUS_PENDING, 'To\'lov kutilmoqda'),
        (STATUS_EXPIRED, 'Muddati tugagan (Bloklangan)'),
        (STATUS_FROZEN, 'Muzlatilgan'),
    )
    STATUS_LABELS = dict(STATUS_CHOICES)
    COMPLETION_STATE_IN_PROGRESS = "in_progress"
    COMPLETION_STATE_COMPLETED = "completed"
    COMPLETION_STATE_PROMOTION_READY = "promotion_ready"
    COMPLETION_STATE_CHOICES = (
        (COMPLETION_STATE_IN_PROGRESS, "Davom etmoqda"),
        (COMPLETION_STATE_COMPLETED, "Tugallangan"),
        (COMPLETION_STATE_PROMOTION_READY, "Keyingi bosqichga tayyor"),
    )
    COMPLETION_STATE_LABELS = dict(COMPLETION_STATE_CHOICES)

    objects = EnrollmentQuerySet.as_manager()

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
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="Holati")
    completion_state = models.CharField(
        max_length=20,
        choices=COMPLETION_STATE_CHOICES,
        default=COMPLETION_STATE_IN_PROGRESS,
        verbose_name="Akademik holat",
    )

    joined_at = models.DateTimeField(auto_now_add=True)
    last_payment_date = models.DateField(null=True, blank=True, verbose_name="So'nggi to'lov sanasi")
    next_payment_deadline = models.DateField(null=True, blank=True, help_text="Navbatdagi to'lov oxirgi muddati")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Kurs tugallangan vaqt")
    promotion_ready_at = models.DateTimeField(null=True, blank=True, verbose_name="Keyingi bosqichga tayyor vaqt")

    def __str__(self):
        return f"{self.student.username} -> {self.cohort.name}"

    def has_active_access(self, *, today=None, grace_days=None):
        if self.status != self.STATUS_ACTIVE:
            return False
        if not self.next_payment_deadline:
            return True
        return self.next_payment_deadline >= enrollment_grace_limit(today=today, grace_days=grace_days)

    def get_effective_status(self, *, today=None, grace_days=None):
        if self.status == self.STATUS_ACTIVE and not self.has_active_access(today=today, grace_days=grace_days):
            return self.STATUS_EXPIRED
        return self.status

    def get_effective_status_display(self, *, today=None, grace_days=None):
        return self.STATUS_LABELS.get(
            self.get_effective_status(today=today, grace_days=grace_days),
            self.status,
        )

    def get_completion_state_display_label(self):
        return self.COMPLETION_STATE_LABELS.get(self.completion_state, self.completion_state)

    def clean(self):
        super().clean()
        if not self.student_id or not self.cohort_id or self.status != self.STATUS_ACTIVE:
            return

        course_id = self.cohort.course_id
        if not course_id or not self.has_active_access():
            return

        conflicting = (
            Enrollment.objects.with_active_access()
            .filter(
                student_id=self.student_id,
                cohort__course_id=course_id,
            )
            .exclude(pk=self.pk)
        )
        if conflicting.exists():
            raise ValidationError(
                {
                    "status": "Talabada ushbu kurs uchun allaqachon faol enrollment mavjud.",
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        unique_together = ('student', 'cohort')  # Bir o'quvchi bitta guruhga faqat bir marta a'zo bo'la oladi
        verbose_name = "Obuna (A'zolik)"
        verbose_name_plural = "Obunalar"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['student', 'status']),
            models.Index(fields=['completion_state']),
        ]


class EnrollmentTransition(models.Model):
    KIND_PROMOTION = "promotion"
    KIND_TRANSFER = "transfer"
    KIND_CHOICES = (
        (KIND_PROMOTION, "Promotion"),
        (KIND_TRANSFER, "Transfer"),
    )

    from django.conf import settings

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollment_transitions",
        verbose_name="O'quvchi",
    )
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, verbose_name="Transition turi")
    source_enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="outgoing_transitions",
        verbose_name="Manba enrollment",
    )
    target_enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="incoming_transitions",
        verbose_name="Yangi enrollment",
    )
    source_cohort = models.ForeignKey(
        Cohort,
        on_delete=models.PROTECT,
        related_name="outgoing_transitions",
        verbose_name="Manba cohort",
    )
    target_cohort = models.ForeignKey(
        Cohort,
        on_delete=models.PROTECT,
        related_name="incoming_transitions",
        verbose_name="Maqsad cohort",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_enrollment_transitions",
        verbose_name="Amalni bajargan xodim",
    )
    note = models.TextField(blank=True, verbose_name="Izoh")
    progress_items_moved = models.PositiveIntegerField(default=0, verbose_name="Ko'chirilgan progress soni")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")

    def __str__(self):
        return (
            f"{self.student.username}: {self.source_cohort.name} -> "
            f"{self.target_cohort.name} ({self.kind})"
        )

    class Meta:
        verbose_name = "Enrollment transition"
        verbose_name_plural = "Enrollment transitions"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["student", "created_at"]),
            models.Index(fields=["kind", "created_at"]),
        ]


class PendingReceiptExists(Exception):
    """Bu enrollmentda allaqachon tasdiqlanmagan chek bor.

    Baza cheklovi (`unique_pending_receipt_per_enrollment`) buzilganda
    chiqariladi. Adapterlar (web forma, Telegram bot) buni ushlab, xom
    `IntegrityError` o'rniga odam o'qiydigan xabar ko'rsatadi.
    """


class PaymentReceipt(models.Model):
    # To'lov cheklarini saqlash
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name='receipts',
                                   verbose_name="O'quvchi obunasi")
    
    from core.private_storage import private_media_storage
    from core.utils import validate_file_size, validate_image_extension
    # Private: chek to'lov hujjati. `MEDIA_ROOT` dan tashqarida saqlanadi va
    # faqat `cohorts:receipt_file` view'i orqali beriladi (A0b).
    receipt_image = models.ImageField(
        upload_to='receipts/%Y/%m/',
        verbose_name="Chek rasmi",
        storage=private_media_storage,
        validators=[validate_file_size, validate_image_extension]
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="To'lov summasi")
    base_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Asl summa",
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Chegirma summasi",
    )
    promo_code_snapshot = models.CharField(max_length=64, blank=True, default="", verbose_name="Promokod")
    promo_campaign_snapshot = models.CharField(max_length=180, blank=True, default="", verbose_name="Promo campaign")
    
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

        if self.base_amount is None:
            self.base_amount = self.amount

        with transaction.atomic():
            super().save(*args, **kwargs)

            if is_new_verification:
                from subscriptions.promo_service import apply_redemption_for_verified_receipt

                apply_redemption_for_verified_receipt(receipt=self)
                enrollment = self.enrollment
                enrollment.status = Enrollment.STATUS_ACTIVE
                enrollment.last_payment_date = timezone.localdate()
                if self.period_end:
                     enrollment.next_payment_deadline = self.period_end
                else:
                     enrollment.next_payment_deadline = timezone.localdate() + datetime.timedelta(days=30)
                enrollment.save()

    def delete(self, *args, **kwargs):
        if not self.is_verified:
            try:
                self.promo_redemption
            except ObjectDoesNotExist:
                pass
            else:
                from subscriptions.promo_service import release_redemption_for_receipt

                release_redemption_for_receipt(
                    receipt=self,
                    reason="Pending receipt deleted",
                )
        return super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "To'lov cheki"
        verbose_name_plural = "To'lov cheklari"
        constraints = [
            # Bitta enrollmentda bir vaqtda faqat bitta tasdiqlanmagan chek.
            #
            # Kafolat ataylab bazada, kodda emas: web ham, bot ham chek
            # yaratishdan oldin "pending chek bormi?" deb o'qib, keyin
            # yozardi — orada qulf yo'q edi. Ikki marta bosilgan tugma yoki
            # ikkita parallel yuborish ikkala tekshiruvdan ham o'tib ketardi.
            # SQLite'da `select_for_update()` no-op bo'lgani uchun qulf bilan
            # tuzatish lokalda umuman ishlamasdi.
            #
            # Tasdiqlangan cheklar cheklanmaydi: har oylik to'lov yangi yozuv.
            models.UniqueConstraint(
                fields=["enrollment"],
                condition=models.Q(is_verified=False),
                name="unique_pending_receipt_per_enrollment",
            ),
        ]


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
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['enrollment', 'date']),
        ]
