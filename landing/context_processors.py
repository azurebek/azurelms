from .models import SiteConfig


def site_config(request):
    site = SiteConfig.objects.first()
    menu_links = site.menu_links.filter(is_active=True) if site else []
    return {
        "site": site,
        "menu_links": menu_links,
    }
