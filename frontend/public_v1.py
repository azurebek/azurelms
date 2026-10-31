"""Public presentation adapter; canonical views retain queries and permissions."""
from urllib.parse import urlsplit

from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import patch_cache_control
from django.utils.functional import cached_property

from frontend.public_content import EDITORIAL, LEGACY, current_renderer


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


# PUBLIC-02 ramkasi: sahifa shablonlari `{% extends public_frame|default:... %}` — editorial yoqilsa
# hali ko'chirilmagan sahifa ham yangi header/footer ichida chiqadi, mazmuni o'zgarmaydi.
PUBLIC_FRAME = {EDITORIAL: "frontend_v1/editorial/base.html"}
DEFAULT_FRAME = "frontend_v1/public/base.html"


def public_template_names(template, renderer):
    """Shablon tanlovining yagona nuqtasi: editorial nusxa bo'lsa u, bo'lmasa hozirgi V1 (sahifama-sahifa ko'chish)."""
    if renderer == EDITORIAL:
        return ["frontend_v1/editorial/" + template, "frontend_v1/public/" + template]
    return ["frontend_v1/public/" + template]


def public_context(request, template, context, renderer=None):
    result = dict(context, frontend_v1_title=TITLES[template],
                  public_frame=PUBLIC_FRAME.get(renderer, DEFAULT_FRAME))
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
    def public_renderer(self):
        # Shablon, kontekst va kesh sarlavhasi bir so'rov ichida ayni qarordan.
        return current_renderer()

    @property
    def public_v1_enabled(self):
        return self.public_renderer != LEGACY

    def get_template_names(self):
        if self.public_v1_enabled:
            return public_template_names(self.template_name, self.public_renderer)
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.public_v1_enabled:
            return context
        return public_context(self.request, self.template_name, context, self.public_renderer)

    def render_to_response(self, context, **kwargs):
        response = super().render_to_response(context, **kwargs)
        if self.public_v1_enabled:
            # Preview, authentication, CSRF and rollout must not leak through caches.
            patch_cache_control(response, private=True, no_store=True)
        return response


def render_public(request, template, context, *, renderer=None):
    # `renderer` berilsa qaror qayta o'qilmaydi: proyeksiya, kontekst va shablon bir xil qarordan
    # (bayroq ikki o'qish orasida o'zgarsa ham mos kelmaslik bo'lmaydi).
    if renderer is None:
        renderer = current_renderer()
    if renderer == LEGACY:
        return render(request, template, context)
    response = render(request, public_template_names(template, renderer),
                      public_context(request, template, context, renderer))
    patch_cache_control(response, private=True, no_store=True)
    return response
