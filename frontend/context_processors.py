from urllib.parse import urlsplit

from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse

from core.flags import flag_enabled

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


def _nav_items_by_placement():
    """Barcha navigatsiya qatorlari bitta so'rovda, joylashuv bo'yicha (PUB1.2b).

    Ilgari har joylashuv (asosiy, utility, uchta footer) alohida so'rov edi —
    har sahifada beshta.
    """
    try:
        items = list(LandingNavItem.objects.order_by("order", "id"))
    except (OperationalError, ProgrammingError):
        items = []
    grouped = {}
    for item in items:
        grouped.setdefault(item.placement, []).append(item)
    return grouped


def _serialize_landing_nav_items(request, placement=LandingNavItem.Placement.MAIN, grouped=None):
    if grouped is None:
        grouped = _nav_items_by_placement()
    nav_items = grouped.get(placement, [])

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

    grouped = _nav_items_by_placement()
    placement = LandingNavItem.Placement
    registration_open = flag_enabled("public_registration")  # DB xatosida e'lon qilingan default
    # Ro'yxat yopiq bo'lsa ro'yxatga olib boruvchi menyu qatori (kalit yoki
    # custom URL orqali) ko'rinmaydi: u yopiq eshikka olib boradi (PUB1.2d, PUB-D2).
    closed_paths = set() if registration_open else {reverse("register")}

    def nav(place):
        rows = _serialize_landing_nav_items(request, place, grouped)
        return [row for row in rows if urlsplit(row["url"]).path not in closed_paths]

    context = {
        # Ro'yxat yopiq bo'lsa "Ro'yxatdan o'tish" CTA'si o'lik yo'lga olib
        # boradi — o'rniga kurslar katalogi (PUB1.2d, PUB-D1/PUB-D2).
        "public_registration_open": registration_open,
        "site_settings": site_settings,
        "auth_page_settings": auth_page_settings,
        "public_page_settings": public_page_settings,
        "landing_nav_items": nav(placement.MAIN),
        "utility_nav_items": nav(placement.UTILITY),
        "footer_platform_links": nav(placement.FOOTER_PLATFORM),
        "footer_company_links": nav(placement.FOOTER_COMPANY),
        "footer_legal_links": nav(placement.FOOTER_LEGAL),
    }
    # Footer guruhlari bitta joyda: legacy va V1 ayni sarlavha va tartibni chizadi.
    context["footer_groups"] = (
        ("Platforma", context["footer_platform_links"]),
        ("Kompaniya", context["footer_company_links"]),
        ("Huquqiy", context["footer_legal_links"]),
    )
    return context
