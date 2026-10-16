"""Mavjud public kontentning read-only auditi (PUBLIC-01 · PUB1.0a).

Render-time sanitizer bugundan ommaga xavfli markup chiqishini to'xtatadi, lekin
DB'dagi asl matnni o'zgartirmaydi — avtomatik qayta yozish owner kontentini
ko'r-ko'rona buzardi. Bu audit qaysi qatorlarda profil olib tashlaydigan narsa
borligini **faqat ID va topilma turi** bilan ko'rsatadi: kontentning o'zi,
payload yoki URL hisobotga, logga va stdoutga chiqmaydi.

Hech qanday yozuv yo'q: faqat `values_list` o'qiladi.
"""

from html.parser import HTMLParser

from django.apps import apps

from core.rich_content_policy import (
    FIGURE_CLASSES,
    LINK_SCHEMES,
    PUBLIC_EDITORIAL_V1,
    approved_image_src,
    safe_url,
)
from frontend.public_url_policy import public_link_url, public_nav_url

# Public rendererlar `public_rich` bilan chiqaradigan maydonlar.
RICH_TEXT_FIELDS = (
    ("frontend.LandingPage", "hero_subtitle"),
    ("frontend.AboutPage", "hero_subtitle"),
    ("frontend.AboutPage", "mission_text"),
    ("frontend.AboutPage", "vision_text"),
    ("frontend.TeamMember", "bio"),
    ("frontend.LegalPage", "content"),
    ("courses.Course", "description"),
    ("subscriptions.Plan", "description"),
    ("blog.BlogPost", "body"),
    ("sit.KnowledgeArticle", "body"),
)

# Admin kiritadigan public havolalar va ularga qo'llanadigan siyosat.
URL_FIELDS = (
    ("frontend.LandingNavItem", "custom_url", "nav"),
    ("frontend.SiteSettings", "telegram_url", "nav"),
    ("frontend.SiteSettings", "instagram_url", "nav"),
    ("frontend.SiteSettings", "youtube_url", "nav"),
    ("sit.University", "official_website", "link"),
    ("sit.University", "source_url", "link"),
    ("sit.UniversityMedia", "video_url", "link"),
    ("sit.Announcement", "external_url", "link"),
    ("sit.KnowledgeArticle", "source_url", "link"),
)

FINDING_KINDS = (
    "executable",       # script/style/svg/form, on* handler, srcdoc
    "embed",            # iframe/object/embed — public sahifada havolaga aylanadi yoki yo'qoladi
    "unsafe_url",       # javascript:/data:/protocol-relative/backslash/user@host
    "presentation",     # style, id yoki ruxsatsiz class
    "external_image",   # ilova media/static'idan tashqaridagi rasm
    "missing_alt",      # alt'siz rasm (dekorativ deb chiqariladi)
)

_EXECUTABLE_TAGS = frozenset({
    "script", "style", "noscript", "template", "svg", "math", "form", "input",
    "button", "select", "textarea", "link", "meta", "base", "frame", "frameset",
    "applet", "noembed",
})
_EMBED_TAGS = frozenset({"iframe", "object", "embed"})
_URL_ATTRS = frozenset({"href", "src", "action", "formaction", "xlink:href", "background", "poster"})

_POLICIES = {"nav": public_nav_url, "link": public_link_url}


class _Inspector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.kinds = set()

    def handle_starttag(self, tag, attrs):
        self._inspect(tag, attrs)

    def handle_startendtag(self, tag, attrs):
        self._inspect(tag, attrs)

    def _inspect(self, tag, attrs):
        if tag in _EXECUTABLE_TAGS:
            self.kinds.add("executable")
        if tag in _EMBED_TAGS:
            self.kinds.add("embed")
        values = {}
        for name, value in attrs:
            value = value or ""
            values[name] = value
            if name.startswith("on") or name == "srcdoc":
                self.kinds.add("executable")
            elif name in ("style", "id"):
                self.kinds.add("presentation")
            elif name == "class":
                tokens = value.split()
                if tag != "figure" or not tokens or any(t not in FIGURE_CLASSES for t in tokens):
                    self.kinds.add("presentation")
            elif name in _URL_ATTRS and tag != "img":
                if not safe_url(value, schemes=LINK_SCHEMES, allow_fragment=True):
                    self.kinds.add("unsafe_url")
        if tag == "img":
            src = values.get("src", "")
            if not safe_url(src, schemes=LINK_SCHEMES):
                self.kinds.add("unsafe_url")
            elif not approved_image_src(src):
                self.kinds.add("external_image")
            if "alt" not in values:
                self.kinds.add("missing_alt")


def inspect_html(value):
    """Bitta HTML qiymatdagi topilma turlari (kontent qaytarilmaydi)."""
    parser = _Inspector()
    try:
        parser.feed(str(value or ""))
        parser.close()
    except Exception:  # noqa: BLE001 — buzuq HTML ham audit natijasi
        parser.kinds.add("executable")
    return parser.kinds


def _rows(label, field):
    model = apps.get_model(label)
    return model._default_manager.order_by("pk").values_list("pk", field)


def audit_public_content():
    """Public rich text va URL maydonlari bo'yicha ID-only hisobot."""
    rich = []
    for label, field in RICH_TEXT_FIELDS:
        findings = {kind: [] for kind in FINDING_KINDS}
        total = flagged = 0
        for pk, value in _rows(label, field):
            total += 1
            kinds = inspect_html(value) if value else set()
            if kinds:
                flagged += 1
            for kind in kinds:
                findings[kind].append(pk)
        rich.append({
            "field": f"{label}.{field}",
            "rows": total,
            "flagged": flagged,
            "findings": {kind: ids for kind, ids in findings.items() if ids},
        })

    urls = []
    for label, field, policy in URL_FIELDS:
        allowed = _POLICIES[policy]
        total = 0
        rejected = []
        for pk, value in _rows(label, field):
            if not value:
                continue
            total += 1
            if not allowed(value):
                rejected.append(pk)
        urls.append({
            "field": f"{label}.{field}",
            "policy": policy,
            "rows": total,
            "rejected": rejected,
        })

    return {"profile": PUBLIC_EDITORIAL_V1, "rich_text": rich, "urls": urls}
