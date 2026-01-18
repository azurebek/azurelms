from django.shortcuts import render
from .models import PageBlock, SiteConfig


def home_view(request):
    blocks = PageBlock.objects.filter(is_active=True)
    site = SiteConfig.objects.first()
    return render(request, "landing/home.html", {
        "blocks": blocks,
        "site": site,
    })
