"""One delivery policy for checkout, payment decisions and staff transitions.

Lock order: course(s) -> cohort(s) -> enrollment -> plan/receipt -> promo.
The course lock also serializes the same student's admission to two cohorts.
Pending is intent, not a seat. Expiry suspends access, not group membership.
"""

from django.core.exceptions import ValidationError


class DeliveryUnavailable(ValidationError):
    pass


def occupied_members(cohort):
    from .models import Enrollment

    return Enrollment.objects.filter(
        cohort=cohort, status__in=(Enrollment.STATUS_ACTIVE, Enrollment.STATUS_EXPIRED),
    )


def occupied_seats(cohort):
    return occupied_members(cohort).count()


def validate_plan_cohort(*, plan, cohort):
    if cohort.plan_id is not None:
        if plan is None or plan.pk != cohort.plan_id:
            raise DeliveryUnavailable("Tarif guruh formatiga mos emas. Mos guruhni tanlang.", code="tier_mismatch")
    elif plan is not None and plan.cohort_capacity_limit is not None:
        raise DeliveryUnavailable("Bu tarif uchun alohida guruh hali ochilmagan.", code="tier_mismatch")


def validate_seat(*, cohort, enrollment=None):
    if cohort.capacity is None:
        return
    members = occupied_members(cohort)
    if enrollment is not None:
        members = members.exclude(pk=enrollment.pk)
    if members.count() >= cohort.capacity:
        raise DeliveryUnavailable(
            "Guruh to'ldi. Boshqa guruh yoki to'lovni qaytarish masalasida administrator bilan bog'laning.",
            code="cohort_full",
        )


def validate_checkout(*, plan, enrollment):
    from subscriptions.catalog import validate_purchase_plan

    validate_purchase_plan(plan=plan, enrollment=enrollment)
    if not enrollment.cohort.is_active and enrollment.status == "pending":
        raise DeliveryUnavailable("Bu guruhga yangi qabul yopilgan.", code="cohort_closed")
    validate_plan_cohort(plan=plan, cohort=enrollment.cohort)
    validate_seat(cohort=enrollment.cohort, enrollment=enrollment)


def lock_cohorts(*cohort_ids):
    from .models import Cohort
    from courses.models import Course

    course_ids = Cohort.objects.filter(pk__in=set(cohort_ids)).values_list("course_id", flat=True)
    list(Course.objects.select_for_update().filter(pk__in=course_ids).order_by("pk"))

    return {
        cohort.pk: cohort for cohort in
        Cohort.objects.select_for_update().filter(pk__in=set(cohort_ids)).order_by("pk")
    }


def lock_enrollment(enrollment_id):
    from .models import Enrollment

    cohort_id = Enrollment.objects.values_list("cohort_id", flat=True).get(pk=enrollment_id)
    cohorts = lock_cohorts(cohort_id)
    enrollment = Enrollment.objects.select_for_update().get(pk=enrollment_id)
    if enrollment.cohort_id != cohort_id:
        raise DeliveryUnavailable("Guruh o'zgargan. Sahifani yangilab qayta urinib ko'ring.")
    enrollment.cohort = cohorts[cohort_id]
    return enrollment
