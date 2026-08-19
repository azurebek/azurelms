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
