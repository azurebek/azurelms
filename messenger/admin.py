from django.contrib import admin
from .models import AIFeedback, ChatRoom, LessonRAGChunk, Message

class MessageInline(admin.TabularInline):
    model = Message
    extra = 1


class AIFeedbackInline(admin.TabularInline):
    model = AIFeedback
    extra = 0
    fields = ("student", "rating", "comment", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at")

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_type', 'created_at')
    list_filter = ('room_type',)
    inlines = [MessageInline] # Xona ichida xabarlarni yozish imkoniyati

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'room', 'is_ai_response', 'context_lesson', 'created_at')
    list_filter = ('is_ai_response', 'room__room_type')
    search_fields = ('text',)
    inlines = [AIFeedbackInline]


@admin.register(LessonRAGChunk)
class LessonRAGChunkAdmin(admin.ModelAdmin):
    list_display = ("id", "course", "lesson", "chunk_index", "embedding_model", "embedding_dim", "updated_at")
    list_filter = ("embedding_model", "course")
    search_fields = ("lesson__title", "course__title", "chunk_text")


@admin.register(AIFeedback)
class AIFeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "rating_badge",
        "room_type",
        "room_name",
        "course_title",
        "message_preview",
        "has_comment",
        "created_at",
    )
    list_filter = ("rating", "message__room__room_type", "created_at")
    search_fields = (
        "student__username",
        "student__first_name",
        "student__last_name",
        "comment",
        "message__text",
        "message__room__name",
    )
    readonly_fields = ("created_at", "updated_at", "message", "student")
    autocomplete_fields = ("message", "student")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "student",
            "message__room__cohort__course",
            "message__context_lesson__module__course",
        )

    @admin.display(description="Baho")
    def rating_badge(self, obj):
        return "Like" if obj.is_positive else "Dislike"

    @admin.display(description="Chat turi")
    def room_type(self, obj):
        return obj.message.room.get_room_type_display()

    @admin.display(description="Chat")
    def room_name(self, obj):
        return obj.message.room.name or "-"

    @admin.display(description="Kurs")
    def course_title(self, obj):
        if obj.message.context_lesson_id:
            return obj.message.context_lesson.module.course.title
        if obj.message.room.cohort_id:
            return obj.message.room.cohort.course.title
        return "-"

    @admin.display(description="AI javobi")
    def message_preview(self, obj):
        return (obj.message.text or "")[:80]

    @admin.display(boolean=True, description="Izoh bor")
    def has_comment(self, obj):
        return bool((obj.comment or "").strip())
