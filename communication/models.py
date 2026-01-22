from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from courses.models import Batch

class ChatRoom(TimeStampedModel):
    GROUP = "GROUP"
    DIRECT = "DIRECT"
    BOT = "BOT"
    TYPE_CHOICES = [(GROUP, "Group"), (DIRECT, "Direct"), (BOT, "Bot")]

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="chat_rooms", null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=GROUP)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="chat_rooms", blank=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.type} room"

    def display_name_for(self, user):
        if self.type == self.GROUP:
            return self.batch.title if self.batch and self.batch.title else "Guruh chat"
        if self.type == self.DIRECT:
            other = self.participants.exclude(id=user.id).first()
            return getattr(other, "display_name", None) or (other.email if other else "Direct chat")
        if self.type == self.BOT:
            return "@azure Assistant"
        return "Chat"

class Message(TimeStampedModel):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    mentions_bot = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.mentions_bot = "@azure" in (self.content or "").lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sender} -> {self.room}"
