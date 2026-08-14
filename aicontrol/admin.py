from django.contrib import admin, messages
from django.utils import timezone

from .models import (
    AIPlanPolicy,
    AISettings,
    AISupplyEvent,
    AISupplyState,
    AIUsageResetEvent,
    AIUserAllowance,
)
from .service import apply_reset_event, get_quota_status


@admin.register(AISettings)
class AISettingsAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "enforcement_enabled",
        "supply_enforcement_enabled",
        "supply_daily_request_limit",
        "supply_minute_request_limit",
        "supply_daily_token_limit",
        "guest_demo_enabled",
        "heavy_search_enabled",
        "updated_at",
    )
    readonly_fields = ("updated_at", "updated_by")
    fieldsets = (
        (
            "Foydalanuvchi AI limiti",
            {
                "fields": (
                    "enforcement_enabled",
                    "exempt_staff",
                    "default_5h_token_limit",
                    "default_weekly_token_limit",
                    "default_model",
                    "default_effort",
                )
            },
        ),
        (
            "Global provider supply",
            {
                "fields": (
                    "supply_enforcement_enabled",
                    "supply_daily_request_limit",
                    "supply_minute_request_limit",
                    "supply_daily_token_limit",
                    "supply_default_reservation_tokens",
                    "supply_cooldown_seconds",
                    "guest_demo_enabled",
                    "heavy_search_enabled",
                )
            },
        ),
        ("Audit", {"fields": ("updated_by", "updated_at")}),
    )

    def has_add_permission(self, request):
        # Singleton — faqat bitta qator
        return bool(
            request.user
            and request.user.is_active
            and request.user.is_superuser
            and not AISettings.objects.exists()
        )

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # Project-wide supply switches affect every user and the external
        # provider quota; only the owner account may mutate this singleton.
        return bool(request.user and request.user.is_active and request.user.is_superuser)

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AISupplyEvent)
class AISupplyEventAdmin(admin.ModelAdmin):
    list_display = (
        "reserved_at",
        "call_type",
        "provider",
        "model_name",
        "status",
        "actual_requests",
        "accounted_tokens",
        "error_kind",
    )
    list_filter = ("bucket_date", "call_type", "provider", "status", "error_kind")
    search_fields = ("request_key", "model_name", "user__username", "user__email")
    date_hierarchy = "reserved_at"
    fields = (
        "request_key",
        "bucket_date",
        "call_type",
        "provider",
        "model_name",
        "user",
        "status",
        "reserved_requests",
        "reserved_tokens",
        "actual_requests",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "accounted_requests",
        "accounted_tokens",
        "error_kind",
        "reserved_at",
        "completed_at",
        "updated_at",
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(AISupplyState)
class AISupplyStateAdmin(admin.ModelAdmin):
    list_display = ("__str__", "circuit_status", "circuit_open_until", "opened_at", "updated_at")
    fields = ("singleton", "circuit_status", "circuit_open_until", "opened_at", "updated_at")
    readonly_fields = fields

    @admin.display(description="Circuit")
    def circuit_status(self, obj):
        return (
            "OPEN / COOLDOWN"
            if obj.circuit_open_until and obj.circuit_open_until > timezone.now()
            else "CLOSED"
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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
