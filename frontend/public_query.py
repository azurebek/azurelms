"""Ochiq ro'yxatlar uchun umumiy so'rov chegaralari va sahifa havolalari (PUB1.3a, PUB1.6a).

Kurslar katalogi va Blog bir xil qoidadan foydalanadi:

* qidiruv matni NFKC, boshqaruv belgilari bo'shliqqa, bo'shliqlar bittaga;
  ko'pi bilan `MAX_TERMS` so'z va `MAX_QUERY_CHARS` belgi — uzun yoki
  shovqinli kirish bazaga yetmaydi;
* sahifa havolalari faqat normallashgan parametrlardan quriladi (raw so'rov
  satri qaytarilmaydi): birinchi, oxirgi va joriy atrofi, oraliqda `None`.

Qidiruv semantikasi (qaysi maydonda, qanday solishtiriladi) har domenning o'zida.
"""

import re
import unicodedata

MAX_QUERY_CHARS = 80
MAX_TERMS = 6

# O'zbek lotin yozuvidagi tutuq belgisining hamma ko'rinishi bitta belgiga.
_APOSTROPHES = str.maketrans({char: "'" for char in "‘’ʻʼ`´′"})
_WHITESPACE = re.compile(r"\s+")


def clean(value):
    """NFKC, boshqaruv belgilari bo'shliqqa, bo'shliqlar bittaga."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = "".join(" " if unicodedata.category(char).startswith("C") else char for char in text)
    return _WHITESPACE.sub(" ", text).strip()


def fold(value):
    """Solishtirish shakli: kichik harf, yagona tutuq belgisi, `İ` → `i`."""
    return clean(value).casefold().replace("̇", "").translate(_APOSTROPHES)


def bounded_text(value):
    """Formada ko'rinadigan va URL'da qoladigan chegaralangan qidiruv matni."""
    words = clean(value).split(" ")[:MAX_TERMS]
    return " ".join(words)[:MAX_QUERY_CHARS].strip()


def page_links(page_obj, url_for_page, *, window=1):
    """Raqamli sahifa havolalari: birinchi, oxirgi va joriy atrofi; oraliqda `None`."""
    total, current = page_obj.paginator.num_pages, page_obj.number
    shown = sorted({1, total, *range(max(1, current - window), min(total, current + window) + 1)})
    links, previous = [], 0
    for number in shown:
        if number - previous > 1:
            links.append(None)
        links.append({"number": number, "url": url_for_page(number), "current": number == current})
        previous = number
    return links


def pagination_context(page_obj, is_paginated, url_for_page):
    """Ikkala renderer shabloni uchun: raqamli havolalar, `rel=prev/next` manzillari."""
    if not is_paginated:
        return {"page_links": [], "previous_page_url": "", "next_page_url": ""}
    return {
        "page_links": page_links(page_obj, url_for_page),
        "previous_page_url": url_for_page(page_obj.number - 1) if page_obj.has_previous() else "",
        "next_page_url": url_for_page(page_obj.number + 1) if page_obj.has_next() else "",
    }
