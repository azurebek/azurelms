from django.utils import timezone

from .models import Cohort, Enrollment


class CheckoutUnavailable(Exception):
    pass


def ensure_checkout_cohort(*, course, today=None):
    today = today or timezone.localdate()
    existing_default = course.cohorts.filter(is_checkout_default=True).order_by("-is_active", "start_date", "id").first()
    if existing_default:
        updates = []
        if not existing_default.is_active:
            existing_default.is_active = True
            updates.append("is_active")
        if existing_default.start_date > today:
            existing_default.start_date = today
            updates.append("start_date")
        if updates:
            existing_default.save(update_fields=updates)
        return existing_default

    active_cohort = pick_checkout_cohort(course=course, today=today)
    if active_cohort:
        active_cohort.is_checkout_default = True
        active_cohort.save(update_fields=["is_checkout_default"])
        return active_cohort

    return Cohort.objects.create(
        name=f"{course.title} - Checkout",
        course=course,
        start_date=today,
        is_active=True,
        is_checkout_default=True,
    )


def pick_checkout_cohort(*, course, today=None):
    today = today or timezone.localdate()
    active_cohorts = course.cohorts.filter(is_active=True).order_by("start_date", "id")

    default_cohort = active_cohorts.filter(is_checkout_default=True).first()
    if default_cohort:
        return default_cohort

    upcoming_cohort = active_cohorts.filter(start_date__gte=today).first()
    if upcoming_cohort:
        return upcoming_cohort

    return active_cohorts.order_by("-start_date", "-id").first()


def _checkout_priority(enrollment, *, target_cohort_id=None, today=None):
    effective_status = enrollment.get_effective_status(today=today)
    status_rank = {
        Enrollment.STATUS_ACTIVE: 0,
        Enrollment.STATUS_PENDING: 1,
        Enrollment.STATUS_EXPIRED: 2,
        Enrollment.STATUS_FROZEN: 3,
    }.get(effective_status, 4)
    target_match_rank = 0 if target_cohort_id and enrollment.cohort_id == target_cohort_id else 1
    joined_rank = -enrollment.joined_at.timestamp() if enrollment.joined_at else 0
    return (status_rank, target_match_rank, joined_rank, -enrollment.id)


def resolve_checkout_enrollment(*, student, course, today=None):
    today = today or timezone.localdate()
    target_cohort = pick_checkout_cohort(course=course, today=today) or ensure_checkout_cohort(
        course=course,
        today=today,
    )

    existing_enrollments = list(
        Enrollment.objects.filter(student=student, cohort__course=course)
        .select_related("cohort", "cohort__course", "plan")
        .order_by("-joined_at", "-id")
    )
    reusable_enrollments = [
        enrollment
        for enrollment in existing_enrollments
        if enrollment.get_effective_status(today=today)
        in {
            Enrollment.STATUS_ACTIVE,
            Enrollment.STATUS_PENDING,
            Enrollment.STATUS_EXPIRED,
        }
    ]
    if reusable_enrollments:
        reusable_enrollments.sort(
            key=lambda enrollment: _checkout_priority(
                enrollment,
                target_cohort_id=target_cohort.id,
                today=today,
            )
        )
        return reusable_enrollments[0], False, target_cohort

    enrollment = Enrollment.objects.create(
        student=student,
        cohort=target_cohort,
        status=Enrollment.STATUS_PENDING,
    )
    return enrollment, True, target_cohort
