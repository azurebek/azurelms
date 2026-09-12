from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class TelegramLessonSession(models.Model):
    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (STATUS_OPEN, "Ochiq"),
        (STATUS_CLOSED, "Yopilgan"),
        (STATUS_CANCELLED, "Bekor qilingan"),
    )

    cohort = models.ForeignKey("cohorts.Cohort", on_delete=models.CASCADE, related_name="telegram_sessions")
    lesson = models.ForeignKey("courses.Lesson", on_delete=models.CASCADE, related_name="telegram_sessions")
    chat_id = models.BigIntegerField(db_index=True, verbose_name="Telegram chat ID")
    chat_title = models.CharField(max_length=255, blank=True, default="", verbose_name="Telegram chat nomi")
    attendance_date = models.DateField(default=timezone.localdate, db_index=True, verbose_name="Davomat sanasi")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    late_after_minutes = models.PositiveIntegerField(default=15, verbose_name="Kechikish chegarasi")
    attendance_message_id = models.BigIntegerField(blank=True, null=True, verbose_name="Davomat post xabar ID")
    started_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="started_telegram_sessions",
        verbose_name="Boshlagan foydalanuvchi",
    )
    closed_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_telegram_sessions",
        verbose_name="Yopgan foydalanuvchi",
    )
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Boshlangan vaqt")
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name="Yopilgan vaqt")

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Telegram dars sessiyasi"
        verbose_name_plural = "Telegram dars sessiyalari"
        constraints = [
            models.UniqueConstraint(
                fields=["chat_id"],
                condition=Q(status="open"),
                name="unique_open_telegram_session_per_chat",
            ),
        ]

    def __str__(self):
        return f"{self.cohort.name} | {self.lesson.title} | {self.attendance_date}"


class BotGuest(models.Model):
    """Bog'lanmagan (mehmon) Telegram foydalanuvchi holati — onboarding voronkasi.

    AI demo savol-javob limiti shu yerda hisoblanadi. Ro'yxatdan o'tib
    bog'langach bu yozuv shunchaki tarix bo'lib qoladi.
    """

    telegram_id = models.BigIntegerField(unique=True, db_index=True, verbose_name="Telegram user ID")
    telegram_username = models.CharField(max_length=255, blank=True, default="")
    demo_questions_used = models.PositiveIntegerField(default=0, verbose_name="AI demo savollar soni")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bot mehmoni"
        verbose_name_plural = "Bot mehmonlari"

    def __str__(self):
        return f"guest:{self.telegram_id} ({self.demo_questions_used} demo savol)"


class TelegramOutbox(models.Model):
    """Platforma bildirishnomasi → Telegram DM navbati (F4).

    users.Notification yaratilganda signal shu yerga yozadi (recipient'da
    telegram_id bo'lsa); worker (run_bot ichida yoki `manage.py telegram_outbox`)
    rate-limit bilan yuboradi. Sayt jarayoni hech qachon o'zi yubormaydi.
    """

    STATUS_PENDING = "pending"
    STATUS_SENDING = "sending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Kutilmoqda"),
        (STATUS_SENDING, "Yuborilmoqda"),
        (STATUS_SENT, "Yuborildi"),
        (STATUS_FAILED, "Xato"),
    )

    notification = models.OneToOneField(
        "users.Notification", on_delete=models.CASCADE, related_name="telegram_outbox",
    )
    telegram_id = models.BigIntegerField(db_index=True, verbose_name="Qabul qiluvchi Telegram ID")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    # Lease: bir qatorni bir vaqtda faqat bitta worker olishi uchun (A1a).
    # Worker o'lib qolsa qator `sending` da muzlab qolmasin — `claimed_at`
    # eskirganda u yana `pending` ga qaytariladi.
    claimed_at = models.DateTimeField(blank=True, null=True, db_index=True)
    claim_token = models.CharField(max_length=32, blank=True, default="")
    # Qayta urinish rejasi (F10). `next_attempt_at` kelajakda bo'lsa qator
    # claim qilinmaydi — backoff shu bilan amalga oshadi. Ilgari nosoz qator
    # darhol `pending` ga qaytib, keyingi siklda (15s) yana urinardi va uch
    # urinish 45 soniyaga sig'ib ketardi.
    next_attempt_at = models.DateTimeField(blank=True, null=True, db_index=True)
    # Nosozlik turi: `rate_limited` / `permanent` / `transient`. Owner uchun
    # "botni bloklagan" bilan "tarmoq uzildi" bir xil ko'rinmasligi kerak —
    # birinchisi hech qachon tuzalmaydi, ikkinchisi o'zi tuzaladi.
    failure_kind = models.CharField(max_length=16, blank=True, default="")

    class Meta:
        ordering = ["id"]
        verbose_name = "Telegram outbox"
        verbose_name_plural = "Telegram outbox"

    def __str__(self):
        return f"outbox:{self.id} → {self.telegram_id} [{self.status}]"


class BotRuntimeSettings(models.Model):
    """Telegram yetkazish tezligi va qayta urinish siyosati — owner sozlamasi (T0).

    Owner qarori (2026-09-11): operatsion qiymat kodda qotirib qo'yilmaydi.
    Bu qiymatlarning har biri ilgari Python konstantasi edi, ya'ni ularni
    o'zgartirish uchun deploy kerak bo'lardi. Eng aniq misol —
    `send_interval_ms`: PR #101 ning o'zida «jonli darsda hamon 429 ko'rinsa,
    oraliqni oshirish kerak» deb yozilgan edi, ya'ni u isbotlangan knob.

    **Yoqish/o'chirish bu yerda yo'q.** U `core/flags.py` registrida
    (`telegram_outbox_sending`). Bitta narsani ikki DB manbasi boshqarsa ular
    bir-biriga zid bo'lishi mumkin va owner qaysi biri amalda ekanini aniqlay
    olmaydi. Bo'linish: vaqt/limit shu yerda, yoqilgan/o'chirilgan flagda.

    Qiymatlar `resolved()` orqali o'qiladi — u hech qachon xato tashlamaydi va
    chegaradan chiqqan qiymatni kodning xavfsiz oralig'iga qisadi. Sabab: bu
    sozlamani owner jonli dars kunida o'zgartiradi, va bitta noto'g'ri raqam
    butun navbatni to'xtatib qo'ymasligi kerak.
    """

    singleton = models.BooleanField(default=True, unique=True, editable=False)

    dm_batch_size = models.PositiveIntegerField(
        default=25,
        validators=[MinValueValidator(1), MaxValueValidator(200)],
        verbose_name="DM navbati: bir siklda nechta xabar",
        help_text="Shaxsiy xabarlar (bildirishnoma DM) uchun bir sikldagi chegara.",
    )
    group_batch_size = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(200)],
        verbose_name="Guruh navbati: bir siklda nechta xabar",
        help_text=(
            "Classbook guruh xabarlari DM'dan OLDIN olinadi, shuning uchun bu "
            "ham jonli darsdagi tezlikka bevosita ta'sir qiladi."
        ),
    )
    poll_interval_seconds = models.PositiveIntegerField(
        default=15,
        validators=[MinValueValidator(1), MaxValueValidator(600)],
        verbose_name="Sikllar orasidagi kutish (soniya)",
        help_text="Worker navbatni qancha vaqtda bir tekshiradi.",
    )
    lease_seconds = models.PositiveIntegerField(
        default=120,
        validators=[MinValueValidator(10), MaxValueValidator(3600)],
        verbose_name="Lease muddati (soniya)",
        help_text=(
            "Worker xabarni yuborayotganda o'lib qolsa, qator shuncha vaqtdan "
            "keyin yana navbatga qaytadi. Juda qisqa qilinsa bitta xabar ikki "
            "marta ketishi ehtimoli oshadi."
        ),
    )
    send_interval_ms = models.PositiveIntegerField(
        default=50,
        validators=[MaxValueValidator(5000)],
        verbose_name="Yuborishlar orasidagi oraliq (millisekund)",
        help_text=(
            "Telegram turli chatlarga ~30 xabar/sekund beradi. 50 ms ≈ 20/sek. "
            "Jonli darsda 429 ko'rinsa shu qiymatni oshiring. 0 — oraliqsiz "
            "(faqat test/debug uchun)."
        ),
    )
    max_attempts = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        verbose_name="Maksimal urinish soni",
        help_text=(
            "Shundan keyin xabar terminal (dead-letter) bo'ladi. 429 va "
            "noto'g'ri token urinish sarflamaydi."
        ),
    )
    base_backoff_seconds = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(3600)],
        verbose_name="Birinchi kutish (soniya)",
        help_text="Keyingi urinishlarda ikkilanadi: 30 → 60 → 120 → 240.",
    )
    max_backoff_seconds = models.PositiveIntegerField(
        default=900,
        validators=[MinValueValidator(5), MaxValueValidator(86400)],
        verbose_name="Maksimal kutish (soniya)",
        help_text="Kutish shundan oshmaydi.",
    )
    metrics_flush_seconds = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(3600)],
        verbose_name="Kuzatuv yozuvi oralig'i (soniya)",
        help_text=(
            "Bot o'z holatini shuncha vaqtda bir marta yozadi. Kichik qiymat "
            "Control Center'da yangiroq raqam beradi, ammo DB'ga ko'proq "
            "yozadi. Bu qiymat chiroqning eskirish chegarasiga ham ta'sir "
            "qiladi: chegara bu oraliqdan ikki baravar past bo'lib qolmaydi."
        ),
    )
    metrics_window_seconds = models.PositiveIntegerField(
        default=300,
        validators=[MinValueValidator(30), MaxValueValidator(86400)],
        verbose_name="O'lchov oynasi (soniya)",
        help_text=(
            "O'rtacha va p95 shu oynadagi update'lardan hisoblanadi. "
            "Oynadan tashqaridagi o'lchov tashlanadi — aks holda uch soat "
            "oldingi sekinlik hozirgi tezlik bo'lib ko'rinardi."
        ),
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Kim o'zgartirdi",
    )

    class Meta:
        verbose_name = "Bot yetkazish sozlamasi"
        verbose_name_plural = "Bot yetkazish sozlamasi"

    def __str__(self):
        return "Bot yetkazish sozlamasi"

    def clean(self):
        """Maksimal kutish bazadan kichik bo'lsa backoff ma'nosini yo'qotadi."""
        super().clean()
        if self.max_backoff_seconds < self.base_backoff_seconds:
            raise ValidationError(
                {
                    "max_backoff_seconds": (
                        "Maksimal kutish birinchi kutishdan kichik bo'lmasligi kerak."
                    )
                }
            )
        if self.metrics_window_seconds < self.metrics_flush_seconds:
            raise ValidationError(
                {
                    "metrics_window_seconds": (
                        "O'lchov oynasi yozuv oralig'idan qisqa bo'lmasligi kerak, "
                        "aks holda o'lchovlarning bir qismi hech qachon "
                        "hisobga olinmaydi."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def resolved(cls):
        """Amaldagi qiymatlar — hech qachon xato tashlamaydi.

        Sozlama qatori yo'q bo'lsa (migratsiyadan oldin, yangi o'rnatish) yoki
        DB javob bermasa kod defaultlari qaytadi. Worker sozlama jadvali
        sababli to'xtab qolmasligi kerak: `core/runtime_gate.py` dagi fail-fast
        **yetishmayotgan xizmat** uchun, bu esa ixtiyoriy moslash qatlami.
        """
        from bot.runtime_settings import DeliveryPolicy

        try:
            row = cls.objects.filter(pk=1).first()
        except Exception:  # noqa: BLE001 — jadval hali yo'q yoki DB yetib bormadi
            row = None
        return DeliveryPolicy.from_row(row)


class BotBroadcastDraft(models.Model):
    """Admin broadcast qoralamasi (F6).

    /broadcast <matn> → matn shu yerda saqlanadi; nishon/tasdiqlash callback
    tugmalari faqat draft id ko'taradi (callback_data 64 baytga sig'ishi uchun).
    Yuborilgach o'chiriladi — restart holatga ta'sir qilmaydi.
    """

    admin = models.ForeignKey(
        "users.CustomUser", on_delete=models.CASCADE, related_name="bot_broadcast_drafts",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bot broadcast qoralama"
        verbose_name_plural = "Bot broadcast qoralamalar"

    def __str__(self):
        return f"draft:{self.id} ({self.admin_id}): {self.text[:40]}"


class BotPendingAction(models.Model):
    """User'dan keyingi xabar kutilayotgan holat (F9).

    aiogram FSM o'rniga DB — bot restart / webhook ko'p-jarayonligida holat
    yo'qolmaydi. Har userda ko'pi bilan bitta faol holat (unique user).

    kind=assignment → target_id: Assignment.id, keyingi matn/foto javob bo'ladi
    kind=quiz       → target_id: Quiz.id, data: {"index": 0, "answers": {...}}
    """

    KIND_ASSIGNMENT = "assignment"
    KIND_QUIZ = "quiz"
    KIND_CHOICES = (
        (KIND_ASSIGNMENT, "Vazifa javobi"),
        (KIND_QUIZ, "Quiz"),
    )

    user = models.OneToOneField(
        "users.CustomUser", on_delete=models.CASCADE, related_name="bot_pending_action",
    )
    kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    target_id = models.PositiveIntegerField()
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bot kutilayotgan amal"
        verbose_name_plural = "Bot kutilayotgan amallar"

    def __str__(self):
        return f"{self.user_id}: {self.kind}#{self.target_id}"


class TelegramLessonCheckIn(models.Model):
    session = models.ForeignKey(
        TelegramLessonSession,
        on_delete=models.CASCADE,
        related_name="checkins",
        verbose_name="Sessiya",
    )
    enrollment = models.ForeignKey(
        "cohorts.Enrollment",
        on_delete=models.CASCADE,
        related_name="telegram_checkins",
        verbose_name="Enrollment",
    )
    telegram_user_id = models.BigIntegerField(verbose_name="Telegram user ID")
    telegram_username = models.CharField(max_length=255, blank=True, default="", verbose_name="Telegram username")
    checked_in_at = models.DateTimeField(auto_now_add=True, verbose_name="Check-in vaqti")

    class Meta:
        ordering = ["checked_in_at"]
        verbose_name = "Telegram check-in"
        verbose_name_plural = "Telegram check-inlar"
        unique_together = ("session", "enrollment")

    def __str__(self):
        return f"{self.enrollment.student.username} | {self.session.lesson.title}"
