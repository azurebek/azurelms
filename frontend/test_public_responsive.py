"""Public qobiqning moslashuvchan qismi: yig'iladigan footer, menyu chegarasi, katalog filtri.

Owner ko'rigi (2026-10-18): telefonda footer “dabdala”, o'rta kenglikda navbar
ikki qatorga tushardi, katalog filtrlari notekis edi. CSS va JS chegaralari
alohida fayllarda — biri o'zgarib ikkinchisi qolib ketmasligi shu yerda qulflanadi
(legacy'da 1040px va 1180px shunday ajralib qolgan edi).
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from aicontrol.models import FeatureFlag
from frontend.models import LegalPage, SiteSettings

STATIC = Path(settings.BASE_DIR) / "static"


def read(relative):
    return (STATIC / relative).read_text(encoding="utf-8")


def media_block(css, query):
    """`@media <query> { ... }` blokining ichi (ichma-ich qavslar hisobga olinadi)."""
    start = css.index(f"@media {query}")
    depth, index = 0, css.index("{", start)
    for position in range(index, len(css)):
        depth += {"{": 1, "}": -1}.get(css[position], 0)
        if depth == 0:
            return css[index + 1:position]
    raise AssertionError(query)


def renderers():
    for enabled, name in ((False, "legacy"), (True, "v1")):
        FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": enabled})
        yield name


class BreakpointAgreementTests(TestCase):
    def test_v1_menu_and_footer_breakpoints_match_between_css_and_js(self):
        css, js = read("frontend_v1/css/public.css"), read("frontend_v1/js/public-header.js")
        self.assertIn("matchMedia('(min-width: 1200px)')", js)
        self.assertIn(".s-public-nav--desktop, .s-public-auth--desktop { display: none; }", media_block(css, "(width < 1200px)"))
        self.assertIn("matchMedia('(max-width: 639.98px)')", js)
        self.assertIn(".s-public-footer__fold[open]", media_block(css, "(width < 640px)"))

    def test_legacy_menu_and_footer_breakpoints_match_between_css_and_js(self):
        css, js = read("css/public-shell.css"), read("js/public.js")
        self.assertIn("matchMedia('(max-width: 1180px)')", js)
        self.assertIn(".pub-nav{ display:none; }", media_block(css, "(max-width:1180px)"))
        self.assertIn("matchMedia('(max-width: 760px)')", js)
        self.assertIn(".pub-foot-fold[open]", media_block(css, "(max-width:760px)"))

    def test_v1_header_never_wraps_its_actions(self):
        css = read("frontend_v1/css/public.css")
        # Asosiy (desktop) qoida — mobil media blokidagi nusxasi emas.
        self.assertRegex(css, r"\.s-public-header__inner \{ min-height: var\(--az-header\);[^}]*flex-wrap: nowrap")
        self.assertRegex(css, r"\.s-public-nav a \{[^}]*white-space: nowrap")
        self.assertRegex(css, r"\.s-public-header__actions \{[^}]*flex-shrink: 0")


class CollapsibleFooterTests(TestCase):
    def setUp(self):
        for page_type in ("privacy", "terms", "faq"):
            LegalPage.objects.create(page_type=page_type, title=page_type, content="<p>Matn</p>")

    def footer(self):
        html = self.client.get(reverse("about")).content.decode()
        return html[html.index("<footer"):]

    def test_each_group_is_a_named_landmark_with_a_fold_that_starts_open(self):
        for name in renderers():
            footer = self.footer()
            groups = re.findall(r'<nav[^>]*aria-label="(Footer: [^"]+)">\s*<details[^>]*data-footer-fold open>', footer)
            with self.subTest(renderer=name):
                # JS bo'lmasa hech narsa yashirinmasligi uchun server ochiq chizadi.
                self.assertEqual(groups, ["Footer: Platforma", "Footer: Kompaniya", "Footer: Huquqiy"])
                self.assertEqual(footer.count("<summary"), footer.count("data-footer-fold"))

    def test_legacy_contact_column_appears_only_when_configured(self):
        FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": False})
        SiteSettings.objects.create()  # model namunasi — sozlanmagan
        self.assertNotIn(">Aloqa<", self.footer())
        SiteSettings.objects.filter(pk=1).update(contact_email="aloqa@example.test")
        footer = self.footer()
        self.assertIn(">Aloqa<", footer)
        self.assertIn('href="mailto:aloqa@example.test"', footer)


class CatalogFilterLayoutTests(TestCase):
    def test_visual_order_matches_keyboard_order(self):
        FeatureFlag.objects.update_or_create(slug="frontend_v1_public", defaults={"enabled": True})
        html = self.client.get(reverse("courses")).content.decode()
        order = re.findall(r'class="[^"]*p-public-filters__(q|levels|sort|submit)\b', html)
        self.assertEqual(order, ["q", "levels", "sort", "submit"])
        css = read("frontend_v1/css/public.css")
        self.assertIn('grid-template-areas: "q q q" "levels sort submit"', css)
