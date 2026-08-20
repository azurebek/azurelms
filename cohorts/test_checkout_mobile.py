"""Checkout telefonda ham to'liq ko'rinishi kerak (A5).

360px da to'lov sahifasi ikki ustunli grid bo'lib qolardi va hech qanday media
qoidasi yo'q edi. Grid bandining sukutdagi `min-width:auto` si birinchi ustunga
kontent talab qilgan 265px ni berardi, xulosa paneliga esa **31px** qolardi —
uning ichidagi "Jami" summasi o'sha qutidan tashqariga to'kilib, ekrandan 66px
chiqib ketardi.

To'lov sahifasida umumiy summani ko'rmaslik qabul qilib bo'lmaydigan holat:
foydalanuvchi qancha to'layotganini bilmay chek yuklaydi.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

TEMPLATE = Path(settings.BASE_DIR) / "templates" / "cohorts" / "checkout.html"


class CheckoutNarrowScreenTests(SimpleTestCase):
    def setUp(self):
        self.markup = TEMPLATE.read_text(encoding="utf-8")
        self.media = re.search(
            r"@media\s*\(\s*max-width:\s*(\d+)px\s*\)\s*\{(.*?)\n\s*\}",
            self.markup,
            re.S,
        )

    def test_layout_collapses_to_one_column_on_phones(self):
        self.assertIsNotNone(
            self.media,
            "media qoidasi yo'q — checkout telefonda ikki ustunda qolib, "
            "xulosa paneli 31px ga siqiladi",
        )
        self.assertGreaterEqual(int(self.media.group(1)), 600, "chegara juda past")
        self.assertRegex(
            self.media.group(2), r"\.co-grid\s*\{[^}]*grid-template-columns:\s*1fr",
            "telefonda bitta ustun bo'lishi shart",
        )

    def test_grid_children_may_shrink(self):
        """`min-width:auto` aynan shu nuqsonni keltirib chiqargan edi."""
        self.assertRegex(
            self.markup, r"\.co-grid\s*>\s*\*\s*\{[^}]*min-width:\s*0",
            "grid bandlari qisqara olmasa, kontent talab qilgan kenglik ustunni itaradi",
        )

    def test_summary_stops_being_sticky_when_stacked(self):
        """Bir ustunda `sticky` panel oqimda o'z joyida turishi kerak."""
        self.assertIsNotNone(self.media, "media qoidasi yo'q")
        self.assertRegex(
            self.media.group(2), r"\.co-summary\s*\{[^}]*position:\s*static",
            "taxlangan holatda sticky panel kontentni bosib turadi",
        )
