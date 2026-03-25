from django.contrib import admin

from bot.models import TelegramLessonCheckIn, TelegramLessonSession


@admin.register(TelegramLessonSession)
class TelegramLessonSessionAdmin(admin.ModelAdmin):
    list_display = ("cohort", "lesson", "attendance_date", "status", "chat_id", "started_by", "started_at")
    list_filter = ("status", "attendance_date")
    search_fields = ("cohort__name", "lesson__title", "chat_title")
    raw_id_fields = ("cohort", "lesson", "started_by", "closed_by")


@admin.register(TelegramLessonCheckIn)
class TelegramLessonCheckInAdmin(admin.ModelAdmin):
    list_display = ("session", "enrollment", "telegram_user_id", "checked_in_at")
    list_filter = ("checked_in_at",)
    search_fields = ("enrollment__student__username", "telegram_username")
    raw_id_fields = ("session", "enrollment")
