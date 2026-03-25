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
