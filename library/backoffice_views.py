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
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.access import is_backoffice_user, teacher_course_queryset
from core.audit import audit_trail_for, record_audit_event
from core.private_media_views import serve_private_file
from courses.models import Lesson

from . import selectors, services
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
    return render(request, "backoffice/library_list.html", context)


@login_required
@user_passes_test(is_backoffice_user)
def resource_editor(request, resource_id=None):
    """Material yuklash (yangi) yoki metadatasini tahrirlash."""
    resource = (
        get_object_or_404(LibraryResource.objects.select_related("course"), pk=resource_id)
        if resource_id
        else None
    )
    form = LibraryResourceForm(
        request.POST or None,
        request.FILES or None,
        instance=resource,
        user=request.user,
    )

    if request.method == "POST" and form.is_valid():
        is_new = resource is None
        upload = form.uploaded_file
        obj = form.save(commit=False)
        if upload is not None:
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
    )
    return render(request, "backoffice/library_form.html", context)


@login_required
@user_passes_test(is_backoffice_user)
@require_POST
def resource_archive(request, resource_id):
    """Arxivlash/tiklash — o'chirishning xavfsiz muqobili."""
    resource = get_object_or_404(LibraryResource, pk=resource_id)
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
def resource_delete(request, resource_id):
    """Butunlay o'chirish — faqat hech qayerda ishlatilmagan material uchun."""
    resource = get_object_or_404(LibraryResource, pk=resource_id)
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
    return render(request, "backoffice/library_picker.html", context)


@login_required
@user_passes_test(is_backoffice_user)
@require_POST
def material_attach(request, lesson_id):
    """Tanlangan manbani darsga biriktiradi (fayl nusxalanmaydi)."""
    lesson = _editable_lesson(request.user, lesson_id)
    resource = get_object_or_404(
        LibraryResource.objects.filter(is_archived=False), pk=request.POST.get("resource")
    )
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
def material_update(request, material_id):
    """Biriktirmaning darsga xos sozlamasini saqlaydi."""
    material = get_object_or_404(
        LessonMaterial.objects.select_related("lesson__module__course", "resource"),
        pk=material_id,
    )
    _editable_lesson(request.user, material.lesson_id)
    form = LessonMaterialForm(request.POST, instance=material)
    if form.is_valid():
        form.save()
        messages.success(request, "Material sozlamasi saqlandi.")
    else:
        errors = "; ".join(
            f"{form.fields[name].label}: {', '.join(errs)}" for name, errs in form.errors.items()
        )
        messages.error(request, errors or "Sozlamani saqlab bo'lmadi.")
    return redirect("backoffice_lesson_edit", lesson_id=material.lesson_id)


@login_required
@user_passes_test(is_backoffice_user)
@require_POST
def material_detach(request, material_id):
    """Biriktirmani uzadi — manba va fayl kutubxonada qoladi."""
    material = get_object_or_404(
        LessonMaterial.objects.select_related("lesson", "resource"), pk=material_id
    )
    _editable_lesson(request.user, material.lesson_id)
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
def material_reorder(request, lesson_id):
    """Biriktirmalar tartibini saqlaydi.

    Forma har qator uchun `order-<id>` raqamini yuboradi; raqamlar bo'yicha
    saralab, `order` qiymatlari 1..N qilib qayta yoziladi. Shu sabab bir xil
    raqam kiritilsa ham tartib aniq bo'lib qoladi.
    """
    lesson = _editable_lesson(request.user, lesson_id)
    positions = []
    for material in LessonMaterial.objects.filter(lesson=lesson):
        raw = request.POST.get(f"order-{material.pk}")
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = material.order
        positions.append((value, material.order, material.pk))
    positions.sort()
    services.reorder_materials(lesson, [pk for _, _, pk in positions])
    messages.success(request, "Materiallar tartibi saqlandi.")
    return redirect("backoffice_lesson_edit", lesson_id=lesson.pk)
