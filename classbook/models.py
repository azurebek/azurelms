from __future__ import annotations

import html

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.private_storage import private_media_storage

from . import grading


class Exercise(models.Model):
    KIND_CHOICES = (
        (grading.KIND_SINGLE_CHOICE, "Bitta javobli tanlov"),
        (grading.KIND_MULTIPLE_CHOICE, "Bir nechta javobli tanlov"),
        (grading.KIND_TRUE_FALSE, "To'g'ri / noto'g'ri"),
        (grading.KIND_SHORT_ANSWER, "Qisqa javob"),
        (grading.KIND_FILL_BLANK, "Bo'sh joyni to'ldirish"),
        (grading.KIND_MATCHING, "Juftliklarni moslashtirish"),
        (grading.KIND_ORDERING, "Tartiblash"),
        (grading.KIND_CATEGORIZATION, "Kategoriyalarga ajratish"),
        (grading.KIND_UNSCRAMBLE, "So'z/gapni yig'ish"),
        (grading.KIND_POLL, "Poll — baholanmaydi"),
    )

    course = models.ForeignKey("courses.Course", on_delete=models.CASCADE, related_name="classbook_exercises")
    lesson = models.ForeignKey(
        "courses.Lesson", on_delete=models.SET_NULL, null=True, blank=True, related_name="classbook_exercises"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_classbook_exercises"
    )
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=32, choices=KIND_CHOICES, db_index=True)
    prompt = models.TextField()
    instructions = models.CharField(max_length=500, blank=True, default="")
    config = models.JSONField(default=dict)
    answer_key = models.JSONField(default=dict)
    explanation = models.TextField(blank=True, default="")
    media = models.FileField(
        upload_to="classbook/exercises/%Y/%m/", storage=private_media_storage, blank=True, null=True
    )
    media_kind = models.CharField(
        max_length=10, choices=(("image", "Rasm"), ("audio", "Audio")), blank=True, default=""
    )
    media_content_type = models.CharField(max_length=120, blank=True, default="")
    time_limit_seconds = models.PositiveSmallIntegerField(
        default=60, validators=[MinValueValidator(5), MaxValueValidator(3600)]
    )
    max_points = models.PositiveSmallIntegerField(default=100, validators=[MinValueValidator(1), MaxValueValidator(1000)])
    speed_bonus_percent = models.PositiveSmallIntegerField(
        default=10, validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    is_active = models.BooleanField(default=True)
    schema_version = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [models.Index(fields=["course", "kind", "is_active"])]
        verbose_name = "Classbook mashqi"
        verbose_name_plural = "Classbook mashqlari"

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.lesson_id and self.course_id and self.lesson.module.course_id != self.course_id:
            raise ValidationError({"lesson": "Dars mashq tanlangan kursga tegishli emas."})
        grading.validate_exercise_payload(self.kind, self.config, self.answer_key)
        if bool(self.media) != bool(self.media_kind):
            raise ValidationError({"media_kind": "Media fayl va uning turi birga ko'rsatiladi."})

    def snapshot(self):
        return {
            "schema_version": self.schema_version,
            "exercise_id": self.id,
            "title": self.title,
            "kind": self.kind,
            "prompt": self.prompt,
            "instructions": self.instructions,
            "config": self.config,
            "answer_key": self.answer_key,
            "explanation": self.explanation,
            "media_kind": self.media_kind,
            "media_name": self.media.name if self.media else "",
            "time_limit_seconds": self.time_limit_seconds,
            "max_points": self.max_points,
            "speed_bonus_percent": self.speed_bonus_percent,
        }


class LessonPlaybook(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_READY = "ready"
    STATUS_CHOICES = ((STATUS_DRAFT, "Qoralama"), (STATUS_READY, "Darsga tayyor"))

    cohort = models.ForeignKey("cohorts.Cohort", on_delete=models.CASCADE, related_name="classbook_playbooks")
    lesson = models.ForeignKey("courses.Lesson", on_delete=models.CASCADE, related_name="classbook_playbooks")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    opening_message = models.TextField(blank=True, default="")
    materials_message = models.TextField(blank=True, default="")
    homework_message = models.TextField(blank=True, default="")
    late_after_minutes = models.PositiveSmallIntegerField(default=15, validators=[MaxValueValidator(180)])
    auto_release_lesson = models.BooleanField(default=True)
    announce_names = models.BooleanField(
        default=False,
        help_text="O'chirilgan holatda guruhga faqat umumiy sonlar yuboriladi.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_classbook_playbooks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["cohort__name", "lesson__module__order", "lesson__order"]
        constraints = [models.UniqueConstraint(fields=["cohort", "lesson"], name="classbook_unique_playbook")]
        verbose_name = "Dars playbook'i"
        verbose_name_plural = "Dars playbook'lari"

    def __str__(self):
        return f"{self.cohort.name} → {self.lesson.title}"

    def clean(self):
        super().clean()
        if self.cohort_id and self.lesson_id and self.cohort.course_id != self.lesson.module.course_id:
            raise ValidationError({"lesson": "Dars cohort kursiga tegishli emas."})
        material_length = len(html.escape(self.opening_message)) + len(html.escape(self.materials_message))
        if material_length > 3500:
            raise ValidationError({
                "materials_message": "Kirish va material matni Telegram limiti uchun qisqaroq bo'lishi kerak."
            })
        if len(html.escape(self.homework_message)) > 3500:
            raise ValidationError({"homework_message": "Uyga vazifa Telegram limiti uchun qisqaroq bo'lishi kerak."})


class PlaybookExercise(models.Model):
    playbook = models.ForeignKey(LessonPlaybook, on_delete=models.CASCADE, related_name="exercise_steps")
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name="playbook_steps")
    order = models.PositiveSmallIntegerField(default=1)
    teacher_note = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["playbook", "order"], name="classbook_unique_playbook_step_order")
        ]

    def __str__(self):
        return f"{self.playbook} · {self.order}. {self.exercise.title}"

    def clean(self):
        super().clean()
        if self.playbook_id and self.exercise_id and self.playbook.cohort.course_id != self.exercise.course_id:
            raise ValidationError({"exercise": "Mashq playbook kursiga tegishli emas."})


class ActivityRun(models.Model):
    STATUS_QUEUED = "queued"
    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_REVEALED = "revealed"
    STATUS_CHOICES = (
        (STATUS_QUEUED, "Navbatda"),
        (STATUS_OPEN, "Ochiq"),
        (STATUS_CLOSED, "Yopilgan"),
        (STATUS_REVEALED, "Natija e'lon qilingan"),
    )

    session = models.ForeignKey(
        "bot.TelegramLessonSession", on_delete=models.CASCADE, related_name="classbook_activities"
    )
    playbook_step = models.ForeignKey(
        PlaybookExercise, on_delete=models.SET_NULL, null=True, blank=True, related_name="runs"
    )
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name="runs")
    order = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True)
    snapshot = models.JSONField(default=dict)
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="opened_classbook_activities"
    )
    opened_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    revealed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["session", "order"], name="classbook_unique_session_activity_order"),
            models.UniqueConstraint(
                fields=["session"], condition=Q(status="open"), name="classbook_one_open_activity_per_session"
            ),
        ]
        indexes = [models.Index(fields=["session", "status", "order"])]

    def __str__(self):
        return f"{self.session} · {self.order}. {self.exercise.title}"

    @property
    def deadline_passed(self):
        return bool(self.closes_at and timezone.now() > self.closes_at)

    @property
    def public_snapshot(self):
        payload = dict(self.snapshot or {})
        payload.pop("answer_key", None)
        if self.status != self.STATUS_REVEALED:
            payload.pop("explanation", None)
        return payload


class StudentResponse(models.Model):
    activity = models.ForeignKey(ActivityRun, on_delete=models.CASCADE, related_name="responses")
    enrollment = models.ForeignKey("cohorts.Enrollment", on_delete=models.CASCADE, related_name="classbook_responses")
    answer = models.JSONField(default=dict)
    score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    accuracy = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    speed_bonus = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_correct = models.BooleanField(default=False)
    grading_details = models.JSONField(default=dict)
    response_ms = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-score", "response_ms", "submitted_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["activity", "enrollment"], name="classbook_one_response_per_activity")
        ]
        indexes = [models.Index(fields=["activity", "-score", "response_ms"])]

    def __str__(self):
        return f"{self.enrollment.student} → {self.activity} ({self.score})"

    @property
    def accuracy_percent(self):
        return self.accuracy * 100


class TelegramGroupDelivery(models.Model):
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
    KIND_ATTENDANCE = "attendance"
    KIND_LINK = "link"
    KIND_TEXT = "text"
    KIND_CHOICES = (
        (KIND_ATTENDANCE, "Davomat tugmasi"),
        (KIND_LINK, "Classbook havolasi"),
        (KIND_TEXT, "Oddiy xabar"),
    )

    session = models.ForeignKey(
        "bot.TelegramLessonSession", on_delete=models.CASCADE, related_name="classbook_group_deliveries"
    )
    activity = models.ForeignKey(
        ActivityRun, on_delete=models.CASCADE, null=True, blank=True, related_name="group_deliveries"
    )
    external_key = models.CharField(max_length=160, unique=True)
    chat_id = models.BigIntegerField(db_index=True)
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default=KIND_TEXT)
    text = models.TextField()
    button_text = models.CharField(max_length=80, blank=True, default="")
    button_path = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=255, blank=True, default="")
    claimed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    claim_token = models.CharField(max_length=32, blank=True, default="")
    telegram_message_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["status", "id"])]
        verbose_name = "Classbook Telegram xabari"
        verbose_name_plural = "Classbook Telegram xabarlari"

    def __str__(self):
        return f"{self.chat_id} · {self.external_key} [{self.status}]"
