"""Build real hashed assets, including rewritten CSS dependencies.

Ikkinchi sinf — haqiqiy yiqilishning nusxasi. Manifest storage yoqilganda
`collectstatic` butun loyihada yiqildi, chunki `jazzmin` paketi o'zining
Bootstrap bundle'ini `.map` fayliga ishora bilan yuboradi, `.map` faylning
o'zini esa yubormaydi. Sintetik ikki faylli test buni sezmagan edi —
o'lik ishora umuman yo'q edi.
"""
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, override_settings
from django.contrib.staticfiles.storage import staticfiles_storage


class StaticManifestTests(SimpleTestCase):
    def test_content_hash_and_css_references_survive_a_fresh_storage_instance(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
            root = Path(source)
            (root / "icon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            (root / "shell.css").write_text('body{background:url("icon.svg")}')
            storages = {**settings.STORAGES, "staticfiles": {
                "BACKEND": "core.custom_storage.HashedStaticFilesStorage",
            }}
            with override_settings(DEBUG=False, STORAGES=storages, STATIC_ROOT=target,
                                   STATICFILES_DIRS=[source], STATICFILES_FINDERS=[
                                       "django.contrib.staticfiles.finders.FileSystemFinder"]):
                call_command("collectstatic", interactive=False, verbosity=0)
                first_url = staticfiles_storage.url("shell.css")
                self.assertRegex(first_url, r"shell\.[0-9a-f]{12}\.css$")
                hashed = staticfiles_storage.stored_name("shell.css")
                self.assertIn(staticfiles_storage.stored_name("icon.svg"), (Path(target) / hashed).read_text())
                (root / "shell.css").write_text('body{color:red;background:url("icon.svg")}')
                call_command("collectstatic", interactive=False, verbosity=0)
                self.assertNotEqual(first_url, staticfiles_storage.url("shell.css"))
            with override_settings(DEBUG=False, STORAGES=storages, STATIC_ROOT=target):
                self.assertNotEqual(first_url, staticfiles_storage.url("shell.css"))
                with self.assertRaises(ValueError):
                    staticfiles_storage.url("missing.css")


@override_settings(DEBUG=False)
class DeadThirdPartyReferenceTests(SimpleTestCase):
    """O'zga paketning o'lik ishorasi deploy'ni to'xtatmaydi."""

    def _collect(self, source, target):
        storages = {**settings.STORAGES, "staticfiles": {
            "BACKEND": "core.custom_storage.HashedStaticFilesStorage",
        }}
        return override_settings(
            DEBUG=False, STORAGES=storages, STATIC_ROOT=target,
            STATICFILES_DIRS=[source],
            STATICFILES_FINDERS=["django.contrib.staticfiles.finders.FileSystemFinder"],
        )

    def test_a_missing_sourcemap_does_not_stop_the_build(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
            root = Path(source)
            # Aynan jazzmin yuboradigan shakl: mavjud bo'lmagan `.map`.
            (root / "vendor.min.js").write_text(
                "var a=1;" + chr(10) + "//# sourceMappingURL=vendor.min.js.map" + chr(10)
            )
            (root / "ours.css").write_text("body{color:red}")

            with self._collect(source, target):
                call_command("collectstatic", interactive=False, verbosity=0)

                # Deploy to'xtamadi va o'zimizniki baribir hash'landi.
                self.assertRegex(staticfiles_storage.url("ours.css"), r"ours\.[0-9a-f]{12}\.css$")
                self.assertRegex(
                    staticfiles_storage.url("vendor.min.js"), r"vendor\.min\.[0-9a-f]{12}\.js$"
                )

    def test_our_own_missing_file_still_fails_loudly(self):
        """Kechirim faqat ichki havolaga — `{% static %}` to'ri joyida qoladi."""
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
            (Path(source) / "ours.css").write_text("body{color:red}")

            with self._collect(source, target):
                call_command("collectstatic", interactive=False, verbosity=0)

                with self.assertRaises(ValueError):
                    staticfiles_storage.url("yoq.css")
