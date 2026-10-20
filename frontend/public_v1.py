"""Public presentation adapter; canonical views retain queries and permissions."""
from urllib.parse import urlsplit

from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import patch_cache_control
from django.utils.functional import cached_property

from core.flags import flag_enabled


TITLES = {
    "index.html": "Bosh sahifa", "about.html": "Platforma haqida",
    "courses/course_list.html": "Kurslar", "courses/course_detail.html": "Kurs",
    "subscriptions/pricing.html": "Tariflar", "legal_page.html": "Ma’lumot",
    "blog/post_list.html": "Blog", "blog/post_detail.html": "Maqola",
    "sit/home.html": "Turkiyada o‘qish", "sit/university_list.html": "Universitetlar",
    "sit/university_detail.html": "Universitet", "sit/knowledge_detail.html": "Qo‘llanma",
}


def safe_return_to(request, fallback):
    """`return_to` faqat ayni ro'yxat sahifasiga (filtr/sahifa bilan) qaytsa; aks holda `fallback`.

    Navigatsiya uchun: tashqi, protocol-relative, boshqa yo'l yoki boshqaruv
    belgili qiymat hech qachon qabul qilinmaydi. Ikkala renderer ishlatadi (PUB1.6a).
    """
    candidate = request.GET.get("return_to", "")
    try:
        parts = urlsplit(candidate)
        valid = (len(candidate) <= 2000 and not parts.scheme and not parts.netloc
                 and parts.path == fallback and not parts.fragment
                 and not any(ord(char) < 32 or char == "\\" for char in candidate))
    except ValueError:
        valid = False
    return candidate if valid else fallback


def public_context(request, template, context):
    result = dict(context, frontend_v1_title=TITLES[template])
    for key, attribute in (("course", "title"), ("post", "title"), ("legal_page", "title"), ("university", "name"), ("article", "title")):
        if result.get(key) is not None:
            result["frontend_v1_title"] = getattr(result[key], attribute)
            break
    else:
        # E'lon qilinmagan huquqiy sahifa ham o'z nomi bilan ko'rinadi (PUB1.0e).
        if result.get("legal_title"):
            result["frontend_v1_title"] = result["legal_title"]
    family = {"courses/course_detail.html": "courses", "blog/post_detail.html": "blog:list", "sit/university_detail.html": "sit:university_list"}.get(template)
    if family:
        result["public_back_url"] = safe_return_to(request, reverse(family))
    return result


class PublicFrontendV1Mixin:
    @cached_property
    def public_v1_enabled(self):
        return flag_enabled("frontend_v1_public")

    def get_template_names(self):
        if self.public_v1_enabled:
            return ["frontend_v1/public/" + self.template_name]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return public_context(self.request, self.template_name, context) if self.public_v1_enabled else context

    def render_to_response(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        if self.public_v1_enabled:
            # Preview, authentication, CSRF and rollout must not leak through caches.
            patch_cache_control(response, private=True, no_store=True)
        return response


def render_public(request, template, context, *, v1=None):
    # `v1` berilsa qaror qayta o'qilmaydi: kontekst va shablon bir xil qarordan
    # (bayroq ikki o'qish orasida o'zgarsa ham mos kelmaslik bo'lmaydi).
    if v1 is None:
        v1 = flag_enabled("frontend_v1_public")
    if not v1:
        return render(request, template, context)
    response = render(request, "frontend_v1/public/" + template, public_context(request, template, context))
    patch_cache_control(response, private=True, no_store=True)
    return response
