from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Notification, NotificationBroadcast
from .notification_service import send_broadcast


class CustomUserAdmin(UserAdmin):
    # Admin panelda qaysi ustunlar ko'rinib turishi kerak?
    list_display = ('username', 'first_name', 'last_name', 'telegram_id', 'total_xp', 'is_staff')

    # Qidiruv va filtrlar
    search_fields = ('username', 'first_name', 'last_name', 'telegram_id')
    list_filter = ('is_staff', 'is_superuser', 'is_active')

    # Foydalanuvchi profiliga kirganda ko'rinadigan qo'shimcha maydonlar (Fieldsets)
    fieldsets = UserAdmin.fieldsets + (
        ('LMS Ma\'lumotlari', {'fields': ('telegram_id', 'telegram_username', 'phone_number', 'avatar', 'total_xp')}),
    )


admin.site.register(CustomUser, CustomUserAdmin)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "title", "category", "is_read", "created_at")
    list_filter = ("category", "is_read", "created_at")
    search_fields = ("recipient__username", "recipient__email", "message", "title")
    readonly_fields = ("created_at", "read_at")


@admin.register(NotificationBroadcast)
class NotificationBroadcastAdmin(admin.ModelAdmin):
    list_display = ("title", "target_type", "is_sent", "sent_at", "created_by", "created_at")
    list_filter = ("target_type", "is_sent", "created_at")
    search_fields = ("title", "message")
    filter_horizontal = ("recipients", "cohorts")
    readonly_fields = ("is_sent", "sent_at", "created_at", "created_by")

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        if not obj.is_sent:
            count = send_broadcast(obj)
            self.message_user(request, f"Bildirishnoma yuborildi: {count} ta foydalanuvchi.")
