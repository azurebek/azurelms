from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field


class Plan(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ta'rif nomi (Masalan: Oddiy)")
    #: Kirish huquqi shu kod bo'yicha aniqlanadi, `name` bo'yicha emas.
    #: Ko'rsatiladigan nomni o'zgartirish huquqni jimgina buzmasligi kerak —
    #: `core/entitlements.py` shu kodni o'qiydi.
    code = models.SlugField(
        max_length=40, unique=True, blank=True, default="",
        verbose_name="Kod",
        help_text="Kirish huquqi uchun barqaror identifikator. Nomdan mustaqil.",
    )
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Oylik to'lov (so'm)")
    description = CKEditor5Field(
        verbose_name="Qisqa izoh",
        help_text="Ta'rif haqida qisqacha ma'lumot",
        config_name="default",
    )
    is_popular = models.BooleanField(default=False, verbose_name="Ommabopmi?")
    is_available_for_purchase = models.BooleanField(default=True, verbose_name="Yangi sotuvga ochiq")
    cohort_capacity_limit = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name="Guruhning maksimal sig'imi",
        help_text="Legacy tarifda bo'sh. Delivery chegarasi; konkret guruh kichikroq bo'lishi mumkin.",
    )
    button_text = models.CharField(max_length=50, default="Boshlash", verbose_name="Tugma matni")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")

    #: Terish xatosidan himoya uchun oqilona yuqori chegara (siyosat emas).
    SANE_GROUP_SIZE = 500

    def clean(self):
        super().clean()
        if self.pk:
            old = Plan.objects.filter(pk=self.pk).values("code", "cohort_capacity_limit").first()
            if old and old["code"] and old["code"] != self.code:
                raise ValidationError({"code": "Tarif kodi barqaror. Yangi tarif yarating."})
            was_delivery = old and old["cohort_capacity_limit"] is not None
            now_delivery = self.cohort_capacity_limit is not None
            if old and was_delivery != now_delivery:
                # Sonni o'zgartirish — egasining qarori. Legacy tarifni
                # delivery tarifiga (yoki teskarisi) aylantirish esa boshqa
                # narsa: `validate_plan_cohort` shu farqqa tayanadi va mavjud
                # guruhlar jimgina noto'g'ri turkumga tushib qolardi.
                raise ValidationError({"cohort_capacity_limit": (
                    "Legacy tarifni delivery tarifiga aylantirib bo'lmaydi. Yangi tarif yarating."
                )})
        if self.cohort_capacity_limit is not None and not 1 <= self.cohort_capacity_limit <= self.SANE_GROUP_SIZE:
            # Yuqori chegara siyosat emas, terish xatosidan himoya: `10` o'rniga
            # `1000` yozilsa sotuv sahifasi shuni va'da qilib qo'yardi. Haqiqiy
            # o'quv guruhi bu songa yaqinlashmaydi.
            raise ValidationError({"cohort_capacity_limit": (
                f"Sig'im 1–{self.SANE_GROUP_SIZE} oralig'ida bo'lishi kerak. "
                f"Kattaroq son kerak bo'lsa, avval raqamni tekshiring."
            )})
        if self.price is not None and Decimal(self.price) < 0:
            raise ValidationError({"price": "Narx manfiy bo'lishi mumkin emas."})

    def save(self, *args, **kwargs):
        # Mavjud planlarda kod yo'q; birinchi saqlashda nomdan olinadi va
        # shundan keyin nomga bog'liq bo'lmay qoladi.
        #
        # Nomlar takrorlanishi mumkin (masalan testlarda yoki bir xil nomli
        # arxiv tarif), kod esa unique — shuning uchun bandi bo'lsa raqam
        # qo'shiladi. Aks holda ikkinchi plan saqlanmay qolardi.
        if not self.code:
            from django.utils.text import slugify

            base = slugify(self.name)[:36] or "plan"
            code = base
            suffix = 2
            while Plan.objects.filter(code=code).exclude(pk=self.pk).exists():
                code = f"{base}-{suffix}"
                suffix += 1
            self.code = code
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["order"]
        verbose_name = "Ta'rif"
        verbose_name_plural = "Ta'riflar"

    def __str__(self):
        return f"{self.name} - {self.price} so'm"


class PlanFeature(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="features")
    name = models.CharField(max_length=200, verbose_name="Imkoniyat (Masalan: Barcha darslarga kirish)")
    is_included = models.BooleanField(default=True, verbose_name="Kiritilganmi?")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")

    class Meta:
        ordering = ["order"]
        verbose_name = "Imkoniyat"
        verbose_name_plural = "Imkoniyatlar"

    def __str__(self):
        return self.name


class PromoCampaign(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_PAUSED = "paused"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_ARCHIVED, "Archived"),
    )

    DISCOUNT_PERCENT = "percent"
    DISCOUNT_FIXED = "fixed"
    DISCOUNT_SET_PRICE = "set_price"
    DISCOUNT_TYPE_CHOICES = (
        (DISCOUNT_PERCENT, "Foiz (%)"),
        (DISCOUNT_FIXED, "Fixed summa"),
        (DISCOUNT_SET_PRICE, "Narxni aniq summa qilish"),
    )

    name = models.CharField(max_length=180, verbose_name="Campaign nomi")
    description = models.TextField(blank=True, verbose_name="Qisqa tavsif")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    discount_type = models.CharField(max_length=16, choices=DISCOUNT_TYPE_CHOICES, verbose_name="Chegirma turi")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Chegirma qiymati")
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Minimal checkout summasi",
    )
    max_total_redemptions = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Jami maksimal ishlatish soni",
    )
    max_redemptions_per_user = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Bir user uchun maksimal ishlatish soni",
    )
    applies_to_first_purchase_only = models.BooleanField(
        default=False,
        verbose_name="Faqat birinchi to'lov uchun",
    )
    allow_on_renewals = models.BooleanField(
        default=True,
        verbose_name="Renewal checkoutlarda ham ishlasin",
    )
    allow_stacking = models.BooleanField(
        default=False,
        verbose_name="Boshqa promo bilan birga ishlatish mumkinmi",
        help_text="Hozir checkout bitta promo qabul qiladi; bu flag keyingi kengaytirish uchun saqlanadi.",
    )
    start_at = models.DateTimeField(null=True, blank=True, verbose_name="Boshlanish vaqti")
    end_at = models.DateTimeField(null=True, blank=True, verbose_name="Tugash vaqti")
    applicable_plans = models.ManyToManyField(
        Plan,
        blank=True,
        related_name="promo_campaigns",
        verbose_name="Faqat shu tariflar uchun",
    )
    applicable_courses = models.ManyToManyField(
        "courses.Course",
        blank=True,
        related_name="promo_campaigns",
        verbose_name="Faqat shu kurslar uchun",
    )
    applicable_cohorts = models.ManyToManyField(
        "cohorts.Cohort",
        blank=True,
        related_name="promo_campaigns",
        verbose_name="Faqat shu cohortlar uchun",
    )
    internal_note = models.TextField(blank=True, verbose_name="Ichki izoh")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "name"]
        verbose_name = "Promo campaign"
        verbose_name_plural = "Promo campaignlar"

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.discount_type == self.DISCOUNT_PERCENT and self.discount_value > 100:
            raise ValidationError({"discount_value": "Foizli chegirma 100 dan katta bo'lishi mumkin emas."})
        if self.end_at and self.start_at and self.end_at <= self.start_at:
            raise ValidationError({"end_at": "Tugash vaqti boshlanish vaqtidan keyin bo'lishi kerak."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def is_active_now(self, *, now=None):
        now = now or timezone.now()
        if self.status != self.STATUS_ACTIVE:
            return False
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        return True


class PromoCode(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_DISABLED = "disabled"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_DISABLED, "Disabled"),
        (STATUS_ARCHIVED, "Archived"),
    )

    campaign = models.ForeignKey(
        PromoCampaign,
        on_delete=models.CASCADE,
        related_name="codes",
        verbose_name="Campaign",
    )
    code = models.CharField(max_length=64, verbose_name="Promo kod")
    normalized_code = models.CharField(max_length=64, unique=True, editable=False)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_promo_codes",
        verbose_name="Faqat shu user uchun",
    )
    max_redemptions = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Kod bo'yicha maksimal ishlatish soni",
    )
    valid_from = models.DateTimeField(null=True, blank=True, verbose_name="Kod boshlanish vaqti")
    valid_until = models.DateTimeField(null=True, blank=True, verbose_name="Kod tugash vaqti")
    note = models.TextField(blank=True, verbose_name="Kod izohi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "Promo kod"
        verbose_name_plural = "Promo kodlar"

    def __str__(self):
        return self.code

    @staticmethod
    def normalize_code(raw_code):
        return (raw_code or "").strip().upper()

    def clean(self):
        super().clean()
        if not self.code:
            raise ValidationError({"code": "Promo kod bo'sh bo'lishi mumkin emas."})
        if self.valid_until and self.valid_from and self.valid_until <= self.valid_from:
            raise ValidationError({"valid_until": "Kod tugash vaqti boshlanishidan keyin bo'lishi kerak."})
        normalized = self.normalize_code(self.code)
        conflict = PromoCode.objects.exclude(pk=self.pk).filter(normalized_code=normalized)
        if conflict.exists():
            raise ValidationError({"code": "Shu promokod allaqachon mavjud."})
        self.normalized_code = normalized

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def is_active_now(self, *, now=None):
        now = now or timezone.now()
        if self.status != self.STATUS_ACTIVE:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return self.campaign.is_active_now(now=now)


class PromoRedemption(models.Model):
    STATUS_RESERVED = "reserved"
    STATUS_APPLIED = "applied"
    STATUS_RELEASED = "released"
    STATUS_REJECTED = "rejected"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = (
        (STATUS_RESERVED, "Reserved"),
        (STATUS_APPLIED, "Applied"),
        (STATUS_RELEASED, "Released"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_EXPIRED, "Expired"),
    )
    ACTIVE_USAGE_STATUSES = {STATUS_RESERVED, STATUS_APPLIED}

    KIND_INITIAL = "initial"
    KIND_RENEWAL = "renewal"
    KIND_CHOICES = (
        (KIND_INITIAL, "Initial checkout"),
        (KIND_RENEWAL, "Renewal checkout"),
    )

    promo_code = models.ForeignKey(
        PromoCode,
        on_delete=models.PROTECT,
        related_name="redemptions",
        verbose_name="Promo kod",
    )
    campaign = models.ForeignKey(
        PromoCampaign,
        on_delete=models.PROTECT,
        related_name="redemptions",
        verbose_name="Campaign",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="promo_redemptions",
        verbose_name="Foydalanuvchi",
    )
    enrollment = models.ForeignKey(
        "cohorts.Enrollment",
        on_delete=models.CASCADE,
        related_name="promo_redemptions",
        verbose_name="Enrollment",
    )
    payment_receipt = models.OneToOneField(
        "cohorts.PaymentReceipt",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promo_redemption",
        verbose_name="To'lov cheki",
    )
    checkout_kind = models.CharField(max_length=16, choices=KIND_CHOICES, default=KIND_INITIAL)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_RESERVED)
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Asl summa")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Chegirma summasi")
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Yakuniy summa")
    code_snapshot = models.CharField(max_length=64, verbose_name="Ishlatilgan kod snapshoti")
    campaign_name_snapshot = models.CharField(max_length=180, verbose_name="Campaign snapshoti")
    discount_type_snapshot = models.CharField(max_length=16, choices=PromoCampaign.DISCOUNT_TYPE_CHOICES)
    discount_value_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    status_note = models.TextField(blank=True, verbose_name="Status izohi")
    reserved_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reserved_at", "-id"]
        verbose_name = "Promo redemption"
        verbose_name_plural = "Promo redemptionlar"
        indexes = [
            models.Index(fields=["status", "reserved_at"]),
            models.Index(fields=["student", "status"]),
        ]

    def __str__(self):
        return f"{self.code_snapshot} -> {self.student}"

    def clean(self):
        super().clean()
        if self.promo_code_id and self.campaign_id and self.promo_code.campaign_id != self.campaign_id:
            raise ValidationError({"campaign": "Campaign promo kod bilan mos bo'lishi kerak."})
        if self.enrollment_id and self.student_id and self.enrollment.student_id != self.student_id:
            raise ValidationError({"student": "Redemption student enrollment bilan mos bo'lishi kerak."})
        if self.payment_receipt_id and self.enrollment_id and self.payment_receipt.enrollment_id != self.enrollment_id:
            raise ValidationError({"payment_receipt": "Receipt enrollment bilan mos bo'lishi kerak."})

    def mark_applied(self, *, note=""):
        if self.status == self.STATUS_APPLIED:
            return
        self.status = self.STATUS_APPLIED
        self.applied_at = timezone.now()
        if note:
            self.status_note = note
        self.save(update_fields=["status", "applied_at", "status_note", "updated_at"])

    def release(self, *, status=STATUS_RELEASED, note=""):
        if self.status not in self.ACTIVE_USAGE_STATUSES:
            return
        self.status = status
        self.released_at = timezone.now()
        if note:
            self.status_note = note
        self.save(update_fields=["status", "released_at", "status_note", "updated_at"])

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
