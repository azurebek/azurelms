from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.functional import cached_property
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


def cohort_occupied_seat_q(*, prefix="members__"):
    """Joyni band qiladigan a'zolik (`delivery_service.occupied_members` bilan bir xil)."""
    return Q(**{f"{prefix}status__in": (ENROLLMENT_STATUS_ACTIVE, ENROLLMENT_STATUS_EXPIRED)})


class CohortQuerySet(models.QuerySet):
    def with_seat_metrics(self, *, today=None):
        """Joy ko'rsatkichlarini bitta so'rovda oldindan hisoblaydi.

        Ular xossalar sifatida ham mavjud, lekin ro'yxat sahifasida har bir
        qator o'z so'rovini yugurtirardi va guruhlar soni ortgan sari sahifa
        sekinlashardi. Ta'rif takrorlanmaydi: shu yerda ham
        `enrollment_active_access_q` ishlatiladi, faqat `members__` prefiksi
        bilan.
        """
        occupied = cohort_occupied_seat_q()
        stale = occupied & ~enrollment_active_access_q(today=today, prefix="members__")
        return self.annotate(
            occupied_seat_count=models.Count("members", filter=occupied, distinct=True),
            stale_seat_count=models.Count("members", filter=stale, distinct=True),
            oldest_stale_deadline=models.Min("members__next_payment_deadline", filter=stale),
        )


class Cohort(models.Model):
    # Guruhlar (Masalan: "Mart A1 - Kechki")
    name = models.CharField(max_length=200, verbose_name="Guruh nomi")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='cohorts')
    plan = models.ForeignKey(
        "subscriptions.Plan", on_delete=models.PROTECT, null=True, blank=True,
        related_name="delivery_cohorts", verbose_name="Guruh tarifi",
    )
    capacity = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Guruh sig'imi")
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

    objects = CohortQuerySet.as_manager()

    def __str__(self):
        return f"{self.name} ({self.course.title})"

    def clean(self):
        super().clean()
        if self.plan_id:
            from subscriptions.models import Plan
            limit = Plan.objects.get(pk=self.plan_id).cohort_capacity_limit
            if limit is None:
                raise ValidationError({"plan": "Delivery chegarasi bor tarifni tanlang."})
            if self.capacity is None:
                self.capacity = limit
            from subscriptions.models import Plan as PlanModel
            if not 1 <= self.capacity <= PlanModel.SANE_GROUP_SIZE:
                # Tarif standarti bilan bir xil terish-xatosi chegarasi:
                # `10` o'rniga `1000` yozilsa checkout shuni e'lon qilardi.
                raise ValidationError({"capacity": (
                    f"Sig'im 1–{PlanModel.SANE_GROUP_SIZE} oralig'ida bo'lishi kerak. "
                    f"Kattaroq son kerak bo'lsa, avval raqamni tekshiring."
                )})
            # Tarifdagi son — shu formatning **standarti**, qattiq shift emas.
            # Egasi bitta guruhga istisno qila olishi kerak (masalan oxirgi
            # bitta o'quvchini qabul qilish). Tasodif emasligi uchun forma
            # sabab va tasdiq so'raydi, qaror auditga tushadi, katalogda esa
            # standartdan oshgani ko'rinib turadi.
        elif self.capacity is not None:
            raise ValidationError({"plan": "Sig'im uchun guruh tarifi tanlanishi kerak."})
        if self.pk:
            old = Cohort.objects.filter(pk=self.pk).first()
            if old and self.members.exists() and (old.plan_id != self.plan_id or old.course_id != self.course_id):
                raise ValidationError("A'zolari bor guruhning kursi/tarifi o'zgarmaydi. Yangi guruh yarating.")
            if self.capacity is not None:
                from .delivery_service import occupied_seats
                if occupied_seats(self) > self.capacity:
                    raise ValidationError({"capacity": "Sig'im band joylar sonidan kam bo'lishi mumkin emas."})

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.course_id:
                Course.objects.select_for_update().get(pk=self.course_id)
            if self.pk:
                Cohort.objects.select_for_update().filter(pk=self.pk).first()
            self.clean()
            return super().save(*args, **kwargs)

    @property
    def occupied_seats(self):
        # `with_seat_metrics()` bilan olingan bo'lsa qayta so'ramaydi.
        if (annotated := getattr(self, "occupied_seat_count", None)) is not None:
            return annotated
        from .delivery_service import occupied_seats
        return occupied_seats(self)

    @property
    def is_full(self):
        return self.capacity is not None and self.occupied_seats >= self.capacity

    @property
    def seats_above_tier_standard(self):
        """Tarif standartidan qancha ko'p joy ochilgani — istisno ko'rinib tursin."""
        if self.capacity is None or self.plan_id is None:
            return 0
        standard = self.plan.cohort_capacity_limit
        if standard is None:
            return 0
        return max(self.capacity - standard, 0)

    @property
    def stale_seats(self):
        """Kirishi ochiq bo'lmagan a'zolar ushlab turgan joylar soni."""
        if (annotated := getattr(self, "stale_seat_count", None)) is not None:
            return annotated
        return len(self._stale_deadlines)

    @property
    def longest_lapse_days(self):
        """Eng uzoq to'lamay turgan a'zoning kunlari (bo'lmasa `None`).

        Owner \"Guruh to'ldi\" ni ko'rganda, joyni bir kun kechikkan
        o'quvchi ushlab turibdimi yoki yarim yil oldin ketgan odammi —
        shu raqam ajratib beradi.
        """
        if hasattr(self, "oldest_stale_deadline"):
            oldest = self.oldest_stale_deadline
        else:
            deadlines = [value for value in self._stale_deadlines if value is not None]
            oldest = min(deadlines) if deadlines else None
        if oldest is None:
            return None
        return (timezone.localdate() - oldest).days

    @cached_property
    def _stale_deadlines(self):
        """Annotatsiyasiz holat uchun: bitta so'rov ikkala ko'rsatkichga yetadi."""
        from .delivery_service import stale_members
        return list(stale_members(self).values_list("next_payment_deadline", flat=True))

    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"
        constraints = [
            models.UniqueConstraint(
                fields=["course"],
                condition=Q(is_checkout_default=True, plan__isnull=True),
                name="cohorts_one_checkout_default_per_course",
            ),
            models.UniqueConstraint(
                fields=["course", "plan"], condition=Q(is_checkout_default=True, plan__isnull=False),
                name="cohorts_one_default_per_course_plan",
            ),
            models.CheckConstraint(
                condition=Q(plan__isnull=True, capacity__isnull=True) | Q(plan__isnull=False, capacity__gte=1, capacity__isnull=False),
                name="cohorts_delivery_capacity_pair",
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
    # Niyat faol tarif emas: quota/entitlement `active_plan()`ni o'qiydi.
    pending_plan = models.ForeignKey(
        "subscriptions.Plan", on_delete=models.PROTECT, null=True, blank=True,
        related_name="pending_enrollments", verbose_name="Tasdiq kutilayotgan tarif",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, verbose_name="Holati")
    completion_state = models.CharField(
        max_length=20,
        choices=COMPLETION_STATE_CHOICES,
        default=COMPLETION_STATE_IN_PROGRESS,
        verbose_name="Akademik holat",
    )

    joined_at = models.DateTimeField(auto_now_add=True)
    # Foydalanuvchi aynan shu enrollment uchun to'lovni boshlagan payt.
    # Telegram'da chek rasmi alohida xabar bo'lib keladi va o'zi bilan hech
    # qanday kurs ma'lumotini olib kelmaydi — nishonni shu maydon aniqlaydi.
    # Usiz bot "eng oxirgi qo'shilgan enrollment" deb taxmin qilardi va ikkita
    # kursi bor o'quvchining puli noto'g'ri kursga yozilardi.
    checkout_started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Checkout boshlangan payt",
    )
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

    def active_plan(self, *, today=None):
        """Bugun kuchda bo'lgan tarif.

        `plan` — tez o'qish uchun denormalizatsiya; haqiqat esa tasdiqlangan
        chekda, chunki har bir chek o'zi to'lagan davrni olib yuradi.
        Yangilash to'lovi joriy muddat tugaganidan boshlanadi, shuning uchun
        kelasi oy uchun oldindan to'langan tarif **o'sha davr boshlangandagina**
        kuchga kiradi. Buning uchun cron kerak emas — vaqt o'zi hal qiladi.
        """
        if not self.pk:
            return self.plan
        receipt = (
            self.receipts.filter(
                is_verified=True, plan__isnull=False, period_start__lte=today or timezone.localdate()
            )
            .select_related("plan")
            .order_by("-period_start", "-id")
            .first()
        )
        return receipt.plan if receipt else self.plan

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
        if self.cohort_id:
            from .delivery_service import validate_plan_cohort, validate_seat
            cohort = self.cohort
            for plan in (self.plan, self.pending_plan):
                if plan is not None:
                    validate_plan_cohort(plan=plan, cohort=cohort)
            if self.status in (self.STATUS_ACTIVE, self.STATUS_EXPIRED):
                validate_plan_cohort(plan=self.plan, cohort=cohort)
                validate_seat(cohort=cohort, enrollment=self)
            elif self._state.adding:
                validate_seat(cohort=cohort)
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
        from .delivery_service import lock_cohorts
        with transaction.atomic():
            if self.cohort_id:
                self.cohort = lock_cohorts(self.cohort_id)[self.cohort_id]
            if self.pk:
                old_cohort = Enrollment.objects.filter(pk=self.pk).values_list("cohort_id", flat=True).first()
                if old_cohort is not None and old_cohort != self.cohort_id:
                    raise ValidationError("Guruhni almashtirish uchun transfer oqimidan foydalaning.")
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
    plan = models.ForeignKey(
        "subscriptions.Plan", on_delete=models.PROTECT, null=True, blank=True,
        related_name="payment_receipts", verbose_name="Sotib olinayotgan tarif",
    )
    plan_code_snapshot = models.CharField(max_length=40, blank=True, default="", editable=False)
    plan_name_snapshot = models.CharField(max_length=100, blank=True, default="", editable=False)
    plan_price_snapshot = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, editable=False,
    )
    KIND_PERIOD = "period"
    KIND_DIFFERENCE = "difference"
    KIND_CHOICES = (
        (KIND_PERIOD, "Davr uchun to'lov"),
        (KIND_DIFFERENCE, "Tarif farqi"),
    )
    #: Farq to'lovi davrni uzaytirmaydi va tarifni o'zgartirmaydi — o'quvchi
    #: allaqachon to'lagan davr ichida yangi tarifga o'tgan, bu esa faqat
    #: ustiga qo'shiladigan summa.
    kind = models.CharField(
        max_length=12, choices=KIND_CHOICES, default=KIND_PERIOD,
        editable=False, verbose_name="To'lov turi",
    )
    plan_snapshot_source = models.CharField(
        max_length=12, default="legacy", editable=False,
        choices=(("checkout", "Checkout vaqtida"), ("legacy", "Tarixiy yozuv")),
    )
    
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

    # Hisob-faktura bir marta yoziladi. Nom/narx yoki faol enrollment
    # o'zgarsa ham tarix o'zgarmaydi. QuerySet.update kabi low-level amallar
    # uchun emas; barcha qo'llab-quvvatlangan write yo'llari shu guarddan o'tadi.
    BILLING_FIELDS = (
        "enrollment", "kind", "plan", "plan_code_snapshot", "plan_name_snapshot",
        "plan_price_snapshot", "plan_snapshot_source", "amount", "base_amount",
        "discount_amount", "promo_code_snapshot", "promo_campaign_snapshot",
        "period_start", "period_end",
    )

    @property
    def plan_label(self):
        return self.plan_name_snapshot or "Tarif qayd etilmagan"

    def granted_deadline(self, *, access_was_open, today=None):
        """Tasdiqlashdan keyingi haqiqiy muddat.

        Davr chek yuborilgan kuni hisoblanadi, tasdiqlash esa qo'lda — owner
        bank o'tkazmasini bir necha soatdan bir necha kungacha keyin
        ko'radi. Kirishi yopiq turgan o'quvchi (birinchi xarid yoki muddati
        o'tgan obuna) shu kunlarni **yo'qotardi**: 30 kunlik pulga 27 kun.

        Shuning uchun kirishi yopiq bo'lgan holatda to'langan davr uzunligi
        kirish ochilgan kundan sanaladi. Kirishi ochiq turgan o'quvchi
        (yangilash yoki grace ichidagi) hech narsa yo'qotmagan — unda
        chekdagi davr oxiri o'z holicha qoladi, ya'ni kechikish sovg'aga
        aylanmaydi.

        Hisob-faktura o'zgarmaydi: chekdagi davr — kelishilgan taklif,
        `next_payment_deadline` esa haqiqatda berilgan xizmat.
        """
        today = today or timezone.localdate()
        date_field = self._meta.get_field("period_start")
        start = date_field.to_python(self.period_start)
        end = self._meta.get_field("period_end").to_python(self.period_end)
        if end is None:
            return today + datetime.timedelta(days=30)
        if access_was_open or start is None or start >= today:
            return end
        return today + (end - start)

    def plan_takes_effect_now(self, *, today=None):
        """Faol tarifni faqat davri boshlangan chek almashtiradi.

        Tasdiqlash paytida almashtirilsa, kelasi oyga oldindan to'langan
        qimmatroq tarif bugundan ishlay boshlardi: 30 kunlik pulga 40 kunlik
        AI kvotasi va o'qituvchi vaqti. Arzonroq tarifga o'tishda esa aksi —
        o'quvchi allaqachon to'lagan kunlarini yo'qotardi.

        Davri boshlanmagan chek `Enrollment.plan`ga tegmaydi;
        `Enrollment.active_plan()` uni o'z vaqtida kuchga kiritadi.
        """
        # `to_python`: DateField qiymatni saqlangunicha turga keltirmaydi,
        # ya'ni `period_start` shu paytda hali matn bo'lishi mumkin.
        period_start = self._meta.get_field("period_start").to_python(self.period_start)
        if period_start is None:
            return True
        return period_start <= (today or timezone.localdate())

    def save(self, *args, **kwargs):
        if kwargs.get("update_fields") is not None and not kwargs["update_fields"]:
            return
        with transaction.atomic():
            # Barcha checkout/decision yozuvlarida bir xil lock tartibi:
            # course -> cohort -> enrollment -> receipt. SQLite IMMEDIATE / PG row lock.
            from .delivery_service import lock_enrollment, validate_plan_cohort, validate_seat
            enrollment = lock_enrollment(self.enrollment_id)
            old = None
            if not self._state.adding:
                old = PaymentReceipt.objects.select_for_update().get(pk=self.pk)
                for name in self.BILLING_FIELDS:
                    field = self._meta.get_field(name)
                    current = field.to_python(field.value_from_object(self))
                    previous = field.to_python(field.value_from_object(old))
                    if current != previous:
                        raise ValidationError({name: "Chek tarixi o'zgartirilmaydi. Yangi chek yarating."})
                if old.is_verified and not self.is_verified:
                    raise ValidationError("Tasdiqlangan chekni qayta pending qilish mumkin emas.")
            else:
                from subscriptions.models import Plan

                plan_id = self.plan_id or enrollment.pending_plan_id or enrollment.plan_id
                if plan_id:
                    self.plan = Plan.objects.get(pk=plan_id)
                    self.plan_code_snapshot = self.plan.code
                    self.plan_name_snapshot = self.plan.name
                    self.plan_price_snapshot = self.plan.price
                    self.plan_snapshot_source = "checkout"
                if self.base_amount is None:
                    self.base_amount = self.amount
                from subscriptions.catalog import validate_purchase_plan
                if self.plan_id:
                    validate_purchase_plan(plan=self.plan, enrollment=enrollment)
                    validate_plan_cohort(plan=self.plan, cohort=enrollment.cohort)

            # update_fields is_verifiedni yozmasa side-effect ham bo'lmaydi.
            writes_verification = kwargs.get("update_fields") is None or "is_verified" in kwargs["update_fields"]
            newly_verified = writes_verification and self.is_verified and (old is None or not old.is_verified)
            if newly_verified and self.kind == self.KIND_PERIOD:
                validate_plan_cohort(plan=self.plan, cohort=enrollment.cohort)
                validate_seat(cohort=enrollment.cohort, enrollment=enrollment)
            super().save(*args, **kwargs)
            if newly_verified and self.kind == self.KIND_DIFFERENCE:
                # Farq to'lovi a'zolikka tegmaydi: davr ham, tarif ham
                # o'zgarmaydi. U faqat allaqachon amalga oshgan tarif
                # o'zgarishining pul tomonini yopadi.
                return
            if newly_verified:
                from subscriptions.promo_service import apply_redemption_for_verified_receipt

                apply_redemption_for_verified_receipt(receipt=self)
                had_access = enrollment.has_active_access()
                enrollment.status = Enrollment.STATUS_ACTIVE
                enrollment.last_payment_date = timezone.localdate()
                enrollment.next_payment_deadline = self.granted_deadline(
                    access_was_open=had_access
                )
                fields = ["status", "last_payment_date", "next_payment_deadline"]
                if self.plan_id and self.plan_takes_effect_now():
                    # Chek tanlagan tarif; keyinroq yozilgan niyat emas.
                    enrollment.plan_id = self.plan_id
                    fields.append("plan")
                enrollment.pending_plan = None
                enrollment.checkout_started_at = None
                fields += ["pending_plan", "checkout_started_at"]
                enrollment.save(update_fields=fields)

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            from .delivery_service import lock_enrollment
            enrollment = lock_enrollment(self.enrollment_id)
            current = PaymentReceipt.objects.select_for_update().get(pk=self.pk)
            if current.is_verified:
                raise ValidationError("Tasdiqlangan to'lov tarixini o'chirish mumkin emas.")
            from subscriptions.promo_service import release_redemption_for_receipt

            release_redemption_for_receipt(receipt=current, reason="Pending receipt deleted")
            enrollment.pending_plan = None
            enrollment.checkout_started_at = None
            enrollment.save(update_fields=["pending_plan", "checkout_started_at"])
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
                fields=["enrollment", "kind"],
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
