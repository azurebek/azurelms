from django.contrib import admin

from bot.models import (
    BotRuntimeSettings,
    TelegramLessonCheckIn,
    TelegramLessonSession,
)


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


@admin.register(BotRuntimeSettings)
class BotRuntimeSettingsAdmin(admin.ModelAdmin):
    """Faqat o'qish uchun — yozish auditlangan yuzadan boradi.

    Admin orqali tahrirlash operatsion o'zgarishni **izsiz** qoldiradi: sabab,
    tasdiq va `SystemAuditEvent` bo'lmaydi. Aynan shu nuqson `AISettingsAdmin`
    da bor va PR #103 dagi review uni ko'rsatdi — shu xatoni takrorlamaslik
    uchun bu yerda qiymatlar ko'rinadi, o'zgartirish esa
    `/backoffice/control/runtime-settings/` da sabab bilan boradi.
    """

    list_display = ("__str__", "dm_batch_size", "send_interval_ms", "max_attempts", "updated_at")
    readonly_fields = [f.name for f in BotRuntimeSettings._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
