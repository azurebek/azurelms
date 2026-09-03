"""Landing sahifada ikkita vertikal scrollbar chiqmaydi.

Owner sahifani ochib "o'ng tarafda nega ikkita yonma-yon scroller bor" dedi.

Sabab CSS spetsifikatsiyasidagi qoida: agar `overflow` ning bir o'qi
`visible` bo'lmasa, ikkinchi o'qdagi `visible` **avtomatik `auto` ga
aylanadi**. `templates/index.html` dagi asosiy wrapper faqat `overflow-x:
hidden` deb yozgan edi, brauzer esa unga `overflow-y: auto` berdi — ya'ni
wrapper alohida scroll konteyneriga aylandi va o'z scrollbarini chizdi.

Brauzerda o'lchangan holat (tuzatishdan oldin):

    overflow-x: hidden · overflow-y: auto (avtomatik)
    scrollHeight 5914 > clientHeight 5898
    scrollbar kengligi: 15px

Ya'ni sahifaning o'z scrollbari yonida yana bittasi turardi.

`overflow-x: clip` gorizontal chiqishni xuddi shunday yashiradi, lekin
scroll konteyneri **yaratmaydi** — o'lchov buni tasdiqladi: `overflow-y`
yana `visible` bo'ldi va 15px scrollbar yo'qoldi.

`hidden` zaxira sifatida oldinda qoladi: `clip` ni tushunmaydigan eski
brauzer (Safari < 16) uni saqlaydi va eski xulq bilan ishlaydi, yangi
brauzer esa keyingi e'lonni oladi. Shuning uchun test **ikkalasini ham**
talab qiladi va tartibni ham tekshiradi.
"""

import re

from django.test import TestCase
from django.urls import reverse


class LandingScrollContainerTests(TestCase):
    def _wrapper_style(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        match = re.search(
            r'<div style="([^"]*min-height:100vh[^"]*overflow-x[^"]*)"', html
        )
        self.assertIsNotNone(match, "landing wrapper topilmadi")
        return match.group(1)

    def test_the_wrapper_does_not_become_a_scroll_container(self):
        style = self._wrapper_style()

        self.assertIn("overflow-x:clip", style.replace(" ", ""))

    def test_the_old_value_stays_as_a_fallback_and_comes_first(self):
        """Eski Safari `clip` ni tushunmaydi — u holda `hidden` amal qiladi."""
        style = self._wrapper_style().replace(" ", "")

        self.assertIn("overflow-x:hidden", style)
        self.assertLess(
            style.index("overflow-x:hidden"),
            style.index("overflow-x:clip"),
            "zaxira qiymat keyin turса, u yangi brauzerda g'olib bo'lib qoladi",
        )

    def test_no_overflow_y_is_declared_on_the_wrapper(self):
        """`overflow-y` ni qo'lda yozish muammoni qaytaradi.

        `overflow-y: auto` yozilsa, wrapper yana scroll konteyneri bo'ladi va
        `clip` ning ma'nosi qolmaydi.
        """
        self.assertNotIn("overflow-y", self._wrapper_style())
