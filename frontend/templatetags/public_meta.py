"""`{% public_meta_tags %}` — har `<head>` uchun yagona metadata bloki (PUB1.1b)."""

from django import template

from frontend.public_meta import build_meta

register = template.Library()


@register.inclusion_tag("components/public_meta.html", takes_context=True)
def public_meta_tags(context, force_noindex=False):
    request = context.get("request")
    if request is None:
        return {"meta": None}
    return {"meta": build_meta(request, context.flatten(), force_noindex=force_noindex)}
