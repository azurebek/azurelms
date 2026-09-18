"""Kutubxonaning canonical yozuv va o'qish yo'llari.

Doktrina: biznes qoidasi servisda turadi, yuzalar (backoffice sahifasi, dars
sahifasi, kelajakdagi bot yoki Mini App) shu funksiyalarni chaqiradi. Shu
sabab "o'quvchi bu materialni ko'ra oladimi" degan savolga javob **bitta**
joyda — `material_visible_to_student()` da.

Uch qoida bu yerda majburlanadi:

1. **Fayl bir marta saqlanadi.** Biriktirish faylni nusxalamaydi, `ForeignKey`
   qo'yadi (`LessonMaterial`).
2. **Yetim fayl qolmaydi.** Fayl almashtirilsa eskisi commitdan keyin
   o'chiriladi; manba butunlay o'chirilsa fayli ham o'chadi.
3. **Ishlatilayotgan manba o'chmaydi.** Uni faqat arxivlash mumkin; arxiv
   mavjud darslarni buzmaydi, faqat yangi biriktirishga taklif qilinmaydi.
"""

import hashlib
import os

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.upload_validation import validate_upload

from .models import (
    LessonMaterial,
    LibraryResource,
    LibrarySettings,
    LibraryTag,
    MaterialAudience,
)


class ResourceInUse(Exception):
    """Manba darslarda ishlatilayotgani uchun o'chirib bo'lmaydi."""


def _checksum(upload):
    """Yuklangan faylning SHA-256 yig'indisi; pozitsiya boshiga qaytariladi."""
    digest = hashlib.sha256()
    try:
        upload.seek(0)
        for chunk in upload.chunks():
            digest.update(chunk)
    finally:
        try:
            upload.seek(0)
        except (AttributeError, ValueError):
            pass
    return digest.hexdigest()


def apply_upload(resource, upload, *, actor=None):
    """Faylni tekshiradi va `resource` ga metadatasi bilan biriktiradi.

    Saqlash (`resource.save()`) chaqiruvchida qoladi — forma bitta tranzaksiyada
    qolgan maydonlarni ham yozadi. Bu funksiya faqat fayl bilan bog'liq
    maydonlarni to'ldiradi va **eski faylni o'chirishni** commitga rejalashtiradi.
    """
    kind = validate_upload(
        upload,
        profile="library",
        field_label="Fayl",
        max_bytes=LibrarySettings.max_upload_bytes(),
    )
    previous_name = resource.file.name if (resource.pk and resource.file) else ""

    resource.file = upload
    resource.original_filename = os.path.basename(getattr(upload, "name", "") or "")[:200]
    resource.file_kind = kind or ""
    resource.file_size = getattr(upload, "size", 0) or 0
    resource.checksum = _checksum(upload)
    if previous_name:
        resource.version = (resource.version or 1) + 1
    if getattr(actor, "pk", None):
        resource.updated_by = actor
        if resource.created_by_id is None:
            resource.created_by = actor

    if previous_name:
        storage = resource.file.storage

        def _drop_old():
            # Yangi fayl boshqa nom bilan saqlanadi; eskisini olib tashlamasak
            # `PRIVATE_MEDIA_ROOT` da hech kim havola qilmaydigan bayt qoladi.
            if previous_name and previous_name != resource.file.name:
                storage.delete(previous_name)

        transaction.on_commit(_drop_old)
    return resource


def sync_tags(resource, raw_tags):
    """`"A1, speaking"` matnidan teglarni yaratadi va manbaga bog'laydi."""
    names = LibraryTag.normalize(raw_tags)
    tags = []
    for name in names:
        tag, _ = LibraryTag.objects.get_or_create(name=name)
        tags.append(tag)
    resource.tags.set(tags)
    return tags


def tags_as_text(resource):
    return ", ".join(tag.name for tag in resource.tags.all())


def duplicate_candidates(checksum, *, exclude_pk=None):
    """Bir xil baytli manbalar — yuklovchini ogohlantirish uchun."""
    if not checksum:
        return LibraryResource.objects.none()
    queryset = LibraryResource.objects.filter(checksum=checksum)
    if exclude_pk:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset


def delete_resource(resource):
    """Manbani butunlay o'chiradi — faqat hech qayerda ishlatilmasa.

    Ishlatilayotgan bo'lsa `ResourceInUse`: bu holatda to'g'ri amal arxivlash.
    Fayl ham o'chiriladi, aks holda ombordagi bayt yetim qolardi.
    """
    if resource.lesson_links.exists():
        raise ResourceInUse(
            "Bu material darslarga biriktirilgan — o'chirish o'rniga arxivlang."
        )
    name = resource.file.name if resource.file else ""
    storage = resource.file.storage if resource.file else None
    resource.delete()
    if name and storage is not None:
        transaction.on_commit(lambda: storage.delete(name))


@transaction.atomic
def attach_to_lesson(lesson, resource, *, actor=None, **options):
    """Manbani darsga biriktiradi; tartib oxiriga qo'yiladi.

    Takroriy biriktirish yangi qator yaratmaydi (`unique` juftlik) — mavjudi
    qaytariladi. Ustoz uchun belgilangan manba avtomatik `teacher` auditoriyasi
    bilan biriktiriladi; modeldagi `clean()` bu qoidani yana bir bor tekshiradi.
    """
    existing = LessonMaterial.objects.filter(lesson=lesson, resource=resource).first()
    if existing is not None:
        return existing, False

    last_order = (
        LessonMaterial.objects.filter(lesson=lesson)
        .order_by("-order")
        .values_list("order", flat=True)
        .first()
    )
    audience = options.pop("audience", None)
    if resource.is_teacher_only:
        audience = MaterialAudience.TEACHER
    material = LessonMaterial(
        lesson=lesson,
        resource=resource,
        order=(last_order or 0) + 1,
        audience=audience or MaterialAudience.STUDENT,
        added_by=actor if getattr(actor, "pk", None) else None,
        **options,
    )
    material.full_clean(exclude=["lesson", "resource", "added_by"])
    material.save()
    return material, True


@transaction.atomic
def reorder_materials(lesson, ordered_ids):
    """Berilgan ID tartibiga ko'ra `order` qiymatlarini qayta yozadi."""
    materials = {m.pk: m for m in LessonMaterial.objects.filter(lesson=lesson)}
    position = 0
    for raw_id in ordered_ids:
        material = materials.pop(int(raw_id), None)
        if material is None:
            continue
        position += 1
        if material.order != position:
            material.order = position
            material.save(update_fields=["order", "updated_at"])
    # Ro'yxatga tushmagan qatorlar oxiriga suriladi — tartib raqami
    # takrorlanib qolmasin.
    for material in materials.values():
        position += 1
        if material.order != position:
            material.order = position
            material.save(update_fields=["order", "updated_at"])


def validate_audience(material):
    """Auditoriya o'zgarishi manbadagi cheklovga zid emasligini tekshiradi."""
    try:
        material.full_clean(exclude=["lesson", "resource", "added_by"])
    except ValidationError:
        raise
    return material


# --------------------------------------------------------------------------- #
# O'qish yo'llari
# --------------------------------------------------------------------------- #

def teacher_materials(lesson):
    """Dars muharriri uchun barcha biriktirmalar (yopiqlari ham)."""
    return (
        LessonMaterial.objects.filter(lesson=lesson)
        .select_related("resource")
        .order_by("order", "pk")
    )


def material_visible_to_student(material, *, now=None):
    """Biriktirma darajasidagi ko'rinuvchanlik — yagona qoida."""
    return material.is_open_for_student(now=now)


def student_materials(lesson, *, now=None):
    """Darsda o'quvchiga ko'rinadigan materiallar.

    Dars qulfi bu yerda tekshirilmaydi: chaqiruvchi allaqachon darsga kirish
    huquqini tekshirgan bo'ladi (`courses/access_service.py`). Fayl view'i esa
    ikkalasini birga tekshiradi — UI ko'rsatmasligi himoya emas.
    """
    moment = now or timezone.now()
    return [
        material
        for material in LessonMaterial.objects.filter(lesson=lesson)
        .select_related("resource")
        .order_by("order", "pk")
        if material_visible_to_student(material, now=moment)
    ]


def student_can_open(user, material, *, now=None):
    """O'quvchi shu materialning **faylini** ocha oladimi.

    Uch shart birga: biriktirma ochiq, o'quvchining kursga faol obunasi bor va
    dars qulfi ochiq. Uchtasi ham serverda tekshiriladi.
    """
    if not material_visible_to_student(material, now=now):
        return False

    from cohorts.models import Enrollment
    from courses.access_service import check_lesson_access

    lesson = material.lesson
    course_id = lesson.module.course_id
    enrollment = (
        Enrollment.objects.with_active_access()
        .filter(student=user, cohort__course_id=course_id)
        .select_related("cohort")
        .first()
    )
    if enrollment is None:
        return False
    return check_lesson_access(user=user, lesson=lesson, enrollment=enrollment).is_allowed
