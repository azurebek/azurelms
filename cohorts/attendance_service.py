from django.db import transaction

from cohorts.models import Attendance


def attendance_xp_for_status(base_xp, status):
    multipliers = {
        Attendance.STATUS_PRESENT: 1.0,
        Attendance.STATUS_PARTIAL: 0.3,
        Attendance.STATUS_ABSENT: 0.0,
    }
    return round(base_xp * multipliers.get(status, 0.0))


@transaction.atomic
def upsert_attendance_and_xp(*, enrollment, lesson, date, status, marked_by):
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
