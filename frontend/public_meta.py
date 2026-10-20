"""Public sahifa metadata'si: bitta qiymat obyekti, bitta qoida (PUB1.1b).

`PublicPageMeta` sarlavha, tavsif, robots, canonical, Open Graph, Twitter,
breadcrumb va JSON-LD'ni bir joyda hisoblaydi. Qoidalar:

* absolute URL faqat `settings.PUBLIC_CANONICAL_ORIGIN`dan — so'rovdagi `Host`
  sarlavhasi canonical'ga ta'sir qilmaydi;
* robots va canonical `frontend/public_policy.py` registridan: sensitive, private,
  preview, filtr/qidiruv, sahifa 2+ va xato sahifalari indekslanmaydi;
* tavsif oddiy matn, 160 belgigacha; rich HTML metadata'ga kirmaydi;
* OG rasmi faqat public media'dan (`approved_image_src`), private yuklama emas;
* JSON-LD faqat sahifada ko'rinadigan maydonlardan; narx/taklif yo'q (PUB1.2).

Blog, SIT, kurs va huquqiy sahifalar uchun ma'lumot kontekstdagi obyektdan
adapter orqali olinadi — view'lar o'zgarmaydi, ikki xil metadata yo'li yo'q.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime

from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe

from core.rich_content_policy import approved_image_src, public_plain_text
from frontend.public_people import real_name
from frontend.public_policy import CacheClass, surface_by_name

DESCRIPTION_MAX = 160
ROBOTS_INDEX = "index, follow"
ROBOTS_QUERY = "noindex, follow"
ROBOTS_NOINDEX = "noindex, nofollow"
ROBOTS_SENSITIVE = "noindex, nofollow, noarchive"
LOCALE = "uz_UZ"

# Umumiy sahifalar uchun sarlavha va tavsif (obyektga bog'liq bo'lmaganlar).
ROUTE_TEXT = {
    "courses": ("Kurslar", "Turk tili kurslari: A1 dan C1 gacha daraja, dastur va o‘qituvchilar."),
    "subscriptions:pricing": ("Tariflar", "Turk tili kurslari tariflari va ularga nimalar kirishi."),
    "blog:list": ("Blog", "Turk tili, o‘qish usullari va Turkiyada ta’lim haqida maqolalar."),
    "sit:home": ("Turkiyada o‘qish", "Turkiya universitetlari, qabul talablari va hujjat topshirish bo‘yicha qo‘llanma."),
    "sit:university_list": ("Universitetlar", "Turkiya universitetlari: shahar, yo‘nalish va qabul holati."),
    "login": ("Kirish", ""),
    "register": ("Ro‘yxatdan o‘tish", ""),
    "password_reset": ("Parolni tiklash", ""),
}


@dataclass(frozen=True)
class OpenGraph:
    title: str
    description: str
    url: str
    type: str
    image: str
    image_alt: str
    locale: str = LOCALE


@dataclass(frozen=True)
class TwitterCard:
    card: str
    title: str
    description: str
    image: str


@dataclass(frozen=True)
class Breadcrumb:
    name: str
    url: str


@dataclass(frozen=True)
class PublicPageMeta:
    title: str
    description: str
    canonical_url: str | None
    robots: str
    open_graph: OpenGraph | None = None
    twitter: TwitterCard | None = None
    breadcrumbs: tuple = ()
    structured_data: tuple = ()
    modified_at: datetime | None = None


@dataclass
class _Inputs:
    """Adapter natijasi: sahifaga xos ma'lumot."""

    title: str = ""
    description: str = ""
    object_path: str = ""
    indexable: bool = True
    image: str = ""
    image_alt: str = ""
    og_type: str = "website"
    modified_at: datetime | None = None
    breadcrumbs: tuple = ()
    structured_data: list = field(default_factory=list)


def canonical_origin():
    return settings.PUBLIC_CANONICAL_ORIGIN


def absolute_url(path):
    """Faqat sozlangan origin bilan: `Host` sarlavhasi hech qachon ishlatilmaydi."""
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("Absolute URL faqat sayt ichidagi yo'ldan quriladi.")
    return canonical_origin() + path


def bounded_description(*values):
    for value in values:
        text = public_plain_text(value or "", DESCRIPTION_MAX)
        if text:
            return text
    return ""


def public_image_url(file_field):
    """Public media rasmi absolute URL'i yoki bo'sh satr (private yuklama emas)."""
    try:
        url = file_field.url if file_field else ""
    except ValueError:
        return ""
    src = approved_image_src(url)
    if not src:
        return ""
    return absolute_url(src) if src.startswith("/") else src


def json_ld(data):
    """`<script type="application/ld+json">` ichiga xavfsiz JSON."""
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)
    for char, escaped in (("<", "\\u003C"), (">", "\\u003E"), ("&", "\\u0026")):
        text = text.replace(char, escaped)
    return mark_safe(text)  # noqa: S308 — yuqorida HTML maxsus belgilari escape qilindi


# --- adapterlar: kontekstdagi obyekt → sahifaga xos ma'lumot -----------------

def _brand(context):
    settings_obj = context.get("site_settings")
    return (getattr(settings_obj, "brand_name", "") or "AzureLMS").strip()


def _home(context):
    page = context.get("page")
    settings_obj = context.get("site_settings")
    return _Inputs(
        title=_brand(context),
        description=bounded_description(getattr(page, "hero_subtitle", ""), getattr(settings_obj, "brand_tagline", "")),
    )


def _about(context):
    page = context.get("page")
    return _Inputs(title="Biz haqimizda", description=bounded_description(getattr(page, "hero_subtitle", "")))


def _legal(context):
    page = context.get("legal_page")
    if page is None:
        # E'lon qilinmagan huquqiy sahifa (503) indekslanmaydi.
        return _Inputs(title=context.get("legal_title", ""), indexable=False)
    # Huquqiy hujjat — kuchga kirgan vaqti (PUB1.5a), FAQ — oxirgi tahrir.
    modified_at = context.get("legal_effective_at") or getattr(page, "updated_at", None)
    return _Inputs(title=page.title, description=bounded_description(page.content), modified_at=modified_at)


def _course(context):
    course = context.get("course")
    if course is None:
        return _Inputs(indexable=False)
    path = reverse("course_detail", args=[course.pk])
    description = bounded_description(course.description)
    image = public_image_url(getattr(course, "thumbnail", None))
    data = {"@context": "https://schema.org", "@type": "Course", "name": course.title,
            "description": description, "url": absolute_url(path),
            "provider": {"@type": "Organization", "name": _brand(context), "sameAs": canonical_origin()}}
    if image:
        data["image"] = image
    return _Inputs(
        title=course.title, description=description, object_path=path, image=image, image_alt=course.title,
        breadcrumbs=(Breadcrumb("Kurslar", absolute_url(reverse("courses"))), Breadcrumb(course.title, absolute_url(path))),
        structured_data=[data],
    )


def _blog_post(context):
    post = context.get("post")
    if post is None:
        return _Inputs(indexable=False)
    path = post.get_absolute_url()
    image = public_image_url(post.cover_image)
    description = bounded_description(post.share_description)
    data = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": post.share_title,
            "description": description, "url": absolute_url(path),
            "datePublished": post.published_at, "dateModified": post.updated_at,
            # Login (username) chiqmaydi: ism bo'lmasa muallif — platforma (PUB1.6a).
            "author": ({"@type": "Person", "name": author_name} if (author_name := real_name(post.author))
                       else {"@type": "Organization", "name": _brand(context)})}
    if image:
        data["image"] = image
    return _Inputs(
        title=post.share_title, description=description, object_path=path, image=image,
        image_alt=post.cover_alt_text or post.share_title, og_type="article", modified_at=post.updated_at,
        indexable=not context.get("is_preview"),
        breadcrumbs=(Breadcrumb("Blog", absolute_url(reverse("blog:list"))), Breadcrumb(post.share_title, absolute_url(path))),
        structured_data=[data],
    )


def _university(context):
    university = context.get("university")
    if university is None:
        return _Inputs(indexable=False)
    path = university.get_absolute_url()
    return _Inputs(
        title=university.name, description=bounded_description(university.description), object_path=path,
        image=public_image_url(university.cover_image), image_alt=university.name,
        indexable=university.is_published and not context.get("is_preview"), modified_at=university.updated_at,
        breadcrumbs=(Breadcrumb("Universitetlar", absolute_url(reverse("sit:university_list"))),
                     Breadcrumb(university.name, absolute_url(path))),
    )


def _article(context):
    article = context.get("article")
    if article is None:
        return _Inputs(indexable=False)
    path = article.get_absolute_url()
    return _Inputs(
        title=article.title, description=bounded_description(article.excerpt, article.body), object_path=path,
        image=public_image_url(article.cover_image), image_alt=article.title, og_type="article",
        indexable=article.is_published and not context.get("is_preview"), modified_at=article.updated_at,
        breadcrumbs=(Breadcrumb("Turkiyada o‘qish", absolute_url(reverse("sit:home"))), Breadcrumb(article.title, absolute_url(path))),
    )


def _pricing(context):
    # Haqqoniy taklif proyeksiyasi (PUB1.2) bo'lmaguncha tariflar indekslanmaydi.
    title, description = ROUTE_TEXT["subscriptions:pricing"]
    return _Inputs(title=title, description=description, indexable=False)


ADAPTERS = {
    "home": _home,
    "about": _about,
    "privacy_policy": _legal,
    "terms_of_service": _legal,
    "faq_page": _legal,
    "course_detail": _course,
    "blog:detail": _blog_post,
    "sit:university_detail": _university,
    "sit:knowledge_detail": _article,
    "subscriptions:pricing": _pricing,
}


def _route_name(request):
    match = getattr(request, "resolver_match", None)
    return getattr(match, "view_name", None)


def _is_query_variant(request):
    # Kampaniya belgilari (`utm_*`) sahifa mazmunini o'zgartirmaydi.
    return any(not key.startswith("utm_") for key in request.GET)


def _page_number(request):
    try:
        return int(request.GET.get("page", "1"))
    except ValueError:
        return 1


def build_meta(request, context, *, force_noindex=False):
    route = _route_name(request)
    policy = surface_by_name().get(route)
    brand = _brand(context)
    adapter = ADAPTERS.get(route)
    if adapter is not None:
        inputs = adapter(context)
    else:
        title, description = ROUTE_TEXT.get(route, ("", ""))
        inputs = _Inputs(title=title or context.get("frontend_v1_title", ""), description=description)
    title = f"{inputs.title} · {brand}" if inputs.title and inputs.title != brand else brand
    description = inputs.description or bounded_description(getattr(context.get("site_settings"), "brand_tagline", ""))

    # Indekslanmaydigan holatlar: registrda yo'q (private), sensitive, holat va
    # xato sahifalari. Ularda canonical va ulashish metadata'si chiqmaydi.
    if force_noindex or policy is None or policy.cache_class == CacheClass.STATUS_NO_STORE:
        return PublicPageMeta(title=title, description=description, canonical_url=None, robots=ROBOTS_NOINDEX)
    if policy.audience == "sensitive":
        return PublicPageMeta(title=title, description=description, canonical_url=None, robots=ROBOTS_SENSITIVE)

    preview = request.GET.get("preview") == "1" or bool(context.get("is_preview"))
    if preview or not inputs.indexable:
        return PublicPageMeta(title=title, description=description, canonical_url=None, robots=ROBOTS_NOINDEX)

    if policy.canonical_policy == "object":
        canonical = absolute_url(inputs.object_path or request.path)
        robots = ROBOTS_INDEX
    else:
        # self/clean_base: so'rov satrisiz yo'l. Qidiruv, filtr va 2+ sahifa
        # indekslanmaydi, lekin havolalari kuzatiladi.
        canonical = absolute_url(request.path)
        robots = ROBOTS_QUERY if (_is_query_variant(request) or _page_number(request) > 1) else ROBOTS_INDEX
    if policy.index_policy == "noindex":
        robots = ROBOTS_NOINDEX

    open_graph = OpenGraph(
        title=inputs.title or brand, description=description, url=canonical, type=inputs.og_type,
        image=inputs.image, image_alt=inputs.image_alt if inputs.image else "",
    )
    twitter = TwitterCard(
        card="summary_large_image" if inputs.image else "summary", title=inputs.title or brand,
        description=description, image=inputs.image,
    )
    structured = list(inputs.structured_data)
    if inputs.breadcrumbs:
        structured.append({
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": index, "name": crumb.name, "item": crumb.url}
                for index, crumb in enumerate(inputs.breadcrumbs, start=1)
            ],
        })
    return PublicPageMeta(
        title=title, description=description, canonical_url=canonical, robots=robots,
        open_graph=open_graph, twitter=twitter, breadcrumbs=inputs.breadcrumbs,
        structured_data=tuple(json_ld(block) for block in structured), modified_at=inputs.modified_at,
    )
