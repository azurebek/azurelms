"""Messenger AI tanlagichi (uslub/model/skill) uchun kontrakt testlari.

Bu testlar mavjud bo'lishining sababi: tanlagich sahifada ochilardi, bosilganda
so'rov ketardi va server `200` qaytarardi — ammo foydalanuvchi hech qanday
o'zgarish ko'rmasdi va "tanlanmayapti" deb o'ylardi. Sabab kodda emas, JS bilan
CSS o'rtasidagi kelishmovchilikda edi: JS tanlangan tugmaga `active` klassini
qo'yadi, CSS esa faqat `is-on` ni bo'yaydi.

Bunday nomuvofiqlikni oddiy view yoki JS testi ushlamaydi — u ikki fayl
o'rtasidagi shartnomada yashiringan. Shuning uchun testlar fayllarni matn
sifatida o'qiydi.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

BASE = Path(settings.BASE_DIR)
CSS = BASE / "static" / "css" / "messenger.css"
JS = BASE / "static" / "js" / "messenger-chat.js"
TEMPLATE = BASE / "templates" / "messenger" / "ai.html"


def _read(path):
    return path.read_text(encoding="utf-8")


class FeedbackButtonStateContractTests(SimpleTestCase):
    """`.feedback-btn` tanlangan holati ko'rinishi shart."""

    def test_state_class_toggled_by_js_is_styled_in_css(self):
        js = _read(JS)
        css = _read(CSS)

        # Faqat `button.classList.toggle(...)` — bu ikkala chaqiruv ham `.feedback-btn`
        # elementlariga tegishli (tanlagich va xabar baholash tugmalari). Boshqa
        # toggle'lar (`status`, `bubble`, `row`) boshqa elementlarga tegadi.
        toggled = set(re.findall(r"button\.classList\.toggle\(\s*['\"]([\w-]+)['\"]", js))
        self.assertTrue(toggled, "messenger-chat.js feedback tugmalarida klass toggle qilmayapti — test eskirgan")

        unstyled = sorted(
            cls for cls in toggled
            if not re.search(r"\.feedback-btn\.%s\b" % re.escape(cls), css)
        )
        self.assertEqual(
            unstyled, [],
            "JS shu klass(lar)ni tanlangan holat uchun qo'yadi, ammo messenger.css "
            "ularni bo'yamaydi — tanlov saqlanadi, lekin ko'rinmaydi: %s" % unstyled,
        )

    def test_no_selected_state_rule_that_nobody_sets(self):
        css = _read(CSS)
        js = _read(JS)
        template = _read(TEMPLATE)

        styled = set(re.findall(r"\.feedback-btn\.([\w-]+)\b", css))
        # `--icon`/`--skill`/`--source` variantlari qoida emas, modifikator klasslari
        styled = {cls for cls in styled if not cls.startswith("-")}

        never_set = sorted(
            cls for cls in styled
            if cls not in js and cls not in template
        )
        self.assertEqual(
            never_set, [],
            "messenger.css bu holat(lar)ni bo'yaydi, lekin ularni na JS na shablon "
            "qo'yadi — o'lik qoida aynan shu nomuvofiqlikni yashirgan edi: %s" % never_set,
        )

    def test_template_marks_current_choice_with_the_same_class_as_js(self):
        js = _read(JS)
        template = _read(TEMPLATE)

        match = re.search(r"button\.classList\.toggle\(\s*['\"]([\w-]+)['\"]\s*,\s*selected", js)
        self.assertIsNotNone(match, "markSelectedOption() o'zgargan — test yangilanishi kerak")
        js_class = match.group(1)

        # Shablon serverda joriy tanlovni belgilaydi; klass JS bilan bir xil bo'lishi shart,
        # aks holda sahifa ochilganda tanlov ko'rinadi, bosgandan keyin yo'qoladi (yoki aksincha).
        for attr in ("data-ai-tone-option", "data-ai-model-option"):
            rendered = re.search(
                r"%s=.*?class=\"feedback-btn\{%% if [^%%]+ %%\} ([\w-]+)\{%% endif %%\}" % re.escape(attr),
                template,
            )
            self.assertIsNotNone(rendered, f"{attr} tugmasi shablonda topilmadi")
            self.assertEqual(
                rendered.group(1), js_class,
                f"{attr}: shablon '{rendered.group(1)}' qo'yadi, JS esa '{js_class}' — "
                "ikkalasi bir xil bo'lishi shart",
            )


class PickerStatusContractTests(SimpleTestCase):
    """Saqlash muvaffaqiyati yoki xatosi ko'rinishi shart."""

    def test_status_targets_referenced_by_js_exist_in_template(self):
        js = _read(JS)
        template = _read(TEMPLATE)

        selectors = set(re.findall(r"setPickerStatus\(\s*['\"]\[(data-ai-[\w-]+-status)\]", js))
        self.assertTrue(selectors, "setPickerStatus chaqiruvlari topilmadi — test eskirgan")

        missing = sorted(sel for sel in selectors if sel not in template)
        self.assertEqual(
            missing, [],
            "JS shu joylarga natija yozadi, ammo shablonda bunday element yo'q — "
            "saqlash xatosi foydalanuvchiga umuman ko'rinmaydi: %s" % missing,
        )
