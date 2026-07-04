"""Yuklangan PDF'dan matn ajratish — AI kontekstiga berish uchun."""
import logging

logger = logging.getLogger(__name__)

MAX_PAGES = 40
MAX_CHARS = 15_000


def extract_pdf_text(file_obj, *, max_chars: int = MAX_CHARS, max_pages: int = MAX_PAGES) -> str:
    """PDF fayldan matnni xato-chidamli ajratadi.

    file_obj — Django FieldFile yoki har qanday binary file-like obyekt.
    Natija bo'sh string bo'lishi mumkin (skan-rasm PDF, buzuq fayl) — chaqiruvchi
    buni foydalanuvchiga tushuntirishi kerak.
    """
    try:
        from pypdf import PdfReader

        needs_close = False
        if hasattr(file_obj, "open") and getattr(file_obj, "closed", False):
            file_obj.open("rb")
            needs_close = True
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        reader = PdfReader(file_obj)
        parts = []
        total = 0
        for index, page in enumerate(reader.pages):
            if index >= max_pages:
                parts.append(f"\n[... hujjat davomi qisqartirildi: jami {len(reader.pages)} sahifa ...]")
                break
            try:
                text = (page.extract_text() or "").strip()
            except Exception:  # bitta buzuq sahifa butun hujjatni yiqitmasin
                continue
            if not text:
                continue
            parts.append(text)
            total += len(text)
            if total >= max_chars:
                parts.append("\n[... matn belgilangan limitda qisqartirildi ...]")
                break

        if needs_close:
            file_obj.close()

        combined = "\n\n".join(parts).strip()
        return combined[:max_chars]
    except Exception as exc:
        logger.warning("PDF matn ajratish xatosi: %s", exc)
        return ""
