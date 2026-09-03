"""Gradient cover sarlavhasi 1200px canvas'dan chiqib ketmaydi.

**Avvalgi da'vom noto'g'ri edi va shu yerda tuzatiladi.** 2026-09-03 da men
namuna kontent seeder'ini yozayotib, katalogdagi kurs nomi cover'dan chiqib
ketgan deb yozgandim. Keyin brauzerda o'lchab ko'rilganda ma'lum bo'ldiki,
u **chiqmagan**: eng uzun satr eski algoritmda ham `1049px` bo'lib, `1200px`
canvas ichida sig'adi. O'sha xulosa skrinshotning eskirgan kadriga
asoslangan ekan.

Haqiqiy, o'lchangan muammo torroq: `_split_title` faqat **bo'sh joy**
bo'yicha bo'ladi, ya'ni bitta uzun so'z bitta satr bo'lib qolaveradi.
`_title_block` esa shriftni zinapoya bilan tanlab `78` da to'xtardi va
zinapoya satr **uzunligiga** qarardi, natijaviy **kenglikka** emas. 76
belgili bo'linmas so'z shu sababdan `3049px` chiqadi — canvas'dan ikki
yarim barobar keng, ya'ni matn qirqiladi va ikkala chetdan oqib ketadi.

Bitta nozik joy hisobga olindi: cover data-URI SVG bo'lib `<img>` orqali
yuklanadi, ya'ni `Manrope` **umuman yuklanmaydi** va brauzer o'z sans
fallback'ini qo'yadi. Shuning uchun kenglik taxminiga tayanib bo'lmaydi va
oxirgi kafolat `textLength` bilan qo'yiladi — u shrift metrikasiga bog'liq
emas.

Testlar o'lchamning o'zini emas, **kuzatiladigan xulqni** tekshiradi: qisqa
sarlavha ilgarigidek chiqadi (regressiya yo'q), uzun sarlavha kichrayadi,
bo'linmas so'z esa qattiq cheklanadi.
"""

import re

from django.test import TestCase

from courses.cover_art import (
    TITLE_MAX_WIDTH, TITLE_MIN_FONT_SIZE, _estimate_line_width, _split_title,
    build_cover_svg,
)


def font_size_of(svg):
    match = re.search(r'font-size="(\d+)"', svg)
    assert match, "SVG da font-size topilmadi"
    return int(match.group(1))


class CoverTitleFitTests(TestCase):
    SHORT = "Turk tili A1"
    LONG = "Turk tili B1 — sertifikat imtihoniga tayyorgarlik"
    BRUTAL = "Muvaffaqiyatsizlashtirilganlardanmisiz degan uzun sarlavha"
    #: Bo'sh joysiz — `_split_title` uni bo'la olmaydi, ya'ni shriftni
    #: kichraytirish ham yetmaydi va `textLength` yagona kafolat bo'lib qoladi.
    UNBREAKABLE = "Muvaffaqiyatsizlashtirilganlardanmisiz" * 2

    def test_a_short_title_keeps_the_original_size(self):
        """Tuzatish mavjud ko'rinishni o'zgartirmasligi kerak."""
        self.assertEqual(font_size_of(build_cover_svg(self.SHORT)), 112)

    def test_a_long_title_shrinks_below_the_old_floor(self):
        """Zinapoya kenglikka qaramasdi; endi eng uzun satrga moslanadi.

        Bu satr eski algoritmda ham canvas'ga sig'ardi (o'lchangan `1049px`),
        ya'ni bu tuzatish **toshishni** emas, chetgacha borib qolgan
        zaxirani kengaytiradi.
        """
        self.assertLess(font_size_of(build_cover_svg(self.LONG)), 78)

    def test_an_unbreakable_word_is_clamped_by_textlength(self):
        """Shriftni kichraytirish yetmaydigan yagona holat.

        `_split_title` faqat bo'sh joy bo'yicha bo'ladi, ya'ni bitta uzun
        so'z bitta satr bo'lib qolaveradi. Shrift poliga tushgach kenglikni
        faqat `textLength` kafolatlaydi — u shrift metrikasiga bog'liq emas,
        shuning uchun yuklanmagan `Manrope` muammosidan ham xoli.
        """
        svg = build_cover_svg(self.UNBREAKABLE)

        self.assertIn(f'textLength="{TITLE_MAX_WIDTH}"', svg)
        self.assertIn('lengthAdjust="spacingAndGlyphs"', svg)

    def test_no_line_is_estimated_wider_than_the_canvas(self):
        for title in (self.SHORT, self.LONG, self.BRUTAL, self.UNBREAKABLE):
            with self.subTest(title=title):
                svg = build_cover_svg(title)
                size = font_size_of(svg)
                for line in _split_title(title):
                    width = _estimate_line_width(line, size)
                    if width > TITLE_MAX_WIDTH:
                        # Poldagi shrift yetmasa, kenglik `textLength` bilan
                        # kafolatlanadi — bu shrift metrikasiga bog'liq emas.
                        self.assertIn("textLength", svg, title)
                    else:
                        self.assertLessEqual(width, TITLE_MAX_WIDTH, line)

    def test_the_font_never_drops_below_the_readable_floor(self):
        self.assertGreaterEqual(
            font_size_of(build_cover_svg(self.BRUTAL)), TITLE_MIN_FONT_SIZE
        )

    def test_a_short_title_is_not_stretched(self):
        """`textLength` qisqa sarlavhaga qo'yilsa, harflar cho'zilib ketardi."""
        self.assertNotIn("textLength", build_cover_svg(self.SHORT))

    def test_an_empty_title_still_renders(self):
        svg = build_cover_svg("")

        self.assertIn("AzureLMS", svg)
        self.assertIn("<text", svg)

    def test_the_title_is_escaped(self):
        svg = build_cover_svg("A & B <script>")

        self.assertIn("&amp;", svg)
        self.assertNotIn("<script>", svg)
