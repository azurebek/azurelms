"""Dars darajasidagi kirish huquqi — barcha yuzalar uchun yagona manba (A3).

Bu mantiq `courses/views.py` ichida yashagan edi va faqat **sahifa
ko'rsatish** uchun ishlatilardi: dars ro'yxatida qulf ikonkasi, dars
sahifasiga kirishda redirect. Telegram bot uni o'sha yerdan import qilib
o'qirdi, ya'ni dublikat yo'q edi — lekin manzil noto'g'ri edi: **yozuv**
yo'llari (vazifa topshirish, quiz baholash) uni umuman chaqirmasdi.

Natijada ikkala yuzada bir xil bo'shliq bor edi:

* web'da `/courses/<c>/lesson/<l>/assignment/<a>/submit/` ga to'g'ridan-to'g'ri
  POST yopiq darsga vazifa topshirardi;
* botda `submit_assignment_answer` va `answer_quiz_question` qulfni qayta
  tekshirmasdi — `start_*` tekshirardi, lekin `BotPendingAction` bazada
  saqlanadi va qulf o'zgargandan keyin ham amal qilaverardi.

UI qulfni ko'rsatishi — himoya emas. Shuning uchun tekshiruv canonical
servisga (`courses/submission_service.py`) ko'chirildi va u shu yerdagi
`check_lesson_access()` ni chaqiradi; har ikkala adapter uni meros oladi.

Ikki qulf bor va ular boshqa-boshqa:

1. **Drip release** — guruh uchun bironta `CohortLessonRelease` qatori bo'lsa,
   faqat ochilgan darslar kiradi. Bitta qator butun kursni drip rejimiga
   o'tkazadi (bu ataylab shunday, `courses/release_service.py` ga qarang).
2. **Ketma-ketlik** — oldingi darsning barcha vazifalari tasdiqlanmaguncha
   keyingisi ochilmaydi.
"""

from dataclasses import dataclass

from .models import AssignmentSubmission, CohortLessonRelease, Lesson


@dataclass
class LessonAccessResult:
    is_allowed: bool
    code: str = ""
    message: str = ""


def build_lesson_access_bundle(course, user, enrollment):
    """Kursning barcha darslari uchun qulf holati (sahifa ko'rsatish uchun).

    Qaytaradi: `lessons`, `lesson_access_map` (`{lesson_id: state}`),
    `first_accessible_lesson` va `drip_enabled`.
    """
    lessons = list(
        Lesson.objects.filter(module__course=course)
        .select_related("module")
        .prefetch_related("assignments")
        .order_by("module__order", "order")
    )
    lesson_access_map = {}
    first_accessible_lesson = None

    drip_enabled = False
    released_lesson_ids = set()
    if enrollment:
        release_qs = CohortLessonRelease.objects.filter(
            cohort=enrollment.cohort,
            lesson__module__course=course,
        )
        drip_enabled = release_qs.exists()
        released_lesson_ids = set(
            release_qs.filter(is_released=True).values_list("lesson_id", flat=True)
        )

    approved_assignment_ids = set()
    if user and user.is_authenticated:
        approved_assignment_ids = set(
            AssignmentSubmission.objects.filter(
                student=user,
                assignment__lesson__module__course=course,
                status=AssignmentSubmission.STATUS_APPROVED,
            ).values_list("assignment_id", flat=True)
        )

    assignment_ids_by_lesson = {
        lesson.id: [assignment.id for assignment in lesson.assignments.all()]
        for lesson in lessons
    }

    for index, lesson in enumerate(lessons):
        state = {
            "is_accessible": True,
            "is_released": True,
            "lock_reason": "",
        }

        if not enrollment:
            state["is_accessible"] = False
            state["lock_reason"] = "Kursga faol obuna kerak."
        else:
            if drip_enabled and lesson.id not in released_lesson_ids:
                state["is_accessible"] = False
                state["is_released"] = False
                state["lock_reason"] = "Bu dars hali o'qituvchi tomonidan ochilmagan."

            if state["is_accessible"] and index > 0:
                previous_lesson = lessons[index - 1]
                previous_assignment_ids = assignment_ids_by_lesson.get(previous_lesson.id, [])
                if previous_assignment_ids and any(
                    assignment_id not in approved_assignment_ids
                    for assignment_id in previous_assignment_ids
                ):
                    state["is_accessible"] = False
                    state["lock_reason"] = (
                        "Oldingi dars vazifasi tekshirilib tasdiqlanmaguncha keyingi dars ochilmaydi."
                    )

        lesson_access_map[lesson.id] = state
        if state["is_accessible"] and first_accessible_lesson is None:
            first_accessible_lesson = lesson

    return {
        "lessons": lessons,
        "lesson_access_map": lesson_access_map,
        "first_accessible_lesson": first_accessible_lesson,
        "drip_enabled": drip_enabled,
    }


def check_lesson_access(*, user, lesson, enrollment=None):
    """Bitta dars uchun yozuv yo'llari chaqiradigan gate.

    `enrollment` berilmasa, kurs bo'yicha faol obuna o'zi topiladi. Obuna
    yo'q bo'lsa ham bu yerda rad etiladi — ammo chaqiruvchi servislar
    obunani allaqachon tekshiradi, shuning uchun bu yerdagi asosiy qiymat
    **dars darajasidagi** ikki qulf.
    """
    course = lesson.module.course
    if enrollment is None:
        from cohorts.models import Enrollment, enrollment_active_access_q

        enrollment = (
            Enrollment.objects.filter(
                enrollment_active_access_q(), student=user, cohort__course=course
            )
            .select_related("cohort")
            .order_by("-joined_at", "-id")
            .first()
        )

    bundle = build_lesson_access_bundle(course, user, enrollment)
    state = bundle["lesson_access_map"].get(lesson.id)
    if state is None:
        # Dars kursga tegishli emas — chaqiruvchi noto'g'ri juftlik bergan.
        return LessonAccessResult(
            is_allowed=False, code="missing", message="Dars topilmadi."
        )
    if state["is_accessible"]:
        return LessonAccessResult(is_allowed=True, code="ok")
    return LessonAccessResult(
        is_allowed=False,
        code="locked",
        message=state["lock_reason"] or "Bu dars hozircha siz uchun yopiq.",
    )
