from courses.models import Lesson, Module
from .models import LessonProgress


def get_next_lesson(enrollment, current_lesson):
    progress, _ = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=current_lesson,
    )
    if not progress.is_completed:
        return None

    next_lesson = (
        Lesson.objects.filter(
            module=current_lesson.module,
            order__gt=current_lesson.order,
        )
        .order_by("order")
        .first()
    )
    if next_lesson:
        return next_lesson

    next_module = (
        Module.objects.filter(
            course=current_lesson.module.course,
            order__gt=current_lesson.module.order,
        )
        .order_by("order")
        .first()
    )
    if not next_module:
        return None

    return Lesson.objects.filter(module=next_module).order_by("order").first()
