import re
from pathlib import Path

from django.template import engines
from django.test import SimpleTestCase


TEMPLATES_ROOT = Path(__file__).resolve().parent.parent / "templates"

# {# ... #} — birinchi yopilishgacha, qator oshib ketishi mumkin.
COMMENT_PATTERN = re.compile(r"\{#.*?#\}", re.DOTALL)


class TemplateCommentHygieneTests(SimpleTestCase):
    """Django'ning `{# #}` izohi FAQAT bir qatorli.

    Ko'p qatorli yozilsa Django uni izoh deb hisoblamaydi va matn sahifada
    ko'rinib qoladi. Standalone shablonda bu foydalanuvchiga chiqadi;
    `{% extends %}` qiluvchi shablonda jim yo'qoladi, ya'ni xato sezilmay
    turadi. Ko'p qatorli izoh uchun `{% comment %}` ishlatiladi.
    """

    def test_no_multiline_hash_comments_in_templates(self):
        offenders = []
        for template_path in sorted(TEMPLATES_ROOT.rglob("*.html")):
            source = template_path.read_text(encoding="utf-8")
            for match in COMMENT_PATTERN.findall(source):
                if "\n" in match:
                    relative = template_path.relative_to(TEMPLATES_ROOT)
                    offenders.append(f"{relative}: {match.splitlines()[0][:60]}…")
        self.assertEqual(
            offenders,
            [],
            "Ko'p qatorli {# #} izoh topildi — {% comment %} ga o'tkazing:\n"
            + "\n".join(offenders),
        )


class ExamShellRendersCleanlyTests(SimpleTestCase):
    """ExamShell standalone hujjat — chiqishi doctype bilan boshlanishi va
    izoh matnini o'z ichiga olmasligi kerak."""

    def test_exam_detail_renders_without_literal_comment_markup(self):
        source = (TEMPLATES_ROOT / "courses" / "exam_detail.html").read_text(encoding="utf-8")
        rendered = engines["django"].from_string(source).render({})
        self.assertNotIn("{#", rendered)
        self.assertTrue(
            rendered.lstrip().lower().startswith("<!doctype html>"),
            "Doctype birinchi bo'lmasa brauzer quirks rejimiga tushadi.",
        )
