"""Upload validatsiyasi — nomga emas, baytlarga ishonadigan yagona gate (A0b).

Muammo: yuklangan faylning `name` va `content_type` maydonlarini brauzer
yuboradi, ya'ni ularni istalgan klient soxtalashtira oladi. Kengaytmani
tekshirish (`.jpg`) hujjatni himoya qilmaydi — `.jpg` deb nomlangan HTML yoki
skript bemalol o'tadi. Model field validatorlari esa `Model.objects.create()`
yo'lida umuman ishga tushmaydi, upload endpointlarimiz aynan shu yo'lni
ishlatadi.

Shuning uchun bu modul faylning **birinchi baytlarini** o'qib turini aniqlaydi
va faqat allowlistdagi turlarni o'tkazadi. Kengaytma ikkilamchi izchillik
tekshiruvi sifatida ishlatiladi: sniff qilingan tur bilan zid kelsa rad etiladi.

Profil qo'shish kerak bo'lsa `PROFILES` ga yangi tur qo'shiladi — bu yagona joy.
"""

import os

from django.core.exceptions import ValidationError

MB = 1024 * 1024

# Sniffer: (kind, offset, signature) — offset'dagi baytlar signature bilan mos kelsa.
_SIGNATURES = (
    ("png", 0, b"\x89PNG\r\n\x1a\n"),
    ("jpeg", 0, b"\xff\xd8\xff"),
    ("gif", 0, b"GIF87a"),
    ("gif", 0, b"GIF89a"),
    ("pdf", 0, b"%PDF-"),
    ("zip", 0, b"PK\x03\x04"),  # docx/xlsx/pptx ham shu konteynerda
    ("ogg", 0, b"OggS"),
    ("webm", 0, b"\x1a\x45\xdf\xa3"),  # Matroska/WebM
    ("mp3", 0, b"ID3"),
    ("mp3", 0, b"\xff\xfb"),
    ("mp3", 0, b"\xff\xf3"),
    ("mp3", 0, b"\xff\xf2"),
)

# RIFF konteyneri: 8-baytdan keyingi tag turni aniqlaydi (WEBP yoki WAVE).
_RIFF_TAGS = {b"WEBP": "webp", b"WAVE": "wav"}

# Matn fayllarida magic-byte yo'q, shuning uchun ular alohida yo'l bilan
# aniqlanadi: kengaytma matnli bo'lsin, kontent UTF-8 sifatida o'qilsin va
# `<` bilan boshlanmasin. Oxirgi shart HTML/SVG/XML'ni `.txt` niqobida
# o'tkazmaslik uchun — ular brauzerda bajarilib ketishi mumkin.
_TEXT_EXTENSIONS = {".txt", ".csv", ".md"}

_EXTENSIONS = {
    "text": _TEXT_EXTENSIONS,
    "png": {".png"},
    "jpeg": {".jpg", ".jpeg"},
    "webp": {".webp"},
    "gif": {".gif"},
    "pdf": {".pdf"},
    "zip": {".zip", ".docx", ".xlsx", ".pptx"},
    "ogg": {".ogg", ".oga"},
    "webm": {".webm"},
    "wav": {".wav"},
    "mp3": {".mp3"},
    "mp4": {".mp4", ".m4a"},
}

IMAGE_KINDS = ("png", "jpeg", "webp", "gif")
DOCUMENT_KINDS = IMAGE_KINDS + ("pdf", "zip", "text")
AUDIO_KINDS = ("webm", "ogg", "wav", "mp3", "mp4")

PROFILES = {
    # Avatar va to'lov cheki — faqat rasm.
    "image": {"kinds": IMAGE_KINDS, "max_bytes": 5 * MB, "label": "rasm"},
    # Chat biriktirmasi va vazifa fayli — rasm, PDF yoki office hujjati.
    "document": {"kinds": DOCUMENT_KINDS, "max_bytes": 12 * MB, "label": "hujjat yoki rasm"},
    # Imtihon speaking yozuvi — brauzer MediaRecorder chiqaradigan konteynerlar.
    "audio": {"kinds": AUDIO_KINDS, "max_bytes": 25 * MB, "label": "audio yozuv"},
}

_HUMAN_KINDS = {
    "png": "PNG", "jpeg": "JPEG", "webp": "WebP", "gif": "GIF",
    "pdf": "PDF", "zip": "ZIP/Office", "ogg": "OGG", "webm": "WebM",
    "wav": "WAV", "mp3": "MP3", "mp4": "MP4/M4A", "text": "matn (.txt/.csv/.md)",
}


def sniff_kind(upload):
    """Faylning boshidagi baytlar bo'yicha turini aniqlaydi; noma'lum bo'lsa `None`.

    O'qish pozitsiyasi doim boshiga qaytariladi, aks holda keyin saqlangan fayl
    boshidan kesilib qolardi.
    """
    try:
        upload.seek(0)
        head = upload.read(512)
    finally:
        try:
            upload.seek(0)
        except (AttributeError, ValueError):
            pass

    if not head:
        return None

    if head[:4] == b"RIFF" and len(head) >= 12:
        return _RIFF_TAGS.get(head[8:12])
    # ISO-BMFF konteyneri (mp4/m4a) — iOS Safari MediaRecorder shu formatda yozadi.
    if len(head) >= 8 and head[4:8] == b"ftyp":
        return "mp4"

    for kind, offset, signature in _SIGNATURES:
        if head[offset:offset + len(signature)] == signature:
            return kind

    if _looks_like_plain_text(head, getattr(upload, "name", "")):
        return "text"
    return None


def _looks_like_plain_text(head, name):
    """Matn faylimi? Faqat matnli kengaytma + UTF-8 + markup emas bo'lsa."""
    ext = os.path.splitext(name or "")[1].lower()
    if ext not in _TEXT_EXTENSIONS:
        return False
    if b"\x00" in head:
        return False
    try:
        # Oxirgi belgi ko'p baytli bo'lib yarim kesilgan bo'lishi mumkin —
        # shuning uchun xato faqat butun prefiks buzuq bo'lsa hisobga olinadi.
        decoded = head.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        if exc.start < len(head) - 4:
            return False
        decoded = head[: exc.start].decode("utf-8")
    return not decoded.lstrip("﻿ \t\r\n").startswith("<")


def validate_upload(upload, *, profile="document", field_label=""):
    """Yuklangan faylni profil bo'yicha tekshiradi; xato bo'lsa `ValidationError`.

    Tartib muhim: avval hajm (katta faylni o'qishdan oldin), keyin baytlar,
    oxirida kengaytma izchilligi.
    """
    spec = PROFILES[profile]
    prefix = f"{field_label}: " if field_label else ""

    size = getattr(upload, "size", 0) or 0
    if size <= 0:
        raise ValidationError(f"{prefix}Fayl bo'sh.")
    if size > spec["max_bytes"]:
        limit_mb = spec["max_bytes"] // MB
        raise ValidationError(f"{prefix}Fayl hajmi {limit_mb} MB dan oshmasligi kerak.")

    kind = sniff_kind(upload)
    if kind is None or kind not in spec["kinds"]:
        allowed = ", ".join(_HUMAN_KINDS[k] for k in spec["kinds"])
        raise ValidationError(
            f"{prefix}Bu fayl turi qabul qilinmaydi. Ruxsat etilgan {spec['label']} "
            f"formatlari: {allowed}."
        )

    # Kengaytma faqat ikkilamchi tekshiruv: mos kelmasa fayl chalg'ituvchi nomda
    # yuborilgan (masalan `.jpg` deb nomlangan PDF) — rad etamiz.
    ext = os.path.splitext(getattr(upload, "name", "") or "")[1].lower()
    if ext and ext not in _EXTENSIONS.get(kind, set()):
        raise ValidationError(
            f"{prefix}Fayl nomidagi kengaytma ({ext}) uning haqiqiy turiga "
            f"({_HUMAN_KINDS[kind]}) mos kelmadi."
        )
    return kind
