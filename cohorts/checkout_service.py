"""Checkout uchun cohort va enrollment tanlash (A4).

O'qish va yozuv yo'llari ataylab ajratilgan:

* `find_checkout_enrollment()` — sahifa ko'rsatish uchun. Hech narsa yozmaydi.
* `resolve_checkout_enrollment()` — forma yuborilganda. Kerak bo'lsa yaratadi.

Ilgari ikkalasi bitta funksiya edi va natijada sahifani ochishning o'zi
`Enrollment` yaratardi — promo preview AJAX chaqirig'i ham. Bundan tashqari
yopilgan qabul o'zidan-o'zi qayta ochilardi (pastda batafsil).
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import Enrollment, PaymentReceipt, PendingReceiptExists
from .delivery_service import lock_enrollment, validate_checkout
from django.core.exceptions import ValidationError

CLOSED_MESSAGE = "Ushbu kursga qabul hali ochilmagan."


class CheckoutUnavailable(Exception):
    pass


def pick_checkout_cohort(*, course, today=None, plan=None):
    """Faol cohortlar orasidan checkout uchun mosini tanlaydi (faqat o'qish)."""
    today = today or timezone.localdate()
    active_cohorts = course.cohorts.filter(is_active=True).order_by("start_date", "id")
    # A delivery package never falls back into an untyped legacy cohort.
    if plan is not None and plan.cohort_capacity_limit is not None:
        active_cohorts = active_cohorts.filter(plan=plan)
    else:
        active_cohorts = active_cohorts.filter(plan__isnull=True)
    available_ids = [c.pk for c in active_cohorts if not c.is_full]
    active_cohorts = active_cohorts.filter(pk__in=available_ids)

    default_cohort = active_cohorts.filter(is_checkout_default=True).first()
    if default_cohort:
        return default_cohort

    upcoming_cohort = active_cohorts.filter(start_date__gte=today).first()
    if upcoming_cohort:
        return upcoming_cohort

    return active_cohorts.order_by("-start_date", "-id").first()


def ensure_checkout_cohort(*, course, today=None, plan=None):
    """Faol cohortlardan birini default deb belgilaydi.

    **Yopiq qabulni ochmaydi.** Ilgari bu funksiya `is_active=True` qilib
    qo'yardi va `start_date`ni bugunga tortardi — ya'ni owner qabulni
    yopgandan keyin bitta o'quvchining checkout sahifasini ochishi uni qayta
    ochib yuborardi. Qabulni faqat owner ochadi.
    """
    cohort = pick_checkout_cohort(course=course, today=today, plan=plan)
    if cohort is None:
        raise CheckoutUnavailable(CLOSED_MESSAGE)

    if not cohort.is_checkout_default and not course.cohorts.filter(plan_id=cohort.plan_id, is_checkout_default=True).exists():
        cohort.is_checkout_default = True
        cohort.save(update_fields=["is_checkout_default"])
    return cohort


def mark_checkout_started(enrollment, *, plan, now=None):
    """Tanlangan tarifni yozadi va to'lov niyatini vaqt bilan belgilaydi.

    Yagona nuqta: web forma ham, Telegram `/yozilish` ham shu yerdan o'tadi.
    `checkout_started_at` keyin chek qaysi enrollmentga tegishli ekanini
    aniqlaydi — Telegram'dan kelgan rasm o'zi bilan kurs ma'lumotini olib
    kelmaydi.
    """
    with transaction.atomic():
        locked = lock_enrollment(enrollment.pk)
        if PaymentReceipt.objects.filter(enrollment=locked, is_verified=False).exists():
            raise PendingReceiptExists("Tasdiqlanmagan chek mavjud. Qarorni kuting.")
        validate_checkout(plan=plan, enrollment=locked)
        locked.pending_plan = plan
        locked.checkout_started_at = now or timezone.now()
        locked.save(update_fields=["pending_plan", "checkout_started_at"])
        enrollment.pending_plan = plan
        enrollment.checkout_started_at = locked.checkout_started_at
    return enrollment


def checkout_period(enrollment, *, today=None):
    """Web va bot uchun yagona 30 kunlik billing hisobi."""
    today = today or timezone.localdate()
    start = today
    if (
        enrollment is not None
        and enrollment.status == Enrollment.STATUS_ACTIVE
        and enrollment.next_payment_deadline
        and enrollment.next_payment_deadline > today
    ):
        start = enrollment.next_payment_deadline
    return start, start + timedelta(days=30)


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


def _reusable_enrollments(*, student, course, today):
    candidates = (
        Enrollment.objects.filter(student=student, cohort__course=course)
        .select_related("cohort", "cohort__course", "plan")
        .order_by("-joined_at", "-id")
    )
    return [
        enrollment
        for enrollment in candidates
        if enrollment.get_effective_status(today=today)
        in {
            Enrollment.STATUS_ACTIVE,
            Enrollment.STATUS_PENDING,
            Enrollment.STATUS_EXPIRED,
        }
    ]


def find_checkout_enrollment(*, student, course, today=None, plan=None):
    """Mavjud enrollment (yoki `None`) va maqsad cohort — hech narsa yozmasdan.

    Qabul yopilgan bo'lsa yangi o'quvchi uchun `CheckoutUnavailable`, ammo
    **mavjud o'quvchi to'lovni davom ettira oladi**: "qabul yopildi" degani
    yangi a'zo olinmaydi, allaqachon o'qiyotgan odam obunasini uzaytira
    olmaydi degani emas.
    """
    today = today or timezone.localdate()
    reusable = _reusable_enrollments(student=student, course=course, today=today)
    if plan is not None:
        # No automatic cross-tier transfer: paid membership stays in its cohort.
        target_plan_id = plan.pk if plan.cohort_capacity_limit is not None else None
        if any(e.status in (Enrollment.STATUS_ACTIVE, Enrollment.STATUS_EXPIRED)
               and e.cohort.plan_id != target_plan_id for e in reusable):
            raise CheckoutUnavailable("Tarifni almashtirish uchun administrator orqali mos guruhga o'ting.")
        if plan.cohort_capacity_limit is not None:
            reusable = [e for e in reusable if e.cohort.plan_id == plan.pk]
        else:
            reusable = [e for e in reusable if e.cohort.plan_id is None]
    target_cohort = pick_checkout_cohort(course=course, today=today, plan=plan)

    if target_cohort is None:
        if not reusable:
            raise CheckoutUnavailable("Guruh to'ldi yoki ushbu tarif uchun qabul hali ochilmagan.")
        target_cohort = reusable[0].cohort

    if not reusable:
        if plan is not None:
            from subscriptions.catalog import validate_purchase_plan
            try:
                validate_purchase_plan(plan=plan)
            except ValidationError as exc:
                raise CheckoutUnavailable(" ".join(exc.messages)) from exc
        return None, target_cohort

    reusable.sort(
        key=lambda enrollment: _checkout_priority(
            enrollment,
            target_cohort_id=target_cohort.id,
            today=today,
        )
    )
    if plan is not None:
        existing = reusable[0]
        # A submitted invoice stays attached to its original group until the
        # owner decides it. Keep the pending-receipt UI reachable even if full.
        if existing.status == Enrollment.STATUS_PENDING and existing.receipts.filter(is_verified=False).exists():
            return existing, existing.cohort
        try:
            validate_checkout(plan=plan, enrollment=existing)
        except ValidationError as exc:
            if existing.status == Enrollment.STATUS_PENDING and target_cohort.pk != existing.cohort_id:
                # Preview the replacement without mutating either enrollment.
                # The write path performs an audited pending-only transition.
                preview = Enrollment(student=student, cohort=target_cohort, status=Enrollment.STATUS_PENDING)
                try:
                    validate_checkout(plan=plan, enrollment=preview)
                except ValidationError as target_exc:
                    raise CheckoutUnavailable(" ".join(target_exc.messages)) from target_exc
                return existing, target_cohort
            raise CheckoutUnavailable(" ".join(exc.messages)) from exc
        return existing, existing.cohort
    return reusable[0], target_cohort


def resolve_checkout_enrollment(*, student, course, today=None, plan=None):
    """Yozuv yo'li: enrollment yo'q bo'lsa yaratadi.

    Faqat foydalanuvchi ataylab amal qilganda chaqiriladi (forma yuborish,
    botda kurs+tarif tanlash) — sahifa ko'rsatishda emas.
    """
    today = today or timezone.localdate()
    with transaction.atomic():
        # A GET remains read-only; on a write re-resolve under the course lock
        # so two web/bot starts reuse the same pending enrollment.
        type(course).objects.select_for_update().get(pk=course.pk)
        enrollment, target_cohort = find_checkout_enrollment(student=student, course=course, today=today, plan=plan)
        if enrollment is not None:
            if plan is not None and enrollment.cohort_id != target_cohort.pk:
                from .transition_service import EnrollmentTransitionError, relocate_pending_checkout
                try:
                    enrollment = relocate_pending_checkout(
                        source_enrollment=enrollment, target_cohort=target_cohort, plan=plan,
                    ).target_enrollment
                except (EnrollmentTransitionError, ValidationError) as exc:
                    raise CheckoutUnavailable(str(exc)) from exc
                return enrollment, True, target_cohort
            return enrollment, False, target_cohort
        target_cohort = ensure_checkout_cohort(course=course, today=today, plan=plan)
        enrollment = Enrollment.objects.create(
            student=student,
            cohort=target_cohort,
            status=Enrollment.STATUS_PENDING,
        )
    return enrollment, True, target_cohort
