"""Xavfsiz public hujjat HTML'i va uning server-side mundarijasi.

Owner kiritgan rich text avval umumiy public sanitizerdan o'tadi. Faqat shundan
keyin ``h2`` sarlavhalariga ilova boshqaradigan, takrorlanmaydigan fragment ID
qo'shiladi. Shu tartib raw ``id``/``name`` clobbering va executable markupning
mundarija orqali qayta kirishiga yo'l qo'ymaydi.
"""

import re
from dataclasses import dataclass

from django.utils.safestring import SafeString, mark_safe
from django.utils.text import slugify

from core.rich_content_policy import public_plain_text, sanitize_public_editorial

_H2_RE = re.compile(r"<h2>(?P<body>.*?)</h2>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class PublicDocumentHeading:
    anchor: str
    label: str


@dataclass(frozen=True)
class PublicDocument:
    html: SafeString
    toc: tuple[PublicDocumentHeading, ...]


def project_public_document(value, *, prefix="section"):
    """Sanitize ``value`` and project safe ``h2`` anchors plus a TOC.

    Empty headings lose their heading wrapper and are omitted from the TOC: the
    presentation layer must not invent owner-visible copy or expose an empty
    accessibility heading.
    """

    sanitized = str(sanitize_public_editorial(value))
    safe_prefix = slugify(str(prefix))[:32] or "section"
    headings = []
    used = set()

    def add_anchor(match):
        body = match.group("body")
        label = public_plain_text(body, max_chars=120)
        if not label:
            return body

        stem = slugify(label)[:64] or f"bolim-{len(headings) + 1}"
        base = f"{safe_prefix}-{stem}"
        anchor = base
        suffix = 2
        while anchor in used:
            anchor = f"{base}-{suffix}"
            suffix += 1
        used.add(anchor)
        headings.append(PublicDocumentHeading(anchor=anchor, label=label))
        return f'<h2 id="{anchor}">{body}</h2>'

    projected = _H2_RE.sub(add_anchor, sanitized)
    # ``projected`` faqat sanitizer chiqishi va yuqorida [a-z0-9-]ga
    # normallashgan IDlardan tuzilgan; SafeString aynan shu boundaryda beriladi.
    return PublicDocument(html=mark_safe(projected), toc=tuple(headings))
