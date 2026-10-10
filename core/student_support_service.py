"""Read-only learner support projection over the existing access policies.

This is the ordinary course link diagnosis: no explicit ``?cohort=`` override.
The newest enrollment with active access wins, matching LessonDetailView's
default selection. Course/catalog visibility, cohort dates and pending renewal
receipts are evidence, never additional lesson gates. Calling the learner view
would record progress, so this projection only consumes the canonical bundle.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from cohorts.models import Enrollment, PaymentReceipt
from core.access import teacher_course_queryset
from courses.access_service import build_lesson_access_bundle
from courses.models import AssignmentSubmission, Lesson


def _actor(actor):
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "pk", None):
        raise PermissionDenied
    try:
        actor = get_user_model().objects.get(pk=actor.pk)
    except get_user_model().DoesNotExist:
        raise PermissionDenied from None
    if not actor.is_active or not (actor.is_staff or actor.is_superuser):
        raise PermissionDenied
    return actor


def _students(actor):
    students = get_user_model().objects.filter(is_staff=False, is_superuser=False)
    if not actor.is_superuser:
        students = students.filter(
            enrollments__cohort__course__in=teacher_course_queryset(actor),
        ).distinct()
    return students


def support_student_queryset(actor):
    """Staff may find learners with any enrollment in their current course scope."""
    return _students(_actor(actor)).only(
        "pk", "username", "first_name", "last_name", "email", "is_active",
        "is_staff", "is_superuser", "date_joined",
    )


def _diagnosis(state, code, title, message):
    return {"state": state, "code": code, "title": title, "message": message}


def build_student_support(*, actor, student_id, course_id=None, lesson_id=None):
    actor = _actor(actor)
    student = _students(actor).only(
        "pk", "username", "first_name", "last_name", "email", "is_active",
        "is_staff", "is_superuser", "date_joined",
    ).get(pk=student_id)
    checked_at = timezone.now()
    today = timezone.localdate(checked_at)
    course_scope = teacher_course_queryset(actor)
    visible_enrollments = Enrollment.objects.filter(
        student=student, cohort__course__in=course_scope,
    ).select_related("cohort", "cohort__course", "plan", "pending_plan").order_by("-joined_at", "-pk")
    selected_course = course_scope.get(pk=course_id) if course_id is not None else None
    if course_id is None:
        newest = visible_enrollments.first()
        if newest is not None:
            selected_course = newest.cohort.course
    if selected_course is None and lesson_id is not None:
        raise Lesson.DoesNotExist

    enrollments = list(visible_enrollments.filter(cohort__course=selected_course)) if selected_course else []
    active_ids = set(
        Enrollment.objects.with_active_access(today=today).filter(
            pk__in=[enrollment.pk for enrollment in enrollments],
        ).values_list("pk", flat=True)
    )
    effective_enrollment = next((item for item in enrollments if item.pk in active_ids), None)
    relevant_enrollment = effective_enrollment or (enrollments[0] if enrollments else None)
    for enrollment in enrollments:
        enrollment.support_access_open = enrollment.pk in active_ids
        enrollment.support_effective_status = enrollment.get_effective_status(today=today)
        enrollment.support_effective_label = enrollment.get_effective_status_display(today=today)

    bundle = build_lesson_access_bundle(selected_course, student, effective_enrollment) if selected_course else None
    lessons = bundle["lessons"] if bundle else []
    if lesson_id is not None:
        selected_lesson = next((lesson for lesson in lessons if lesson.pk == lesson_id), None)
        if selected_lesson is None:
            raise Lesson.DoesNotExist
    else:
        selected_lesson = lessons[0] if lessons else None
    state = bundle["lesson_access_map"].get(selected_lesson.pk) if selected_lesson else None

    previous_lesson = None
    previous_submissions = []
    previous_assignments_missing = []
    if selected_lesson is not None:
        index = lessons.index(selected_lesson)
        if index:
            # The same ordered list that the canonical gate evaluated, including
            # historical tied order values. No different UI-only ordering rule.
            previous_lesson = lessons[index - 1]
            assignments = list(previous_lesson.assignments.all())
            submissions = list(AssignmentSubmission.objects.filter(
                student=student, assignment_id__in=[item.pk for item in assignments],
            ).select_related("assignment").only(
                "pk", "assignment_id", "student_id", "status", "submitted_at", "updated_at",
                "assignment__id", "assignment__title", "assignment__lesson_id",
            ).order_by("assignment_id", "pk"))
            submitted_ids = {item.assignment_id for item in submissions}
            previous_submissions = [item for item in submissions if item.status != AssignmentSubmission.STATUS_APPROVED]
            previous_assignments_missing = [item for item in assignments if item.pk not in submitted_ids]

    if not student.is_active:
        diagnosis = _diagnosis("blocked", "account_inactive", "Hisob faol emas",
                               "O‘quvchi hisobi o‘chirilgan. Avval hisob holatini tekshirish kerak.")
    elif selected_course is None:
        diagnosis = _diagnosis("empty", "no_course", "Kursni tanlang",
                               "O‘quvchining kursga yozilish qaydi topilmadi. Tekshiriladigan kursni tanlang.")
    elif effective_enrollment is None:
        effective_status = relevant_enrollment.get_effective_status(today=today) if relevant_enrollment else None
        if effective_status == Enrollment.STATUS_PENDING:
            diagnosis = _diagnosis("blocked", "pending", "Obuna faollashtirilmagan",
                                   "Bu kursdagi a’zolik to‘lov kutilmoqda holatida. To‘lov qaydini tekshiring.")
        elif effective_status == Enrollment.STATUS_EXPIRED:
            message = ("To‘lov muddati va amaldagi imtiyozli muddat tugagan."
                       if relevant_enrollment.status == Enrollment.STATUS_ACTIVE else
                       "Bu kursdagi a’zolik muddati tugagan holatda.")
            diagnosis = _diagnosis("blocked", "expired", "Obuna muddati tugagan", message)
        elif effective_status == Enrollment.STATUS_FROZEN:
            diagnosis = _diagnosis("blocked", "frozen", "A’zolik muzlatilgan",
                                   "Bu kursdagi a’zolik muzlatilgan. Guruhdagi a’zolik holatini tekshiring.")
        elif relevant_enrollment is None:
            diagnosis = _diagnosis("blocked", "no_enrollment", "Kursga yozilmagan",
                                   "Bu o‘quvchi tanlangan kursga yozilmagan.")
        else:
            diagnosis = _diagnosis("blocked", "no_active_enrollment", "Faol obuna topilmadi",
                                   "Tanlangan kursda darsga kirish imkonini beradigan faol a’zolik yo‘q.")
    elif selected_lesson is None:
        diagnosis = _diagnosis("empty", "no_lessons", "Kursga hali dars qo‘shilmagan",
                               "Obuna faol. Kursga dars qo‘shilgach uning kirish holatini tekshirish mumkin.")
    elif state["is_accessible"]:
        diagnosis = _diagnosis("open", "open", "Darsga kirish ochiq",
                               "Joriy hisob, obuna va dars tartibi bo‘yicha kirishga to‘sqinlik topilmadi.")
    elif bundle["drip_enabled"] and not state["is_released"]:
        diagnosis = _diagnosis("blocked", "drip", "Dars guruhga ochilmagan", state["lock_reason"])
    else:
        diagnosis = _diagnosis("blocked", "sequence", "Oldingi dars vazifasi tasdiqlanmagan", state["lock_reason"])

    pending_query = PaymentReceipt.objects.filter(
        enrollment_id__in=[item.pk for item in enrollments], is_verified=False,
    ).select_related("enrollment", "enrollment__cohort", "plan").defer(
        "receipt_image",
    ).order_by("-submitted_at", "-pk")
    pending_receipts = list(pending_query[:20])
    # The recommendation belongs to the diagnosed membership, independently
    # of the bounded course-wide evidence list and its receipt submission order.
    relevant_pending_receipt = (pending_query.filter(enrollment_id=relevant_enrollment.pk).first()
                               if relevant_enrollment is not None else None)
    return {
        "student": student, "course_options": list(course_scope.order_by("title", "pk")),
        "selected_course": selected_course, "lessons": lessons, "selected_lesson": selected_lesson,
        "enrollments": enrollments, "effective_enrollment": effective_enrollment,
        "relevant_enrollment": relevant_enrollment, "diagnosis": diagnosis, "checked_at": checked_at,
        "pending_receipts": pending_receipts, "previous_lesson": previous_lesson,
        "relevant_pending_receipt": relevant_pending_receipt,
        "previous_submissions": previous_submissions,
        "previous_assignments_missing": previous_assignments_missing,
        "multiple_active_enrollments": len(active_ids) > 1,
        "enrollment_access_open": effective_enrollment is not None,
    }
