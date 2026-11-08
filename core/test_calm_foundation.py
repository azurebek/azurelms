"""DESIGN-02 S1 foundation: safe fallback, official fonts and OFF parity."""
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path
from unittest import skipUnless

from django.template.loader import render_to_string
from django.test import TestCase
from fontTools.ttLib import TTFont

from core.flags import flag_by_slug
from core.frontend_v1 import calm_template_names
from frontend.models import SiteSettings


ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "static" / "frontend_v1" / "fonts"


class CalmFoundationTests(TestCase):
    def test_flag_is_default_off_and_template_fallback_is_ordered(self):
        self.assertFalse(flag_by_slug("platform_calm_v1").default)
        template = "frontend_v1/dashboard.html"
        self.assertEqual(calm_template_names(template, enabled=False), [template])
        self.assertEqual(
            calm_template_names(template, enabled=True),
            ["frontend_v1/calm/dashboard.html", template],
        )

    def test_base_shell_off_output_has_no_calm_marker_or_asset(self):
        html = render_to_string("frontend_v1/base.html", {"site_settings": SiteSettings()})
        self.assertIn('class=""', html)
        self.assertNotIn("s-calm", html)
        self.assertNotIn("frontend_v1/css/calm.css", html)

    def test_official_figtree_files_are_pinned_with_license(self):
        expected = {
            "Figtree-Regular.woff2": "72de3fc98fde5a540d729ddca05c035e0b0e444c4ee5f4e0a8c30220e4406c93",
            "Figtree-Medium.woff2": "da1916212ef66e1ed93cd9fa00a1954874daf92f7ae5a99309e77c35d986a588",
            "Figtree-SemiBold.woff2": "b1e611e9d3d8ce9e9695a9af5edb7085087f959fe1dd107846ad9d454dbe7c5e",
        }
        for name, digest in expected.items():
            path = FONT_DIR / name
            with self.subTest(font=name):
                self.assertEqual(sha256(path.read_bytes()).hexdigest(), digest)
        license_text = (FONT_DIR / "OFL.txt").read_text(encoding="utf-8")
        self.assertIn("SIL OPEN FONT LICENSE Version 1.1", license_text)
        source = (FONT_DIR / "SOURCE.md").read_text(encoding="utf-8")
        self.assertIn("032dfa7fe219ef3a02890d6d3add84eacc9aebfe", source)

    @skipUnless(find_spec("brotli"), "WOFF2 cmap probe needs the optional Brotli decoder")
    def test_figtree_weights_and_native_turkish_uzbek_glyphs(self):
        # U+2018 is the project's rendered Uzbek tutuq mark. U+02BB input is
        # accepted by search normalization and safely falls through the CSS
        # family list because the unmodified upstream font does not encode it.
        required = "ğĞşŞıİçÇöÖüÜ‘’"
        for name, weight in (("Figtree-Regular.woff2", 400), ("Figtree-Medium.woff2", 500),
                             ("Figtree-SemiBold.woff2", 600)):
            with self.subTest(font=name):
                font = TTFont(FONT_DIR / name)
                self.assertEqual(font["OS/2"].usWeightClass, weight)
                cmap = font.getBestCmap()
                self.assertFalse([char for char in required if ord(char) not in cmap])
