from django.db.models import Prefetch, Q

from frontend.public_query import MAX_QUERY_CHARS, bounded_text, clean

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
    from .public import effective_universities

    queryset = University.objects.all() if include_unpublished else effective_universities()
    return queryset.prefetch_related(
        Prefetch("faculties", queryset=_faculty_queryset(), to_attr="visible_faculties")
    )


def featured_open_universities(limit=3):
    """Qabul ochiq universitetlar: avval "bosh sahifada ko'rsatilsin" belgilanganlar, so'ng qolgan ochiqlar.

    SIT bosh sahifasi va platforma bosh sahifasining SIT bandi (PUBLIC-02) shu bitta qoidadan o'qiydi —
    ikki joyda ikki xil tanlov paydo bo'lmasin.
    """
    base_queryset = university_catalog_queryset()
    featured = list(base_queryset.filter(is_featured=True, admission_status=University.AdmissionStatus.OPEN)[:limit])
    if len(featured) < limit:
        featured.extend(
            base_queryset.filter(admission_status=University.AdmissionStatus.OPEN)
            .exclude(pk__in=[university.pk for university in featured])[: limit - len(featured)]
        )
    return featured


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


def advisor_catalog_queryset():
    """AI maslahatchi uchun katalog: nashr etilgan universitet + dastur + tayyorlov kursi.

    Detail queryset'dan farqi — talab/hujjat/xizmat/media olinmaydi, chunki ular
    prompt'ga kirmaydi. N+1 bo'lmasligi uchun kerakli bog'lanishlar prefetch qilinadi.
    """
    return university_catalog_queryset().prefetch_related(
        Prefetch(
            "preparation_courses",
            queryset=UniversityPreparationCourse.objects.filter(is_active=True).order_by("order", "language"),
            to_attr="visible_preparation_courses",
        )
    )


def apply_catalog_filters(queryset, params):
    # Kirish katalog va Blog bilan bir chegarada (PUB1.6b, `frontend/public_query`).
    search_query = bounded_text(params.get("q", ""))
    university_type = params.get("type", "").strip()
    city = clean(params.get("city", ""))[:MAX_QUERY_CHARS]
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
    from .public import effective_universities

    base = effective_universities()
    return {
        "cities": list(base.order_by("city").values_list("city", flat=True).distinct()),
        "university_types": University.UniversityType.choices,
        "languages": UniversityProgram.Language.choices,
        "degree_levels": UniversityProgram.DegreeLevel.choices,
        "admission_statuses": University.AdmissionStatus.choices,
    }


def portal_stats():
    from .public import effective_universities

    universities = effective_universities()
    programs = UniversityProgram.objects.filter(
        is_active=True,
        faculty__is_active=True,
        faculty__university__in=effective_universities(),
    )
    return {
        "universities": universities.count(),
        "programs": programs.count(),
        "cities": universities.values("city").distinct().count(),
        "languages": programs.values("language").distinct().count(),
    }
