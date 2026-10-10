"""Scoped course authoring shared by backoffice adapters.

Every mutation checks a signed snapshot under a stable row lock, validates the
current parent scope, and commits its audit record in the same transaction.
Snapshots deliberately follow the existing editor contract: replayed creates
are rejected, but they are not durable operation receipts or revision counters.
An external writer changing values and restoring them (ABA) is not detected.
Saving lesson content never creates a release or a private draft.
"""

import hashlib
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils.crypto import constant_time_compare, salted_hmac

from core.access import teacher_course_queryset
from core.audit import record_audit_event
from courses.models import Course, Lesson, Module


LESSON_FIELDS = ("title", "module", "video_url", "content", "order", "xp_reward")


class AuthoringConflict(ValidationError):
    def __init__(self):
        super().__init__(
            "Ma’lumot boshqa oynada o‘zgargan. Yozganlaringizni olib, so‘nggi holatni oching.",
            code="stale",
        )


def _sign(actor, action, state):
    return salted_hmac(
        "course-authoring", json.dumps([actor.pk, action, state], default=str),
        algorithm="sha256",
    ).hexdigest()


def outline_revision(actor, course):
    return _sign(actor, "outline", [
        course.pk,
        list(Module.objects.filter(course=course).order_by("order", "pk")
             .values_list("pk", "title", "order")),
        list(Lesson.objects.filter(module__course=course).order_by("pk")
             .values_list("pk", "module_id", "title", "order")),
    ])


def lesson_revision(actor, lesson):
    return _sign(actor, "lesson", [
        lesson.pk,
        [str(lesson._meta.get_field(name).value_from_object(lesson)) for name in LESSON_FIELDS],
    ])


def _course_value(course, name):
    field = course._meta.get_field(name)
    value = field.value_from_object(course)
    if field.get_internal_type() == "DecimalField" and value is not None:
        value = f"{field.to_python(value):.{field.decimal_places}f}"
    return str(value)


def course_revision(actor, course=None):
    from core.backoffice_forms import CourseBackofficeForm

    state = (
        [course.pk, [_course_value(course, name)
                     for name in CourseBackofficeForm.Meta.fields]]
        if course is not None else
        list(teacher_course_queryset(actor).order_by("pk").values_list("pk", flat=True))
    )
    return _sign(actor, "course" if course is not None else "new-course", state)


def _check_revision(expected, current):
    if not isinstance(expected, str) or not constant_time_compare(expected, current):
        raise AuthoringConflict()


def _actor(actor):
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "pk", None):
        raise PermissionDenied
    try:
        current = get_user_model().objects.select_for_update().get(pk=actor.pk)
    except get_user_model().DoesNotExist:
        raise PermissionDenied from None
    if not current.is_active or not (current.is_staff or current.is_superuser):
        raise PermissionDenied
    return current


def _course(actor, course_id):
    return teacher_course_queryset(actor).select_for_update().get(pk=course_id)


def _module_state(module):
    return {"course_id": module.course_id, "title": module.title, "order": module.order}


def _lesson_state(lesson):
    return {
        "module_id": lesson.module_id, "title": lesson.title, "order": lesson.order,
        "xp_reward": lesson.xp_reward, "video_url": lesson.video_url or "",
        "content_sha256": hashlib.sha256((lesson.content or "").encode()).hexdigest(),
    }


def _course_state(course):
    from core.backoffice_forms import CourseBackofficeForm

    state = {
        name: _course_value(course, name)
        for name in CourseBackofficeForm.Meta.fields if name != "description"
    }
    state["description_sha256"] = hashlib.sha256((course.description or "").encode()).hexdigest()
    return state


def _audit(*, actor, action, target, before, after, request):
    record_audit_event(
        action=action, actor=actor, target=target, request=request,
        reason="Kurs va dars ustaxonasida saqlandi.", before=before, after=after,
    )


@transaction.atomic
def save_course(*, actor, data, expected_revision, course_id=None, request=None):
    """Validate the canonical course form again against the locked current row."""
    from core.backoffice_forms import CourseBackofficeForm

    actor = _actor(actor)
    course = _course(actor, course_id) if course_id is not None else None
    _check_revision(expected_revision, course_revision(actor, course))
    before = _course_state(course) if course is not None else {}
    form = CourseBackofficeForm(data, instance=course, user=actor)
    if not form.is_valid():
        raise ValidationError(form.errors.as_data())
    course = form.save(commit=False)
    if not course.instructor_id:
        course.instructor = actor
    if not actor.is_superuser and course.instructor_id != actor.pk:
        raise PermissionDenied
    course.full_clean()
    after = _course_state(course)
    created = course.pk is None
    if not created and before == after:
        return course, False
    course.save()
    if not course.modules.exists():
        Module.objects.create(course=course, title="1. Boshlanish", order=1)
    _audit(actor=actor, action="course.create" if created else "course.update",
           target=course, before=before, after=after, request=request)
    return course, True


@transaction.atomic
def save_module(*, actor, course_id, title, expected_revision, module_id=None, request=None):
    actor = _actor(actor)
    course = _course(actor, course_id)
    _check_revision(expected_revision, outline_revision(actor, course))
    if not isinstance(title, str):
        raise ValidationError({"title": "Modul nomini kiriting."})
    if module_id is None:
        order = (course.modules.aggregate(last=Max("order"))["last"] or 0) + 1
        module = Module(course=course, order=order)
        before = {}
    else:
        module = Module.objects.select_for_update().get(pk=module_id, course=course)
        before = _module_state(module)
    module.title = title.strip()
    module.full_clean()
    after = _module_state(module)
    created = module.pk is None
    if not created and before == after:
        return module, False
    module.save()
    _audit(actor=actor, action="module.create" if created else "module.update",
           target=module, before=before, after=after, request=request)
    return module, True


@transaction.atomic
def move_module(*, actor, course_id, module_id, direction, expected_revision, request=None):
    """Move one module one step; never trust an arbitrary submitted ID list."""
    actor = _actor(actor)
    course = _course(actor, course_id)
    _check_revision(expected_revision, outline_revision(actor, course))
    if direction not in ("up", "down"):
        raise ValidationError({"direction": "Yuqoriga yoki pastga siljitishni tanlang."})
    modules = list(course.modules.select_for_update().order_by("order", "pk"))
    module = next((item for item in modules if str(item.pk) == str(module_id)), None)
    if module is None:
        raise Module.DoesNotExist
    index = modules.index(module)
    destination = index + (-1 if direction == "up" else 1)
    if not 0 <= destination < len(modules):
        return False
    before = {str(item.pk): item.order for item in modules}
    modules[index], modules[destination] = modules[destination], modules[index]
    for position, item in enumerate(modules, 1):
        item.order = position
    Module.objects.bulk_update(modules, ["order"])
    _audit(actor=actor, action="module.reorder", target=course, before=before,
           after={str(item.pk): item.order for item in modules}, request=request)
    return True


@transaction.atomic
def save_lesson(*, actor, course_id, data, expected_revision, lesson_id=None, request=None):
    actor = _actor(actor)
    course = _course(actor, course_id)
    if lesson_id is None:
        lesson = None
        _check_revision(expected_revision, outline_revision(actor, course))
    else:
        lesson = Lesson.objects.select_for_update().get(pk=lesson_id, module__course=course)
        _check_revision(expected_revision, lesson_revision(actor, lesson))
    before = _lesson_state(lesson) if lesson is not None else {}
    required = ("title", "module") if lesson is None else LESSON_FIELDS
    missing = {name: "Bu maydonni to‘ldiring." for name in required if name not in data}
    if missing:
        raise ValidationError(missing)
    module_value = data["module"]
    module_id = module_value.pk if isinstance(module_value, Module) else module_value
    try:
        module = course.modules.select_for_update().get(pk=module_id)
    except (Module.DoesNotExist, TypeError, ValueError, ValidationError):
        raise ValidationError({"module": "Shu kursdagi modulni tanlang."}) from None
    if lesson is None:
        next_order = (module.lessons.aggregate(last=Max("order"))["last"] or 0) + 1
        lesson = Lesson(module=module, order=next_order)
    lesson.module = module
    for name in LESSON_FIELDS:
        if name != "module" and name in data:
            setattr(lesson, name, data[name])
    if not isinstance(lesson.title, str):
        raise ValidationError({"title": "Dars nomini kiriting."})
    lesson.title = lesson.title.strip()
    lesson.video_url = lesson.video_url or ""
    lesson.content = lesson.content or ""
    lesson.full_clean()
    after = _lesson_state(lesson)
    created = lesson.pk is None
    if not created and before == after:
        return lesson, False
    lesson.save()
    _audit(actor=actor, action="lesson.create" if created else "lesson.update",
           target=lesson, before=before, after=after, request=request)
    return lesson, True
