"""SIT'ning umumiy ochiq infratuzilmaga adapteri (PUB1.6b).

Umumiy ochiq qatlam — route registri, meta, sitemap, cache, ro'yxat so'rovi —
SIT haqida faqat shu moduldan so'raydi: qaysi universitet, qo'llanma va e'lon
hozir amalda (effective), katalog havolalari qanday quriladi. SIT haqiqati
(manba, dolzarblik, versiya, so'rov, AI) SIT-01'da qoladi: SIT1.x effective
selectorlari kelganda faqat shu funksiyalarning ichi almashadi — sitemap, meta
yoki view'larda ikkinchi qoida paydo bo'lmaydi.

Katalog havolalari faqat normallashgan filtrdan quriladi (raw so'rov satri
qaytmaydi), standart qiymatlar URL'ga yozilmaydi, sahifa 1 yozilmaydi.
"""

from urllib.parse import urlencode

from django.db.models import Q
from django.urls import reverse

from .models import Announcement, KnowledgeArticle, University

# Formadagi tartib; `status` standarti "open" — URL'da yozilmaydi.
CATALOG_FILTER_KEYS = ("q", "type", "city", "language", "level", "price", "status")
DEFAULT_STATUS = University.AdmissionStatus.OPEN


def effective_universities():
    return University.objects.published()


def effective_articles():
    return KnowledgeArticle.objects.published()


def effective_announcements():
    """E'lon qilingan e'lonlar; nashr etilmagan universitetga bog'langani chiqmaydi (qoralama sizmasin)."""
    return Announcement.objects.filter(is_published=True).filter(
        Q(university__isnull=True) | Q(university__in=effective_universities())
    )


def catalog_pairs(filters, *, page=1):
    pairs = []
    for key in CATALOG_FILTER_KEYS:
        value = filters.get(key) or ""
        if key == "status" and value == DEFAULT_STATUS:
            continue
        if value:
            pairs.append((key, value))
    if page and page > 1:
        pairs.append(("page", str(page)))
    return pairs


def catalog_url(filters, *, page=1):
    query = urlencode(catalog_pairs(filters, page=page))
    return reverse("sit:university_list") + (f"?{query}" if query else "")
