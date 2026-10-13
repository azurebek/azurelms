"""Canonical, scoped commands for a material's use in one lesson.

The signed snapshots retain the existing editor token format. They are checked
under actor/course/lesson/resource/link locks, independently of presentation
flags. These commands never replace or delete the shared resource file.
"""
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.crypto import constant_time_compare, salted_hmac

from core.access import teacher_course_queryset
from core.audit import record_audit_event
from courses.models import Lesson
from library.backoffice_forms import LessonMaterialForm
from library.models import LessonMaterial, LibraryResource
from library.services import reorder_materials as _save_order


class MaterialConflict(ValidationError):
    def __init__(self):
        super().__init__('Ma’lumot boshqa oynada o‘zgargan. Saqlanmadi; yozganlaringizni olib, so‘nggi holatni oching.', code='stale')


def _sign(actor, action, state):
    return salted_hmac('frontend-v1-editors', json.dumps([actor.pk, action, state], default=str),
                       algorithm='sha256').hexdigest()


def material_revision(actor, material, action='material'):
    state = [str(field.value_from_object(material)) for field in material._meta.concrete_fields]
    state += [str(material.resource.updated_at), material.resource.is_teacher_only]
    return _sign(actor, action, state)


def reorder_revision(actor, lesson):
    return _sign(actor, 'reorder', [lesson.pk, list(lesson.materials.order_by('pk')
        .values_list('pk', 'order', 'updated_at'))])


def _revision(expected, current):
    if not isinstance(expected, str) or not constant_time_compare(expected, current):
        raise MaterialConflict()


def _actor(actor):
    if not getattr(actor, 'is_authenticated', False) or not getattr(actor, 'pk', None):
        raise PermissionDenied
    current = get_user_model().objects.select_for_update().filter(pk=actor.pk).first()
    if current is None or not current.is_active or not (current.is_staff or current.is_superuser):
        raise PermissionDenied
    return current


def _lesson(actor, lesson_id, course_id=None):
    reference = Lesson.objects.select_related('module').get(pk=lesson_id)
    if course_id is not None and reference.module.course_id != course_id:
        raise Lesson.DoesNotExist
    # Scope is rechecked against the current actor and locked course.
    course = teacher_course_queryset(actor).select_for_update().filter(pk=reference.module.course_id).first()
    if course is None:
        raise Lesson.DoesNotExist
    return Lesson.objects.select_for_update().get(pk=lesson_id, module__course_id=course.pk)


def _material(actor, material_id, lesson_id=None, course_id=None):
    reference = LessonMaterial.objects.get(pk=material_id)
    if lesson_id is not None and reference.lesson_id != lesson_id:
        raise LessonMaterial.DoesNotExist
    lesson = _lesson(actor, reference.lesson_id, course_id)
    resource = LibraryResource.objects.select_for_update().get(pk=reference.resource_id)
    material = LessonMaterial.objects.select_for_update().get(
        pk=material_id, lesson_id=lesson.pk, resource_id=resource.pk)
    material.lesson, material.resource = lesson, resource
    return material


def _duplicate(data, keys):
    if hasattr(data, 'getlist'):
        return any(len(data.getlist(key)) != 1 for key in keys if key in data)
    return any(isinstance(data.get(key), (list, tuple)) for key in keys if key in data)


def _state(material):
    return {name: (value.isoformat() if hasattr(value, 'isoformat') else value)
            for name in LessonMaterialForm.Meta.fields
            for value in [getattr(material, name)]}


@transaction.atomic
def update_material(*, actor, material_id, data, expected_revision, request=None,
                    lesson_id=None, course_id=None):
    actor = _actor(actor)
    material = _material(actor, material_id, lesson_id, course_id)
    _revision(expected_revision, material_revision(actor, material))
    if _duplicate(data, LessonMaterialForm.Meta.fields):
        raise ValidationError('Takrorlangan maydon. Hech narsa saqlanmadi.')
    before = _state(material)
    form = LessonMaterialForm(data, instance=material)
    if not form.is_valid():
        raise ValidationError(form.errors.as_data())
    after = _state(material)
    changed = before != after
    if changed:
        form.save()
        record_audit_event(action='library.material.update', actor=actor, request=request,
            target=material, before=before, after=after)
    return material, changed


@transaction.atomic
def detach_material(*, actor, material_id, expected_revision, request=None,
                    lesson_id=None, course_id=None):
    actor = _actor(actor)
    material = _material(actor, material_id, lesson_id, course_id)
    _revision(expected_revision, material_revision(actor, material, 'detach'))
    result = material.lesson_id
    record_audit_event(action='library.material.detach', actor=actor, request=request,
        target=material, before={'lesson': result, 'resource': material.resource_id})
    material.delete()
    return result


@transaction.atomic
def reorder_materials(*, actor, lesson_id, positions, expected_revision, request=None, course_id=None):
    actor = _actor(actor)
    lesson = _lesson(actor, lesson_id, course_id)
    _revision(expected_revision, reorder_revision(actor, lesson))
    materials = list(LessonMaterial.objects.select_for_update().filter(lesson=lesson).order_by('order', 'pk'))
    expected_keys = {f'order-{item.pk}' for item in materials}
    submitted_keys = {key for key in positions if key.startswith('order-')}
    invalid = expected_keys != submitted_keys or _duplicate(positions, expected_keys)
    ordered = []
    for material in materials:
        raw = positions.get(f'order-{material.pk}')
        if (not isinstance(raw, str) or not raw or not raw.isascii() or not raw.isdecimal()
                or len(raw) > 10 or int(raw) > 2147483647):
            invalid = True
        else:
            ordered.append((int(raw), material.order, material.pk))
    if invalid:
        raise ValidationError('Har bir material uchun 0–2147483647 oralig‘ida bitta butun tartib raqamini kiriting.')
    ordered.sort()
    before = {str(item.pk): item.order for item in materials}
    after = {str(item[2]): position for position, item in enumerate(ordered, 1)}
    changed = before != after
    if changed:
        _save_order(lesson, [item[2] for item in ordered])
        record_audit_event(action='library.material.reorder', actor=actor, request=request,
            target=lesson, before=before, after=after)
    return changed
