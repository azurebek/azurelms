"""Kutubxona qidiruvi — ro'yxat sahifasi va dars muharriri uchun bitta manba.

**Nega oddiy baza qidiruvi.** Loyihada hozir Postgres full-text yoki tashqi
indeks ishlatilmaydi (`SearchVector` hech joyda yo'q) va kutubxona hajmi
minglar tartibida. Shu miqyosda indekslangan ustunlar ustidagi `icontains` +
aniq filtrlar yetadi va yangi infratuzilma talab qilmaydi. Og'irroq yechimga
o'tish kerak bo'lsa, o'zgarish shu funksiyada bo'ladi — chaqiruvchilar emas.

Qidiruv matni bo'shliq bo'yicha bo'linadi va har bo'lak **alohida** AND
sharti bo'ladi: "a1 speaking tanishuv" so'rovi uchta belgini birdan qanoat
qiladigan materialni topadi, shu bilan "A1 + speaking + introductions"
ssenariysi ishlaydi. Har bo'lak nom, tavsif, mavzu yoki teg ichidan izlanadi.
"""

from django.db.models import Q

from .models import LibraryResource, LibraryTag

#: Ro'yxatdagi sahifa hajmi. Ming yozuvda ham sahifa yengil qolishi kerak.
PAGE_SIZE = 24

#: Bo'sh qiymat = "hammasi" degan filtrlar uchun umumiy belgi.
ANY = ""


def _token_filter(token):
    return (
        Q(title__icontains=token)
        | Q(description__icontains=token)
        | Q(topic__icontains=token)
        | Q(tags__name__icontains=token)
    )


def search_resources(
    *,
    query="",
    resource_type=ANY,
    language=ANY,
    level=ANY,
    course_id=None,
    topic=ANY,
    tag=ANY,
    file_kind=ANY,
    include_archived=False,
    only_archived=False,
    base_queryset=None,
):
    """Filtrlangan manbalar queryset'i (annotatsiyasi bilan, tartiblangan).

    `include_archived=False` — odatiy holat: arxiv ro'yxatda ko'rinmaydi va
    dars muharriridagi tanlovga ham tushmaydi.
    """
    queryset = base_queryset if base_queryset is not None else LibraryResource.objects.all()

    if only_archived:
        queryset = queryset.archived()
    elif not include_archived:
        queryset = queryset.active()

    for token in (query or "").split():
        queryset = queryset.filter(_token_filter(token))

    if resource_type:
        queryset = queryset.filter(resource_type=resource_type)
    if language:
        queryset = queryset.filter(language=language)
    if level:
        queryset = queryset.filter(level=level)
    if course_id:
        queryset = queryset.filter(course_id=course_id)
    if topic:
        queryset = queryset.filter(topic__icontains=topic)
    if tag:
        queryset = queryset.filter(tags__name=tag.lower())
    if file_kind:
        queryset = queryset.filter(file_kind=file_kind)

    # `tags` bo'yicha filtr JOIN yasaydi — bir material bir necha marta
    # qaytmasligi uchun `distinct()`.
    return (
        queryset.distinct()
        .select_related("course", "created_by")
        .prefetch_related("tags")
        .with_usage()
        .order_by("-updated_at", "-pk")
    )


def filters_from_request(request):
    """GET parametrlarini normallashtirib beradi (bo'sh qiymat = hammasi)."""
    get = request.GET
    course_id = get.get("course", "").strip()
    return {
        "query": get.get("q", "").strip(),
        "resource_type": get.get("type", "").strip(),
        "language": get.get("language", "").strip(),
        "level": get.get("level", "").strip(),
        "course_id": int(course_id) if course_id.isdigit() else None,
        "topic": get.get("topic", "").strip(),
        "tag": get.get("tag", "").strip(),
        "file_kind": get.get("kind", "").strip(),
        "only_archived": get.get("archived") == "1",
    }


def used_file_kinds():
    """Bazada haqiqatan uchraydigan fayl turlari — filtr ro'yxati uchun."""
    return sorted(
        value
        for value in LibraryResource.objects.exclude(file_kind="")
        .values_list("file_kind", flat=True)
        .distinct()
        if value
    )


def popular_tags(limit=40):
    """Eng ko'p ishlatilgan teglar — filtr paneli uchun."""
    from django.db.models import Count

    return (
        LibraryTag.objects.annotate(usage=Count("resources"))
        .filter(usage__gt=0)
        .order_by("-usage", "name")[:limit]
    )
