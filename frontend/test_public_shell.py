"""PUB1.2d — public qobiq: bitta menyu manbasi, o'lik havola yo'q, soxta va'da yo'q.

Owner qarori bo'lmagan joyda rejadagi xavfsiz default (PUB-D1 avval kurs,
PUB-D2 ro'yxat yopiq bo'lsa lead yo'q, PUB-D7 faqat sozlangan aloqa va SLA
va'dasisiz, PUB-D16 SIT mavjud, takrorsiz) ishlatiladi.
"""

import importlib
import re
from urllib.parse import urlsplit

from django.apps import apps

from django.test import TestCase
from django.urls import reverse

from aicontrol.models import FeatureFlag
from frontend.models import LandingNavItem, LegalPage, SiteSettings


HREF = re.compile(r'href="([^"]*)"')
nav_migration = importlib.import_module("frontend.migrations.0022_nav_sit_key")


def set_flag(slug, enabled):
    FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": enabled})


def renderers():
    for enabled, name in ((False, "legacy"), (True, "v1")):
        set_flag("frontend_v1_public", enabled)
        yield name


def nav_block(html, marker):
    start = html.index(marker)
    return html[start:html.index("</nav>", start)]


def links(fragment):
    return HREF.findall(fragment)


class ShellMixin:
    PAGES = ("about", "courses", "blog:list", "sit:home", "privacy_policy")
    # SIT o'z qobig'iga ega (alohida bo'lim navbari) — umumiy menyu u yerda chizilmaydi.
    SHELL_PAGES = ("about", "courses", "blog:list", "privacy_policy")

    def setUp(self):
        for page_type in ("privacy", "terms", "faq"):
            LegalPage.objects.create(page_type=page_type, title=f"Owner {page_type}", content="<p>Owner matni</p>")
        set_flag("public_registration", True)

    def page(self, name):
        response = self.client.get(reverse(name))
        self.assertEqual(response.status_code, 200, name)
        return response.content.decode()

    def header_navs(self, html, renderer):
        if renderer == "legacy":
            return nav_block(html, 'class="pub-nav"'), nav_block(html, 'class="pub-mobile-nav"')
        return nav_block(html, "s-public-nav--desktop"), nav_block(html, 'aria-label="Mobil navigatsiya"')


class LinkIntegrityTests(ShellMixin, TestCase):
    def test_every_internal_link_on_public_pages_resolves(self):
        checked = {}
        for registration in (True, False):
            set_flag("public_registration", registration)
            for name in renderers():
                for page in ("home", *self.PAGES):
                    html = self.page(page)
                    with self.subTest(renderer=name, page=page, registration=registration):
                        self.assertNotIn('href="#"', html)
                        for href in links(html):
                            parts = urlsplit(href)
                            if href.startswith("#"):
                                anchor = href[1:]
                                if anchor:
                                    self.assertRegex(html, rf'id="{re.escape(anchor)}"', href)
                                continue
                            if parts.scheme or parts.netloc or not parts.path.startswith("/"):
                                continue
                            if parts.path.startswith(("/static/", "/media/", "/design/")):
                                continue
                            if parts.path not in checked:
                                checked[parts.path] = self.client.get(parts.path).status_code
                            self.assertLess(checked[parts.path], 400, href)

    def test_misrouted_certificate_and_admission_links_are_gone(self):
        LandingNavItem.objects.all().delete()  # owner sozlamasi yo'q — default'lar
        for name in renderers():
            for page in ("home", *self.PAGES):
                html = self.page(page)
                with self.subTest(renderer=name, page=page):
                    self.assertNotIn("Sertifikatlar</a>", html)
                    self.assertNotIn("Qabul yo&#x27;li", html)
                    self.assertNotIn("Namuna sertifikatni ko", html)


class NavigationSourceTests(ShellMixin, TestCase):
    def test_desktop_mobile_and_both_renderers_share_one_menu(self):
        seen = {}
        for name in renderers():
            for page in self.SHELL_PAGES:
                desktop, mobile = self.header_navs(self.page(page), name)
                with self.subTest(renderer=name, page=page):
                    self.assertTrue(set(links(desktop)) <= set(links(mobile)))
                    seen.setdefault(page, {})[name] = links(desktop)
        for page, by_renderer in seen.items():
            self.assertEqual(by_renderer["legacy"], by_renderer["v1"], page)

    def test_sit_appears_once_in_header_and_once_in_footer(self):
        sit = reverse("sit:home")
        # Migratsiyadan keyingi seed holati, so'ng owner qatorlari yo'q (kod default'lari).
        for state in ("seeded", "defaults"):
            if state == "defaults":
                LandingNavItem.objects.all().delete()
            for name in renderers():
                html = self.page("about")
                desktop, _ = self.header_navs(html, name)
                footer = html[html.index("<footer"):]
                with self.subTest(state=state, renderer=name):
                    self.assertEqual(links(desktop).count(sit), 1)
                    self.assertEqual(links(footer).count(sit), 1)

    def test_owner_menu_row_reaches_both_renderers(self):
        LandingNavItem.objects.create(placement=LandingNavItem.Placement.MAIN, key="courses",
                                      label="OWNER-KURSLAR", order=1)
        for name in renderers():
            desktop, mobile = self.header_navs(self.page("about"), name)
            with self.subTest(renderer=name):
                self.assertIn("OWNER-KURSLAR", desktop)
                self.assertIn("OWNER-KURSLAR", mobile)

    def test_current_section_is_marked_once(self):
        for name in renderers():
            for page, path in (("courses", reverse("courses")), ("blog:list", reverse("blog:list"))):
                desktop, mobile = self.header_navs(self.page(page), name)
                with self.subTest(renderer=name, page=page):
                    for nav in (desktop, mobile):
                        current = re.findall(r'<a href="([^"]*)"[^>]*aria-current="page"', nav)
                        self.assertEqual(current, [path])

    def test_navigation_landmarks_have_unique_names(self):
        for name in renderers():
            for page in ("home", *self.SHELL_PAGES):
                navs = re.findall(r"<nav\b[^>]*>", self.page(page))
                labels = [re.search(r'aria-label="([^"]+)"', nav) for nav in navs]
                with self.subTest(renderer=name, page=page):
                    self.assertTrue(navs)
                    self.assertTrue(all(labels), navs)
                    labels = [match.group(1) for match in labels]
                    self.assertEqual(len(labels), len(set(labels)), labels)

    def test_footer_is_grouped_into_named_landmarks(self):
        for name in renderers():
            html = self.page("about")
            footer = html[html.index("<footer"):]
            labels = re.findall(r'<nav[^>]*aria-label="(Footer: [^"]+)"', footer)
            with self.subTest(renderer=name):
                self.assertEqual(labels, ["Footer: Platforma", "Footer: Kompaniya", "Footer: Huquqiy"])


class SeedMigrationTests(TestCase):
    def rows(self, placement):
        return list(LandingNavItem.objects.filter(placement=placement).order_by("order", "id")
                    .values_list("key", "label"))

    def test_misrouted_seed_rows_are_replaced_by_sit(self):
        self.assertEqual([key for key, _ in self.rows("footer_platform")], ["courses", "pricing", "sit"])

    def test_owner_edited_rows_and_existing_sit_are_kept(self):
        LandingNavItem.objects.filter(placement="footer_platform").delete()
        LandingNavItem.objects.create(placement="footer_platform", key="about", label="Sertifikatlar",
                                      custom_url="/certificates/verify/", order=1)
        LandingNavItem.objects.create(placement="footer_platform", key="custom", label="SIT",
                                      custom_url="/sit/", order=2)
        before = self.rows("footer_platform")
        nav_migration.fix_public_navigation(apps, None)
        self.assertEqual(self.rows("footer_platform"), before)

    def test_seeded_main_menu_gains_sit_once(self):
        # 0013 seed'i asosiy menyuni to'ldirgan; 0022 SIT'ni oxiriga bir marta qo'shadi.
        nav_migration.fix_public_navigation(apps, None)
        self.assertEqual([key for key, _ in self.rows("main")], ["home", "courses", "pricing", "about", "blog", "sit"])
        self.assertEqual(self.rows("main")[-1], ("sit", "Turkiyada o‘qish"))


class RegistrationStateTests(ShellMixin, TestCase):
    def test_closed_registration_has_no_register_route_and_offers_the_catalog(self):
        register = reverse("register")
        for state in (True, False):
            set_flag("public_registration", state)
            for name in renderers():
                for page in ("home", "about", "courses"):
                    html = self.page(page)
                    with self.subTest(renderer=name, page=page, open=state):
                        self.assertEqual(register in links(html), state)
                        self.assertIn(reverse("courses"), links(html))

    def test_custom_register_menu_row_hides_while_closed(self):
        LandingNavItem.objects.create(placement="footer_company", key="custom", label="QABUL-CUSTOM",
                                      custom_url="/users/register/?from=footer", order=9)
        for state in (True, False):
            set_flag("public_registration", state)
            for name in renderers():
                with self.subTest(renderer=name, open=state):
                    self.assertEqual("QABUL-CUSTOM" in self.page("about"), state)


class ContactAndPromiseTests(ShellMixin, TestCase):
    def test_unconfigured_social_and_contact_render_nothing(self):
        SiteSettings.objects.create(telegram_url="", instagram_url="", youtube_url="", contact_email="", contact_phone="")
        for name in renderers():
            for page in ("home", "about", "privacy_policy"):
                html = self.page(page)
                with self.subTest(renderer=name, page=page):
                    self.assertNotIn(">TELEGRAM<", html)
                    self.assertNotIn('href="tel:"', html)
                    self.assertNotIn('href="mailto:"', html)
                    self.assertNotIn("legal@azurelms.uz", html)

    def test_model_placeholder_contact_is_not_published(self):
        from io import StringIO

        from django.core.management import call_command

        from core.public_readiness import contact_readiness

        SiteSettings.objects.create()  # telefon/email — model namunasi
        for name in renderers():
            for page in ("home", "about", "privacy_policy"):
                html = self.page(page)
                with self.subTest(renderer=name, page=page):
                    self.assertNotIn("123 45 67", html)
                    self.assertNotIn("info@azurelms.uz", html)
        self.assertEqual(contact_readiness(), ())
        out = StringIO()
        call_command("audit_public_readiness", stdout=out)
        self.assertIn("Public aloqa: sozlanmagan", out.getvalue())

        SiteSettings.objects.filter(pk=1).update(contact_phone="+998 71 200 00 00", contact_email="aloqa@example.test")
        set_flag("frontend_v1_public", False)
        html = self.page("about")
        self.assertIn('href="tel:+998712000000"', html)
        self.assertIn('href="mailto:aloqa@example.test"', html)
        self.assertEqual(contact_readiness(), ("telefon", "email"))

    def test_configured_social_links_appear(self):
        SiteSettings.objects.create(telegram_url="https://t.me/azurelms", instagram_url="", youtube_url="")
        set_flag("frontend_v1_public", False)
        html = self.page("about")
        self.assertIn('href="https://t.me/azurelms"', html)
        self.assertNotIn(">INSTAGRAM<", html)

    def test_no_response_time_promises(self):
        SiteSettings.objects.create(contact_email="aloqa@example.test")
        from django.contrib.auth import get_user_model

        member = get_user_model().objects.create_user("yordam-shell", email="ys@example.test", password="Yordam-2026!")
        pages = [self.page("privacy_policy")]
        self.client.force_login(member)
        pages.append(self.client.get(reverse("help_center")).content.decode())
        for html in pages:
            for promise in ("javob beramiz", "3 soatda", "ish kunida"):
                self.assertNotIn(promise, html)
        self.assertIn("aloqa@example.test", pages[0])
