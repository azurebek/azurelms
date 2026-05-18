from django.db.utils import OperationalError, ProgrammingError

from .models import AuthPageSettings, LandingNavItem, LandingPage, SiteSettings


def _serialize_nav_queryset(request, nav_items):
    return [
        {
            "key": item.key,
            "label": item.label,
            "url": item.get_url(),
            "is_active": item.is_active_for(request),
            "open_in_new_tab": item.open_in_new_tab,
        }
        for item in nav_items
        if item.is_visible
    ]


def _serialize_default_nav_items(request, items):
    return [
        {
            "key": item["key"],
            "label": item["label"],
            "url": item.get("custom_url") or LandingNavItem.get_url_for_key(item["key"]),
            "is_active": LandingNavItem.is_key_active(item["key"], request),
            "open_in_new_tab": False,
        }
        for item in items
        if item["is_visible"]
    ]


def _serialize_landing_nav_items(request, placement=LandingNavItem.Placement.MAIN):
    try:
        nav_items = list(LandingNavItem.objects.filter(placement=placement))
    except (OperationalError, ProgrammingError):
        nav_items = []

    if not nav_items:
        if placement == LandingNavItem.Placement.UTILITY:
            return _serialize_default_nav_items(request, LandingNavItem.default_utility_items())
        if placement in {
            LandingNavItem.Placement.FOOTER_PLATFORM,
            LandingNavItem.Placement.FOOTER_COMPANY,
            LandingNavItem.Placement.FOOTER_LEGAL,
        }:
            return _serialize_default_nav_items(request, LandingNavItem.default_footer_items(placement))
        return _serialize_default_nav_items(request, LandingNavItem.default_items())

    return _serialize_nav_queryset(request, nav_items)


def site_settings_context(request):
    try:
        site_settings = SiteSettings.load()
    except (OperationalError, ProgrammingError):
        site_settings = SiteSettings()

    try:
        auth_page_settings = AuthPageSettings.load()
    except (OperationalError, ProgrammingError):
        auth_page_settings = AuthPageSettings()

    try:
        public_page_settings = LandingPage.load()
    except (OperationalError, ProgrammingError):
        public_page_settings = LandingPage()

    return {
        "site_settings": site_settings,
        "auth_page_settings": auth_page_settings,
        "public_page_settings": public_page_settings,
        "landing_nav_items": _serialize_landing_nav_items(request),
        "utility_nav_items": _serialize_landing_nav_items(request, LandingNavItem.Placement.UTILITY),
        "footer_platform_links": _serialize_landing_nav_items(request, LandingNavItem.Placement.FOOTER_PLATFORM),
        "footer_company_links": _serialize_landing_nav_items(request, LandingNavItem.Placement.FOOTER_COMPANY),
        "footer_legal_links": _serialize_landing_nav_items(request, LandingNavItem.Placement.FOOTER_LEGAL),
    }
