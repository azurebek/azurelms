from .models import SiteSettings


def site_settings_context(request):
    return {
        "site_settings": SiteSettings.load(),
    }
