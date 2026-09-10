from django.contrib import admin

from .models import (
    ActivityRun,
    Exercise,
    LessonPlaybook,
    PlaybookExercise,
    StudentResponse,
    TelegramGroupDelivery,
)


class PlaybookExerciseInline(admin.TabularInline):
    model = PlaybookExercise
    extra = 0
    ordering = ("order",)


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "kind", "time_limit_seconds", "max_points", "is_active", "updated_at")
    list_filter = ("kind", "is_active", "course")
    search_fields = ("title", "prompt")
    raw_id_fields = ("lesson", "created_by")


@admin.register(LessonPlaybook)
class LessonPlaybookAdmin(admin.ModelAdmin):
    list_display = ("cohort", "lesson", "status", "late_after_minutes", "auto_release_lesson", "updated_at")
    list_filter = ("status", "auto_release_lesson", "cohort")
    raw_id_fields = ("cohort", "lesson", "created_by")
    inlines = (PlaybookExerciseInline,)


@admin.register(ActivityRun)
class ActivityRunAdmin(admin.ModelAdmin):
    list_display = ("session", "order", "exercise", "status", "opened_at", "closed_at")
    list_filter = ("status",)
    raw_id_fields = ("session", "exercise", "playbook_step", "opened_by")


@admin.register(StudentResponse)
class StudentResponseAdmin(admin.ModelAdmin):
    list_display = ("activity", "enrollment", "score", "max_score", "is_correct", "response_ms", "submitted_at")
    list_filter = ("is_correct", "submitted_at")
    raw_id_fields = ("activity", "enrollment")
    readonly_fields = ("answer", "score", "max_score", "accuracy", "speed_bonus", "grading_details", "response_ms")


@admin.register(TelegramGroupDelivery)
class TelegramGroupDeliveryAdmin(admin.ModelAdmin):
    list_display = ("external_key", "chat_id", "kind", "status", "attempts", "created_at", "sent_at")
    list_filter = ("kind", "status")
    search_fields = ("external_key", "text")
    readonly_fields = ("claim_token", "claimed_at", "telegram_message_id", "created_at", "sent_at")
