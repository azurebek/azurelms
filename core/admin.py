"""Core admin — operatsion sozlamalar faqat o'qish uchun ko'rinadi."""

from django.contrib import admin

from core.models import OperationalSettings


@admin.register(OperationalSettings)
class OperationalSettingsAdmin(admin.ModelAdmin):
    """Faqat o'qish uchun — yozish auditlangan yuzadan boradi.

    Admin orqali tahrirlash operatsion o'zgarishni **izsiz** qoldiradi: sabab,
    tasdiq va `SystemAuditEvent` bo'lmaydi. Aynan shu nuqson `AISettingsAdmin`
    da bor va PR #103 dagi review uni ko'rsatdi — shu xatoni takrorlamaslik
    uchun bu yerda qiymatlar ko'rinadi, o'zgartirish esa
    `/backoffice/control/runtime-settings/` da sabab bilan boradi.
    """

    list_display = ("__str__", "backup_stale_after_days", "queue_age_amber_minutes", "queue_age_red_minutes", "updated_at")
    readonly_fields = [f.name for f in OperationalSettings._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
