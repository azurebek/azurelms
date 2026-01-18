from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser, Profile


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    ordering = ("email",)
    list_display = ("email", "is_staff", "is_superuser", "is_active", "last_login")
    search_fields = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "goal", "level", "xp_points", "streak_days", "is_onboarded")
    search_fields = ("user__email", "display_name")
    list_filter = ("goal", "level", "is_onboarded")
