import base64
import tempfile
from pathlib import Path

from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from frontend.models import SiteSettings


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class BrandControlViewTests(TestCase):
    def setUp(self):
        self.media_dir = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.media_override.enable()
        User = get_user_model()
        self.owner = User.objects.create_superuser(
            username="brand_owner",
            email="brand-owner@example.test",
            password="pass-12345",
        )
        self.staff = User.objects.create_user(
            username="brand_staff",
            email="brand-staff@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.brand = SiteSettings.load()

    def tearDown(self):
        self.media_override.disable()
        self.media_dir.cleanup()

    def _payload(self, **overrides):
        payload = {
            "brand_name": self.brand.brand_name,
            "brand_tagline": self.brand.brand_tagline,
            "logo_mark_text": self.brand.logo_mark_text,
            "change_reason": "Yangi brend paketi tasdiqlandi",
            "confirm_change": "on",
        }
        payload.update(overrides)
        return payload

    def test_only_owner_can_open_brand_control(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("backoffice_brand"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backoffice/brand_control.html")
        self.assertContains(response, "Bitta joydan barcha logolar")

        self.client.force_login(self.staff)
        response = self.client.get(reverse("backoffice_brand"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response["Location"])

    def test_save_requires_confirmation_and_reason(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("backoffice_brand"),
            self._payload(brand_name="Tasdiqsiz brend", confirm_change=""),
        )
        self.assertEqual(response.status_code, 200)
        self.brand.refresh_from_db()
        self.assertNotEqual(self.brand.brand_name, "Tasdiqsiz brend")
        self.assertContains(response, "Barcha logo yuzalari yangilanishini tasdiqlayman")

    def test_owner_change_is_saved_and_audited_with_reason(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("backoffice_brand"),
            self._payload(brand_name="Markaziy Brend", logo_mark_text="MB"),
        )
        self.assertRedirects(response, reverse("backoffice_brand"))
        self.brand.refresh_from_db()
        self.assertEqual(self.brand.brand_name, "Markaziy Brend")
        self.assertEqual(self.brand.logo_mark_text, "MB")
        entry = LogEntry.objects.get(user=self.owner)
        self.assertIn("Brend nomi", entry.change_message)
        self.assertIn("Yangi brend paketi tasdiqlandi", entry.change_message)

    def test_uploaded_mark_is_used_by_canonical_logo_component(self):
        self.client.force_login(self.owner)
        mark = SimpleUploadedFile("central-mark.png", PNG_1X1, content_type="image/png")
        response = self.client.post(
            reverse("backoffice_brand"),
            self._payload(logo_mark_image=mark),
        )
        self.assertRedirects(response, reverse("backoffice_brand"))
        self.brand.refresh_from_db()
        html = render_to_string(
            "components/brand_logo.html",
            {"site_settings": self.brand, "mark_only": True},
        )
        self.assertIn(self.brand.logo_mark_image.url, html)
        self.assertIn("brand-logo-image--mark", html)


class BrandSurfaceContractTests(SimpleTestCase):
    SURFACE_TEMPLATES = (
        "templates/base_public.html",
        "templates/index.html",
        "templates/users/base_app.html",
        "templates/base_teacher.html",
        "templates/backoffice/base.html",
        "templates/messenger/ai.html",
        "templates/bot/miniapp_base.html",
        "templates/registration/base_auth.html",
        "templates/courses/certificate.html",
        "templates/courses/certificate_appendix.html",
        "templates/courses/exam_detail.html",
        "templates/users/certificates.html",
        "templates/errors/_base_error.html",
    )

    def test_every_logo_surface_uses_the_canonical_component(self):
        project_root = Path(__file__).resolve().parent.parent
        for relative_path in self.SURFACE_TEMPLATES:
            with self.subTest(template=relative_path):
                source = (project_root / relative_path).read_text(encoding="utf-8")
                self.assertIn('components/brand_logo.html', source)

    def test_every_standalone_document_declares_the_canonical_favicon(self):
        """Har mustaqil <head> markaziy favicon'ni o'qishi kerak.

        Yangi shell qo'shilganda bu test uni eslatadi; aks holda sahifa jim
        ravishda brauzer default ikonkasi bilan qoladi.
        """
        templates_root = Path(__file__).resolve().parent.parent / "templates"
        missing = []
        for template_path in sorted(templates_root.rglob("*.html")):
            source = template_path.read_text(encoding="utf-8")
            if "<head>" not in source:
                continue
            if "components/brand_favicon.html" not in source:
                missing.append(str(template_path.relative_to(templates_root)))
        self.assertEqual(missing, [], f"Favicon include yo'q: {missing}")
