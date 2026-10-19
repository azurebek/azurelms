"""`{% activity_notice "register" "c-caption" %}` — forma yonidagi ma'lumot eslatmasi (PUB1.5b)."""

from django import template
from django.urls import reverse
from django.utils.html import format_html

from frontend.activity_notices import NOTICES

register = template.Library()


@register.simple_tag
def activity_notice(key, css_class=""):
    notice = NOTICES[key]
    return format_html(
        '<p class="{}" data-activity-notice="{}">{} <a href="{}">Maxfiylik siyosati</a></p>',
        css_class, notice.key, notice.text, reverse("privacy_policy"),
    )
