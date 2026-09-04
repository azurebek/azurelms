"""Dars sahifasining pastki paneli suzuvchi qush ostida qolmaydi.

Owner xabar qildi: dars sahifasida «Bajarildi» belgisi o'ng pastdagi AzureAI
qushi ostida qolib ketgan. Brauzerda o'lchandi va tasdiqlandi — 1280px
kenglikda belgi 1154–1264px oralig'ida, qush esa 1190–1256px, ya'ni ustma-ust
tushgan.

Sabab: qush `position: fixed; right: 24px` bilan turadi va hech qanday
joyni band qilmaydi, pastki panel esa o'ng chetgacha cho'ziladi.

Tuzatish: qushning izi `--azai-safe-right` o'zgaruvchisida e'lon qilinadi va
pastki panel shuni o'ng bo'shliq sifatida oladi. Bu test aynan shu ikki
uchni ushlab turadi: o'zgaruvchi e'lon qilingan bo'lsin va panel undan
foydalansin. Piksel o'lchovi brauzerda qilinadi, testda emas — bu yerdagi
maqsad tuzatish jimgina yo'qolib qolmasligi.
"""

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class LessonFooterClearsTheFloatingWidgetTests(SimpleTestCase):
    def _read(self, relative):
        return (Path(settings.BASE_DIR) / relative).read_text(encoding="utf-8")

    def test_the_widget_stylesheet_declares_its_footprint(self):
        css = self._read("static/css/ai-widget.css")

        self.assertIn("--azai-safe-right", css)

    def test_the_lesson_footer_reserves_that_footprint(self):
        template = self._read("templates/courses/lesson_detail.html")

        self.assertIn("padding-right:var(--azai-safe-right", template)

    def test_the_footer_wraps_so_narrow_screens_stack_instead_of_colliding(self):
        """375px da ikkita tugma yonma-yon sig'maydi — ular ustma-ust tushadi."""
        template = self._read("templates/courses/lesson_detail.html")
        after_reservation = template.split("padding-right:var(--azai-safe-right")[1]
        footer_style = after_reservation.split('">')[0]

        self.assertIn("flex-wrap:wrap", footer_style)
