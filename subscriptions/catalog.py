"""Public catalog policy. Archiving is not revoking purchased access."""

from django.db.models import Q

from .models import Plan


def purchase_plans(*, student=None, course=None):
    """New sales plus the student's existing paid tier for renewal.

    An archived plan is never newly sold; an existing active/expired member
    can renew it. A pending intent is deliberately not a paid subscription.
    """
    allowed = Q(is_available_for_purchase=True)
    if student is not None and course is not None:
        from cohorts.models import Enrollment

        enrollments = Enrollment.objects.filter(
            student=student, cohort__course=course,
            status__in=(Enrollment.STATUS_ACTIVE, Enrollment.STATUS_EXPIRED),
        ).select_related("plan")
        plan_ids = [plan.pk for e in enrollments if (plan := e.active_plan()) is not None]
        allowed |= Q(pk__in=plan_ids)
    return Plan.objects.filter(allowed).order_by("order", "id")


def validate_purchase_plan(*, plan, enrollment=None):
    from django.core.exceptions import ValidationError
    from cohorts.models import Enrollment

    if plan.is_available_for_purchase:
        return
    if enrollment is not None and enrollment.status in (Enrollment.STATUS_ACTIVE, Enrollment.STATUS_EXPIRED):
        active_plan = enrollment.active_plan()
        if active_plan and active_plan.pk == plan.pk:
            return
    raise ValidationError("Bu tarif yangi sotuvlar uchun yopilgan.")
