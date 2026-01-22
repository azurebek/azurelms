from django.contrib import admin
from django.utils.html import format_html
from users.models import Profile
from .models import AttendanceRecord, Enrollment, LessonProgress


@admin.action(description="Approve & give XP (20)")
def approve_assignments(modeladmin, request, queryset):
    updated = queryset.update(assignment_status=LessonProgress.APPROVED)
    for progress in queryset.select_related("enrollment__user"):
        profile, _ = Profile.objects.get_or_create(user=progress.enrollment.user)
        profile.xp_points = (profile.xp_points or 0) + 20
        profile.save(update_fields=["xp_points"])
    modeladmin.message_user(request, f"{updated} ta vazifa qabul qilindi va XP berildi.")


@admin.action(description="Reject & comment")
def reject_assignments(modeladmin, request, queryset):
    updated = queryset.update(assignment_status=LessonProgress.REJECTED)
    modeladmin.message_user(request, f"{updated} ta vazifa rad etildi.")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = (
        "lesson",
        "enrollment",
        "assignment_status",
        "assignment_file_link",
        "is_video_watched",
        "quiz_score",
    )
    list_filter = ("assignment_status", "lesson__module__course")
    search_fields = ("lesson__title", "enrollment__user__email")
    actions = [approve_assignments, reject_assignments]

    @admin.display(description="File")
    def assignment_file_link(self, obj):
        if obj.assignment_file:
            return format_html('<a href="{}" target="_blank">Download</a>', obj.assignment_file.url)
        return "-"


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("user", "batch", "is_active")
    list_filter = ("is_active", "batch__course")
    search_fields = ("user__email", "batch__title")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "date", "is_present", "xp_awarded")
    list_filter = ("date", "is_present", "enrollment__batch")
    search_fields = ("enrollment__user__email",)
    date_hierarchy = "date"
    ordering = ("-date",)

    @admin.action(description="Mark present & add XP (10)")
    def mark_present(self, request, queryset):
        updated = queryset.update(is_present=True, xp_awarded=10)
        for record in queryset.select_related("enrollment__user"):
            profile, _ = Profile.objects.get_or_create(user=record.enrollment.user)
            profile.xp_points = (profile.xp_points or 0) + 10
            profile.save(update_fields=["xp_points"])
        self.message_user(request, f"{updated} ta davomat present qilindi.")

    actions = ["mark_present"]
