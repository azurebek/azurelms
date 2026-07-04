"""AI hujjat qatlami: PDF o'qish (pypdf) va PDF yaratish (fpdf2).

E2B kabi tashqi sandbox KERAK EMAS: o'qish — oddiy matn ekstraksiyasi,
yozish — AI markdown-subset yozadi, PDF'ni o'z serverimiz fpdf2 bilan
deterministik yasaydi (AI kodi bajarilmaydi).
"""
from .reader import extract_pdf_text
from .writer import PDF_DOC_PATTERN, build_pdf, extract_pdf_doc_block

__all__ = ["extract_pdf_text", "build_pdf", "extract_pdf_doc_block", "PDF_DOC_PATTERN"]
