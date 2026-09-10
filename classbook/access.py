from core.access import teacher_cohort_queryset
from cohorts.models import Enrollment, enrollment_active_access_q


def can_manage_cohort(user, cohort):
    return bool(
        getattr(user, "is_authenticated", False)
        and user.is_active
        and teacher_cohort_queryset(user).filter(pk=cohort.pk).exists()
    )


def active_enrollment_for(user, cohort):
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return None
    return (
        Enrollment.objects.select_related("student", "cohort", "cohort__course")
        .filter(enrollment_active_access_q(), student=user, cohort=cohort)
        .first()
    )


def can_join_session(user, session):
    return active_enrollment_for(user, session.cohort) is not None
