from django.db.utils import OperationalError, ProgrammingError

from .models import AuthPageSettings, LandingNavItem, LandingPage, SiteSettings
from .public_url_policy import public_nav_url


# Navbar va footer havolalari shu yerda bir marta navigatsiya siyosatidan
# o'tadi (PUB1.0a). Legacy va V1 ayni ro'yxatni oladi; ruxsatsiz URL'li
# element ko'rinmaydi — `#` yoki `javascript:` havolasi bo'lib chiqmaydi.
# Yashirilgan qatorlar `manage.py audit_public_content` hisobotida ko'rinadi.
def _serialize_nav_queryset(request, nav_items):
    rows = []
    for item in nav_items:
        if not item.is_visible:
            continue
        url = public_nav_url(item.get_url())
        if not url:
            continue
        rows.append({
            "key": item.key,
            "label": item.label,
            "url": url,
            "is_active": item.is_active_for(request),
            "open_in_new_tab": item.open_in_new_tab,
        })
    return rows


def _serialize_default_nav_items(request, items):
    rows = []
    for item in items:
        if not item["is_visible"]:
            continue
        url = public_nav_url(item.get("custom_url") or LandingNavItem.get_url_for_key(item["key"]))
        if not url:
            continue
        rows.append({
            "key": item["key"],
            "label": item["label"],
            "url": url,
            "is_active": LandingNavItem.is_key_active(item["key"], request),
            "open_in_new_tab": False,
        })
    return rows


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
        site_settings = SiteSettings.current()
    except (OperationalError, ProgrammingError):
        site_settings = SiteSettings()

    try:
        auth_page_settings = AuthPageSettings.current()
    except (OperationalError, ProgrammingError):
        auth_page_settings = AuthPageSettings()

    try:
        public_page_settings = LandingPage.current()
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
