from django.contrib import admin
from .models import Batch, Course, Lesson, Module


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "level")
    search_fields = ("title", "level")


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order", "exam_weight")
    list_filter = ("course",)
    search_fields = ("title", "course__title")
    ordering = ("course", "order")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "order", "video_source", "quiz_required")
    list_filter = ("video_source", "module__course")
    search_fields = ("title", "module__title", "module__course__title")
    ordering = ("module", "order")


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "status", "start_date", "price")
    list_filter = ("status", "course")
    search_fields = ("title", "course__title")
