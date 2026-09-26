"""Kutubxonaning ichki yuzasi — faqat staff/owner uchun.

Ruxsat qoidasi ikki qatlamli va **ikkalasi ham serverda**:

* kutubxonaga kirish — `core.access.is_backoffice_user` (staff yoki owner);
* darsga biriktirish/uzish — `core.access.teacher_course_queryset`, ya'ni
  o'qituvchi faqat **o'ziga biriktirilgan kurs** darsiga tegadi (default-deny).

O'quvchi uchun bu yerda hech qanday manzil yo'q: u faqat darsdagi biriktirmani
`library/views.py` orqali ochadi.

**Ombor staff uchun umumiy.** Manbalar o'qituvchilar orasida bo'linmaydi —
maqsad aynan qayta ishlatish, va hozir mualliflar soni bitta-ikkita. Yozuvni
cheklaydigan chegara boshqa joyda: darsga biriktirish faqat o'z kursida
mumkin. Kelajakda muallif bo'yicha scope kerak bo'lsa, o'zgarish
`selectors.search_resources(base_queryset=...)` ga tushadi.

**Audit nimaga yoziladi.** Repo qoidasi bo'yicha auditlangan mutation shakli
(sabab + tasdiq) operatsion boshqaruv yuzalari uchun. Kontent yozish har safar
sabab so'rashni ko'tarmaydi, shuning uchun bu yerda sabab so'ralmaydi, ammo
**hayotiy sikl** amallari — arxivlash, tiklash, o'chirish va fayl almashtirish —
`SystemAuditEvent` ga tushadi: aynan shular keyin "bu material qayerga ketdi"
degan savolni tug'diradi.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.access import is_backoffice_user, teacher_course_queryset
from core.audit import audit_trail_for, record_audit_event
from core import frontend_v1_editors as editor_v1
from core.private_media_views import serve_private_file
from courses.models import Lesson

from . import selectors, services
from . import frontend_v1 as v1
from .backoffice_forms import LessonMaterialForm, LibraryResourceForm
from .models import (
    FILE_KIND_LABELS,
    LessonMaterial,
    LibraryResource,
    LibrarySettings,
    ResourceLanguage,
    ResourceLevel,
    ResourceType,
)


def _base_context(active, **extra):
    return {
        "active_nav": "backoffice",
        "bo_active": active,
        "counts": {},
        **extra,
    }


def _filter_options(filters):
    """Filtr paneli uchun tanlovlar va joriy holat."""
    return {
        "filters": filters,
        "type_choices": ResourceType.choices,
        "language_choices": ResourceLanguage.choices,
        "level_choices": ResourceLevel.choices,
        "kind_choices": [
            (kind, FILE_KIND_LABELS.get(kind, kind.upper()))
            for kind in selectors.used_file_kinds()
        ],
        "tag_choices": selectors.popular_tags(),
    }


def _editable_lesson(user, lesson_id):
    """Foydalanuvchi tahrirlay oladigan dars yoki 404.

    404 ataylab: 403 begona kursda shu ID li dars borligini tasdiqlab qo'yardi.
    """
    return get_object_or_404(
        Lesson.objects.select_related("module__course").filter(
            module__course__in=teacher_course_queryset(user)
        ),
        pk=lesson_id,
    )


@login_required
@user_passes_test(is_backoffice_user)
def resource_list(request):
    """Kutubxona ro'yxati: qidiruv, filtrlar, sahifalash."""
    filters = selectors.filters_from_request(request)
    resources = selectors.search_resources(**filters)
    page_obj = Paginator(resources, selectors.PAGE_SIZE).get_page(request.GET.get("page"))

    stats = LibraryResource.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_archived=False)),
        archived=Count("id", filter=Q(is_archived=True)),
    )
    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = _base_context(
        "library",
        page_obj=page_obj,
        stats=stats,
        courses=teacher_course_queryset(request.user).order_by("title"),
        querystring=query_params.urlencode(),
        **_filter_options(filters),
    )
    return v1.render_library(request, 'list', context)


@login_required
@user_passes_test(is_backoffice_user)
@transaction.atomic
def resource_editor(request, resource_id=None):
    """Material yuklash (yangi) yoki metadatasini tahrirlash."""
    resources = (LibraryResource.objects.select_for_update() if request.method == 'POST'
                 else LibraryResource.objects.select_related('course'))
    resource = (
        get_object_or_404(resources, pk=resource_id)
        if resource_id
        else None
    )
    error = v1.write_error(request, resource, 'save') if request.method == 'POST' else None
    previous_file = resource.file.name if resource and resource.file else ''
    form = LibraryResourceForm(
        request.POST if request.method == 'POST' else None,
        request.FILES or None,
        instance=resource,
        user=request.user,
    )

    valid = form.is_valid() if request.method == 'POST' else False
    if error:
        form.add_error(None, error[0])
    if request.method == "POST" and valid and not error:
        is_new = resource is None
        upload = form.uploaded_file
        obj = form.save(commit=False)
        if upload is not None:
            # ModelForm has already assigned the new upload to obj.file.
            # apply_upload must see the OLD stored name for commit-time cleanup.
            obj.file = previous_file
            services.apply_upload(obj, upload, actor=request.user)
        if is_new and not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        obj.save()
        services.sync_tags(obj, form.cleaned_data.get("tags_text", ""))

        if is_new or upload is not None:
            record_audit_event(
                action="library.resource.create" if is_new else "library.resource.file_replace",
                request=request,
                target=obj,
                target_label=obj.title,
                after={"version": obj.version, "file_kind": obj.file_kind, "size": obj.file_size},
            )
        messages.success(request, "Material saqlandi.")
        return redirect("library_backoffice:resource_edit", resource_id=obj.pk)

    if resource and request.method == 'POST':
        # Invalid ModelForm mutates its instance: sidebar must show saved state,
        # while bound inputs retain exactly the rejected user's draft.
        resource = LibraryResource.objects.select_related('course').get(pk=resource.pk)

    usage = (
        LessonMaterial.objects.filter(resource=resource)
        .select_related("lesson__module__course")
        .order_by("lesson__module__course__title", "lesson__module__order", "lesson__order")
        if resource
        else LessonMaterial.objects.none()
    )
    duplicates = (
        services.duplicate_candidates(resource.checksum, exclude_pk=resource.pk)[:5]
        if resource
        else LibraryResource.objects.none()
    )
    context = _base_context(
        "library",
        resource=resource,
        form=form,
        usage=usage,
        duplicates=duplicates,
        audit_events=audit_trail_for(resource) if resource else [],
        max_upload_mb=LibrarySettings.max_upload_bytes() // (1024 * 1024),
        library_conflict=bool(error and error[1] == 409),
    )
    status = error[1] if error else (400 if request.method == 'POST' and v1.enabled(request) else 200)
    return v1.render_library(request, 'form', context, status=status)


@login_required
@user_passes_test(is_backoffice_user)
@require_POST
@transaction.atomic
def resource_archive(request, resource_id):
    """Arxivlash/tiklash — o'chirishning xavfsiz muqobili."""
    resource = get_object_or_404(LibraryResource.objects.select_for_update(), pk=resource_id)
    error = v1.write_error(request, resource, 'archive')
    if error:
        return v1.action_error(request, error, resource)
    if resource.is_archived:
        resource.restore(actor=request.user)
        action, note = "library.resource.restore", "Material arxivdan qaytarildi."
    else:
        resource.archive(actor=request.user)
        action, note = "library.resource.archive", "Material arxivlandi."
    record_audit_event(
        action=action,
        request=request,
        target=resource,
        target_label=resource.title,
        after={"is_archived": resource.is_archived, "usage": resource.usage_total},
    )
    messages.success(request, note)
    return redirect("library_backoffice:resource_edit", resource_id=resource.pk)


@login_required
@user_passes_test(is_backoffice_user)
@require_POST
@transaction.atomic
def resource_delete(request, resource_id):
    """Butunlay o'chirish — faqat hech qayerda ishlatilmagan material uchun."""
    resource = get_object_or_404(LibraryResource.objects.select_for_update(), pk=resource_id)
    error = v1.write_error(request, resource, 'delete')
    if error:
        return v1.action_error(request, error, resource)
    title = resource.title
    try:
        services.delete_resource(resource)
    except services.ResourceInUse as exc:
        messages.error(request, str(exc))
        return redirect("library_backoffice:resource_edit", resource_id=resource_id)

    record_audit_event(
        action="library.resource.delete",
        request=request,
        target_label=title,
        before={"title": title},
    )
    messages.success(request, "Material o'chirildi.")
    return redirect("library_backoffice:resources")


@login_required
@user_passes_test(is_backoffice_user)
def resource_file(request, resource_id):
    """Staff uchun faylni ko'rish/yuklab olish (ruxsat tekshiriladi)."""
    resource = get_object_or_404(LibraryResource, pk=resource_id)
    return serve_private_file(
        request,
        resource.file,
        download_name=resource.original_filename or resource.title,
    )


# --------------------------------------------------------------------------- #
# Dars muharriri bilan integratsiya
# --------------------------------------------------------------------------- #

@login_required
@user_passes_test(is_backoffice_user)
def lesson_picker(request, lesson_id):
    """«Kutubxonadan tanlash» — qidiruvli tanlov sahifasi.

    Modal emas, alohida sahifa: server tomonda render qilinadi, JS'siz ham
    ishlaydi, Back tugmasi va URL'dagi filtr saqlanadi.
    """
    lesson = _editable_lesson(request.user, lesson_id)
    filters = selectors.filters_from_request(request)
    attached_ids = set(
        LessonMaterial.objects.filter(lesson=lesson).values_list("resource_id", flat=True)
    )
    resources = selectors.search_resources(**filters)
    page_obj = Paginator(resources, selectors.PAGE_SIZE).get_page(request.GET.get("page"))
    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = _base_context(
        "lessons",
        lesson=lesson,
        page_obj=page_obj,
        attached_ids=attached_ids,
        courses=teacher_course_queryset(request.user).order_by("title"),
        querystring=query_params.urlencode(),
        **_filter_options(filters),
    )
    return v1.render_library(request, 'picker', context)


@login_required
@user_passes_test(is_backoffice_user)
@require_POST
@transaction.atomic
def material_attach(request, lesson_id):
    """Tanlangan manbani darsga biriktiradi (fayl nusxalanmaydi)."""
    lesson = _editable_lesson(request.user, lesson_id)
    # Same lock order as link settings/detach/reorder: lesson before resource.
    lesson = Lesson.objects.select_for_update().get(pk=lesson.pk)
    resource_id = request.POST.get('resource', '')
    if not resource_id.isascii() or not resource_id.isdecimal() or len(resource_id) > 18:
        raise Http404
    resource = get_object_or_404(
        LibraryResource.objects.select_for_update().filter(is_archived=False), pk=int(resource_id)
    )
    error = v1.write_error(request, resource, 'attach', lesson.pk)
    if error:
        return v1.action_error(request, error, resource, lesson)
    material, created = services.attach_to_lesson(lesson, resource, actor=request.user)
    if created:
        record_audit_event(
            action="library.material.attach",
            request=request,
            target=material,
            target_label=f"{lesson.title} ← {resource.title}",
            after={"lesson": lesson.pk, "resource": resource.pk, "audience": material.audience},
        )
        messages.success(request, "Material darsga biriktirildi.")
    else:
        messages.info(request, "Bu material darsga allaqachon biriktirilgan.")

    if request.POST.get("next") == "picker":
        # Ketma-ket bir nechta material biriktirish uchun tanlov sahifasiga
        # qaytamiz — qidiruv va filtr saqlanadi.
        picker_url = reverse("library_backoffice:lesson_picker", args=[lesson.pk])
        querystring = request.POST.get("querystring", "").strip()
        return redirect(f"{picker_url}?{querystring}" if querystring else picker_url)
    return redirect("backoffice_lesson_edit", lesson_id=lesson.pk)


@login_required
@user_passes_test(is_backoffice_user)
@require_POST
@transaction.atomic
def material_update(request, material_id):
    """Biriktirmaning darsga xos sozlamasini saqlaydi."""
    material = _locked_material(request, material_id)
    error = editor_v1.write_error(request, editor_v1.material_revision(request.user, material, 'material'))
    form = LessonMaterialForm(request.POST, instance=material)
    valid = form.is_valid()
    if error:
        form.add_error(None, error[0])
    if valid and not error:
        form.save()
        messages.success(request, "Material sozlamasi saqlandi.")
    elif editor_v1.enabled(request):
        material.refresh_from_db()
        return editor_v1.render_editor(request, 'material', {
            'material': material, 'form': form,
            'editor_revision': request.POST.get('editor_revision', ''),
            'editor_conflict': bool(error and error[1] == 409),
        }, status=error[1] if error else 400)
    else:
        errors = "; ".join(
            f"{form.fields[name].label if name in form.fields else 'Sozlama'}: {', '.join(errs)}" for name, errs in form.errors.items()
        )
        messages.error(request, errors or "Sozlamani saqlab bo'lmadi.")
    return redirect("backoffice_lesson_edit", lesson_id=material.lesson_id)


@login_required
@user_passes_test(is_backoffice_user)
@require_POST
@transaction.atomic
def material_detach(request, material_id):
    """Biriktirmani uzadi — manba va fayl kutubxonada qoladi."""
    material = _locked_material(request, material_id)
    error = editor_v1.write_error(request, editor_v1.material_revision(request.user, material, 'detach'))
    if error:
        return editor_v1.render_editor(request, 'conflict', {
            'editor_error': error[0],
            'reload_url': reverse('backoffice_lesson_edit', args=[material.lesson_id]),
        }, status=error[1])
    lesson_id = material.lesson_id
    label = f"{material.lesson.title} ← {material.resource.title}"
    material.delete()
    record_audit_event(
        action="library.material.detach",
        request=request,
        target_label=label,
        before={"lesson": lesson_id},
    )
    messages.success(request, "Material darsdan uzildi (kutubxonada qoldi).")
    return redirect("backoffice_lesson_edit", lesson_id=lesson_id)


@login_required
@user_passes_test(is_backoffice_user)
@require_POST
@transaction.atomic
def material_reorder(request, lesson_id):
    """Biriktirmalar tartibini saqlaydi.

    Forma har qator uchun `order-<id>` raqamini yuboradi; raqamlar bo'yicha
    saralab, `order` qiymatlari 1..N qilib qayta yoziladi. Shu sabab bir xil
    raqam kiritilsa ham tartib aniq bo'lib qoladi.
    """
    lesson = _editable_lesson(request.user, lesson_id)
    lesson = Lesson.objects.select_for_update().get(pk=lesson.pk)
    error = editor_v1.write_error(request, editor_v1.reorder_revision(request.user, lesson))
    positions = []
    materials = list(services.teacher_materials(lesson))
    expected_keys = {f'order-{item.pk}' for item in materials}
    submitted_keys = {key for key in request.POST if key.startswith('order-')}
    invalid = expected_keys != submitted_keys
    for material in materials:
        raw = request.POST.get(f"order-{material.pk}")
        material.posted_order = raw if raw is not None else ''
        if (len(request.POST.getlist(f'order-{material.pk}')) != 1 or not raw
                or not raw.isascii() or not raw.isdecimal() or len(raw) > 10 or int(raw) > 2147483647):
            invalid = True
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = material.order
        positions.append((value, material.order, material.pk))
    if editor_v1.enabled(request) and (error or invalid):
        return editor_v1.render_editor(request, 'reorder', {
            'lesson': lesson, 'materials': materials,
            'editor_error': error[0] if error else 'Har bir material uchun 0–2147483647 oralig‘ida bitta butun tartib raqamini kiriting.',
            'editor_revision': request.POST.get('editor_revision', ''),
            'editor_conflict': bool(error and error[1] == 409),
        }, status=error[1] if error else 400)
    positions.sort()
    services.reorder_materials(lesson, [pk for _, _, pk in positions])
    messages.success(request, "Materiallar tartibi saqlandi.")
    return redirect("backoffice_lesson_edit", lesson_id=lesson.pk)


def _locked_material(request, material_id):
    """Called only inside atomic writers. No lock on a nullable joined table."""
    material = get_object_or_404(LessonMaterial, pk=material_id)
    lesson = _editable_lesson(request.user, material.lesson_id)
    Lesson.objects.select_for_update().get(pk=lesson.pk)
    resource = LibraryResource.objects.select_for_update().get(pk=material.resource_id)
    material = get_object_or_404(LessonMaterial.objects.select_for_update(), pk=material_id, lesson_id=lesson.pk)
    material.resource = resource
    return material
