from django.contrib import admin
from .models import ChatRoom, Message

class MessageInline(admin.TabularInline):
    model = Message
    extra = 1

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