"""Published-only sitemap registri (PUB1.1c).

`sitemap.xml` faqat shu registrdagi manbalardan quriladi: har yozuv sahifa
o'zi bergan canonical'ga teng, 200 qaytaradi va `index, follow`. Manba sahifa
view'i ishlatadigan **ayni** tanlovni (selector) ishlatadi — "e'lon qilingan"
ikki joyda ikki xil hisoblanmaydi.

Kirmaydi: preview, filtr/qidiruv/sahifalash, token, auth, xato, tariflar
(PUB1.2 haqqoniy taklifigacha `noindex`) va e'lon qilinmagan huquqiy sahifa.
`lastmod` faqat obyektda haqiqiy o'zgarish vaqti bo'lsa — sun'iy sana yo'q.

Yangi domen (masalan SIT1.7a) ikkinchi sitemap yaratmaydi: shu yerga manba
qo'shadi.
"""

from dataclasses import dataclass
from datetime import datetime

from django.urls import reverse

from frontend.public_meta import absolute_url
from frontend.public_policy import surface_by_name

# Bitta sitemap fayli protokol chegarasi.
MAX_URLS = 50000


@dataclass(frozen=True)
class SitemapEntry:
    route_name: str
    loc: str
    lastmod: datetime | None = None


def _static(route_name):
    return [SitemapEntry(route_name, absolute_url(reverse(route_name)))]


def _legal(route_name, page_type):
    def source():
        from frontend import legal_revisions
        from frontend.models import LegalPage

        # Sahifa view'ining ayni manbasi: huquqiy hujjat — amaldagi versiya (PUB1.5a).
        if page_type in legal_revisions.KINDS:
            revision = legal_revisions.effective_revision(page_type)
            if revision is None:
                return []
            return [SitemapEntry(route_name, absolute_url(reverse(route_name)), revision.effective_at)]
        page = LegalPage.published(page_type)
        if page is None:
            return []
        return [SitemapEntry(route_name, absolute_url(reverse(route_name)), page.updated_at)]
    return source


def _courses():
    from courses.models import Course

    # `CourseDetailView` ayni filtri: faol kurs.
    return [
        SitemapEntry("course_detail", absolute_url(reverse("course_detail", args=[pk])))
        for pk in Course.objects.filter(is_active=True).order_by("pk").values_list("pk", flat=True)
    ]


def _blog_posts():
    from blog.models import BlogPost

    return [
        SitemapEntry("blog:detail", absolute_url(post.get_absolute_url()), post.updated_at)
        for post in BlogPost.objects.published().only("slug", "updated_at").order_by("-published_at", "pk")
    ]


def _universities():
    # SIT nimani "amalda" deb hisoblashini faqat o'zi biladi (PUB1.6b adapteri).
    from sit.public import effective_universities

    return [
        SitemapEntry("sit:university_detail", absolute_url(university.get_absolute_url()), university.updated_at)
        for university in effective_universities().only("slug", "updated_at").order_by("pk")
    ]


def _articles():
    from sit.public import effective_articles

    return [
        SitemapEntry("sit:knowledge_detail", absolute_url(article.get_absolute_url()), article.updated_at)
        for article in effective_articles().only("slug", "updated_at").order_by("pk")
    ]


SOURCES = (
    lambda: _static("home"),
    lambda: _static("about"),
    _legal("privacy_policy", "privacy"),
    _legal("terms_of_service", "terms"),
    _legal("faq_page", "faq"),
    lambda: _static("courses"),
    _courses,
    lambda: _static("blog:list"),
    _blog_posts,
    lambda: _static("sit:home"),
    lambda: _static("sit:university_list"),
    _universities,
    _articles,
)


def sitemap_entries():
    """Registrdagi barcha yozuvlar; registryda `exclude` route kirsa xato."""
    surfaces = surface_by_name()
    entries = []
    for source in SOURCES:
        for entry in source():
            policy = surfaces.get(entry.route_name)
            if policy is None or policy.sitemap_policy == "exclude" or policy.audience != "anonymous":
                raise ValueError(f"{entry.route_name}: sitemap'ga kirmaydigan route.")
            entries.append(entry)
            if len(entries) > MAX_URLS:
                raise ValueError("Sitemap 50 000 URL chegarasidan oshdi — sitemap index kerak.")
    return entries
