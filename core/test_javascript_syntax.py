"""Buzilgan JavaScript fayl testlardan o'tib ketmasin.

Bu test aynan bir hodisadan keyin yozildi: `messenger-chat.js` ichida
apostrof noto'g'ri qochirilgan edi va fayl butunlay ishlamay qoldi —
chat yuborish tugmasi ham, profil paneli ham. Django test suite'i esa
**to'liq yashil** edi, chunki u JavaScriptni umuman o'qimaydi.

Ya'ni bitta belgi butun messenger'ni o'ldirib, hech qanday signal
bermasdan merge bo'lishi mumkin edi.

`node` bo'lmasa test o'tkazib yuboriladi — u holda bu yerda soxta
ishonch yaratmaslik uchun aniq skip yoziladi.
"""

import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class EveryScriptParsesTests(SimpleTestCase):
    def setUp(self):
        self.node = shutil.which("node")
        if not self.node:
            self.skipTest("node topilmadi — JS sintaksisi tekshirilmadi")

    def test_every_static_javascript_file_parses(self):
        root = Path(settings.BASE_DIR) / "static" / "js"
        files = sorted(root.rglob("*.js"))
        self.assertTrue(files, "static/js bo'sh — tekshiruv ma'nosiz")

        broken = []
        for path in files:
            result = subprocess.run(
                [self.node, "--check", str(path)],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                first_line = (result.stderr or "").strip().splitlines()
                broken.append(f"{path.name}: {first_line[-1] if first_line else 'xato'}")

        self.assertEqual(broken, [], "Sintaksis xatosi bor JS fayllar: " + "; ".join(broken))
