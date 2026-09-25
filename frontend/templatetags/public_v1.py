from urllib.parse import urlsplit

from django import template

register = template.Library()


@register.filter
def public_url(value):
    """Admin-authored navigation is a link, never executable markup."""
    value = str(value or "").strip()
    if not value or value == "#" or any(ord(char) < 32 or char == "\\" for char in value):
        return ""
    try:
        parts = urlsplit(value)
    except ValueError:
        return ""
    if parts.scheme in {"http", "https", "mailto", "tel"}:
        return value
    return value if not parts.scheme and not parts.netloc and value.startswith("/") else ""
