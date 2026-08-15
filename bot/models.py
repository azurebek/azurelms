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

    class Meta:
        ordering = ["id"]
        verbose_name = "Telegram outbox"
        verbose_name_plural = "Telegram outbox"

    def __str__(self):
        return f"outbox:{self.id} → {self.telegram_id} [{self.status}]"


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
