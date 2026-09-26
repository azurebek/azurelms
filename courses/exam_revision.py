"""Shared input revisions. Call only inside an atomic attempt transaction."""
from django.core.exceptions import ValidationError
from .models import ExamAttempt


def lock_writable_attempt(attempt):
    current = ExamAttempt.objects.select_for_update().get(pk=attempt.pk)
    if current.is_completed or current.is_time_limit_exceeded():
        raise ValidationError('Urinish yopilgan yoki vaqti tugagan. Holatni tekshiring.')
    return current


def bump_answer_revision(attempt, key):
    # All learner writers lock the attempt before touching answer rows.
    attempt.answer_versions = dict(attempt.answer_versions)
    attempt.answer_versions[key] = attempt.answer_versions.get(key, 0) + 1
    attempt.input_revision += 1
    attempt.save(update_fields=['answer_versions', 'input_revision'])
