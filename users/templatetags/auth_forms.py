"""Auth formalari uchun kichik yordamchilar (PUB1.4b)."""

from django import template
from django.forms.forms import NON_FIELD_ERRORS

register = template.Library()


@register.filter
def field_error_count(form):
    """Xatosi bor maydonlar soni — xulosa xatoni takrorlamaydi, faqat nechta joyni tekshirishni aytadi."""
    errors = getattr(form, "errors", None) or {}
    return sum(1 for name in errors if name != NON_FIELD_ERRORS)
