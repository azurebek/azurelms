"""Blog ro'yxati so'rovi — ochiq katalog bilan umumiy kontrakt (PUB1.6a).

Kirish kurslar katalogidagi chegaralar bilan (`frontend/public_query`): qisqa
matn, bir nechta so'z, boshqaruv belgilarisiz; teg — faqat slug ko'rinishidagi
qiymat (boshqasi e'tiborsiz). Har ro'yxat to'liq tartibda (oxirida `id`), sahifa
va teg havolalari faqat normallashgan parametrlardan quriladi — raw so'rov satri
sahifaga qaytmaydi.

Qidiruv semantikasi (sarlavha, qisqa matn, matn va teg nomida `icontains`)
BLOG1.3 gacha o'zgarmaydi: u Blog domenining ishi (BLOG-01).
"""

import re
from dataclasses import dataclass
from urllib.parse import urlencode

from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from frontend.public_query import bounded_text

LIST_ORDERING = ("-featured", "-published_at", "-created_at", "-id")
TOP_TAG_LIMIT = 8
RELATED_LIMIT = 3
_TAG_SLUG = re.compile(r"[-a-zA-Z0-9_]{1,70}")


@dataclass(frozen=True)
class BlogListQuery:
    q: str = ""
    tag: str = ""

    @classmethod
    def from_params(cls, params):
        tag = str(params.get("tag", "")).strip()
        return cls(q=bounded_text(params.get("q", "")), tag=tag if _TAG_SLUG.fullmatch(tag) else "")

    @property
    def is_filtered(self):
        return bool(self.q or self.tag)

    def pairs(self, *, tag=None, page=1):
        tag = self.tag if tag is None else tag
        pairs = [("q", self.q)] if self.q else []
        if tag:
            pairs.append(("tag", tag))
        if page and page > 1:
            pairs.append(("page", str(page)))
        return pairs

    def url(self, **overrides):
        query = urlencode(self.pairs(**overrides))
        return reverse("blog:list") + (f"?{query}" if query else "")


def published_posts():
    from blog.models import BlogPost

    return BlogPost.objects.published().select_related("author").prefetch_related("tags")


def list_queryset(query):
    queryset = published_posts()
    if query.q:
        queryset = queryset.filter(
            Q(title__icontains=query.q)
            | Q(excerpt__icontains=query.q)
            | Q(body__icontains=query.q)
            | Q(tags__name__icontains=query.q)
        ).distinct()
    if query.tag:
        queryset = queryset.filter(tags__slug=query.tag)
    return queryset.order_by(*LIST_ORDERING)


def top_tags():
    """E'lon qilingan maqolasi bor teglar — nom bo'yicha barqaror tartibda."""
    from blog.models import BlogPost, BlogTag

    published = Q(posts__status=BlogPost.STATUS_PUBLISHED, posts__published_at__lte=timezone.now())
    return list(
        BlogTag.objects.annotate(post_total=Count("posts", filter=published))
        .filter(post_total__gt=0)
        .order_by("name", "id")[:TOP_TAG_LIMIT]
    )


def related_posts(post):
    return list(
        published_posts()
        .filter(Q(tags__in=post.tags.all()) | Q(author=post.author))
        .exclude(pk=post.pk)
        .distinct()
        .order_by(*LIST_ORDERING)[:RELATED_LIMIT]
    )
