"""Rasm qatlami: (1) yuklangan rasmni vision-model uchun tayyorlash,
(2) AI yozgan <SVG_IMAGE> blokidan xavfsiz SVG fayl yasash.

SVG XAVFSIZLIGI: AI chiqishi ishonchsiz hisoblanadi. sanitize_svg qat'iy
allowlist bilan ishlaydi — script/foreignObject/event-handlerlar/tashqi
havolalar olib tashlanadi, natija <img> ichida ham, to'g'ridan ochilganda ham
kod bajarmaydi.
"""
import base64
import io
import logging
import re
from xml.etree import ElementTree

logger = logging.getLogger(__name__)

MAX_IMAGE_SIDE = 1280
MAX_SOURCE_BYTES = 10 * 1024 * 1024

SVG_IMAGE_PATTERN = re.compile(
    r"<SVG_IMAGE(?:\s+title=\"(?P<title>[^\"]{0,200})\")?\s*>(?P<body>.*?)</SVG_IMAGE>",
    re.DOTALL | re.IGNORECASE,
)

SVG_NS = "http://www.w3.org/2000/svg"

_ALLOWED_TAGS = {
    "svg", "g", "defs", "title", "desc", "style",
    "rect", "circle", "ellipse", "line", "polyline", "polygon", "path",
    "text", "tspan", "textPath",
    "linearGradient", "radialGradient", "stop",
    "clipPath", "mask", "pattern", "marker", "symbol", "use",
}
_ALLOWED_ATTR_PREFIXES = ("stroke", "fill", "font", "stop-", "clip", "marker")
_ALLOWED_ATTRS = {
    "id", "class", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry",
    "width", "height", "viewBox", "preserveAspectRatio", "transform", "d",
    "points", "opacity", "offset", "gradientUnits", "gradientTransform",
    "patternUnits", "text-anchor", "dominant-baseline", "dx", "dy", "dur",
    "letter-spacing", "style", "xmlns",
}


def image_to_data_url(file_obj, *, max_side: int = MAX_IMAGE_SIDE) -> str:
    """Yuklangan rasmni vision uchun kichraytirilgan JPEG data-URL'ga aylantiradi.

    Xato/juda katta fayl bo'lsa bo'sh string qaytadi (vision o'chadi, chat ishlayveradi).
    """
    try:
        from PIL import Image

        if hasattr(file_obj, "open") and getattr(file_obj, "closed", False):
            file_obj.open("rb")
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        raw = file_obj.read()
        if not raw or len(raw) > MAX_SOURCE_BYTES:
            return ""

        image = Image.open(io.BytesIO(raw))
        image = image.convert("RGB")
        image.thumbnail((max_side, max_side))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{encoded}"
    except Exception as exc:
        logger.warning("Rasmni vision uchun tayyorlash xatosi: %s", exc)
        return ""


def extract_svg_block(reply_text: str):
    """AI javobidan <SVG_IMAGE> blokini ajratadi.

    Natija: (tozalangan_javob, title yoki None, svg_matni yoki None).
    """
    if not reply_text or "<SVG_IMAGE" not in reply_text.upper():
        return reply_text, None, None
    match = SVG_IMAGE_PATTERN.search(reply_text)
    if not match:
        return reply_text, None, None
    title = (match.group("title") or "").strip() or "AzureLMS rasmi"
    body = (match.group("body") or "").strip()
    cleaned = SVG_IMAGE_PATTERN.sub("", reply_text).strip()
    if "<svg" not in body.lower():
        return cleaned or reply_text, None, None
    return cleaned, title, body


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _attr_allowed(name: str) -> bool:
    local = _local_name(name).lower()
    if local.startswith("on"):
        return False
    if local in {"href", "xlink:href"} or name.endswith("}href"):
        return False  # use/tashqi havolalar butunlay taqiqlanadi
    if local in _ALLOWED_ATTRS or local in {a.lower() for a in _ALLOWED_ATTRS}:
        return True
    return any(local.startswith(prefix) for prefix in _ALLOWED_ATTR_PREFIXES)


def sanitize_svg(svg_text: str) -> str:
    """AI yozgan SVG'ni qat'iy allowlist bilan zararsizlantiradi.

    Yaroqsiz/parslanmaydigan SVG uchun bo'sh string qaytadi.
    """
    try:
        cleaned = re.sub(r"<\?xml[^>]*\?>", "", svg_text).strip()
        cleaned = re.sub(r"<!DOCTYPE[^>]*>", "", cleaned, flags=re.IGNORECASE).strip()
        root = ElementTree.fromstring(cleaned)
    except ElementTree.ParseError as exc:
        logger.warning("SVG parse xatosi: %s", exc)
        return ""

    if _local_name(root.tag).lower() != "svg":
        return ""

    def scrub(element):
        for child in list(element):
            name = _local_name(child.tag).lower()
            if name not in {t.lower() for t in _ALLOWED_TAGS}:
                element.remove(child)
                continue
            scrub(child)
        for attr in list(element.attrib):
            if not _attr_allowed(attr):
                del element.attrib[attr]
            else:
                value = element.attrib[attr].strip()
                if "javascript:" in value.lower() or "url(" in value.lower() and "http" in value.lower():
                    del element.attrib[attr]

        if _local_name(element.tag).lower() == "style" and element.text:
            # style ichida import/tashqi url taqiqlanadi
            if "@import" in element.text.lower() or "url(" in element.text.lower():
                element.text = ""

    scrub(root)

    root.attrib["xmlns"] = SVG_NS
    ElementTree.register_namespace("", SVG_NS)
    serialized = ElementTree.tostring(root, encoding="unicode")
    return serialized
