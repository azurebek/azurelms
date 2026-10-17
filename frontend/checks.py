"""System check: har nomli route public, ops yoki private deb tasniflangan (PUB1.1a).

`manage.py check` (va har `runserver`/deploy) shu orqali yangi route'ning
anonimga ochiq-yopiqligi ongli qaror bo'lishini talab qiladi.
"""

from django.core.checks import Error, Tags, register

PUBLIC_ROUTE_REGISTRY_CHECK_ID = "azurelms.E201"


@register(Tags.urls)
def check_public_route_registry(app_configs, **kwargs):
    from frontend.public_policy import registry_errors

    return [
        Error(message, hint="frontend/public_policy.py", id=PUBLIC_ROUTE_REGISTRY_CHECK_ID)
        for message in registry_errors()
    ]


CANONICAL_ORIGIN_CHECK_ID = "azurelms.E202"


@register()
def check_canonical_origin(app_configs, **kwargs):
    """`PUBLIC_CANONICAL_ORIGIN` faqat `sxema://host[:port]` bo'ladi; serverda https (PUB1.1b)."""
    from urllib.parse import urlsplit

    from django.conf import settings

    origin = getattr(settings, "PUBLIC_CANONICAL_ORIGIN", "")
    parts = urlsplit(origin)
    problem = ""
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        problem = "sxema (http/https) va host bo'lishi shart"
    elif parts.path or parts.query or parts.fragment or parts.username or parts.password:
        problem = "yo'l, so'rov satri yoki login bo'lmasligi kerak"
    elif not settings.IS_LOCAL and parts.scheme != "https":
        problem = "serverda https bo'lishi shart"
    if not problem:
        return []
    return [Error(
        f"PUBLIC_CANONICAL_ORIGIN={origin!r}: {problem}.",
        hint="Masalan https://lms.example.com — canonical, og:url va ulashish havolalari shundan quriladi.",
        id=CANONICAL_ORIGIN_CHECK_ID,
    )]
