from django.db import models
from django.conf import settings
from cohorts.models import Cohort
from courses.models import Course, Lesson
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatRoom(models.Model):
    # Chat xonasi turlari
    ROOM_TYPES = (
        ('group', 'Guruh Chati (Cohort)'),
        ('private', 'Shaxsiy (1:1)'),
        ('ai', 'Azure AI Yordamchisi'),
    )

    room_type = models.CharField(max_length=10, choices=ROOM_TYPES, verbose_name="Chat turi")
    name = models.CharField(max_length=200, blank=True, null=True, help_text="Guruh nomi yoki AI bot nomi")

    # Agar chat guruhga tegishli bo'lsa
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, null=True, blank=True, related_name='group_chats')

    # Chatda kimlar ishtirok etyapti? (1:1 uchun 2 ta odam, AI uchun 1 ta odam)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='chat_rooms')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_room_type_display()} | {self.name or 'Chat'}"

    class Meta:
        verbose_name = "Chat Xonasi"
        verbose_name_plural = "Chat Xonalari"


class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')

    # Xabarni kim yozdi? (Agar AI yozgan bo'lsa, sender bo'sh qolishi mumkin)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    text = models.TextField(verbose_name="Xabar matni")

    is_ai_response = models.BooleanField(default=False, help_text="Bu xabarni AI yozganmi?")

    # SEHRLI MAYDON: O'quvchi qaysi darsda turib savol bergani shu yerda saqlanadi
    context_lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True,
                                       help_text="Kontekst uchun dars")

    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False, verbose_name="O'qildimi?")

    def __str__(self):
        sender_name = self.sender.username if self.sender else "Azure AI"
        return f"{sender_name}: {self.text[:30]}..."

    class Meta:
        ordering = ['created_at']  # Xabarlar doim vaqti bo'yicha ketma-ket chiqadi
        verbose_name = "Xabar"
        verbose_name_plural = "Xabarlar"
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['room', 'created_at']),
        ]


class AILongTermMemory(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='ai_memory')
    learned_facts = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AI Memory for {self.user.username}"


class LessonRAGChunk(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="rag_chunks")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="rag_chunks")
    chunk_index = models.PositiveIntegerField(default=0)
    chunk_text = models.TextField()
    chunk_hash = models.CharField(max_length=64)
    content_hash = models.CharField(max_length=64)
    token_count = models.PositiveIntegerField(default=0)
    embedding = models.JSONField(default=list, blank=True)
    embedding_model = models.CharField(max_length=80, default="gemini-embedding-001")
    embedding_dim = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "RAG Chunk"
        verbose_name_plural = "RAG Chunklar"
        unique_together = ("lesson", "chunk_index", "embedding_model")
        indexes = [
            models.Index(fields=["course", "lesson"]),
            models.Index(fields=["lesson", "embedding_model"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} | {self.lesson.title}"

class AIFeedback(models.Model):
    # AI javoblari uchun feedback (Thumbs up/down)
    RATING_POSITIVE = 1
    RATING_NEGATIVE = -1
    RATING_CHOICES = (
        (RATING_POSITIVE, 'Ijobiy (Thumbs Up)'),
        (RATING_NEGATIVE, 'Salbiy (Thumbs Down)'),
    )

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='feedback_entries')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_feedback_entries',
    )
    rating = models.SmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(blank=True, default="", help_text="Qo'shimcha izoh")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student} -> message {self.message_id} | {self.rating}"

    @property
    def is_positive(self):
        return self.rating == self.RATING_POSITIVE

    class Meta:
        verbose_name = "AI Feedback"
        verbose_name_plural = "AI Feedbacklar"
        unique_together = ("message", "student")
        indexes = [
            models.Index(fields=["rating", "created_at"]),
            models.Index(fields=["student", "created_at"]),
        ]
