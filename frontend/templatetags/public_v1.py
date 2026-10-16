from django import template

from frontend.public_url_policy import public_link_url

register = template.Library()


@register.filter
def public_url(value):
    """Admin-authored link is a link, never executable markup.

    V1 shablonlari mavjud nom bilan chaqiradi; qoida endi yagona
    `frontend.public_url_policy`da — legacy renderer ham ayni funksiyani oladi.
    Navbar/footer elementlari context processor'da navigatsiya siyosatidan
    (faqat https) allaqachon o'tgan bo'ladi.
    """
    return public_link_url(value)
