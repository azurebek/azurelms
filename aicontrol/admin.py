from django.contrib import admin, messages
from django.utils import timezone

from .models import AISettings, AIPlanPolicy, AIUserAllowance, AIUsageResetEvent
from .service import apply_reset_event, get_quota_status


@admin.register(AISettings)
class AISettingsAdmin(admin.ModelAdmin):
    list_display = ("__str__", "enforcement_enabled", "default_5h_token_limit", "default_weekly_token_limit", "updated_at")
    readonly_fields = ("updated_at",)

    def has_add_permission(self, request):
        # Singleton — faqat bitta qator
        return not AISettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AIPlanPolicy)
class AIPlanPolicyAdmin(admin.ModelAdmin):
    list_display = ("plan", "token_limit_5h", "token_limit_weekly", "is_active", "updated_at")
    list_filter = ("is_active",)


@admin.register(AIUserAllowance)
class AIUserAllowanceAdmin(admin.ModelAdmin):
    list_display = ("user", "usage_summary", "is_blocked", "override_5h_token_limit", "override_weekly_token_limit", "updated_at")
    list_filter = ("is_blocked",)
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    readonly_fields = ("usage_summary", "updated_at")
    actions = ("reset_5h", "reset_weekly", "unblock")

    @admin.display(description="Joriy usage (5h / hafta)")
    def usage_summary(self, obj):
        status = get_quota_status(obj.user)
        if status.reason in {"exempt", "disabled"}:
            return f"({status.reason})"
        return f"{status.used_5h:,}/{status.limit_5h:,}  ·  {status.used_weekly:,}/{status.limit_weekly:,}"

    @admin.action(description="5 soatlik usage'ni reset qilish")
    def reset_5h(self, request, queryset):
        updated = queryset.update(reset_5h_at=timezone.now())
        self.message_user(request, f"{updated} foydalanuvchining 5 soatlik usage'i reset qilindi.")

    @admin.action(description="Haftalik usage'ni reset qilish")
    def reset_weekly(self, request, queryset):
        updated = queryset.update(reset_weekly_at=timezone.now())
        self.message_user(request, f"{updated} foydalanuvchining haftalik usage'i reset qilindi.")

    @admin.action(description="Blokdan chiqarish")
    def unblock(self, request, queryset):
        updated = queryset.update(is_blocked=False)
        self.message_user(request, f"{updated} foydalanuvchi blokdan chiqarildi.")


@admin.register(AIUsageResetEvent)
class AIUsageResetEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "scope", "window", "reason", "affected_count", "created_by")
    list_filter = ("kind", "scope", "window")
    readonly_fields = ("affected_count", "created_by", "created_at")

    def save_model(self, request, obj, form, change):
        creating = obj.pk is None
        if creating:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        if creating:
            # Yaratilgan zahoti qo'llanadi (bayram/event reseti)
            count = apply_reset_event(obj)
            self.message_user(
                request,
                f"{obj.get_kind_display()} qo'llandi — {count} foydalanuvchiga ta'sir qildi.",
                level=messages.SUCCESS,
            )
