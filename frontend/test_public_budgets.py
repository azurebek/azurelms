"""PUB1.7b — ochiq sahifalar asset byudjeti, o'z serverimizdagi shrift/ikonka, media.

Asosiy da'volar, ikkala rendererda:
* har ochiq va kirish sahifasi faqat o'z serverimizdagi CSS/JS'ni yuklaydi (tashqi 0),
  har fayl static'da topiladi va siqilgan hajm `BUDGETS`dan oshmaydi — sekinlashish CI'da;
* V1 ochiq sahifasi ilova bundle'ini (`auth.css`, `learning.css`, `shell.js`) yuklamaydi;
* Google Fonts va jsDelivr na shablonda, na static'da, na CSP'da — CSP faqat torayadi;
* karta rasmlari sekin yuklanadi va joyi band, sahifaning bosh (LCP) rasmi sekin emas;
* `audit_public_media` fayli yo'q ochiq media havolasini topadi va hech narsa o'chirmaydi.
"""

import re
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import FeatureFlag
from blog.models import BlogPost
from core.csp_policy import build_csp_policy
from courses.models import Course
from frontend import public_budgets
from frontend.public_media import missing_public_media
from frontend.testing_legal import publish_legal
from sit.models import University
from users.models import CustomUser

CDN_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net")


class BudgetWorld(TestCase):
    def setUp(self):
        self.author = CustomUser.objects.create_user("muallif", "m@example.test", "x", first_name="Ali")
        self.post = BlogPost.objects.create(title="Maqola", author=self.author, excerpt="e", body="<p>b</p>",
                                            status=BlogPost.STATUS_PUBLISHED, published_at=timezone.now())
        self.course = Course.objects.create(title="Kurs", description="d", level="beginner")
        self.university = University.objects.create(name="Universitet", short_name="U", city="Istanbul", is_published=True,
                                                    source_url="https://example.edu.tr/", last_verified_on=date.today())
        publish_legal("privacy")

    def pages(self):
        public = {
            "home": reverse("home"), "about": reverse("about"), "courses": reverse("courses"),
            "course": reverse("course_detail", args=[self.course.pk]), "pricing": reverse("subscriptions:pricing"),
            "blog": reverse("blog:list"), "post": self.post.get_absolute_url(), "sit": reverse("sit:home"),
            "universities": reverse("sit:university_list"), "university": self.university.get_absolute_url(),
            "privacy": reverse("privacy_policy"),
        }
        auth = {"login": reverse("login"), "reset": reverse("password_reset")}
        return [("public", name, url) for name, url in public.items()] + [("auth", name, url) for name, url in auth.items()]

    def renderer(self, v1):
        for slug in ("frontend_v1_public", "frontend_v1_auth"):
            FeatureFlag.objects.update_or_create(slug=slug, defaults={"enabled": v1})


class AssetBudgetTests(BudgetWorld):
    def test_every_page_stays_local_resolvable_and_within_budget(self):
        for renderer, v1 in (("legacy", False), ("v1", True)):
            self.renderer(v1)
            for kind, name, url in self.pages():
                with self.subTest(renderer=renderer, page=name):
                    response = self.client.get(url)
                    self.assertLess(response.status_code, 500)
                    weight = public_budgets.page_weight(response.content.decode())  # topilmasa FileNotFoundError
                    self.assertEqual(weight["external"], [])
                    self.assertTrue(weight["paths"])
                    budget = public_budgets.BUDGETS[(renderer, kind)]
                    self.assertLessEqual(weight["css"], budget["css"], f"CSS {weight['css']} > {budget['css']}")
                    self.assertLessEqual(weight["js"], budget["js"], f"JS {weight['js']} > {budget['js']}")

    def test_v1_public_pages_do_not_load_the_app_bundle(self):
        self.renderer(True)
        for kind, name, url in self.pages():
            paths = public_budgets.page_weight(self.client.get(url).content.decode())["paths"]
            with self.subTest(page=name):
                if kind == "public":
                    self.assertFalse(set(paths) & set(public_budgets.APP_BUNDLE), paths)
                else:
                    self.assertIn("frontend_v1/css/auth.css", paths)

    def test_flash_messages_keep_their_style_without_the_app_bundle(self):
        components = (Path(settings.BASE_DIR) / "static/frontend_v1/css/components.css").read_text(encoding="utf-8")
        self.assertIn(".v1-messages", components)
        self.assertIn(".v1-error", components)


class SelfHostedAssetTests(SimpleTestCase):
    def test_no_template_or_static_file_points_at_font_or_icon_cdns(self):
        base = Path(settings.BASE_DIR)
        offenders = []
        for root in ("templates", "static"):
            for path in (base / root).rglob("*"):
                if path.suffix not in {".html", ".css", ".js"} or "admin" in path.parts:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                if any(host in text for host in CDN_HOSTS):
                    offenders.append(str(path.relative_to(base)))
        self.assertEqual(offenders, [])

    def test_csp_only_narrowed(self):
        directives = build_csp_policy("example.test")["DIRECTIVES"]
        for name in ("script-src", "style-src", "font-src"):
            with self.subTest(directive=name):
                self.assertFalse([value for value in directives[name] if any(host in value for host in CDN_HOSTS)])
        self.assertEqual(directives["font-src"], ["'self'"])

    def test_vendored_fonts_and_icons_are_complete_and_licensed(self):
        base = Path(settings.BASE_DIR) / "static" / "vendor"
        fonts_css = (base / "fonts" / "fonts.css").read_text(encoding="utf-8")
        for name in re.findall(r"url\(([^)]+\.woff2)\)", fonts_css):
            self.assertTrue((base / "fonts" / name).exists(), name)
        self.assertIn("'Space Grotesk'", fonts_css)
        self.assertIn("'Space Mono'", fonts_css)
        icons = (base / "bootstrap-icons" / "bootstrap-icons.min.css").read_text(encoding="utf-8")
        self.assertIn('url("fonts/bootstrap-icons.woff2")', icons)
        self.assertNotIn("?", icons.split("}")[0])  # manifest hashi so'rov qatorisiz fayl nomini topadi
        self.assertTrue((base / "bootstrap-icons" / "fonts" / "bootstrap-icons.woff2").exists())
        for license_file in ("fonts/LICENSE-space-grotesk.txt", "fonts/LICENSE-space-mono.txt", "bootstrap-icons/LICENSE.txt"):
            self.assertTrue((base / license_file).exists(), license_file)


class ImagePolicyTests(BudgetWorld):
    def test_cards_load_lazily_in_a_reserved_box_and_the_lead_image_does_not(self):
        BlogPost.objects.filter(pk=self.post.pk).update(cover_image="blog/covers/yoq.jpg", featured=False)
        self.renderer(True)
        listing = self.client.get(reverse("blog:list")).content.decode()
        self.assertIn('class="p-public-image p-public-image--card" src="/media/blog/covers/yoq.jpg"', listing)
        card = listing[listing.index("p-public-image--card"):]
        self.assertIn('loading="lazy" decoding="async"', card[:300])
        detail = self.client.get(self.post.get_absolute_url()).content.decode()
        lead = detail[detail.index('src="/media/blog/covers/yoq.jpg"') - 80:detail.index('src="/media/blog/covers/yoq.jpg"') + 120]
        self.assertNotIn("lazy", lead)
        css = (Path(settings.BASE_DIR) / "static/frontend_v1/css/public.css").read_text(encoding="utf-8")
        self.assertIn(".p-public-image--card { aspect-ratio: 16 / 9; object-fit: cover;", css)

    def test_legacy_motion_respects_reduced_motion(self):
        for css in ("static/css/public-shell.css", "static/css/sit.css"):
            with self.subTest(css=css):
                text = (Path(settings.BASE_DIR) / css).read_text(encoding="utf-8")
                self.assertIn("@media (prefers-reduced-motion: reduce)", text)


class MediaAuditTests(BudgetWorld):
    def test_missing_public_files_are_reported_and_nothing_is_changed(self):
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            post = BlogPost.objects.get(pk=self.post.pk)
            post.cover_image.save("bor.jpg", ContentFile(b"\xff\xd8\xff"), save=False)
            BlogPost.objects.filter(pk=post.pk).update(cover_image=post.cover_image.name)
            University.objects.filter(pk=self.university.pk).update(cover_image="sit/universities/covers/yoq.jpg")
            BlogPost.objects.create(title="Qoralama", author=self.author, body="<p>q</p>", status=BlogPost.STATUS_DRAFT)
            BlogPost.objects.filter(title="Qoralama").update(cover_image="blog/covers/qoralama-yoq.jpg")
            checked, missing = missing_public_media()
            self.assertEqual(checked, 2)  # qoralama ochiq emas — tekshirilmaydi
            self.assertEqual([(m.source, m.field, m.name) for m in missing],
                             [("sit.University", "cover_image", "sit/universities/covers/yoq.jpg")])
            out = StringIO()
            call_command("audit_public_media", stdout=out)
            self.assertIn("fayli yo'q: 1", out.getvalue())
            self.assertEqual(University.objects.get(pk=self.university.pk).cover_image.name, "sit/universities/covers/yoq.jpg")
