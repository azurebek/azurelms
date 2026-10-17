"""Dalili tasdiqlangan public da'volar shablon uchun (PUB1.2a)."""

from django import template

from frontend.public_claims import verified_landing_statistics

register = template.Library()


@register.simple_tag
def verified_statistics(limit=None):
    return verified_landing_statistics(limit)
