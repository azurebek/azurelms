"""Messenger AI tanlagichi uchun kontrakt testlari.

Bu testlar mavjud bo'lishining sababi: tanlagich sahifada ochilardi, bosilganda
so'rov ketardi va server `200` qaytarardi — ammo foydalanuvchi hech qanday
o'zgarish ko'rmasdi va "tanlanmayapti" deb o'ylardi. Sabab kodda emas, JS bilan
CSS o'rtasidagi kelishmovchilikda edi: JS tanlangan tugmaga `active` klassini
qo'yadi, CSS esa faqat `is-on` ni bo'yardi.

Bunday nomuvofiqlikni na view testi, na JS testi ushlaydi — u ikki fayl
o'rtasidagi shartnomada yashiringan. Shuning uchun testlar fayllarni matn
sifatida o'qiydi.

Testlar qaysi tanlagich mavjudligini **shablondan** aniqlaydi, qattiq yozilgan
ro'yxatdan emas: model kompozitorga ko'chdi, uslub esa sozlamalar sahifasiga
o'tdi, va test bunday ko'chishlarda yolg'on qizil bermasligi kerak.
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


def _state_classes_toggled_on_buttons(js):
    """`button.classList.toggle(...)` — ikkala chaqiruv ham tanlov holati uchun.

    Boshqa toggle'lar (`status`, `bubble`, `row`) boshqa elementlarga tegadi.
    """
    return set(re.findall(r"button\.classList\.toggle\(\s*['\"]([\w-]+)['\"]", js))


def _components_that_receive_state():
    """Tanlov holatini oladigan komponent klasslari — manbadan aniqlanadi.

    Shablonda `data-ai-*-option`, JSda esa `data-feedback-rating` tugmalari.
    Qattiq yozilgan ro'yxat markup o'zgarganda jim eskiradi.
    """
    components = set()

    for line in _read(TEMPLATE).splitlines():
        if not re.search(r"data-ai-[\w-]+-option", line):
            continue
        match = re.search(r'class="([\w-]+)', line)
        if match:
            components.add(match.group(1))

    js = _read(JS)
    for match in re.finditer(r"className\s*=\s*'([\w-]+)'", js):
        start = match.end()
        if "data-feedback-rating" in js[start:start + 200]:
            components.add(match.group(1))

    return components


class SelectedStateContractTests(SimpleTestCase):
    """Tanlangan holat ko'rinishi shart."""

    def test_every_component_that_receives_state_is_styled_for_it(self):
        css = _read(CSS)
        components = _components_that_receive_state()
        states = _state_classes_toggled_on_buttons(_read(JS))

        self.assertTrue(components, "holat oladigan komponent topilmadi — test eskirgan")
        self.assertTrue(states, "JS feedback tugmalarida klass toggle qilmayapti — test eskirgan")

        unstyled = sorted(
            f".{component}.{state}"
            for component in components
            for state in states
            if not re.search(r"\.%s\.%s\b" % (re.escape(component), re.escape(state)), css)
        )
        self.assertEqual(
            unstyled, [],
            "JS bu holatni qo'yadi, ammo messenger.css uni bo'yamaydi — "
            "tanlov saqlanadi, lekin ko'rinmaydi: %s" % unstyled,
        )

    def test_no_selected_state_rule_that_nobody_sets(self):
        css = _read(CSS)
        js = _read(JS)
        template = _read(TEMPLATE)

        never_set = set()
        for component in _components_that_receive_state():
            for state in re.findall(r"\.%s\.([\w-]+)\b" % re.escape(component), css):
                if state not in js and state not in template:
                    never_set.add(f".{component}.{state}")

        self.assertEqual(
            sorted(never_set), [],
            "messenger.css bu holat(lar)ni bo'yaydi, lekin ularni na JS na shablon "
            "qo'yadi — o'lik qoida aynan shu nomuvofiqlikni yashirgan edi: %s" % sorted(never_set),
        )

    def test_template_marks_current_choice_with_the_same_class_as_js(self):
        js = _read(JS)
        template = _read(TEMPLATE)

        match = re.search(r"button\.classList\.toggle\(\s*['\"]([\w-]+)['\"]\s*,\s*selected", js)
        self.assertIsNotNone(match, "markSelectedOption() o'zgargan — test yangilanishi kerak")
        js_class = match.group(1)

        # Shablon serverda joriy tanlovni belgilaydi. Klass JS bilan bir xil bo'lmasa,
        # tanlov sahifa ochilganda ko'rinib, bosgandan keyin yo'qoladi (yoki aksincha).
        rendered = re.findall(
            r'data-ai-[\w-]+-option="[^"]*"\s+class="[\w-]+\{%\s*if [^%]+%\}\s*([\w-]+)\s*\{%\s*endif\s*%\}',
            template,
        )
        self.assertTrue(rendered, "shablonda serverda belgilanadigan variant topilmadi")
        self.assertEqual(
            sorted(set(rendered)), [js_class],
            f"shablon {sorted(set(rendered))} qo'yadi, JS esa '{js_class}' — bir xil bo'lishi shart",
        )


class PickerStatusContractTests(SimpleTestCase):
    """Saqlash muvaffaqiyati yoki xatosi ko'rinishi shart."""

    def test_every_picker_in_the_template_has_a_status_target(self):
        template = _read(TEMPLATE)

        present = set(re.findall(r"data-ai-([\w-]+)-option", template))
        self.assertTrue(present, "shablonda birorta tanlagich topilmadi — test eskirgan")

        missing = sorted(
            f"data-ai-{name}-status"
            for name in present
            if f"data-ai-{name}-status" not in template
        )
        self.assertEqual(
            missing, [],
            "JS shu joylarga natija yozadi, ammo shablonda bunday element yo'q — "
            "saqlash xatosi foydalanuvchiga umuman ko'rinmaydi: %s" % missing,
        )
