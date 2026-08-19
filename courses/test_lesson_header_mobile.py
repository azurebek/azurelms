"""Dars sarlavhasi tor ekranda sig'ishi kerak (A5).

360px da sarlavhaning o'ng guruhi `flex:0 0 auto` bo'lgani va ichida qat'iy
160px progress bar turgani uchun guruh 371px joy talab qilardi: "AI repetitor"
tugmasi ekrandan 11px chiqib ketar, chap guruh esa `min-width:0` bilan nolga
siqilib, kurs nomi **butunlay ko'rinmasdi**.

Yechim tor ekranda ortiqcha elementlarni olib tashlash. Ammo yorliqni yashirish
tugmani nomsiz qoldirmasligi kerak — shuning uchun `aria-label` majburiy.

Bu qoidalar shablon ichidagi `<style>` blokida yashaydi va ularni tasodifan
o'chirib yuborish oson; test shuni ushlaydi.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

TEMPLATE = Path(settings.BASE_DIR) / "templates" / "courses" / "lesson_detail.html"


class LessonHeaderNarrowScreenTests(SimpleTestCase):
    def setUp(self):
        self.markup = TEMPLATE.read_text(encoding="utf-8")

    def test_progress_bar_is_hidden_on_narrow_screens(self):
        self.assertIn("lhead-progress", self.markup, "progress bar klasssiz qoldi — qoida unga tegmaydi")

        rule = re.search(
            r"@media\s*\(\s*max-width:\s*(\d+)px\s*\)\s*\{[^}]*\.lhead-progress\s*\{[^}]*display:\s*none",
            self.markup,
        )
        self.assertIsNotNone(
            rule,
            "160px progress bar tor ekranda yashirilmasa, sarlavha 360px ga sig'maydi",
        )
        self.assertGreaterEqual(
            int(rule.group(1)), 400,
            "chegara juda past — 360px va 390px qurilmalar qoidadan tashqarida qoladi",
        )

    def test_ai_button_keeps_a_name_when_its_label_is_hidden(self):
        hides_label = re.search(
            r"@media\s*\(\s*max-width:\s*\d+px\s*\)\s*\{[^}]*\.lhead-ai-label\s*\{[^}]*display:\s*none",
            self.markup,
        )
        if not hides_label:
            self.skipTest("yorliq yashirilmayapti — nom talabi ham qo'llanmaydi")

        link = re.search(r'<a[^>]*class="[^"]*lhead-ai[^"]*"[^>]*>', self.markup)
        self.assertIsNotNone(link, "`lhead-ai` havolasi topilmadi")
        self.assertIn(
            "aria-label", link.group(0),
            "matn yashirilganda tugma nomsiz qoladi — skrin riderda 'link' bo'lib eshitiladi",
        )

    def test_course_title_can_still_shrink(self):
        """Chap guruh `min-width:0` bo'lmasa, uzun nom o'ng guruhni itarib yuboradi."""
        self.assertIn("min-width:0", self.markup)
        self.assertIn("text-overflow:ellipsis", self.markup)
