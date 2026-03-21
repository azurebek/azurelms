from django.conf import settings


def backoffice_flags(_request):
    return {
        "ENABLE_LEGACY_ADMIN": getattr(settings, "ENABLE_LEGACY_ADMIN", True),
    }
