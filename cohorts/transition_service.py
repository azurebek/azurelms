from dataclasses import dataclass

from django.db import transaction
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


def _create_target_enrollment_for_transfer(*, source_enrollment, target_cohort, source_status):
    return Enrollment.objects.create(
        student=source_enrollment.student,
        cohort=target_cohort,
        plan=source_enrollment.plan,
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


def transfer_enrollment_to_cohort(*, source_enrollment, target_cohort, created_by=None, note=""):
    target_cohort = _ensure_target_cohort(target_cohort)
    if source_enrollment.cohort_id == target_cohort.id:
        raise EnrollmentTransitionError("Transfer uchun boshqa cohort tanlanishi kerak.")
    if source_enrollment.cohort.course_id != target_cohort.course_id:
        raise EnrollmentTransitionError("Transfer faqat shu kursning boshqa cohortiga qilinadi.")

    _ensure_unique_target_enrollment(student=source_enrollment.student, target_cohort=target_cohort)

    with transaction.atomic():
        source_enrollment = (
            Enrollment.objects.select_for_update()
            .select_related("cohort", "cohort__course", "student", "plan")
            .get(pk=source_enrollment.pk)
        )
        source_status = source_enrollment.status
        _freeze_source_enrollment(source_enrollment)
        target_enrollment = _create_target_enrollment_for_transfer(
            source_enrollment=source_enrollment,
            target_cohort=target_cohort,
            source_status=source_status,
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
        source_enrollment = (
            Enrollment.objects.select_for_update()
            .select_related("cohort", "cohort__course", "student", "plan")
            .get(pk=source_enrollment.pk)
        )
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
        _notify_promotion(transition=transition)
    return TransitionResult(
        source_enrollment=source_enrollment,
        target_enrollment=target_enrollment,
        transition=transition,
    )
