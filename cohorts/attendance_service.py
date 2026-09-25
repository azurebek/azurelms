import json

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from cohorts.models import Attendance, Cohort, Enrollment, enrollment_active_access_q


def attendance_xp_for_status(base_xp, status):
    multipliers = {
        Attendance.STATUS_PRESENT: 1.0,
        Attendance.STATUS_PARTIAL: 0.3,
        Attendance.STATUS_ABSENT: 0.0,
    }
    return round(base_xp * multipliers.get(status, 0.0))


@transaction.atomic
def upsert_attendance_and_xp(*, enrollment, lesson, date, status, marked_by):
    # Shared by web, bot and the sheet writer: serialize even first-row inserts.
    Cohort.objects.select_for_update().get(pk=enrollment.cohort_id)
    attendance, _ = Attendance.objects.select_for_update().get_or_create(
        enrollment=enrollment,
        lesson=lesson,
        date=date,
        defaults={
            "status": status,
            "xp_awarded": 0,
            "marked_by": marked_by,
        },
    )

    old_xp = attendance.xp_awarded
    new_xp = attendance_xp_for_status(lesson.xp_reward, status)
    xp_diff = new_xp - old_xp

    if xp_diff != 0:
        from users.xp import award_xp

        award_xp(enrollment.student, xp_diff)

    attendance.status = status
    attendance.xp_awarded = new_xp
    attendance.marked_by = marked_by
    attendance.save(update_fields=["status", "xp_awarded", "marked_by", "marked_at"])

    # Jonli darsga qatnashish ham malakali kunlik faollik — dars sanasi
    # bo'yicha qayd etiladi. Kech belgilangan o'tmish sanani service o'zi
    # e'tiborsiz qoldiradi (seriyani orqaga surmaydi).
    if status in (Attendance.STATUS_PRESENT, Attendance.STATUS_PARTIAL):
        from users.streak import record_activity
        record_activity(enrollment.student, on_date=date)

    return attendance


def attendance_sheet_state(*, cohort, lesson, lock=False):
    enrollments = Enrollment.objects.filter(enrollment_active_access_q(), cohort=cohort).order_by('pk')
    records = Attendance.objects.filter(enrollment__in=enrollments, lesson=lesson).order_by('date', 'pk')
    if lock:
        enrollments = enrollments.select_for_update(of=('self',))
        records = records.select_for_update()
    enrollments = list(enrollments.select_related('student'))
    records = list(records)
    # Keep historical dates. The most recent record for this lesson is edited.
    current = {record.enrollment_id: record for record in records}
    payload = [cohort.pk, lesson.pk, lesson.xp_reward, str(timezone.localdate()),
               [(e.pk, e.student_id) for e in enrollments],
               [(r.pk, r.enrollment_id, str(r.date), r.status, r.xp_awarded, r.marked_at.isoformat()) for r in records]]
    revision = salted_hmac('attendance-sheet-v1', json.dumps(payload)).hexdigest()
    return enrollments, current, revision


@transaction.atomic
def save_attendance_sheet(*, cohort, lesson, marks, expected_revision, actor, request=None):
    """Atomic native sheet adapter; XP/streak still belong to the row service."""
    from core.access import teacher_course_queryset
    from core.audit import record_audit_event
    from courses.models import Lesson

    cohort = Cohort.objects.select_for_update().get(pk=cohort.pk)
    if not cohort.is_active or not teacher_course_queryset(actor).filter(pk=cohort.course_id).exists():
        raise ValidationError('Guruhga ruxsat o‘zgargan. Hech narsa saqlanmadi.', code='stale_sheet')
    lesson = Lesson.objects.get(pk=lesson.pk)
    if lesson.module.course_id != cohort.course_id:
        raise ValidationError('Dars guruh kursiga mos emas.', code='stale_sheet')
    enrollments, current, revision = attendance_sheet_state(cohort=cohort, lesson=lesson, lock=True)
    if revision != expected_revision:
        raise ValidationError('Davomat yoki faol ro‘yxat yangilangan. Saqlanmadi; joriy holatni o‘qib, tanlovlarni qayta tasdiqlang.', code='stale_sheet')
    ids = {e.pk for e in enrollments}
    if not set(marks).issubset(ids) or any(value not in ('', *dict(Attendance.STATUS_CHOICES)) for value in marks.values()):
        raise ValidationError('Davomat tanlovlari joriy ro‘yxatga mos emas.', code='invalid_marks')
    before, after = {}, {}
    # XP/streak rows are shared across cohorts. Acquire their implicit user
    # locks in one global order even when two cohorts enrolled people in a
    # different order, so concurrent sheets cannot deadlock A->B / B->A.
    for enrollment in sorted(enrollments, key=lambda item: (item.student_id, item.pk)):
        status = marks.get(enrollment.pk, '')
        if not status:
            continue
        record = current.get(enrollment.pk)
        before[str(enrollment.pk)] = record.status if record else None
        upsert_attendance_and_xp(enrollment=enrollment, lesson=lesson,
            date=record.date if record else timezone.localdate(), status=status, marked_by=actor)
        after[str(enrollment.pk)] = status
    if after:
        record_audit_event(action='attendance.sheet', actor=actor, request=request, target=cohort,
            target_label=f'{cohort.name} → {lesson.title}', before=before, after=after)
    return len(after), attendance_sheet_state(cohort=cohort, lesson=lesson)[2]
