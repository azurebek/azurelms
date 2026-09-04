"""Darsni tugatilgan deb belgilash — o'quvchining o'z qarori.

Ilgari dars sahifasini **ochishning o'zi** uni tugatilgan deb belgilardi
(`LessonDetailView.get_context_data`). Natijada chap ustundagi ro'yxatni
bosib chiqqan o'quvchida hamma dars yashil belgi olardi, foiz esa haqiqatni
ko'rsatmasdi: «12%» aslida «12% ochilgan» degani edi, «o'rganilgan» emas.

Endi belgini o'quvchi o'zi qo'yadi (Coursera naqshi). Bu xavfsiz, chunki
tugatish belgisi hech qanday qulfni ochmaydi va XP bermaydi:

* dars qulflari `courses/access_service.py` da — drip release va oldingi
  darsning tasdiqlangan vazifasi;
* XP davomatdan keladi (`cohorts/attendance_service.py`).

Seriya (streak) faqat **birinchi marta** yoziladi: bekor qilib qayta
bosish bilan kunlik faollikni takrorlab bo'lmaydi.
"""

from dataclasses import dataclass

from django.utils import timezone

from .models import LessonProgress


@dataclass
class ProgressDecision:
    ok: bool
    code: str
    is_completed: bool
    message: str


def mark_lesson_completed(enrollment, lesson):
    progress, created = LessonProgress.objects.get_or_create(
        enrollment=enrollment, lesson=lesson,
    )
    if progress.is_completed:
        return ProgressDecision(
            ok=True, code="already", is_completed=True,
            message="Bu dars allaqachon belgilangan.",
        )

    first_time = progress.completed_at is None
    progress.is_completed = True
    if first_time:
        progress.completed_at = timezone.now()
    progress.save(update_fields=["is_completed", "completed_at", "last_accessed_at"])

    if first_time:
        # Bekor qilib qayta bosish kunlik faollikni takrorlamaydi.
        from users.streak import record_activity

        record_activity(enrollment.student)

    return ProgressDecision(
        ok=True, code="completed", is_completed=True,
        message=f"\"{lesson.title}\" bajarildi deb belgilandi.",
    )


def unmark_lesson_completed(enrollment, lesson):
    """Xato bosilgan belgini olib tashlaydi.

    `completed_at` saqlanadi: u «qachon birinchi marta tugatildi» degan
    tarix, va seriya qoidasi shunga tayanadi.
    """
    progress = LessonProgress.objects.filter(enrollment=enrollment, lesson=lesson).first()
    if progress is None or not progress.is_completed:
        return ProgressDecision(
            ok=True, code="already", is_completed=False,
            message="Bu dars belgilanmagan edi.",
        )

    progress.is_completed = False
    progress.save(update_fields=["is_completed", "last_accessed_at"])
    return ProgressDecision(
        ok=True, code="cleared", is_completed=False,
        message="Belgi olib tashlandi.",
    )
