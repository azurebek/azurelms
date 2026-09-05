"""«Davom etish» — qayerda to'xtagan bo'lsa, o'sha yerdan.

UX auditning 6-topilmasi. Tugma «Davom etish» deb yozilgan edi, ammo
`course_detail` ga eltardi: 20 ta darsni tugatgan o'quvchi kurs tavsifiga
tushib, mundarijadan o'zi qayerda qolganini qidirishi kerak edi.

`CourseStudyRedirectView` da mo'ljal bor edi — docstring'ida «current
lesson (or the first lesson)» deb yozilgan. Ammo kod faqat
`first_accessible_lesson` ni ishlatardi, ya'ni har safar birinchi ochiq
darsni ochardi. Va veb'dagi «Davom etish» tugmalari bu view'ga umuman
bormasdi: Telegram Mini App bormoqda edi, veb esa yo'q — yana adapter
farqi.

Tanlash tartibi (birinchi mos kelgani yutadi):

1. **Yarim qolgan dars** — eng oxirgi ochilgan, hali tugallanmagan va
   hamon ochiq dars. Odam aynan shu yerda to'xtagan.
2. **Keyingi qilinadigan ish** — hech narsa yarim qolmagan bo'lsa,
   ro'yxatdagi birinchi ochiq va tugallanmagan dars.
3. **Hammasi tugagan** — oxirgi ochilgan ochiq dars (qayta o'qish uchun),
   u ham bo'lmasa birinchi ochiq dars.

Uchinchi holat ataylab kurs sahifasiga eltmaydi: «davom etish» bosgan
odam darsni ko'rmoqchi, tavsifni emas.
"""

from .access_service import build_lesson_access_bundle
from .models import LessonProgress


def resume_lesson(user, course, enrollment):
    """Qaytaradi: `(lesson, bundle)`. Ochiq dars bo'lmasa `(None, bundle)`.

    `bundle` ham qaytariladi — chaqiruvchi uni qayta hisoblab o'tirmasin
    (u kursning barcha darslari bo'yicha bir necha so'rov qiladi).
    """
    bundle = build_lesson_access_bundle(course, user, enrollment)
    access_map = bundle["lesson_access_map"]
    lessons = bundle["lessons"]

    def is_open(lesson):
        return access_map.get(lesson.id, {}).get("is_accessible", False)

    open_lessons = [lesson for lesson in lessons if is_open(lesson)]
    if not open_lessons:
        return None, bundle

    open_ids = {lesson.id for lesson in open_lessons}
    by_id = {lesson.id: lesson for lesson in open_lessons}

    # `LessonProgress.Meta.ordering` allaqachon `-last_accessed_at`, ammo
    # bunga tayanmaymiz: tartib modelda o'zgarsa bu yerdagi mantiq jimgina
    # buzilgan bo'lardi.
    touched = list(
        LessonProgress.objects.filter(enrollment=enrollment, lesson_id__in=open_ids)
        .order_by("-last_accessed_at")
        .values_list("lesson_id", "is_completed")
    )

    # 1. Yarim qolgan dars.
    for lesson_id, is_completed in touched:
        if not is_completed:
            return by_id[lesson_id], bundle

    # 2. Keyingi qilinadigan ish.
    completed_ids = {lesson_id for lesson_id, done in touched if done}
    for lesson in open_lessons:
        if lesson.id not in completed_ids:
            return lesson, bundle

    # 3. Hammasi tugagan.
    if touched:
        return by_id[touched[0][0]], bundle
    return open_lessons[0], bundle
