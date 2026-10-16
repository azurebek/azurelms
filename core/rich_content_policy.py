"""Public rich text uchun yagona, nomlangan sanitizer profili (PUBLIC-01 · PUB1.0a).

Landing, About, legal/FAQ, kurs tavsifi, tarif tavsifi, Blog va SIT qo'llanmasi
DB'dagi HTMLni ommaga ko'rsatadi. Legacy rendererlar uni raw `|safe` bilan,
V1 esa umumiy `bleach_tags.sanitize` bilan chiqarardi. Ikkinchisi ham public
sirt uchun yetarli emas: u `iframe`, global `style/class/id` va keng CSSni
o'tkazadi, protocol-relative (`//host`) va backslashli (`/\\host`) havolalarni
esa tekshirmaydi — brauzer ikkalasini ham tashqi saytga ochadi.

Nega `bleach_tags.sanitize`ni joyida qattiqlashtirmadik: u private dars, imtihon
va amaliyot kontentini ham chiqaradi; uni o'zgartirish o'sha consumerlarni
moslik auditisiz sindirardi (SIT-01 va BLOG-01 rejalari ham unga tegmaslikni
talab qiladi). Shuning uchun public sirt alohida, **nomlangan va versiyalangan**
profil oladi. Qoida o'zgarsa yangi nom (`..._V2`) beriladi — saqlangan
snapshot qaysi qoida bilan tozalangani shunda aniq qoladi.

Tozalash ikki bosqichda. Birinchisi `<script>`, `<style>`, `<svg>` kabi
konteynerlarni ichidagi matn bilan olib tashlaydi (aks holda bleach tegni
olib, `alert(1)` yoki CSS matnini sahifada qoldiradi). Ikkinchisi — xavfsizlik
chegarasi: faqat semantik teglar, aniq atributlar va tekshirilgan URL'lar.
Birinchi bosqich xato qilsa ham ikkinchisi executable markupni o'tkazmaydi;
eng yomon holat — ko'rinadigan matn, XSS emas.

Bu modul `core`da: Blog/SIT domain wrapperlari (`blog/content_policy.py`,
`sit/content_policy.py`) keyin shu profilni tanlaydi, parallel allowlist
yozilmaydi.
"""

import re
from html import unescape
from urllib.parse import urlsplit

import bleach
from bleach.html5lib_shim import Filter
from django.conf import settings

PUBLIC_EDITORIAL_V1 = "PUBLIC_EDITORIAL_V1"

# CKEditor 5 konfiguratsiyasi (`core/settings.py`) aynan shu teglarni hosil
# qiladi: sarlavha, ro'yxat, iqtibos, jadval va `figure` ichidagi rasm.
EDITORIAL_TAGS = frozenset({
    "p", "br", "hr", "div", "span",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u", "s", "sub", "sup", "small", "mark",
    "ul", "ol", "li",
    "blockquote", "pre", "code",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
    "figure", "figcaption", "img",
    "a",
})

# `iframe` ikkinchi bosqichga kiradi, lekin hech qachon chiqmaydi: filter uni
# xavfsiz havolaga aylantiradi yoki butunlay olib tashlaydi.
_EMBED_TAGS = frozenset({"iframe"})

# Ichidagi matn bilan birga yo'qoladigan konteynerlar.
_DROP_WITH_CONTENT = frozenset({
    "script", "style", "noscript", "template", "textarea", "select", "title",
    "xmp", "svg", "math", "object", "embed", "applet", "frameset", "noembed",
})

# CKEditor 5 `figure` uchun ishlatadigan presentation classlari. Boshqa har qanday
# class/style/id rad etiladi.
FIGURE_CLASSES = frozenset({
    "image", "table", "image_resized", "image-style-side",
    "image-style-align-left", "image-style-align-right", "image-style-align-center",
})

LINK_SCHEMES = ("http", "https", "mailto", "tel")
NAV_SCHEMES = ("https", "mailto", "tel")

_UNSAFE_URL_CHARS = re.compile(r"[\x00-\x1f\x7f\\]")
_POSITIVE_INT = re.compile(r"^[1-9][0-9]{0,4}$")
_WHITESPACE = re.compile(r"\s+")
_BLOCK_BOUNDARY = re.compile(
    r"</(?:p|div|h[1-6]|li|blockquote|pre|tr|th|td|caption|figcaption|figure)>|<br\s*/?>|<hr\s*/?>"
)


def safe_url(value, *, schemes=LINK_SCHEMES, allow_local=True, allow_fragment=False):
    """Ruxsat etilgan URLni qaytaradi, aks holda ``""``.

    Lokal manzil faqat bitta ``/`` bilan boshlanadi: ``//host`` va ``/\\host``
    brauzerda tashqi saytga aylanadi, shuning uchun ular rad etiladi. Control
    belgilar (``java\\tscript:``) va backslash har qanday joyda rad. Absolute
    ``http(s)`` manzilda host bo'lishi shart va ``user@host`` hiylasi rad.
    """
    value = str(value or "").strip()
    if not value or _UNSAFE_URL_CHARS.search(value):
        return ""
    if value.startswith("#"):
        return value if allow_fragment and len(value) > 1 else ""
    try:
        parts = urlsplit(value)
    except ValueError:
        return ""
    scheme = parts.scheme.lower()
    if not scheme:
        if allow_local and value.startswith("/") and not value.startswith("//") and not parts.netloc:
            return value
        return ""
    if scheme not in schemes:
        return ""
    if scheme in ("http", "https"):
        if not parts.hostname or "@" in parts.netloc:
            return ""
        try:
            parts.port
        except ValueError:
            return ""
        return value
    # mailto / tel
    return value if parts.path.strip() else ""


def _local_prefix(url):
    url = str(url or "")
    if not url or urlsplit(url).scheme:
        return ""
    return "/" + url.lstrip("/")


def approved_image_src(value):
    """Rasm faqat ilovaning o'z media/static manzilidan.

    Tashqi hostdan ulangan rasm o'quvchi IP'sini begona serverga beradi va
    keyinchalik boshqa kontentga almashtirilishi mumkin. S3 yoqilganda
    `MEDIA_URL` absolute bo'ladi — o'sha host avtomatik tasdiqlangan.
    """
    url = safe_url(value, schemes=("https",), allow_local=True)
    if not url:
        return ""
    # `/media/../boshqa/` prefiksdan o'tadi, ammo brauzer uni media'dan tashqaridagi
    # same-origin endpointga normallashtiradi va `<img>` o'sha yerga GET yuboradi.
    path = urlsplit(url).path
    if "%2e" in path.lower() or any(segment in (".", "..") for segment in path.split("/")):
        return ""
    media_url = str(settings.MEDIA_URL or "")
    prefixes = [p for p in (_local_prefix(media_url), _local_prefix(settings.STATIC_URL)) if p]
    if urlsplit(media_url).scheme == "https":
        prefixes.append(media_url)
    return url if any(url.startswith(prefix) for prefix in prefixes) else ""


def _figure_class_allowed(tag, name, value):
    tokens = value.split()
    return bool(tokens) and all(token in FIGURE_CLASSES for token in tokens)


def _positive_int(tag, name, value):
    return bool(_POSITIVE_INT.match(value.strip()))


def _cell_attr(tag, name, value):
    if name in ("colspan", "rowspan"):
        return _positive_int(tag, name, value)
    return name == "scope" and value in ("row", "col", "rowgroup", "colgroup")


def _img_attribute(tag, name, value):
    if name in ("width", "height"):
        return _positive_int(tag, name, value)
    return name in ("src", "alt", "title")


def _ol_attribute(tag, name, value):
    return name == "start" and _positive_int(tag, name, value)


# Global `class/style/id` yo'q: arbitrary id sahifadagi boshqa elementni
# soya qiladi (DOM clobbering), class/style esa UI'ni soxta tugma yoki
# overlayga aylantira oladi.
EDITORIAL_ATTRIBUTES = {
    "a": ["href", "title", "target"],
    "img": _img_attribute,
    "iframe": ["src", "title"],
    "figure": _figure_class_allowed,
    "th": _cell_attr,
    "td": _cell_attr,
    "ol": _ol_attribute,
}


def _attr(name):
    """html5lib token atributlari `(namespace, name)` kalit bilan saqlanadi."""
    return (None, name)


class _DropContainers(Filter):
    """Birinchi bosqich: `_DROP_WITH_CONTENT` teglarini matni bilan olib tashlaydi."""

    def __iter__(self):
        skip_name = None
        depth = 0
        for token in super().__iter__():
            kind = token["type"]
            name = token.get("name")
            if skip_name is not None:
                if kind == "StartTag" and name == skip_name:
                    depth += 1
                elif kind == "EndTag" and name == skip_name:
                    depth -= 1
                    if depth == 0:
                        skip_name = None
                continue
            if name in _DROP_WITH_CONTENT:
                if kind == "StartTag":
                    skip_name, depth = name, 1
                continue
            yield token


class _EditorialLinks(Filter):
    """Ikkinchi bosqich: havola, rasm va embedni profil qoidasiga keltiradi."""

    def __iter__(self):
        in_embed = False
        # Har ochilgan `a` uchun: saqlandimi (True) yoki unwrap qilindimi (False).
        links = []
        for token in super().__iter__():
            kind = token["type"]
            name = token.get("name")

            if in_embed:
                if kind == "EndTag" and name in _EMBED_TAGS:
                    in_embed = False
                continue

            if name in _EMBED_TAGS and kind in ("StartTag", "EmptyTag"):
                in_embed = kind == "StartTag"
                yield from self._embed_as_link(token)
                continue

            if name == "a" and kind == "StartTag":
                link = self._link(token)
                links.append(link is not None)
                if link is not None:
                    yield link
                continue

            if name == "a" and kind == "EndTag":
                # Rad etilgan havola matn bo'lib qoladi: `href`siz `<a>` CSSda
                # baribir havoladek chiziladi va bosib bo'lmaydigan tugma bo'ladi.
                if not links or links.pop():
                    yield token
                continue

            if name == "img" and kind in ("StartTag", "EmptyTag"):
                replacement = self._image(token)
                if replacement is not None:
                    yield replacement
                continue

            yield token

    @staticmethod
    def _link(token):
        data = dict(token.get("data") or {})
        href = safe_url(data.get(_attr("href")), schemes=LINK_SCHEMES, allow_fragment=True)
        target = data.get(_attr("target"))
        if not href:
            return None
        data.pop(_attr("target"), None)
        data.pop(_attr("rel"), None)
        data[_attr("href")] = href
        external = urlsplit(href).scheme in ("http", "https")
        if target == "_blank":
            data[_attr("target")] = "_blank"
        if external or target == "_blank":
            data[_attr("rel")] = "noopener noreferrer"
        return {**token, "data": data}

    @staticmethod
    def _image(token):
        data = dict(token.get("data") or {})
        src = approved_image_src(data.get(_attr("src")))
        alt = data.get(_attr("alt"))
        if not src:
            # Rasm ruxsatsiz manzildan: ma'nosi saqlanishi uchun faqat alt matni.
            return {"type": "Characters", "data": alt} if alt else None
        data[_attr("src")] = src
        # alt yo'q bo'lsa — dekorativ belgisi; audit buni alohida ko'rsatadi.
        data.setdefault(_attr("alt"), "")
        return {**token, "type": "EmptyTag", "data": data}

    @staticmethod
    def _embed_as_link(token):
        """Raw embed public sahifaga chiqmaydi; xavfsiz https bo'lsa havola qoladi."""
        data = token.get("data") or {}
        src = safe_url(data.get(_attr("src")), schemes=("https",), allow_local=False)
        if not src:
            return
        yield {
            "type": "StartTag", "name": "a", "namespace": None,
            "data": {
                _attr("href"): src,
                _attr("target"): "_blank",
                _attr("rel"): "noopener noreferrer",
            },
        }
        yield {"type": "Characters", "data": "Videoni ochish"}
        yield {"type": "EndTag", "name": "a", "namespace": None}


_STAGE_ONE = bleach.sanitizer.Cleaner(
    tags=EDITORIAL_TAGS | _EMBED_TAGS | _DROP_WITH_CONTENT,
    attributes=lambda tag, name, value: True,
    protocols=list(LINK_SCHEMES),
    strip=True,
    strip_comments=True,
    filters=[_DropContainers],
)

_STAGE_TWO = bleach.sanitizer.Cleaner(
    tags=EDITORIAL_TAGS | _EMBED_TAGS,
    attributes=EDITORIAL_ATTRIBUTES,
    protocols=list(LINK_SCHEMES),
    strip=True,
    strip_comments=True,
    filters=[_EditorialLinks],
)

_PLAIN = bleach.sanitizer.Cleaner(tags=set(), attributes={}, strip=True, strip_comments=True)


def sanitize_public_editorial(value):
    """`PUBLIC_EDITORIAL_V1` bo'yicha tozalangan HTML (oddiy `str`, safe emas).

    Idempotent: natijani qayta tozalash uni o'zgartirmaydi. Belgilangan safe
    qilish template wrapperning ishi (`frontend.templatetags.public_content`).
    """
    if not value:
        return ""
    return _STAGE_TWO.clean(_STAGE_ONE.clean(str(value)))


def public_plain_text(value, max_chars=None):
    """Meta description va preview uchun ayni profildan olingan oddiy matn.

    Avval profil bilan tozalanadi (script/style matni ham ketadi), keyin barcha
    teglar olinadi va bo'shliqlar bittaga qisqaradi. Natija HTML emas —
    template uni odatdagidek escape qiladi.
    """
    # Blok chegarasida bo'shliq: aks holda `<h2>Salom</h2><p>Dunyo` "SalomDunyo"ga
    # yopishib qoladi. Tozalangan HTML normallashgani uchun oddiy regex yetarli.
    html = _BLOCK_BOUNDARY.sub(r"\g<0> ", sanitize_public_editorial(value))
    text = unescape(_PLAIN.clean(html))
    text = _WHITESPACE.sub(" ", text).strip()
    if max_chars and len(text) > max_chars:
        head = text[: max_chars - 1]
        # Kesish so'z o'rtasiga tushsa, chala so'z tashlanadi; so'z chegarasiga
        # tushsa, oxirgi to'liq so'z saqlanadi.
        if not text[max_chars - 1].isspace() and " " in head:
            head = head.rsplit(" ", 1)[0]
        text = f"{head.rstrip(' ,.;:')}…"
    return text
