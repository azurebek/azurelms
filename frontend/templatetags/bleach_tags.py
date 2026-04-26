import bleach
from bleach.css_sanitizer import CSSSanitizer
from django import template
from django.conf import settings

register = template.Library()

# Allowed HTML tags for the rich text editor
ALLOWED_TAGS = [
    'a', 'b', 'i', 'strong', 'em', 'p', 'br',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'span', 'div',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'img', 'blockquote', 'pre', 'code', 'hr', 'iframe'
]

# Allowed attributes for specific tags
ALLOWED_ATTRIBUTES = {
    '*': ['class', 'style', 'id'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height'],
    'iframe': ['src', 'width', 'height', 'frameborder', 'allow', 'allowfullscreen']
}

# Allowed CSS styles
ALLOWED_STYLES = [
    'color', 'font-family', 'font-size', 'font-weight',
    'text-align', 'background-color', 'width', 'height',
    'margin', 'padding', 'margin-top', 'margin-bottom', 'margin-left', 'margin-right',
    'padding-top', 'padding-bottom', 'padding-left', 'padding-right',
    'border', 'border-radius', 'float', 'display'
]

from django.utils.safestring import mark_safe

@register.filter(name='sanitize')
def sanitize(value):
    """
    Sanitizes HTML content to prevent XSS attacks while allowing rich text formatting.
    """
    if not value:
        return ""
        
    css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_STYLES)
        
    cleaned_html = bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        css_sanitizer=css_sanitizer,
        strip=True
    )
    return mark_safe(cleaned_html)
