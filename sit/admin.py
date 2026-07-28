from django.contrib import admin

from .models import (
    Announcement,
    KnowledgeArticle,
    University,
    UniversityDocument,
    UniversityFaculty,
    UniversityMedia,
    UniversityPreparationCourse,
    UniversityProgram,
    UniversityRequirement,
    UniversityServiceItem,
)


class UniversityFacultyInline(admin.TabularInline):
    model = UniversityFaculty
    extra = 1
    fields = ("name", "is_active", "order")


class UniversityPreparationCourseInline(admin.TabularInline):
    model = UniversityPreparationCourse
    extra = 0


class UniversityRequirementInline(admin.TabularInline):
    model = UniversityRequirement
    extra = 1


class UniversityDocumentInline(admin.TabularInline):
    model = UniversityDocument
    extra = 1


class UniversityServiceItemInline(admin.TabularInline):
    model = UniversityServiceItem
    extra = 1


class UniversityMediaInline(admin.TabularInline):
    model = UniversityMedia
    extra = 0


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "city",
        "university_type",
        "admission_status",
        "tuition_from",
        "is_featured",
        "is_published",
        "order",
    )
    list_filter = ("is_published", "is_featured", "university_type", "admission_status", "city")
    list_editable = ("is_featured", "is_published", "order")
    search_fields = ("name", "short_name", "city", "description")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            "Asosiy ma'lumot",
            {
                "fields": (
                    ("name", "short_name", "slug"),
                    ("city", "location_detail", "university_type"),
                    "description",
                    ("founded_year", "student_count"),
                    ("official_website", "source_url", "last_verified_on"),
                )
            },
        ),
        (
            "Qabul va kontrakt",
            {
                "fields": (
                    ("admission_status", "admission_deadline", "academic_year"),
                    ("tuition_from", "tuition_currency"),
                    ("application_help_enabled", "application_help_fee"),
                )
            },
        ),
        (
            "Ko'rinish va nashr",
            {
                "fields": (
                    ("cover_theme", "cover_image", "logo_image"),
                    ("is_featured", "is_published", "order"),
                    ("created_at", "updated_at"),
                )
            },
        ),
    )
    inlines = (
        UniversityFacultyInline,
        UniversityPreparationCourseInline,
        UniversityRequirementInline,
        UniversityDocumentInline,
        UniversityServiceItemInline,
        UniversityMediaInline,
    )


class UniversityProgramInline(admin.TabularInline):
    model = UniversityProgram
    extra = 1


@admin.register(UniversityFaculty)
class UniversityFacultyAdmin(admin.ModelAdmin):
    list_display = ("name", "university", "is_active", "order")
    list_filter = ("is_active", "university")
    search_fields = ("name", "university__name", "university__short_name")
    inlines = (UniversityProgramInline,)


@admin.register(UniversityProgram)
class UniversityProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "faculty", "degree_level", "language", "tuition_fee", "is_active", "order")
    list_filter = ("degree_level", "language", "is_active", "faculty__university")
    search_fields = ("name", "faculty__name", "faculty__university__name")
    list_editable = ("is_active", "order")


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "university", "published_on", "is_published", "order")
    list_filter = ("is_published", "category", "published_on")
    search_fields = ("title", "university__name")
    list_editable = ("is_published", "order")
    date_hierarchy = "published_on"


@admin.register(KnowledgeArticle)
class KnowledgeArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_featured", "is_published", "published_on", "order")
    list_filter = ("is_published", "is_featured", "category")
    search_fields = ("title", "excerpt", "body")
    prepopulated_fields = {"slug": ("title",)}
    list_editable = ("is_featured", "is_published", "order")
    readonly_fields = ("created_at", "updated_at")
