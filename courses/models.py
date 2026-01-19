from django.db import models
from core.models import TimeStampedModel

class Course(TimeStampedModel):
    title = models.CharField(max_length=200)
    level = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.title

class Module(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=1)
    exam_weight = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.course} / {self.title}"

class Lesson(TimeStampedModel):
    YOUTUBE_EMBED = "YOUTUBE"
    TELEGRAM_LINK = "TELEGRAM"
    VIDEO_SOURCE_CHOICES = [
        (YOUTUBE_EMBED, "YouTube Embed"),
        (TELEGRAM_LINK, "Telegram Link"),
    ]

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=1)
    video_source = models.CharField(max_length=20, choices=VIDEO_SOURCE_CHOICES, default=YOUTUBE_EMBED)
    video_id = models.CharField(max_length=255, blank=True)

    homework_description = models.TextField(blank=True)  # keyin CKEditor5Field qilamiz
    notes_html = models.TextField(blank=True)
    quiz_required = models.BooleanField(default=False)
    quiz_pass_score = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.module} / {self.title}"

class Batch(TimeStampedModel):
    ENROLLING = "enrolling"
    ACTIVE = "active"
    CLOSED = "closed"
    STATUS_CHOICES = [
        (ENROLLING, "Enrolling"),
        (ACTIVE, "Active"),
        (CLOSED, "Closed"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="batches")
    title = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ENROLLING)
    start_date = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.title or f"{self.course.title} batch"
