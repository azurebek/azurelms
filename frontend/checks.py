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
