"""Shablonlar uchun gigiyena testlari.

`{# ... #}` Django'da **faqat bitta qatorda** ishlaydi. Ko'p qatorli variant
izoh sifatida qayta ishlanmaydi — u sahifada oddiy matn bo'lib chiqadi. Bu
2026-08-19 da messenger kompozitorida sodir bo'ldi: izoh matni qatorda 200px
joy egallab, model/skill chiplarini 18px ga siqib qo'ydi va butun asboblar
qatorini 166px balandlikka cho'zdi.

Xatoni topish qiyin, chunki u sintaksis xatosi emas: Django jim o'tkazib
yuboradi, test yiqilmaydi va faqat sahifaga qarab turgan odam sezadi.
Ko'p qatorli izoh uchun `{% comment %}` ishlatiladi.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

TEMPLATES_DIR = Path(settings.BASE_DIR) / "templates"


class TemplateCommentSyntaxTests(SimpleTestCase):
    def test_no_multiline_hash_comments(self):
        offenders = []

        for path in sorted(TEMPLATES_DIR.rglob("*.html")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                opens = line.count("{#")
                closes = line.count("#}")
                if opens > closes:
                    relative = path.relative_to(TEMPLATES_DIR)
                    offenders.append(f"{relative}:{number}: {line.strip()[:70]}")

        self.assertEqual(
            offenders, [],
            "`{# #}` bitta qatorda yopilmagan — Django uni izoh deb qabul qilmaydi "
            "va matn sahifada ko'rinadi. Ko'p qatorli izoh uchun `{% comment %}` "
            "ishlating:\n" + "\n".join(offenders),
        )

    def test_the_check_actually_reads_templates(self):
        """Ro'yxat bo'sh bo'lsa yuqoridagi test hech nima tekshirmaydi."""
        self.assertGreater(len(list(TEMPLATES_DIR.rglob("*.html"))), 20)


#: `class="..."` ichidagi Django tagi/o'zgaruvchisi klass nomi emas.
#: Masalan `class="brand-field--check{% if x %} is-on{% endif %}"` da
#: `brand-field--check{%` degan "klass" paydo bo'ladi — shuning uchun tag avval
#: olib tashlanadi.
DJANGO_TAG = re.compile(r"\{[%{].*?[%}]\}", re.S)


class BrandControlCssClassTests(SimpleTestCase):
    """Backoffice shablonlarida aniqlanmagan `brand-*` klass qolmasligi kerak.

    Bu nuqson turi loyihada allaqachon uchragan: 2026-09-05 UX auditida
    `brand-logo-image--large` shablonda ishlatilib, hech qayerda aniqlanmagan
    edi va yuklangan logo ko'rik panelini yorib yuborgan. Xatoning yomon
    tomoni — u **jim**: sahifa ochiladi, test yashil turadi, faqat ko'rinish
    buziladi. 2026-09-11 da T0 sahifasida aynan shu takrorlandi
    (`brand-note`), shu sabab tekshiruv avtomatlashtirildi.

    Qamrov ataylab `brand-*` bilan cheklangan: `cc-*` klasslari boshqa faylda
    (`control-center.css`), Bootstrap va `bi-*` esa umuman boshqa paketda.
    Tekshirilmaydigan prefiksni qo'shib qo'yish testni yolg'on qizil qilardi.
    """

    CSS_PATH = Path(settings.BASE_DIR) / "static" / "css" / "brand-control.css"
    PREFIX = "brand-"

    def _templates(self):
        root = Path(settings.BASE_DIR) / "templates" / "backoffice"
        return sorted(root.glob("*.html"))

    def _used_classes(self, html):
        names = set()
        for chunk in re.findall(r'class="([^"]*)"', html):
            for name in DJANGO_TAG.sub(" ", chunk).split():
                if name.startswith(self.PREFIX):
                    names.add(name)
        return names

    def test_every_brand_class_used_in_backoffice_templates_is_defined(self):
        css = self.CSS_PATH.read_text(encoding="utf-8")
        undefined = {}
        for template in self._templates():
            missing = sorted(
                name
                for name in self._used_classes(template.read_text(encoding="utf-8"))
                if f".{name}" not in css
            )
            if missing:
                undefined[template.name] = missing
        self.assertEqual(
            undefined,
            {},
            "shablonda aniqlanmagan CSS klass bor — yuklanganda jim buziladi",
        )

    def test_django_tags_are_not_mistaken_for_class_names(self):
        """Nazorat: tag olib tashlanmasa test yolg'on qizil bo'lardi."""
        html = '<div class="brand-field{% if x %} brand-field--check{% endif %}">'
        self.assertEqual(
            self._used_classes(html), {"brand-field", "brand-field--check"}
        )

    def test_the_check_actually_reads_the_stylesheet(self):
        """Nazorat: tekshiruv haqiqatan CSS o'qiydimi.

        Aks holda fayl nomi o'zgarsa yoki yo'l buzilsa test "hammasi joyida"
        deb ko'rsatib turardi.
        """
        self.assertTrue(self.CSS_PATH.exists(), self.CSS_PATH)
        css = self.CSS_PATH.read_text(encoding="utf-8")
        self.assertIn(".brand-panel", css)
        self.assertGreater(len(self._templates()), 3)
