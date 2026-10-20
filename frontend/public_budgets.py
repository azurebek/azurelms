"""Ochiq sahifalarning asset byudjeti (PUB1.7b).

Har ochiq sahifa (legacy va V1) faqat o'z serverimizdagi CSS/JS'ni yuklaydi;
ularning siqilgan (gzip) hajmi shu yerdagi byudjetdan oshsa
`frontend/test_public_budgets.py` CI'da yiqiladi — sekinlashish jim o'tmaydi.

Byudjet 2026-10-20 o'lchovidan ~10% zaxira bilan. Ataylab qo'shilgan katta
asset uchun byudjetni shu faylda, sababi bilan oshiring; "testni o'chirish"
yo'li yo'q. Rasm/video baytlari bu yerda emas (ular kontentga bog'liq) —
ular uchun `manage.py audit_public_media` va karta o'lchami qoidasi bor.

V1 ochiq sahifasi ilova bundle'ini (`auth.css`, `learning.css`, `shell.js`)
umuman yuklamaydi.
"""

import gzip
import re
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.staticfiles import finders

TAG_RE = re.compile(r"<(link|script)\b([^>]*)>", re.I)
ATTR_RE = {name: re.compile(rf'\b{name}\s*=\s*"([^"]*)"', re.I) for name in ("href", "src", "rel")}
# Uchinchi tomonga ulanish bo'ladigan `<link>` turlari (atribut tartibidan qat'i nazar).
FETCHING_RELS = {"stylesheet", "preload", "preconnect", "dns-prefetch", "modulepreload", "prefetch"}
APP_BUNDLE = ("frontend_v1/css/auth.css", "frontend_v1/css/learning.css", "frontend_v1/js/shell.js")

# Siqilgan (gzip -9) bayt, sahifa turi bo'yicha eng og'ir sahifa. 2026-10-20 o'lchovi:
# legacy ochiq 20 221 / 2 858, legacy kirish 16 980 / 7 663, V1 ochiq 8 210 / 2 313
# (ilova bundle'isiz; avval ~11 000 CSS), V1 kirish 8 273 / 7 345.
BUDGETS = {
    ("legacy", "public"): {"css": 22_500, "js": 3_200},
    ("legacy", "auth"): {"css": 19_000, "js": 8_500},
    ("v1", "public"): {"css": 9_100, "js": 2_600},
    ("v1", "auth"): {"css": 9_200, "js": 8_200},
}


def _attr(attrs, name):
    match = ATTR_RE[name].search(attrs)
    return match.group(1) if match else ""


def asset_urls(html):
    """`[(tur, url), ...]` — tur `css`, `js` yoki `hint` (preconnect/preload kabi)."""
    assets = []
    for tag, attrs in TAG_RE.findall(html):
        if tag.lower() == "script":
            src = _attr(attrs, "src")
            if src:
                assets.append(("js", src))
            continue
        href, rels = _attr(attrs, "href"), set(_attr(attrs, "rel").lower().split())
        if not href or not rels & FETCHING_RELS:
            continue
        assets.append(("css" if "stylesheet" in rels else "hint", href))
    return assets


def is_external(url):
    parts = urlsplit(url)
    return bool(parts.scheme or parts.netloc)


def static_path(url):
    """`/static/x/y.css?v=…` → `x/y.css`; static bo'lmasa ``None``."""
    path = urlsplit(url).path
    prefix = settings.STATIC_URL if settings.STATIC_URL.startswith("/") else "/" + settings.STATIC_URL
    return path[len(prefix):] if path.startswith(prefix) else None


def gzip_size(path):
    found = finders.find(path)
    if not found:
        raise FileNotFoundError(path)
    with open(found, "rb") as handle:
        return len(gzip.compress(handle.read(), compresslevel=9, mtime=0))


def page_weight(html):
    """`{"css": bayt, "js": bayt, "paths": [...], "external": [...]}`."""
    weight = {"css": 0, "js": 0, "paths": [], "external": []}
    for kind, url in asset_urls(html):
        if is_external(url):
            weight["external"].append(url)
            continue
        path = static_path(url)
        if path is None or kind == "hint":
            continue
        weight["paths"].append(path)
        weight[kind] += gzip_size(path)
    return weight
