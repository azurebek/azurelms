from django.db.models import Prefetch, Q

from .models import (
    University,
    UniversityDocument,
    UniversityFaculty,
    UniversityMedia,
    UniversityPreparationCourse,
    UniversityProgram,
    UniversityRequirement,
    UniversityServiceItem,
)


PRICE_FILTERS = {
    "under_1000": Q(tuition_from__lte=1000),
    "1000_2000": Q(tuition_from__gte=1000, tuition_from__lte=2000),
    "over_2000": Q(tuition_from__gt=2000),
}


def _faculty_queryset():
    return UniversityFaculty.objects.filter(is_active=True).prefetch_related(
        Prefetch(
            "programs",
            queryset=UniversityProgram.objects.filter(is_active=True).order_by("order", "name"),
            to_attr="visible_programs",
        )
    ).order_by("order", "name")


def university_catalog_queryset(*, include_unpublished=False):
    queryset = University.objects.all() if include_unpublished else University.objects.published()
    return queryset.prefetch_related(
        Prefetch("faculties", queryset=_faculty_queryset(), to_attr="visible_faculties")
    )


def university_detail_queryset(*, include_unpublished=False):
    return university_catalog_queryset(include_unpublished=include_unpublished).prefetch_related(
        Prefetch(
            "preparation_courses",
            queryset=UniversityPreparationCourse.objects.filter(is_active=True).order_by("order", "language"),
            to_attr="visible_preparation_courses",
        ),
        Prefetch(
            "requirements",
            queryset=UniversityRequirement.objects.filter(is_active=True).order_by("order", "id"),
            to_attr="visible_requirements",
        ),
        Prefetch(
            "required_documents",
            queryset=UniversityDocument.objects.filter(is_active=True).order_by("order", "id"),
            to_attr="visible_required_documents",
        ),
        Prefetch(
            "service_items",
            queryset=UniversityServiceItem.objects.filter(is_active=True).order_by("order", "id"),
            to_attr="visible_service_items",
        ),
        Prefetch(
            "media_items",
            queryset=UniversityMedia.objects.filter(is_active=True).order_by("order", "id"),
            to_attr="visible_media_items",
        ),
    )


def apply_catalog_filters(queryset, params):
    search_query = params.get("q", "").strip()
    university_type = params.get("type", "").strip()
    city = params.get("city", "").strip()
    language = params.get("language", "").strip()
    degree = params.get("level", "").strip()
    price = params.get("price", "").strip()
    admission_status = params.get("status", University.AdmissionStatus.OPEN).strip()

    if search_query:
        queryset = queryset.filter(Q(name__icontains=search_query) | Q(city__icontains=search_query))
    if university_type in University.UniversityType.values:
        queryset = queryset.filter(university_type=university_type)
    if city:
        queryset = queryset.filter(city__iexact=city)
    if language in UniversityProgram.Language.values:
        queryset = queryset.filter(faculties__programs__language=language, faculties__programs__is_active=True)
    if degree in UniversityProgram.DegreeLevel.values:
        queryset = queryset.filter(faculties__programs__degree_level=degree, faculties__programs__is_active=True)
    if price in PRICE_FILTERS:
        queryset = queryset.filter(PRICE_FILTERS[price])
    if admission_status != "all":
        if admission_status not in University.AdmissionStatus.values:
            admission_status = University.AdmissionStatus.OPEN
        queryset = queryset.filter(admission_status=admission_status)

    filter_state = {
        "q": search_query,
        "type": university_type,
        "city": city,
        "language": language,
        "level": degree,
        "price": price,
        "status": admission_status,
    }
    return queryset.distinct(), filter_state


def catalog_filter_options():
    base = University.objects.published()
    return {
        "cities": list(base.order_by("city").values_list("city", flat=True).distinct()),
        "university_types": University.UniversityType.choices,
        "languages": UniversityProgram.Language.choices,
        "degree_levels": UniversityProgram.DegreeLevel.choices,
        "admission_statuses": University.AdmissionStatus.choices,
    }


def portal_stats():
    universities = University.objects.published()
    return {
        "universities": universities.count(),
        "programs": UniversityProgram.objects.filter(
            is_active=True,
            faculty__is_active=True,
            faculty__university__is_published=True,
        ).count(),
        "cities": universities.values("city").distinct().count(),
        "languages": UniversityProgram.objects.filter(
            is_active=True,
            faculty__is_active=True,
            faculty__university__is_published=True,
        ).values("language").distinct().count(),
    }
