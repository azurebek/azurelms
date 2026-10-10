"""Public stylesheet references only; draft and actor data never enter markup."""
from django import template
from django.db import DatabaseError
from django.templatetags.static import static
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html

from core.flags import UnknownFlag, flag_enabled

register = template.Library()


@register.simple_tag(takes_context=True)
def published_design_css(context):
    if context.get('design_theme_disabled'):
        return ''
    try:
        if not flag_enabled('backoffice_design_workspace'):
            return ''
        theme_url = reverse('design_theme_css')
        adapter_url = static('backoffice/design-runtime.css')
    except (DatabaseError, UnknownFlag, NoReverseMatch):
        # A missing migration/route or unreadable flag keeps the static theme.
        return ''
    return format_html(
        '<link rel="stylesheet" href="{}" media="screen" data-design-published>'
        '<link rel="stylesheet" href="{}" media="screen" data-design-runtime>',
        theme_url, adapter_url,
    )
