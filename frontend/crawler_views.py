"""`robots.txt` va `sitemap.xml` (PUB1.1c).

`robots.txt` maxfiylik yoki auth vositasi emas: private yo'llar ro'yxati
berilmaydi (u xaritaga aylanardi) va `noindex` sahifalar yopilmaydi — aks holda
crawler `noindex`ni ko'ra olmasdi. Faqat sitemap ko'rsatkichi.
"""

from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.views.decorators.http import require_safe

from frontend.public_meta import absolute_url
from frontend.public_sitemap import sitemap_entries


def _no_stale_cache(response):
    # Obyekt e'lon qilinmay qolsa keyingi so'rovda xaritadan chiqishi kerak.
    response["Cache-Control"] = "no-cache"
    return response


@require_safe
def robots_txt(request):
    body = "User-agent: *\nDisallow:\n\nSitemap: " + absolute_url("/sitemap.xml") + "\n"
    return _no_stale_cache(HttpResponse(body, content_type="text/plain; charset=utf-8"))


@require_safe
def sitemap_xml(request):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for entry in sitemap_entries():
        lastmod = f"<lastmod>{entry.lastmod.isoformat(timespec='seconds')}</lastmod>" if entry.lastmod else ""
        lines.append(f"<url><loc>{escape(entry.loc)}</loc>{lastmod}</url>")
    lines.append("</urlset>")
    return _no_stale_cache(HttpResponse("\n".join(lines) + "\n", content_type="application/xml; charset=utf-8"))
