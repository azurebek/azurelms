"""AI javobidagi <PDF_DOC> blokidan haqiqiy PDF yasash (fpdf2).

AI faqat markdown-subset MATN yozadi (kod emas!): sarlavha (#, ##), ro'yxat
(- yoki 1.), jadval (| ustun | ustun |) va oddiy paragraflar. PDF'ni fpdf2
deterministik quradi — hech qanday AI kodi bajarilmaydi (e2b keraksiz).
Unicode: DejaVu shriftlari (turkcha ı/ğ/ş/ç va o'zbekcha to'liq qo'llanadi).
"""
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

PDF_DOC_PATTERN = re.compile(
    r"<PDF_DOC(?:\s+title=\"(?P<title>[^\"]{0,200})\")?\s*>(?P<body>.*?)</PDF_DOC>",
    re.DOTALL | re.IGNORECASE,
)

FONTS_DIR = Path(__file__).resolve().parent / "fonts"
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


def extract_pdf_doc_block(reply_text: str):
    """AI javobidan <PDF_DOC> blokini ajratadi.

    Natija: (tozalangan_javob_matni, title yoki None, body yoki None).
    Blok topilmasa matn o'zgarishsiz qaytadi.
    """
    if not reply_text or "<PDF_DOC" not in reply_text.upper():
        return reply_text, None, None
    match = PDF_DOC_PATTERN.search(reply_text)
    if not match:
        return reply_text, None, None
    title = (match.group("title") or "").strip() or "AzureLMS hujjati"
    body = (match.group("body") or "").strip()
    cleaned = PDF_DOC_PATTERN.sub("", reply_text).strip()
    if not body:
        return cleaned or reply_text, None, None
    return cleaned, title, body


def _strip_inline_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return text


def _parse_table_row(line: str):
    inner = line.strip().strip("|")
    return [_strip_inline_markdown(cell.strip()) for cell in inner.split("|")]


def build_pdf(*, title: str, body: str) -> bytes:
    """Markdown-subset matndan PDF baytlarini yasaydi."""
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_font("DejaVu", "", str(FONTS_DIR / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"))
    pdf.add_page()

    page_width = pdf.w - pdf.l_margin - pdf.r_margin

    # Sarlavha + brend chizig'i
    pdf.set_font("DejaVu", "B", 17)
    pdf.set_text_color(18, 87, 230)  # --azure
    pdf.multi_cell(page_width, 9, title)
    pdf.set_draw_color(18, 87, 230)
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, pdf.get_y() + 1.5, pdf.l_margin + page_width, pdf.get_y() + 1.5)
    pdf.ln(6)
    pdf.set_text_color(20, 22, 28)

    lines = body.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i].rstrip()
        stripped = raw.strip()

        if not stripped:
            pdf.ln(2.5)
            i += 1
            continue

        # Jadval bloki
        if _TABLE_ROW_RE.match(stripped):
            table_rows = []
            while i < len(lines) and _TABLE_ROW_RE.match(lines[i].strip()):
                if not _TABLE_SEP_RE.match(lines[i].strip()):
                    table_rows.append(_parse_table_row(lines[i]))
                i += 1
            if table_rows:
                pdf.set_font("DejaVu", "", 10.5)
                with pdf.table(
                    first_row_as_headings=True,
                    line_height=6.5,
                    padding=1.6,
                ) as table:
                    for r_index, row_cells in enumerate(table_rows):
                        row = table.row()
                        for cell in row_cells:
                            row.cell(cell)
                pdf.ln(3)
            continue

        # Sarlavhalar
        if stripped.startswith("### "):
            pdf.set_font("DejaVu", "B", 11.5)
            pdf.multi_cell(page_width, 6.5, _strip_inline_markdown(stripped[4:]))
            pdf.ln(1)
        elif stripped.startswith("## "):
            pdf.set_font("DejaVu", "B", 13)
            pdf.multi_cell(page_width, 7, _strip_inline_markdown(stripped[3:]))
            pdf.ln(1.5)
        elif stripped.startswith("# "):
            pdf.set_font("DejaVu", "B", 15)
            pdf.multi_cell(page_width, 8, _strip_inline_markdown(stripped[2:]))
            pdf.ln(2)
        # Ro'yxatlar
        elif stripped.startswith(("- ", "* ")):
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(page_width - 6, 6.2, "•  " + _strip_inline_markdown(stripped[2:]), new_x="LMARGIN")
        elif re.match(r"^\d{1,2}[.)]\s+", stripped):
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(page_width - 6, 6.2, _strip_inline_markdown(stripped), new_x="LMARGIN")
        # Oddiy paragraf
        else:
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(page_width, 6.2, _strip_inline_markdown(stripped))
        i += 1

    # Footer brend
    pdf.set_y(-14)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(150, 152, 160)
    pdf.cell(page_width, 5, "AzureLMS · Azure AI tomonidan tayyorlandi", align="R")

    return bytes(pdf.output())
