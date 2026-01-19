from django.db import models
from django.conf import settings
from core.models import TimeStampedModel
from courses.models import Batch, Lesson

class Enrollment(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="enrollments")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("user", "batch")]

    def __str__(self):
        return f"{self.user} -> {self.batch}"

class LessonProgress(TimeStampedModel):
    NOT_SUBMITTED = "NOT_SUBMITTED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ASSIGNMENT_STATUS_CHOICES = [
        (NOT_SUBMITTED, "Not submitted"),
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    ]

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_items")

    is_video_watched = models.BooleanField(default=False)
    quiz_score = models.PositiveIntegerField(default=0)

    assignment_status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS_CHOICES, default=NOT_SUBMITTED)
    assignment_file = models.FileField(upload_to="homeworks/", blank=True, null=True)
    assignment_text = models.TextField(blank=True)
    assignment_admin_feedback = models.TextField(blank=True)

    class Meta:
        unique_together = [("enrollment", "lesson")]

    @property
    def is_completed(self):
        quiz_passed = True
        if self.lesson.quiz_required:
            quiz_passed = self.quiz_score >= self.lesson.quiz_pass_score
        return self.is_video_watched and quiz_passed and self.assignment_status == self.APPROVED

    def __str__(self):
        return f"{self.enrollment} / {self.lesson}"


class AttendanceRecord(TimeStampedModel):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField()
    is_present = models.BooleanField(default=True)
    xp_awarded = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("enrollment", "date")]

    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f"{self.enrollment} / {self.date} ({status})"
