from django.db import transaction
from django.utils import timezone

from .policy_service import check_exam_entry_policy
from .models import ExamAttempt


class ExamAttemptStartBlocked(Exception):
    def __init__(self, message, *, code):
        super().__init__(message)
        self.code = code


def get_latest_exam_attempt(*, student, exam):
    return (
        ExamAttempt.objects.filter(student=student, exam=exam)
        .order_by("-attempt_number", "-id")
        .first()
    )


def get_latest_exam_attempt_for_exam_id(*, student, exam_id):
    return (
        ExamAttempt.objects.filter(student=student, exam_id=exam_id)
        .order_by("-attempt_number", "-id")
        .first()
    )


def get_in_progress_exam_attempt(*, student, exam_id):
    return (
        ExamAttempt.objects.filter(student=student, exam_id=exam_id, is_completed=False)
        .order_by("-attempt_number", "-id")
        .first()
    )


def expire_attempt_if_time_limit_reached(attempt, *, now=None):
    if not attempt or attempt.is_completed:
        return False
    if not attempt.is_time_limit_exceeded(now=now):
        return False
    attempt.submit_for_review(submitted_at=now or timezone.now())
    return True


def start_exam_attempt(*, student, exam):
    policy_result = check_exam_entry_policy(student=student, exam=exam)
    if not policy_result.is_allowed:
        raise ExamAttemptStartBlocked(policy_result.message, code=policy_result.code or "exam_policy")

    now = timezone.now()
    latest_attempt = get_latest_exam_attempt(student=student, exam=exam)
    if latest_attempt:
        if expire_attempt_if_time_limit_reached(latest_attempt, now=now):
            raise ExamAttemptStartBlocked(
                "Oldingi urinish tekshiruv kutilmoqda.",
                code="pending_review",
            )
        if not latest_attempt.is_completed:
            latest_attempt.ensure_section_reviews()
            return latest_attempt, False
        if not latest_attempt.is_reviewed:
            raise ExamAttemptStartBlocked(
                "Oldingi urinish tekshiruv kutilmoqda.",
                code="pending_review",
            )
        if latest_attempt.passed:
            raise ExamAttemptStartBlocked(
                "Siz bu imtihondan allaqachon o'tgansiz.",
                code="already_passed",
            )
        if latest_attempt.attempt_number >= exam.max_attempts:
            raise ExamAttemptStartBlocked(
                "Urinishlar limiti tugagan. Iltimos, ustoz bilan bog'laning.",
                code="attempt_limit_reached",
            )

    with transaction.atomic():
        latest_attempt = (
            ExamAttempt.objects.select_for_update()
            .filter(student=student, exam=exam)
            .order_by("-attempt_number", "-id")
            .first()
        )
        if latest_attempt:
            if not latest_attempt.is_completed:
                latest_attempt.ensure_section_reviews()
                return latest_attempt, False
            if not latest_attempt.is_reviewed:
                raise ExamAttemptStartBlocked(
                    "Oldingi urinish tekshiruv kutilmoqda.",
                    code="pending_review",
                )
            if latest_attempt.passed:
                raise ExamAttemptStartBlocked(
                    "Siz bu imtihondan allaqachon o'tgansiz.",
                    code="already_passed",
                )
            if latest_attempt.attempt_number >= exam.max_attempts:
                raise ExamAttemptStartBlocked(
                    "Urinishlar limiti tugagan. Iltimos, ustoz bilan bog'laning.",
                    code="attempt_limit_reached",
                )
            next_attempt_number = latest_attempt.attempt_number + 1
        else:
            next_attempt_number = 1

        attempt = ExamAttempt.objects.create(
            student=student,
            exam=exam,
            attempt_number=next_attempt_number,
        )
        attempt.ensure_section_reviews()
        return attempt, True
