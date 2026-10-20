"""Ochiq kurslar katalogi so'rovi (PUB1.3a).

Qidiruv kurs tavsifining boy HTML'ida emas, saqlangan oddiy-matn
proyeksiyasida (`Course.search_text`) ishlaydi: teg va atribut nomlari
topilmaydi, katta-kichik harf, `o‘/o'/oʻ` va Unicode shakllari bir xil
solishtiriladi. Kirish chegaralangan: qisqa matn, bir nechta so'z, faqat
ma'lum daraja va tartib qiymatlari. Har ro'yxat to'liq tartibda (oxirida `id`),
sahifa havolalari faqat normallashgan parametrlardan quriladi.

`courses/0026` migratsiyasi shu moduldagi `search_document`ni chaqiradi.
Normallashtirishni o'zgartirsangiz mavjud qatorlarni
`manage.py rebuild_course_search --apply` bilan yangilang.

Kirish chegaralari, normallashtirish va sahifa havolalari Blog bilan umumiy:
`frontend/public_query.py` (PUB1.6a).
"""

from dataclasses import dataclass
from urllib.parse import urlencode

from django.urls import reverse

from core.rich_content_policy import public_plain_text
from frontend import public_query
from frontend.public_query import MAX_QUERY_CHARS, MAX_TERMS, bounded_text, fold  # noqa: F401 — tashqi import nomlari

DEFAULT_SORT = "newest"
SORT_ORDERING = {
    "newest": ("-created_at", "-id"),
    "oldest": ("created_at", "id"),
    "popular": ("-annotated_students_count", "-created_at", "-id"),
}
SEARCH_SOURCE_FIELDS = frozenset({"title", "description"})
SEARCH_BATCH_SIZE = 200


def search_document(title, description):
    return fold(f"{title or ''} {public_plain_text(description)}")


def level_values():
    from courses.models import Course

    return tuple(value for value, _label in Course.LEVEL_CHOICES)


@dataclass(frozen=True)
class CatalogQuery:
    q: str = ""
    terms: tuple = ()
    levels: tuple = ()
    sort: str = DEFAULT_SORT

    @classmethod
    def from_params(cls, params):
        q = bounded_text(params.get("q", ""))
        terms = tuple(dict.fromkeys(term for term in fold(q).split(" ") if term))
        requested = set(params.getlist("level"))
        levels = tuple(value for value in level_values() if value in requested)
        sort = params.get("sort", DEFAULT_SORT)
        return cls(q=q, terms=terms, levels=levels, sort=sort if sort in SORT_ORDERING else DEFAULT_SORT)

    @property
    def is_filtered(self):
        return bool(self.terms or self.levels)

    @property
    def custom_sort(self):
        """Formada saqlanadigan tartib: standart bo'lsa bo'sh (URL toza qoladi)."""
        return "" if self.sort == DEFAULT_SORT else self.sort

    def pairs(self, *, levels=None, page=1):
        pairs = [("q", self.q)] if self.q else []
        pairs += [("level", level) for level in (self.levels if levels is None else levels)]
        if self.sort != DEFAULT_SORT:
            pairs.append(("sort", self.sort))
        if page and page > 1:
            pairs.append(("page", str(page)))
        return pairs

    def url(self, **overrides):
        query = urlencode(self.pairs(**overrides))
        return reverse("courses") + (f"?{query}" if query else "")


def catalog_queryset(query):
    from django.db.models import Count

    from cohorts.models import enrollment_active_access_q
    from courses.models import Course

    queryset = (
        Course.objects.filter(is_active=True)
        .select_related("instructor")
        .annotate(
            annotated_lessons_count=Count("modules__lessons", distinct=True),
            annotated_students_count=Count(
                "cohorts__members",
                filter=enrollment_active_access_q(prefix="cohorts__members__"),
                distinct=True,
            ),
        )
    )
    for term in query.terms:
        queryset = queryset.filter(search_text__contains=term)
    if query.levels:
        queryset = queryset.filter(level__in=query.levels)
    return queryset.order_by(*SORT_ORDERING[query.sort])


def page_links(page_obj, query, *, window=1):
    """Raqamli sahifa havolalari: birinchi, oxirgi va joriy atrofi; oraliqda `None`."""
    return public_query.page_links(page_obj, lambda number: query.url(page=number), window=window)


def refresh_search_text(queryset, *, apply=True, batch_size=SEARCH_BATCH_SIZE):
    """Eskirgan qidiruv proyeksiyalari soni; `apply` bo'lsa faqat ular yoziladi.

    Kurslar `pk` bo'yicha keyset sahifalarda o'qiladi va yoziladi: xotirada
    bir vaqtda `batch_size` tadan ortiq tavsif turmaydi (PR #216 review). Tarixiy
    model (migratsiya) bilan ham ishlaydi — yozish `queryset.model` orqali.
    """
    manager = queryset.model._default_manager
    ordered = queryset.order_by("pk").only("pk", "title", "description", "search_text")
    stale_count, last_pk = 0, None
    while True:
        page = ordered if last_pk is None else ordered.filter(pk__gt=last_pk)
        rows = list(page[:batch_size])
        if not rows:
            return stale_count
        stale = []
        for course in rows:
            document = search_document(course.title, course.description)
            if course.search_text != document:
                course.search_text = document
                stale.append(course)
        if apply and stale:
            manager.bulk_update(stale, ["search_text"])
        stale_count += len(stale)
        last_pk = rows[-1].pk
