from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.access import is_control_center_owner

from .backoffice_forms import (
    AnnouncementBackofficeForm,
    KnowledgeArticleBackofficeForm,
    UniversityBackofficeForm,
    UniversityDocumentFormSet,
    UniversityFacultyFormSet,
    UniversityMediaFormSet,
    UniversityPreparationCourseFormSet,
    UniversityProgramFormSet,
    UniversityRequirementFormSet,
    UniversityServiceItemFormSet,
)
from .models import Announcement, KnowledgeArticle, University, UniversityProgram


STALE_AFTER_DAYS = 90


def _base_context(active, **extra):
    return {
        "active_nav": "backoffice",
        "bo_active": active,
        "counts": {},
        **extra,
    }


def _audit_record(*, user, obj, action_flag, message):
    LogEntry.objects.log_actions(
        user_id=user.pk,
        queryset=obj.__class__.objects.filter(pk=obj.pk),
        action_flag=action_flag,
        change_message=message,
        single_object=True,
    )


def _recent_audit(obj):
    if not obj or not obj.pk:
        return LogEntry.objects.none()
    content_type = ContentType.objects.get_for_model(obj)
    return LogEntry.objects.filter(
        content_type=content_type,
        object_id=str(obj.pk),
    ).select_related("user")[:8]


def _draft_aware_post(request):
    if request.method != "POST":
        return None
    data = request.POST.copy()
    if "save_draft" in request.POST:
        data["is_published"] = ""
    return data


def _university_formsets(university, data=None, files=None):
    common = {"data": data, "files": files, "instance": university}
    program_queryset = UniversityProgram.objects.filter(
        faculty__university=university
    ).select_related("faculty")
    return [
        {
            "key": "faculties",
            "title": "Fakultet va institutlar",
            "description": "Yangi fakultetni avval saqlang, keyin unga dastur biriktiring.",
            "formset": UniversityFacultyFormSet(prefix="faculties", **common),
        },
        {
            "key": "programs",
            "title": "Dasturlar",
            "description": "Daraja, ta'lim tili, davomiylik va yillik kontrakt.",
            "formset": UniversityProgramFormSet(
                data=data,
                files=files,
                prefix="programs",
                queryset=program_queryset,
                form_kwargs={"university": university},
            ),
        },
        {
            "key": "preparation",
            "title": "Til tayyorlov kurslari",
            "description": "Universitet taklif qiladigan tayyorlov tillari va narxlari.",
            "formset": UniversityPreparationCourseFormSet(prefix="preparation", **common),
        },
        {
            "key": "requirements",
            "title": "Qabul talablari",
            "description": "Abituriyent bajarishi kerak bo'lgan shartlar.",
            "formset": UniversityRequirementFormSet(prefix="requirements", **common),
        },
        {
            "key": "documents",
            "title": "Kerakli hujjatlar",
            "description": "Arizaga ilova qilinadigan hujjatlar ro'yxati.",
            "formset": UniversityDocumentFormSet(prefix="documents", **common),
        },
        {
            "key": "services",
            "title": "Yordam xizmati",
            "description": "AzureLMS ariza yordami tarkibiga kiradigan bandlar.",
            "formset": UniversityServiceItemFormSet(prefix="services", **common),
        },
        {
            "key": "media",
            "title": "Media",
            "description": "Universitet galereyasidagi rasm yoki video havolalari.",
            "formset": UniversityMediaFormSet(prefix="media", **common),
        },
    ]


@login_required
@user_passes_test(is_control_center_owner)
def dashboard(request):
    today = timezone.localdate()
    stale_cutoff = today - timedelta(days=STALE_AFTER_DAYS)
    published_universities = University.objects.filter(is_published=True)
    stale_universities = published_universities.filter(
        Q(last_verified_on__lt=stale_cutoff)
        | Q(last_verified_on__isnull=True)
        | Q(source_url="")
    ).order_by("last_verified_on", "name")

    context = _base_context(
        "sit",
        metrics={
            "universities": University.objects.count(),
            "published_universities": published_universities.count(),
            "open_admissions": published_universities.filter(
                admission_status=University.AdmissionStatus.OPEN
            ).count(),
            "programs": UniversityProgram.objects.filter(is_active=True).count(),
            "announcements": Announcement.objects.filter(is_published=True).count(),
            "guides": KnowledgeArticle.objects.filter(is_published=True).count(),
            "stale": stale_universities.count(),
        },
        stale_after_days=STALE_AFTER_DAYS,
        stale_universities=stale_universities[:8],
        recent_universities=University.objects.annotate(
            program_count=Count("faculties__programs", distinct=True)
        ).order_by("-updated_at")[:6],
        recent_announcements=Announcement.objects.select_related("university").order_by(
            "-updated_at"
        )[:6],
        recent_guides=KnowledgeArticle.objects.order_by("-updated_at")[:6],
    )
    return render(request, "backoffice/sit_dashboard.html", context)


@login_required
@user_passes_test(is_control_center_owner)
def university_list(request):
    queryset = University.objects.annotate(
        program_count=Count("faculties__programs", distinct=True)
    )
    query = request.GET.get("q", "").strip()
    publication = request.GET.get("publication", "all")
    admission = request.GET.get("admission", "all")
    university_type = request.GET.get("type", "all")
    freshness = request.GET.get("freshness", "all")
    stale_cutoff = timezone.localdate() - timedelta(days=STALE_AFTER_DAYS)

    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(short_name__icontains=query)
            | Q(city__icontains=query)
        )
    if publication == "published":
        queryset = queryset.filter(is_published=True)
    elif publication == "draft":
        queryset = queryset.filter(is_published=False)
    if admission != "all":
        queryset = queryset.filter(admission_status=admission)
    if university_type != "all":
        queryset = queryset.filter(university_type=university_type)
    if freshness == "stale":
        queryset = queryset.filter(is_published=True).filter(
            Q(last_verified_on__lt=stale_cutoff)
            | Q(last_verified_on__isnull=True)
            | Q(source_url="")
        )

    paginator = Paginator(queryset.order_by("order", "name"), 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "backoffice/sit_university_list.html",
        _base_context(
            "sit",
            page_obj=page_obj,
            universities=page_obj.object_list,
            result_count=paginator.count,
            filters={
                "q": query,
                "publication": publication,
                "admission": admission,
                "type": university_type,
                "freshness": freshness,
            },
            admission_choices=University.AdmissionStatus.choices,
            type_choices=University.UniversityType.choices,
            stale_cutoff=stale_cutoff,
        ),
    )


@login_required
@user_passes_test(is_control_center_owner)
def university_editor(request, university_id=None):
    university = (
        get_object_or_404(University, pk=university_id)
        if university_id
        else None
    )
    form_data = _draft_aware_post(request)
    form = UniversityBackofficeForm(
        form_data,
        request.FILES or None,
        instance=university,
    )
    formset_sections = (
        _university_formsets(
            university,
            data=request.POST if request.method == "POST" else None,
            files=request.FILES if request.method == "POST" else None,
        )
        if university
        else []
    )

    if request.method == "POST":
        formsets_valid = all(
            section["formset"].is_valid() for section in formset_sections
        )
        if form.is_valid() and formsets_valid:
            related_changes = [
                section["title"]
                for section in formset_sections
                if section["formset"].has_changed()
            ]
            model_changes = form.changed_model_fields
            if university and not model_changes and not related_changes:
                messages.info(request, "O'zgarish topilmadi; hech narsa yozilmadi.")
                return redirect(
                    "sit_backoffice:university_edit",
                    university_id=university.pk,
                )

            is_new = university is None
            with transaction.atomic():
                university = form.save()
                for section in formset_sections:
                    section["formset"].save()
                changed_labels = [
                    form.fields[name].label for name in model_changes
                ] + related_changes
                reason = form.cleaned_data["change_reason"].strip()
                action_flag = ADDITION if is_new else CHANGE
                action = "yaratildi" if is_new else "yangilandi"
                details = ", ".join(changed_labels) or "asosiy ma'lumot"
                _audit_record(
                    user=request.user,
                    obj=university,
                    action_flag=action_flag,
                    message=(
                        f"SIT universiteti {action}: {details}. "
                        f"Sabab: {reason}"
                    ),
                )
            messages.success(request, "Universitet saqlandi.")
            return redirect(
                "sit_backoffice:university_edit",
                university_id=university.pk,
            )

    return render(
        request,
        "backoffice/sit_university_form.html",
        _base_context(
            "sit",
            university=university,
            form=form,
            formset_sections=formset_sections,
            recent_changes=_recent_audit(university),
        ),
    )


@login_required
@user_passes_test(is_control_center_owner)
def announcement_list(request):
    queryset = Announcement.objects.select_related("university")
    query = request.GET.get("q", "").strip()
    publication = request.GET.get("publication", "all")
    category = request.GET.get("category", "all")
    homepage = request.GET.get("homepage", "all")
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) | Q(university__name__icontains=query)
        )
    if publication == "published":
        queryset = queryset.filter(is_published=True)
    elif publication == "draft":
        queryset = queryset.filter(is_published=False)
    if category != "all":
        queryset = queryset.filter(category=category)
    if homepage == "yes":
        queryset = queryset.filter(show_on_home=True)
    elif homepage == "no":
        queryset = queryset.filter(show_on_home=False)
    page_obj = Paginator(queryset.order_by("order", "-published_on"), 24).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "backoffice/sit_content_list.html",
        _base_context(
            "sit",
            content_kind="announcement",
            title="SIT e'lonlari",
            eyebrow="Yangilik va qabullar",
            create_url_name="sit_backoffice:announcement_create",
            objects=page_obj.object_list,
            page_obj=page_obj,
            result_count=page_obj.paginator.count,
            filters={
                "q": query,
                "publication": publication,
                "category": category,
                "homepage": homepage,
            },
            category_choices=Announcement.Category.choices,
        ),
    )


@login_required
@user_passes_test(is_control_center_owner)
def announcement_editor(request, announcement_id=None):
    announcement = (
        get_object_or_404(Announcement, pk=announcement_id)
        if announcement_id
        else None
    )
    form = AnnouncementBackofficeForm(
        _draft_aware_post(request),
        request.FILES or None,
        instance=announcement,
    )
    if request.method == "POST" and form.is_valid():
        changes = form.changed_model_fields
        if announcement and not changes:
            messages.info(request, "O'zgarish topilmadi; hech narsa yozilmadi.")
            return redirect(
                "sit_backoffice:announcement_edit",
                announcement_id=announcement.pk,
            )
        is_new = announcement is None
        with transaction.atomic():
            announcement = form.save()
            labels = [form.fields[name].label for name in changes]
            _audit_record(
                user=request.user,
                obj=announcement,
                action_flag=ADDITION if is_new else CHANGE,
                message=(
                    f"SIT e'loni {'yaratildi' if is_new else 'yangilandi'}: "
                    f"{', '.join(labels) or 'asosiy ma’lumot'}. "
                    f"Sabab: {form.cleaned_data['change_reason'].strip()}"
                ),
            )
        messages.success(request, "E'lon saqlandi.")
        return redirect(
            "sit_backoffice:announcement_edit",
            announcement_id=announcement.pk,
        )
    return render(
        request,
        "backoffice/sit_content_form.html",
        _base_context(
            "sit",
            content_kind="announcement",
            title="SIT e'loni",
            list_url_name="sit_backoffice:announcements",
            obj=announcement,
            form=form,
            recent_changes=_recent_audit(announcement),
        ),
    )


@login_required
@user_passes_test(is_control_center_owner)
def guide_list(request):
    queryset = KnowledgeArticle.objects.all()
    query = request.GET.get("q", "").strip()
    publication = request.GET.get("publication", "all")
    featured = request.GET.get("featured", "all")
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(category__icontains=query)
            | Q(excerpt__icontains=query)
        )
    if publication == "published":
        queryset = queryset.filter(is_published=True)
    elif publication == "draft":
        queryset = queryset.filter(is_published=False)
    if featured == "yes":
        queryset = queryset.filter(is_featured=True)
    elif featured == "no":
        queryset = queryset.filter(is_featured=False)
    page_obj = Paginator(queryset.order_by("order", "-published_on"), 24).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "backoffice/sit_content_list.html",
        _base_context(
            "sit",
            content_kind="guide",
            title="SIT qo'llanmalari",
            eyebrow="Bilim bazasi",
            create_url_name="sit_backoffice:guide_create",
            objects=page_obj.object_list,
            page_obj=page_obj,
            result_count=page_obj.paginator.count,
            filters={
                "q": query,
                "publication": publication,
                "featured": featured,
            },
        ),
    )


@login_required
@user_passes_test(is_control_center_owner)
def guide_editor(request, guide_id=None):
    guide = (
        get_object_or_404(KnowledgeArticle, pk=guide_id)
        if guide_id
        else None
    )
    form = KnowledgeArticleBackofficeForm(
        _draft_aware_post(request),
        request.FILES or None,
        instance=guide,
    )
    if request.method == "POST" and form.is_valid():
        changes = form.changed_model_fields
        if guide and not changes:
            messages.info(request, "O'zgarish topilmadi; hech narsa yozilmadi.")
            return redirect("sit_backoffice:guide_edit", guide_id=guide.pk)
        is_new = guide is None
        with transaction.atomic():
            guide = form.save()
            labels = [form.fields[name].label for name in changes]
            _audit_record(
                user=request.user,
                obj=guide,
                action_flag=ADDITION if is_new else CHANGE,
                message=(
                    f"SIT qo'llanmasi {'yaratildi' if is_new else 'yangilandi'}: "
                    f"{', '.join(labels) or 'asosiy ma’lumot'}. "
                    f"Sabab: {form.cleaned_data['change_reason'].strip()}"
                ),
            )
        messages.success(request, "Qo'llanma saqlandi.")
        return redirect("sit_backoffice:guide_edit", guide_id=guide.pk)
    return render(
        request,
        "backoffice/sit_content_form.html",
        _base_context(
            "sit",
            content_kind="guide",
            title="SIT qo'llanmasi",
            list_url_name="sit_backoffice:guides",
            obj=guide,
            form=form,
            recent_changes=_recent_audit(guide),
        ),
    )
