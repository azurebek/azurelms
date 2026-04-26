from django.db.utils import OperationalError, ProgrammingError

from .models import AuthPageSettings, LandingNavItem, SiteSettings


def _serialize_landing_nav_items(request):
    try:
        nav_items = list(LandingNavItem.objects.all())
    except (OperationalError, ProgrammingError):
        nav_items = []

    if not nav_items:
        return [
            {
                "key": item["key"],
                "label": item["label"],
                "url": LandingNavItem.get_url_for_key(item["key"]),
                "is_active": LandingNavItem.is_key_active(item["key"], request),
            }
            for item in LandingNavItem.default_items()
            if item["is_visible"]
        ]

    return [
        {
            "key": item.key,
            "label": item.label,
            "url": item.get_url(),
            "is_active": item.is_active_for(request),
        }
        for item in nav_items
        if item.is_visible
    ]


def site_settings_context(request):
    try:
        site_settings = SiteSettings.load()
    except (OperationalError, ProgrammingError):
        site_settings = SiteSettings()

    try:
        auth_page_settings = AuthPageSettings.load()
    except (OperationalError, ProgrammingError):
        auth_page_settings = AuthPageSettings()

    return {
        "site_settings": site_settings,
        "auth_page_settings": auth_page_settings,
        "landing_nav_items": _serialize_landing_nav_items(request),
    }
