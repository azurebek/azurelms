from django.db import transaction

from .models import Enrollment


def expire_overdue_enrollments(*, queryset=None, today=None, grace_days=Enrollment.ACCESS_GRACE_DAYS):
    base_queryset = queryset if queryset is not None else Enrollment.objects.all()
    overdue_enrollments = list(
        base_queryset.overdue_for_expiration(today=today, grace_days=grace_days).select_related("student")
    )
    if not overdue_enrollments:
        return 0

    enrollment_ids = [enrollment.id for enrollment in overdue_enrollments]
    with transaction.atomic():
        Enrollment.objects.filter(id__in=enrollment_ids).update(status=Enrollment.STATUS_EXPIRED)

    from messenger.access import sync_student_chat_access

    synced_student_ids = set()
    for enrollment in overdue_enrollments:
        enrollment.status = Enrollment.STATUS_EXPIRED
        if enrollment.student_id in synced_student_ids:
            continue
        sync_student_chat_access(enrollment.student)
        synced_student_ids.add(enrollment.student_id)

    return len(enrollment_ids)
