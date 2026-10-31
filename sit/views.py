from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse

from frontend.public_query import MAX_QUERY_CHARS, pagination_context
from frontend.public_v1 import render_public, safe_return_to

from . import public
from .models import KnowledgeArticle, University, UniversityProgram
from .policy import preview_requested
from .selectors import (
    apply_catalog_filters,
    catalog_filter_options,
    featured_open_universities,
    portal_stats,
    university_catalog_queryset,
    university_detail_queryset,
)

CATALOG_PAGE_SIZE = 12


def home(request):
    context = {
        "active_nav": "home",
        "featured_universities": featured_open_universities(3),
        "announcements": (
            public.effective_announcements()
            .filter(show_on_home=True)
            .select_related("university")
            .order_by("order", "-published_on", "-id")[:4]
        ),
        "knowledge_articles": public.effective_articles().filter(is_featured=True)[:3],
        "portal_stats": portal_stats(),
    }
    return render_public(request, "sit/home.html", context)


def university_list(request):
    """Ochiq SIT katalogi: chegaralangan kirish, toza sahifa havolalari (PUB1.6b).

    Mavjud bo'lmagan sahifa 404 — boshqa sahifaning nusxasi emas (katalog va Blog
    bilan bir xil).
    """
    queryset, filter_state = apply_catalog_filters(university_catalog_queryset(), request.GET)
    paginator = Paginator(queryset.order_by("order", "name", "id"), CATALOG_PAGE_SIZE)
    try:
        page_obj = paginator.page(request.GET.get("page") or 1)
    except (EmptyPage, PageNotAnInteger):
        raise Http404
    return_to = public.catalog_url(filter_state, page=page_obj.number)
    context = {
        "active_nav": "universities",
        "universities": page_obj.object_list,
        "page_obj": page_obj,
        "result_count": paginator.count,
        "filters": filter_state,
        "status_label": dict(University.AdmissionStatus.choices).get(filter_state["status"], "Barchasi"),
        "max_query_chars": MAX_QUERY_CHARS,
        # Universitet sahifasidagi "orqaga" ayni filtr va sahifaga qaytaradi.
        "sit_return_to": "" if return_to == reverse("sit:university_list") else return_to,
        "pages_label": "Universitetlar sahifalari",
        **pagination_context(
            page_obj, paginator.num_pages > 1, lambda number: public.catalog_url(filter_state, page=number)
        ),
        **catalog_filter_options(),
    }
    return render_public(request, "sit/university_list.html", context)


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
    include_unpublished = preview_requested(request)
    university = get_object_or_404(
        university_detail_queryset(include_unpublished=include_unpublished),
        slug=slug,
    )
    context = {
        "active_nav": "universities",
        "university": university,
        "program_sections": _program_sections(university),
        "is_preview": include_unpublished and not university.is_published,
        "public_back_url": safe_return_to(request, reverse("sit:university_list")),
    }
    return render_public(request, "sit/university_detail.html", context)


def knowledge_detail(request, slug):
    include_unpublished = preview_requested(request)
    queryset = KnowledgeArticle.objects.all() if include_unpublished else public.effective_articles()
    article = get_object_or_404(queryset, slug=slug)
    return render_public(
        request,
        "sit/knowledge_detail.html",
        {
            "active_nav": "knowledge",
            "article": article,
            "is_preview": include_unpublished and not article.is_published,
        },
    )
