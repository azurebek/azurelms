"""Ochiq sahifalardagi media fayllari reestri va audit (PUB1.7b).

Ochiq sahifada ko'rinadigan har rasm/video maydoni shu ro'yxatda: qaysi model,
qaysi maydon, qaysi qatorlar ochiq. `missing_public_media()` saqlovchida
(lokal disk yoki S3) fayli yo'q havolalarni topadi — sahifada buzilgan rasm
yoki ishlamaydigan video bo'lib chiqadigan narsalar. Faqat o'qiydi; hech narsa
o'chirmaydi va tuzatmaydi (`manage.py audit_public_media`).

Yangi ochiq media maydoni qo'shilsa — shu ro'yxatga ham qo'shing.
"""

from dataclasses import dataclass


def _blog_posts():
    from blog.models import BlogPost

    return BlogPost.objects.published()


def _universities():
    from sit.public import effective_universities

    return effective_universities()


def _university_media():
    from sit.models import UniversityMedia
    from sit.public import effective_universities

    return UniversityMedia.objects.filter(is_active=True, university__in=effective_universities())


def _articles():
    from sit.public import effective_articles

    return effective_articles()


def _testimonials():
    # Faqat saytda chiqadigan fikrlar (rozilik bilan) — yashirin fikrning rasmi ochiq media emas.
    from frontend.models import Testimonial
    from frontend.public_claims import public_testimonials

    return Testimonial.objects.filter(pk__in=[item.pk for item in public_testimonials(limit=None)])


def _courses():
    from courses.models import Course

    return Course.objects.filter(is_active=True)


def _model(path):
    def queryset():
        from django.apps import apps

        return apps.get_model(path)._default_manager.all()

    return queryset


# (nom, maydonlar, ochiq qatorlar)
PUBLIC_MEDIA = (
    ("blog.BlogPost", ("cover_image",), _blog_posts),
    ("sit.University", ("cover_image", "logo_image"), _universities),
    ("sit.UniversityMedia", ("image",), _university_media),
    ("sit.KnowledgeArticle", ("cover_image",), _articles),
    ("courses.Course", ("thumbnail", "preview_video"), _courses),
    ("frontend.LandingPage", (
        "hero_background_image", "hero_background_video", "hero_image", "hero_video",
        "how_it_works_background_image", "how_it_works_background_video",
        "footer_background_image", "footer_background_video", "cta_background_image", "cta_background_video",
    ), _model("frontend.LandingPage")),
    ("frontend.Testimonial", ("avatar",), _testimonials),
    ("frontend.TeamMember", ("avatar",), _model("frontend.TeamMember")),
    ("frontend.SiteSettings", ("logo_image", "logo_dark_image", "logo_mark_image", "favicon_image"),
     _model("frontend.SiteSettings")),
)


@dataclass(frozen=True)
class MissingMedia:
    source: str
    pk: int
    field: str
    name: str


def missing_public_media():
    """`(tekshirilgan soni, [MissingMedia, ...])` — fayli saqlovchida yo'q ochiq havolalar."""
    checked, missing = 0, []
    for source, fields, queryset in PUBLIC_MEDIA:
        for row in queryset().only("pk", *fields).order_by("pk"):
            for field in fields:
                file = getattr(row, field)
                if not file or not file.name:
                    continue
                checked += 1
                if not file.storage.exists(file.name):
                    missing.append(MissingMedia(source, row.pk, field, file.name))
    return checked, missing
