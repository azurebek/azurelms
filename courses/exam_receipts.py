"""Bound technical recovery history, never answers/grades or audit events."""
import uuid

from core.operational_settings import current_thresholds
from .models import ExamActionReceipt


def trim_receipts(gate):
    """Caller holds the user lock and the action transaction.

    Rotate before eviction: every removed identity was issued with an older
    epoch. An exact delayed retry can therefore never become a new write.
    The successful response includes the fresh epoch for subsequent actions.
    """
    limit = current_thresholds().exam_receipt_limit
    rows = ExamActionReceipt.objects.filter(student_id=gate.student_id, exam_id=gate.exam_id)
    cutoff = next(iter(rows.order_by('-pk').values_list('pk', flat=True)[limit:limit + 1]), None)
    if cutoff is not None:
        gate.epoch = uuid.uuid4()
        gate.save(update_fields=['epoch'])
        rows.filter(pk__lte=cutoff).delete()
