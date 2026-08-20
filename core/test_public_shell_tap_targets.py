"""Public shelldagi havolalar barmoq bilan bosiladigan bo'lishi kerak (A5).

Checkout sahifasini 320/360/390px da o'lchaganda kontentning o'zi toza chiqdi,
ammo har bir public sahifaga tegadigan umumiy shellda kichik nishonlar topildi:
footerdagi 14 havola `146x17px`, headerdagi "Chiqish" `58x19px`.

WCAG 2.5.8 (AA) kamida `24x24` CSS px talab qiladi; loyihaning o'z konvensiyasi
esa boshqa joylarda 36px. 17px balandlikdagi havolani telefonda aniq bosish
qiyin va xato bosish qo'shni havolani ochadi.

Bu qoidalarni tasodifan yo'qotish oson — matn hajmini o'zgartirish yetadi.
Shuning uchun test balandlikni CSS'da ochiq talab qiladi.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

CSS = Path(settings.BASE_DIR) / "static" / "css" / "public-shell.css"

#: WCAG 2.5.8 (AA) minimal nishon o'lchami.
MIN_TAP_TARGET_PX = 24


class PublicShellTapTargetTests(SimpleTestCase):
    def setUp(self):
        self.css = CSS.read_text(encoding="utf-8")

    def _min_height_for(self, selector):
        """Selektor blokidagi `min-height` qiymati (px)."""
        pattern = re.escape(selector) + r"\s*\{([^}]*)\}"
        match = re.search(pattern, self.css)
        if not match:
            return None
        height = re.search(r"min-height:\s*(\d+)px", match.group(1))
        return int(height.group(1)) if height else None

    def test_footer_links_are_tappable(self):
        value = self._min_height_for(".pub-foot-links a")
        self.assertIsNotNone(
            value,
            "footer havolalari faqat matn balandligini oladi — telefonda 17px bo'lib qoladi",
        )
        self.assertGreaterEqual(value, MIN_TAP_TARGET_PX)

    def test_footer_bottom_links_are_tappable(self):
        for selector in (".pub-foot-bottom a", ".pub-foot-social a"):
            value = self._min_height_for(selector)
            self.assertIsNotNone(value, f"{selector} uchun minimal balandlik yo'q")
            self.assertGreaterEqual(value, MIN_TAP_TARGET_PX, selector)

    def test_header_auth_control_is_tappable(self):
        value = self._min_height_for(".pub-login")
        self.assertIsNotNone(value, "header'dagi Kirish/Chiqish 19px bo'lib qoladi")
        self.assertGreaterEqual(
            value, MIN_TAP_TARGET_PX,
            "bu asosiy amal — loyiha konvensiyasi bo'yicha 36px maqsad qilinadi",
        )

    def test_tappable_links_actually_render_as_boxes(self):
        """Oddiy `inline` havolaga balandlik ta'sir qilmaydi — quti bo'lishi shart."""
        for selector in (".pub-foot-links a", ".pub-foot-bottom a", ".pub-login"):
            block = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", self.css)
            self.assertIsNotNone(block, selector)
            self.assertRegex(
                block.group(1), r"display:\s*(inline-)?flex",
                f"{selector}: `min-height` inline elementda e'tiborsiz qoladi",
            )
