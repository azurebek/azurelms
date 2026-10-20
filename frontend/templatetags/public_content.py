"""Public sahifalar uchun rich text va URL filterlari (PUBLIC-01 · PUB1.0a).

Legacy va V1 rendererlar DB'dagi public HTMLni faqat shu `public_rich` orqali
chiqaradi: `frontend_v1_public` flagini o'chirib eski shablonga qaytish raw
`|safe`ga qaytish degani emas. Private dars/imtihon kontenti bu filterga
ko'chirilmaydi — u `bleach_tags.sanitize`da qoladi.
"""

from django import template
from django.utils.safestring import mark_safe

from core.rich_content_policy import public_plain_text, sanitize_public_editorial
from frontend.public_people import public_person_name
from frontend.public_url_policy import public_link_url, public_nav_url

register = template.Library()


@register.filter
def public_rich(value):
    """`PUBLIC_EDITORIAL_V1` bilan tozalangan, chiqarishga tayyor HTML."""
    return mark_safe(sanitize_public_editorial(value))


@register.filter
def public_plain(value, max_chars=None):
    """Meta/preview uchun oddiy matn; template uni odatdagidek escape qiladi."""
    try:
        limit = int(max_chars) if max_chars else None
    except (TypeError, ValueError):
        limit = None
    return public_plain_text(value, limit)


@register.filter
def public_som(value):
    """Narx o'zbekcha ko'rinishda: `200000` → `200 000` (guruhlar bo'linmaydigan bo'shliq bilan).

    Faqat ko'rinish: qiymat `Plan.price`dan o'zgarmay keladi (PUB1.3c).
    """
    from decimal import Decimal, InvalidOperation

    try:
        number = int(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return ""
    return f"{number:,}".replace(",", "\u00a0")


@register.filter
def public_nav(value):
    """Navbar/footer/ijtimoiy tarmoq havolasi; ruxsatsiz bo'lsa ``""``."""
    return public_nav_url(value)


@register.filter
def public_link(value):
    """Kontent yoki manba havolasi; ruxsatsiz bo'lsa ``""``."""
    return public_link_url(value)


@register.filter
def public_person(user, role="user"):
    """Ochiq sahifadagi ism: hisobdagi to'liq ism, bo'lmasa umumiy nom; login hech qachon (PUB1.6a)."""
    return public_person_name(user, role)


@register.filter
def public_initials(user, role="user"):
    """Avatar o'rnidagi bosh harflar — `public_person` ismidan, ko'pi bilan ikkita."""
    return "".join(word[0] for word in public_person_name(user, role).split()[:2]).upper()
