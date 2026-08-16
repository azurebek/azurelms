"""Guruhga dars ochish/yopish — yagona canonical yo'l (A3).

Ilgari `CohortLessonRelease` faqat Django admin orqali yozilardi. Admin esa
default o'chiq (`ENABLE_LEGACY_ADMIN=False`), ya'ni **darsni ochishning owner
uchun amaldagi yo'li yo'q edi**: drip-release o'qish tomonida ishlab turardi
(`courses/views.py` uni darsni yopish uchun o'qiydi), yozish tomoni esa
yetishmasdi.

Bu yerda mantiq bir joyda: idempotentlik, audit yozuvi va o'quvchilarga
bildirishnoma. Yuzalar (o'qituvchi sahifasi, kelajakda bot) faqat shu
funksiyani chaqiradi.
"""

from django.db import transaction

from cohorts.models import Enrollment, enrollment_active_access_q
from courses.models import CohortLessonRelease


def release_map_for_cohort(cohort):
    """`{lesson_id: CohortLessonRelease}` — sahifa ko'rsatish uchun."""
    return {
        release.lesson_id: release
        for release in CohortLessonRelease.objects.filter(cohort=cohort)
    }


def drip_is_active(cohort, course):
    """Drip rejimi shu kurs uchun yoqilganmi.

    Muhim nozik joy: `courses/views.py` drip'ni **bironta ham** release qatori
    borligiga qarab yoqadi. Ya'ni birinchi ochilgan dars qolgan hammasini
    yopib qo'yadi — bu yuzada ogohlantirish sifatida ko'rsatiladi.
    """
    return CohortLessonRelease.objects.filter(
        cohort=cohort,
        lesson__module__course=course,
    ).exists()


def set_lesson_release(*, cohort, lesson, released, actor, note="", request=None):
    """Darsni guruh uchun ochadi yoki yopadi. Holat o'zgarmasa hech narsa yozmaydi.

    Qaytaradi: `(release, changed)`.
    """
    from core.audit import record_audit_event

    with transaction.atomic():
        release, created = CohortLessonRelease.objects.get_or_create(
            cohort=cohort,
            lesson=lesson,
            defaults={
                "is_released": released,
                "released_by": actor,
                "release_note": note,
            },
        )
        changed = created or release.is_released != released
        if not changed:
            return release, False

        if not created:
            release.is_released = released
            release.released_by = actor
            release.release_note = note
            release.save(update_fields=["is_released", "released_by", "release_note", "updated_at"])

        record_audit_event(
            action="lesson.release" if released else "lesson.lock",
            request=request,
            actor=actor,
            target=release,
            target_label=f"{cohort.name} → {lesson.title}",
            reason=note,
            before={"is_released": None if created else (not released)},
            after={"is_released": released},
        )

        if released:
            _notify_released(cohort=cohort, lesson=lesson, release=release)

    return release, True


def _notify_released(*, cohort, lesson, release):
    """Guruhning faol o'quvchilariga "yangi dars ochildi" bildirishnomasi.

    `external_key` release qatoriga bog'langan: dars yopilib qayta ochilsa
    ham bitta o'quvchiga bitta xabar tushadi.
    """
    from users.notification_service import create_notification

    students = (
        Enrollment.objects.filter(enrollment_active_access_q(), cohort=cohort)
        .select_related("student")
    )
    url = f"/courses/{cohort.course_id}/lesson/{lesson.id}/"
    for enrollment in students:
        create_notification(
            recipient=enrollment.student,
            title="Yangi dars ochildi",
            message=f"\"{lesson.title}\" darsi guruhingiz uchun ochildi.",
            icon="unlock",
            url=url,
            external_key=f"lesson-release-{release.id}",
        )
