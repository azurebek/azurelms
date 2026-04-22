import uuid
from dataclasses import dataclass

from django.urls import reverse
from django.utils import timezone

from cohorts.models import Enrollment
from users.notification_service import create_notification

from .models import Certificate, ExamAttempt
from .policy_service import check_certificate_policy


@dataclass
class CourseCompletionSnapshot:
    has_visa: bool = False
    has_final: bool = False
    visa_score: float = 0
    final_score: float = 0
    visa_weight: int = 0
    final_weight: int = 0

    @property
    def is_completed(self):
        return self.has_visa and self.has_final

    @property
    def final_grade(self):
        total_weight = self.visa_weight + self.final_weight
        if total_weight > 0:
            return int(
                (self.visa_score * self.visa_weight + self.final_score * self.final_weight)
                / total_weight
            )
        return int((self.visa_score + self.final_score) / 2)


def build_course_completion_snapshot(*, student, course):
    snapshot = CourseCompletionSnapshot()
    passing_attempts = (
        ExamAttempt.objects.filter(
            student=student,
            exam__course=course,
            passed=True,
            is_reviewed=True,
        )
        .select_related("exam")
        .order_by("exam__exam_type", "-attempt_number", "-id")
    )

    for attempt in passing_attempts:
        if attempt.exam.exam_type == "visa" and not snapshot.has_visa:
            snapshot.has_visa = True
            snapshot.visa_score = float(attempt.score)
            snapshot.visa_weight = attempt.exam.weight_percentage
        elif attempt.exam.exam_type == "final" and not snapshot.has_final:
            snapshot.has_final = True
            snapshot.final_score = float(attempt.score)
            snapshot.final_weight = attempt.exam.weight_percentage
    return snapshot


def _mark_latest_enrollment_promotion_ready(*, student, course):
    enrollment = (
        Enrollment.objects.filter(student=student, cohort__course=course)
        .select_related("cohort")
        .order_by("-joined_at", "-id")
        .first()
    )
    if not enrollment:
        return None

    now = timezone.now()
    update_fields = []
    if enrollment.completion_state != Enrollment.COMPLETION_STATE_PROMOTION_READY:
        enrollment.completion_state = Enrollment.COMPLETION_STATE_PROMOTION_READY
        update_fields.append("completion_state")
    if enrollment.completed_at is None:
        enrollment.completed_at = now
        update_fields.append("completed_at")
    if enrollment.promotion_ready_at is None:
        enrollment.promotion_ready_at = now
        update_fields.append("promotion_ready_at")
    if update_fields:
        enrollment.save(update_fields=update_fields)
    return enrollment


def evaluate_course_completion(*, student, course):
    snapshot = build_course_completion_snapshot(student=student, course=course)
    if not snapshot.is_completed:
        return None, False, None

    policy_result = check_certificate_policy(student=student, course=course)
    if not policy_result.is_allowed:
        return None, False, None

    existing_certificate = Certificate.objects.filter(student=student, course=course).first()
    certificate_id = (
        existing_certificate.certificate_id
        if existing_certificate
        else f"AZ-{course.id}-{student.id}-{uuid.uuid4().hex[:6].upper()}"
    )
    certificate, created = Certificate.objects.update_or_create(
        student=student,
        course=course,
        defaults={
            "final_score": snapshot.final_grade,
            "certificate_id": certificate_id,
        },
    )
    if created:
        create_notification(
            recipient=student,
            title="Sertifikat tayyor",
            message=(
                f"{course.title} kursi bo'yicha sertifikatingiz tayyor bo'ldi. "
                "Uni ko'rishingiz yoki yuklab olishingiz mumkin."
            ),
            icon="award",
            url=reverse("certificate_detail", kwargs={"certificate_id": certificate.certificate_id}),
            external_key=f"certificate-issued-{certificate.id}",
        )

    enrollment = _mark_latest_enrollment_promotion_ready(student=student, course=course)
    return certificate, created, enrollment
