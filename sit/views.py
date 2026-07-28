from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Announcement, KnowledgeArticle, University, UniversityProgram
from .selectors import (
    apply_catalog_filters,
    catalog_filter_options,
    portal_stats,
    university_catalog_queryset,
    university_detail_queryset,
)


def home(request):
    base_queryset = university_catalog_queryset()
    featured_universities = list(
        base_queryset.filter(is_featured=True, admission_status=University.AdmissionStatus.OPEN)[:3]
    )
    if len(featured_universities) < 3:
        existing_ids = [university.pk for university in featured_universities]
        featured_universities.extend(
            list(
                base_queryset.filter(admission_status=University.AdmissionStatus.OPEN)
                .exclude(pk__in=existing_ids)[: 3 - len(featured_universities)]
            )
        )

    context = {
        "active_nav": "home",
        "featured_universities": featured_universities,
        "announcements": (
            Announcement.objects.filter(is_published=True)
            .select_related("university")
            .order_by("order", "-published_on")[:4]
        ),
        "knowledge_articles": KnowledgeArticle.objects.published().filter(is_featured=True)[:3],
        "portal_stats": portal_stats(),
    }
    return render(request, "sit/home.html", context)


def university_list(request):
    queryset, filter_state = apply_catalog_filters(university_catalog_queryset(), request.GET)
    paginator = Paginator(queryset, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "active_nav": "universities",
        "universities": page_obj.object_list,
        "page_obj": page_obj,
        "result_count": paginator.count,
        "filters": filter_state,
        **catalog_filter_options(),
    }
    return render(request, "sit/university_list.html", context)


def _program_sections(university):
    sections = []
    for degree_value, degree_label in UniversityProgram.DegreeLevel.choices:
        faculty_groups = []
        for faculty in university.visible_faculties:
            programs = [
                program
                for program in faculty.visible_programs
                if program.degree_level == degree_value
            ]
            if programs:
                faculty_groups.append({"faculty": faculty, "programs": programs})
        if faculty_groups:
            sections.append(
                {
                    "value": degree_value,
                    "label": degree_label,
                    "faculty_groups": faculty_groups,
                }
            )
    return sections


def university_detail(request, slug):
    include_unpublished = bool(
        request.GET.get("preview") == "1"
        and request.user.is_authenticated
        and (request.user.is_staff or request.user.is_superuser)
    )
    university = get_object_or_404(
        university_detail_queryset(include_unpublished=include_unpublished),
        slug=slug,
    )
    context = {
        "active_nav": "universities",
        "university": university,
        "program_sections": _program_sections(university),
        "is_preview": include_unpublished and not university.is_published,
    }
    return render(request, "sit/university_detail.html", context)


def knowledge_detail(request, slug):
    include_unpublished = bool(
        request.GET.get("preview") == "1"
        and request.user.is_authenticated
        and (request.user.is_staff or request.user.is_superuser)
    )
    queryset = KnowledgeArticle.objects.all() if include_unpublished else KnowledgeArticle.objects.published()
    article = get_object_or_404(queryset, slug=slug)
    return render(
        request,
        "sit/knowledge_detail.html",
        {
            "active_nav": "knowledge",
            "article": article,
            "is_preview": include_unpublished and not article.is_published,
        },
    )
