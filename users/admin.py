from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


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