from dataclasses import dataclass

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from courses.models import LessonProgress
from users.notification_service import create_notification

from .models import Cohort, Enrollment, EnrollmentTransition


class EnrollmentTransitionError(Exception):
    pass


@dataclass
class TransitionResult:
    source_enrollment: Enrollment
    target_enrollment: Enrollment
    transition: EnrollmentTransition


def locked_enrollment_queryset():
    """Transition uchun qulflangan o'qish so'rovi.

    `of=("self",)` shart: `plan` nullable FK bo'lgani uchun `select_related`
    LEFT OUTER JOIN yasaydi, PostgreSQL esa "FOR UPDATE cannot be applied to
    the nullable side of an outer join" deb rad etadi. SQLite'da
    `select_for_update()` umuman no-op, shuning uchun xato faqat PostgreSQL'da
    ko'rinadi — ya'ni transfer va promotion productionda butunlay yiqilardi.
    Qulflanishi kerak bo'lgan yagona satr — enrollmentning o'zi.
    """
    return (
        Enrollment.objects.select_for_update(of=("self",))
        .select_related("cohort", "cohort__course", "student", "plan")
    )


def _audit_transition(*, action, transition, created_by, note):
    """Transition operatsion ledgerga ham tushadi (A2 / §3).

    `EnrollmentTransition` domen yozuvi sifatida yetarli, ammo unda `source`,
    IP va release SHA yo'q — ya'ni "kim, qayerdan" savoliga javob bermaydi.
    """
    from core.audit import record_audit_event

    record_audit_event(
        action=action,
        actor=created_by,
        target=transition,
        target_label=f"{transition.student.username}: {transition.source_cohort.name} → {transition.target_cohort.name}",
        reason=note,
        before={"cohort": transition.source_cohort.name},
        after={"cohort": transition.target_cohort.name},
    )


def _locked_enrollment(pk):
    return locked_enrollment_queryset().get(pk=pk)


def _ensure_target_cohort(target_cohort):
    if not isinstance(target_cohort, Cohort):
        raise EnrollmentTransitionError("Maqsad cohort topilmadi.")
    return target_cohort


def _ensure_unique_target_enrollment(*, student, target_cohort):
    if Enrollment.objects.filter(student=student, cohort=target_cohort).exists():
        raise EnrollmentTransitionError("Talaba ushbu cohortga allaqachon biriktirilgan.")


def _ensure_no_active_enrollment_for_course(*, student, target_course, exclude_enrollment_id=None):
    queryset = Enrollment.objects.with_active_access().filter(
        student=student,
        cohort__course=target_course,
    )
    if exclude_enrollment_id:
        queryset = queryset.exclude(id=exclude_enrollment_id)
    if queryset.exists():
        raise EnrollmentTransitionError("Talabada ushbu kurs uchun allaqachon faol enrollment mavjud.")


def _freeze_source_enrollment(source_enrollment, *, completion_state=None):
    update_fields = []
    if source_enrollment.status != Enrollment.STATUS_FROZEN:
        source_enrollment.status = Enrollment.STATUS_FROZEN
        update_fields.append("status")
    if completion_state and source_enrollment.completion_state != completion_state:
        source_enrollment.completion_state = completion_state
        update_fields.append("completion_state")
    if completion_state == Enrollment.COMPLETION_STATE_COMPLETED and source_enrollment.completed_at is None:
        source_enrollment.completed_at = timezone.now()
        update_fields.append("completed_at")
    if update_fields:
        source_enrollment._suppress_status_change_notifications = True
        source_enrollment.save(update_fields=update_fields)


def _create_target_enrollment_for_transfer(*, source_enrollment, target_cohort, source_status, plan):
    return Enrollment.objects.create(
        student=source_enrollment.student,
        cohort=target_cohort,
        plan=plan,
        status=source_status,
        completion_state=source_enrollment.completion_state,
        last_payment_date=source_enrollment.last_payment_date,
        next_payment_deadline=source_enrollment.next_payment_deadline,
        completed_at=source_enrollment.completed_at,
        promotion_ready_at=source_enrollment.promotion_ready_at,
    )


def _create_target_enrollment_for_promotion(*, source_enrollment, target_cohort):
    return Enrollment.objects.create(
        student=source_enrollment.student,
        cohort=target_cohort,
        plan=source_enrollment.plan,
        status=Enrollment.STATUS_PENDING,
        completion_state=Enrollment.COMPLETION_STATE_IN_PROGRESS,
    )


def _move_lesson_progress(*, source_enrollment, target_enrollment):
    progress_qs = LessonProgress.objects.filter(enrollment=source_enrollment)
    moved_count = progress_qs.count()
    if moved_count:
        progress_qs.update(enrollment=target_enrollment)
    return moved_count


def _notify_transfer(*, transition):
    create_notification(
        recipient=transition.student,
        title="Guruhingiz yangilandi",
        message=(
            f"Siz {transition.source_cohort.course.title} kursida "
            f"{transition.target_cohort.name} guruhiga o'tkazildingiz."
        ),
        icon="shuffle",
        url="/users/dashboard/",
        external_key=f"enrollment-transition-{transition.id}",
    )


def _notify_promotion(*, transition):
    create_notification(
        recipient=transition.student,
        title="Keyingi bosqich tayyor",
        message=(
            f"Siz {transition.target_cohort.course.title} kursining "
            f"{transition.target_cohort.name} guruhiga o'tkazildingiz. "
            "Davom etish uchun yangi enrollment tasdiqlanishini tekshirib turing."
        ),
        icon="arrow-up-circle",
        url="/users/subscriptions/",
        external_key=f"enrollment-transition-{transition.id}",
    )


def relocate_pending_checkout(*, source_enrollment, target_cohort, plan):
    """Move an unpaid intent, never an invoice or paid membership.

    Preserve the old enrollment and record the transition; direct cohort FK
    edits remain forbidden. Called only on an explicit web/bot checkout write.
    """
    from .delivery_service import lock_cohorts, validate_checkout

    with transaction.atomic():
        locked = lock_cohorts(source_enrollment.cohort_id, target_cohort.pk)
        source = _locked_enrollment(source_enrollment.pk)
        target = locked[target_cohort.pk]
        if (
            source.status != Enrollment.STATUS_PENDING or source.plan_id is not None
            or source.last_payment_date is not None or source.next_payment_deadline is not None
            or source.receipts.exists() or LessonProgress.objects.filter(enrollment=source).exists()
        ):
            raise EnrollmentTransitionError("To'lov yoki o'qish tarixi bor guruhni administrator orqali almashtiring.")
        if source.cohort_id == target.pk or source.cohort.course_id != target.course_id or source.cohort.plan_id != target.plan_id:
            raise EnrollmentTransitionError("Checkout faqat shu kurs va tarifning boshqa guruhiga o'tadi.")
        _ensure_unique_target_enrollment(student=source.student, target_cohort=target)
        replacement = Enrollment(
            student=source.student, cohort=target, status=Enrollment.STATUS_PENDING,
            pending_plan=plan, checkout_started_at=source.checkout_started_at,
        )
        validate_checkout(plan=plan, enrollment=replacement)
        _freeze_source_enrollment(source)
        source.pending_plan = None
        source.checkout_started_at = None
        source.save(update_fields=["pending_plan", "checkout_started_at"])
        replacement.save()
        note = "To'lgan/yopilgan guruhdagi to'lanmagan checkout mos bo'sh guruhga o'tkazildi."
        transition = EnrollmentTransition.objects.create(
            student=source.student, kind=EnrollmentTransition.KIND_TRANSFER,
            source_enrollment=source, target_enrollment=replacement,
            source_cohort=source.cohort, target_cohort=target, note=note,
        )
        _audit_transition(action="enrollment.checkout_reassign", transition=transition, created_by=source.student, note=note)
        return TransitionResult(source, replacement, transition)


def transfer_enrollment_to_cohort(
    *, source_enrollment, target_cohort, created_by=None, note="", allow_tier_change=False,
):
    """O'quvchini shu kursning boshqa guruhiga ko'chiradi.

    `allow_tier_change` — tarifni ham almashtirish uchun **ataylab** beriladi.
    Sukut bo'yicha rad etiladi, chunki tarif o'zgarishi pulga tegadi: yangi
    tarif joriy davr oxirigacha to'lanmagan holda ishlaydi. Tizim narx
    farqini hisoblamaydi — u ownerning qaroriga qoladi (`pricing-packages-plan.md`
    dagi ochiq savol). Shuning uchun bu yerda faqat "ataylabmi" degan
    savolga javob beriladi, hisob-kitob emas.
    """
    target_cohort = _ensure_target_cohort(target_cohort)
    if source_enrollment.cohort_id == target_cohort.id:
        raise EnrollmentTransitionError("Transfer uchun boshqa cohort tanlanishi kerak.")
    if source_enrollment.cohort.course_id != target_cohort.course_id:
        raise EnrollmentTransitionError("Transfer faqat shu kursning boshqa cohortiga qilinadi.")

    _ensure_unique_target_enrollment(student=source_enrollment.student, target_cohort=target_cohort)

    with transaction.atomic():
        from .delivery_service import lock_cohorts, validate_plan_cohort, validate_seat
        locked_cohorts = lock_cohorts(source_enrollment.cohort_id, target_cohort.pk)
        target_cohort = locked_cohorts[target_cohort.pk]
        source_enrollment = _locked_enrollment(source_enrollment.pk)
        if source_enrollment.receipts.filter(is_verified=False).exists():
            # Chek eski a'zolikka bog'langan va uni ko'chirib bo'lmaydi
            # (`PaymentReceipt.BILLING_FIELDS` — hisob-faktura o'zgarmas).
            # Ko'chirsak, keyin tasdiqlangan chek muzlatilgan eski guruhni
            # qayta faollashtirardi yoki "bitta kursda bitta faol a'zolik"
            # tekshiruvida yiqilardi: kelgan pul noto'g'ri ishlatilardi yoki
            # umuman tasdiqlab bo'lmasdi. Shuning uchun avval chek hal
            # qilinadi — tasdiqlanadi yoki rad etiladi.
            raise EnrollmentTransitionError(
                "Bu o'quvchida tasdiq kutayotgan chek bor. Avval to'lov cheklari "
                "sahifasida qaror qabul qiling, keyin ko'chiring."
            )
        current_plan = source_enrollment.active_plan()
        target_plan = current_plan
        try:
            # "Tarif almashadimi" savoli qayta yozilmaydi: mavjud tarif
            # maqsad guruhda hamon amal qiladimi — shu bitta tekshiruv
            # javob beradi (legacy guruhlar tarifsiz bo'lgani uchun
            # oddiy `plan_id` solishtiruvi noto'g'ri javob berardi).
            validate_plan_cohort(plan=current_plan, cohort=target_cohort)
        except ValidationError:
            if not allow_tier_change:
                raise EnrollmentTransitionError(
                    "Bu guruh boshqa tarifda. Tarifni ham o'zgartirishni ataylab tasdiqlang."
                )
            target_plan = target_cohort.plan
        try:
            validate_plan_cohort(plan=target_plan, cohort=target_cohort)
            validate_seat(cohort=target_cohort)
        except ValidationError as exc:
            raise EnrollmentTransitionError(" ".join(exc.messages)) from exc
        source_status = source_enrollment.status
        _freeze_source_enrollment(source_enrollment)
        target_enrollment = _create_target_enrollment_for_transfer(
            source_enrollment=source_enrollment,
            target_cohort=target_cohort,
            source_status=source_status,
            plan=target_plan,
        )
        moved_count = _move_lesson_progress(
            source_enrollment=source_enrollment,
            target_enrollment=target_enrollment,
        )
        transition = EnrollmentTransition.objects.create(
            student=source_enrollment.student,
            kind=EnrollmentTransition.KIND_TRANSFER,
            source_enrollment=source_enrollment,
            target_enrollment=target_enrollment,
            source_cohort=source_enrollment.cohort,
            target_cohort=target_cohort,
            created_by=created_by,
            note=note,
            progress_items_moved=moved_count,
        )
        _audit_transition(
            action="enrollment.transfer",
            transition=transition,
            created_by=created_by,
            note=note,
        )
        _notify_transfer(transition=transition)
    return TransitionResult(
        source_enrollment=source_enrollment,
        target_enrollment=target_enrollment,
        transition=transition,
    )


def promote_enrollment_to_cohort(*, source_enrollment, target_cohort, created_by=None, note=""):
    target_cohort = _ensure_target_cohort(target_cohort)
    if source_enrollment.cohort_id == target_cohort.id:
        raise EnrollmentTransitionError("Promotion uchun boshqa cohort tanlanishi kerak.")
    if source_enrollment.cohort.course_id == target_cohort.course_id:
        raise EnrollmentTransitionError("Promotion keyingi kurs cohortiga qilinadi, shu kurs ichida emas.")
    if source_enrollment.completion_state != Enrollment.COMPLETION_STATE_PROMOTION_READY:
        raise EnrollmentTransitionError("Faqat promotion_ready enrollment promotion qilinadi.")

    _ensure_unique_target_enrollment(student=source_enrollment.student, target_cohort=target_cohort)
    _ensure_no_active_enrollment_for_course(
        student=source_enrollment.student,
        target_course=target_cohort.course,
    )

    with transaction.atomic():
        from .delivery_service import lock_cohorts, validate_plan_cohort, validate_seat
        locked_cohorts = lock_cohorts(source_enrollment.cohort_id, target_cohort.pk)
        target_cohort = locked_cohorts[target_cohort.pk]
        source_enrollment = _locked_enrollment(source_enrollment.pk)
        try:
            validate_plan_cohort(plan=source_enrollment.active_plan(), cohort=target_cohort)
            validate_seat(cohort=target_cohort)
        except ValidationError as exc:
            raise EnrollmentTransitionError(" ".join(exc.messages)) from exc
        target_enrollment = _create_target_enrollment_for_promotion(
            source_enrollment=source_enrollment,
            target_cohort=target_cohort,
        )
        _freeze_source_enrollment(
            source_enrollment,
            completion_state=Enrollment.COMPLETION_STATE_COMPLETED,
        )
        transition = EnrollmentTransition.objects.create(
            student=source_enrollment.student,
            kind=EnrollmentTransition.KIND_PROMOTION,
            source_enrollment=source_enrollment,
            target_enrollment=target_enrollment,
            source_cohort=source_enrollment.cohort,
            target_cohort=target_cohort,
            created_by=created_by,
            note=note,
            progress_items_moved=0,
        )
        _audit_transition(
            action="enrollment.promote",
            transition=transition,
            created_by=created_by,
            note=note,
        )
        _notify_promotion(transition=transition)
    return TransitionResult(
        source_enrollment=source_enrollment,
        target_enrollment=target_enrollment,
        transition=transition,
    )
