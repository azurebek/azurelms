"""Imtihon landscape telefonda ishlashi kerak (A5).

568x320 da yozish bo'limi yaroqsiz edi. Sabab kenglik emas, **balandlik**:
mavjud `@media (max-width:900px)` qoidasi promptga `40vh` beradi — portretda
bu 337px, landscape'da esa 128px, ya'ni butun tanaga qolgan 146px dan
tahrirlash qismiga 18px qoladi. Javob maydoni 38px ga siqilar, so'z hisoblagichi
va "min 40 · max 120" talabi esa ekran ostida qolardi.

Eng yomoni: `.exam{overflow:hidden}` bo'lgani uchun ularga **yetib bo'lmasdi** —
scroll yo'q edi. O'quvchi landscape'da necha so'z yozganini ko'rmasdi.

Bu turdagi nuqson jim: sahifa "ishlaydi", test yiqilmaydi, faqat past ekranda
qaragan odam ko'radi.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

CSS = Path(settings.BASE_DIR) / "static" / "css" / "exam-shell.css"


class ExamShortViewportTests(SimpleTestCase):
    def setUp(self):
        self.css = CSS.read_text(encoding="utf-8")
        block = re.search(
            r"@media\s*\(\s*max-height:\s*(\d+)px\s*\)\s*\{(.*?)\n\}",
            self.css,
            re.S,
        )
        self.block = block

    def test_a_short_viewport_rule_exists(self):
        self.assertIsNotNone(
            self.block,
            "balandlikka qarab qoida yo'q — landscape telefonda yozish bo'limi "
            "18px ga siqiladi va uni faqat ekranga qarab bilish mumkin",
        )
        self.assertGreaterEqual(
            int(self.block.group(1)), 360,
            "chegara juda past — 360px balandlikdagi landscape qoidadan tashqarida qoladi",
        )

    def test_exam_body_can_scroll_on_short_viewports(self):
        """`.exam` klip qiladi; tana siljimasa kontentga yetib bo'lmaydi."""
        self.assertIsNotNone(self.block, "qoida yo'q")
        body_rule = re.search(r"\.exam-body\s*\{[^}]*overflow-y:\s*auto", self.block.group(2))
        self.assertIsNotNone(
            body_rule,
            "past ekranda `.exam-body` siljimasa, so'z hisoblagichi va talab "
            "ekran ostida qolib, unga yetib bo'lmaydi",
        )

    def test_essay_field_keeps_a_usable_height(self):
        self.assertIsNotNone(self.block, "qoida yo'q")
        essay = re.search(r"\.x-essay\s*\{[^}]*min-height:\s*(\d+)px", self.block.group(2))
        self.assertIsNotNone(essay, "javob maydoniga minimal balandlik berilmagan")
        self.assertGreaterEqual(
            int(essay.group(1)), 100,
            "40-120 so'zlik insho uchun 100px dan past maydon yaroqsiz",
        )

    def test_the_clipping_shell_is_still_the_reason_this_rule_is_needed(self):
        """Agar `.exam` klip qilmasa, qoida keraksiz bo'lib qoladi — buni bilib turaylik."""
        self.assertRegex(
            self.css, r"\.exam\{[^}]*overflow:\s*hidden",
            "`.exam` endi klip qilmasa, yuqoridagi qoidalar qayta ko'rib chiqilsin",
        )
