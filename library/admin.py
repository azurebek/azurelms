"""Legacy Django admin ro'yxatlari (faqat `ENABLE_LEGACY_ADMIN` bilan ochiq).

Asosiy ish yuzasi — `/backoffice/library/`. Bu yerdagi ro'yxatlar zaxira
ko'rinish uchun. `LibrarySettings` ataylab **faqat o'qish uchun**: uni
o'zgartirish operatsion qaror va u auditlangan yuzadan (runtime-settings)
boradi — admin faqat `updated_by` ni yozib, izsiz o'zgarish qoldirardi.
"""

from django import forms
from django.contrib import admin
from django.db import models

from .models import LessonMaterial, LibraryResource, LibrarySettings, LibraryTag


@admin.register(LibraryTag)
class LibraryTagAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "created_at")


class LessonMaterialInline(admin.TabularInline):
    model = LessonMaterial
    extra = 0
    fields = ("lesson", "display_title", "order", "audience", "is_visible", "is_downloadable")


@admin.register(LibraryResource)
class LibraryResourceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "resource_type",
        "level",
        "language",
        "file_kind",
        "version",
        "is_teacher_only",
        "is_archived",
        "updated_at",
    )
    list_filter = ("resource_type", "level", "language", "is_archived", "is_teacher_only")
    search_fields = ("title", "description", "topic", "tags__name")
    filter_horizontal = ("tags",)
    # Private storage URL bermaydi, `ClearableFileInput` esa mavjud faylni
    # ko'rsatish uchun aynan `value.url` ni so'raydi — shuning uchun oddiy
    # `FileInput`.
    formfield_overrides = {models.FileField: {"widget": forms.FileInput}}
    readonly_fields = (
        "original_filename",
        "file_kind",
        "file_size",
        "checksum",
        "version",
        "archived_at",
        "created_by",
        "updated_by",
        "created_at",
        "updated_at",
    )
    inlines = [LessonMaterialInline]


@admin.register(LessonMaterial)
class LessonMaterialAdmin(admin.ModelAdmin):
    list_display = ("lesson", "resource", "order", "audience", "is_visible", "is_downloadable")
    list_filter = ("audience", "is_visible", "is_downloadable", "is_required")
    search_fields = ("lesson__title", "resource__title", "display_title")
    autocomplete_fields = ("resource",)


@admin.register(LibrarySettings)
class LibrarySettingsAdmin(admin.ModelAdmin):
    list_display = ("max_upload_mb", "updated_by", "updated_at")
    readonly_fields = ("max_upload_mb", "updated_by", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
