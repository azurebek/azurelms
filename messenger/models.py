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


class AIMemoryFact(models.Model):
    CATEGORY_PREFERENCE = "preference"
    CATEGORY_LEARNING_GOAL = "learning_goal"
    CATEGORY_WEAK_TOPIC = "weak_topic"
    CATEGORY_SCHEDULE = "schedule"
    CATEGORY_PROFILE = "profile"
    CATEGORY_DO_NOT_REMEMBER = "do_not_remember"
    CATEGORY_OTHER = "other"
    CATEGORY_CHOICES = (
        (CATEGORY_PREFERENCE, "Preference"),
        (CATEGORY_LEARNING_GOAL, "Learning goal"),
        (CATEGORY_WEAK_TOPIC, "Weak topic"),
        (CATEGORY_SCHEDULE, "Schedule"),
        (CATEGORY_PROFILE, "Profile"),
        (CATEGORY_DO_NOT_REMEMBER, "Do not remember"),
        (CATEGORY_OTHER, "Other"),
    )

    STATUS_ACTIVE = "active"
    STATUS_ARCHIVED = "archived"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_ACTIVE, "Active"),
        (STATUS_ARCHIVED, "Archived"),
        (STATUS_REJECTED, "Rejected"),
    )

    VISIBILITY_USER_VISIBLE = "user_visible"
    VISIBILITY_INTERNAL = "internal"
    VISIBILITY_CHOICES = (
        (VISIBILITY_USER_VISIBLE, "User visible"),
        (VISIBILITY_INTERNAL, "Internal"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_memory_facts")
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    key = models.CharField(max_length=120, blank=True, default="")
    value = models.TextField()
    source_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_memory_facts",
    )
    source_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_memory_facts",
    )
    confidence = models.FloatField(default=0.8)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default=VISIBILITY_USER_VISIBLE)
    fingerprint = models.CharField(max_length=64)
    metadata = models.JSONField(blank=True, default=dict)
    embedding = models.JSONField(default=list, blank=True)
    embedding_model = models.CharField(max_length=80, blank=True, default="")
    embedding_dim = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} | {self.category}: {self.value[:60]}"

    class Meta:
        verbose_name = "AI Memory Fact"
        verbose_name_plural = "AI Memory Facts"
        constraints = [
            models.UniqueConstraint(fields=["user", "fingerprint"], name="unique_ai_memory_fact_fingerprint"),
        ]
        indexes = [
            models.Index(fields=["user", "status", "category"]),
            models.Index(fields=["user", "updated_at"]),
            models.Index(fields=["user", "embedding_model"]),
            models.Index(fields=["fingerprint"]),
        ]


class AIMemoryTrace(models.Model):
    EVENT_RETRIEVED = "retrieved"
    EVENT_SAVED = "saved"
    EVENT_SKIPPED = "skipped"
    EVENT_ARCHIVED = "archived"
    EVENT_CHOICES = (
        (EVENT_RETRIEVED, "Retrieved"),
        (EVENT_SAVED, "Saved"),
        (EVENT_SKIPPED, "Skipped"),
        (EVENT_ARCHIVED, "Archived"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_memory_traces")
    fact = models.ForeignKey(
        AIMemoryFact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trace_events",
    )
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_memory_traces",
    )
    event_type = models.CharField(max_length=24, choices=EVENT_CHOICES)
    reason = models.TextField(blank=True, default="")
    score = models.FloatField(null=True, blank=True)
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} | {self.event_type} | {self.reason[:50]}"

    class Meta:
        verbose_name = "AI Memory Trace"
        verbose_name_plural = "AI Memory Traces"
        indexes = [
            models.Index(fields=["user", "event_type", "created_at"]),
            models.Index(fields=["fact", "created_at"]),
        ]


class AIConversationSummary(models.Model):
    room = models.OneToOneField(ChatRoom, on_delete=models.CASCADE, related_name="ai_conversation_summary")
    summary_text = models.TextField(blank=True, default="")
    covered_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="covered_by_ai_summaries",
    )
    covered_message_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AI summary for room {self.room_id}"

    class Meta:
        verbose_name = "AI Conversation Summary"
        verbose_name_plural = "AI Conversation Summaries"
        indexes = [
            models.Index(fields=["updated_at"]),
        ]


class AIResponseRun(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FALLBACK = "fallback"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FALLBACK, "Fallback"),
        (STATUS_FAILED, "Failed"),
    )

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="ai_response_runs")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_response_runs")
    user_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_response_runs",
    )
    ai_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_generated_runs",
    )
    context_lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True)
    client_message_id = models.CharField(max_length=80, blank=True, default="")
    user_question = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    model_name = models.CharField(max_length=120, blank=True, default="")
    skill_slug = models.CharField(max_length=80, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    duration_ms = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(blank=True, default=dict)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AI run {self.id} | {self.room_id} | {self.status}"

    class Meta:
        verbose_name = "AI Response Run"
        verbose_name_plural = "AI Response Runs"
        indexes = [
            models.Index(fields=["room", "created_at"]),
            models.Index(fields=["student", "status", "created_at"]),
            models.Index(fields=["user_message", "status"]),
        ]


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
