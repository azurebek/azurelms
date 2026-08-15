"""Test fayllari repo ichidagi `media/` ga tushmasligini qo'riqlaydi.

`core.test_runner.MediaIsolatedTestRunner` olib tashlansa yoki `TEST_RUNNER`
sozlamasi o'zgarsa, bu testlar darhol va aniq sabab bilan yiqiladi — aks holda
muammo jimgina qaytadi va uni faqat `media/` da to'planib qolgan axlatdan
sezish mumkin bo'lardi.
"""

from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import SimpleTestCase


class MediaIsolationTests(SimpleTestCase):
    def test_test_runner_is_the_media_isolated_one(self):
        self.assertEqual(
            settings.TEST_RUNNER,
            "core.test_runner.AzureLmsTestRunner",
            "TEST_RUNNER o'zgartirilsa testlar yana repo `media/` ga yoza boshlaydi",
        )

    def test_media_root_is_not_the_repository_media_directory(self):
        repo_media = (Path(settings.BASE_DIR) / "media").resolve()
        self.assertNotEqual(Path(settings.MEDIA_ROOT).resolve(), repo_media)

    def test_media_root_is_outside_the_project_tree(self):
        base = Path(settings.BASE_DIR).resolve()
        media_root = Path(settings.MEDIA_ROOT).resolve()
        self.assertFalse(
            media_root == base or base in media_root.parents,
            f"test MEDIA_ROOT loyiha ichida: {media_root}",
        )

    def test_saved_file_lands_in_the_temporary_root(self):
        name = default_storage.save("isolation-check.txt", ContentFile(b"salom"))
        try:
            saved = Path(default_storage.path(name)).resolve()
            self.assertTrue(
                Path(settings.MEDIA_ROOT).resolve() in saved.parents,
                f"fayl kutilmagan joyga saqlandi: {saved}",
            )
        finally:
            default_storage.delete(name)

    def test_tests_use_the_fast_password_hasher(self):
        """Sekin PBKDF2 qaytib qolsa suite bir necha barobar sekinlashadi.

        O'lchov: `users` app testlari 53.3s -> 2.1s. Bu sozlama faqat test
        runner ichida qo'llanadi, `settings.py` da emas — production hech
        qachon uni ko'rmaydi.
        """
        from core.test_runner import FAST_TEST_PASSWORD_HASHERS

        self.assertEqual(settings.PASSWORD_HASHERS, FAST_TEST_PASSWORD_HASHERS)

    def test_production_settings_do_not_ship_the_fast_hasher(self):
        """Tez hasher sozlama faylida bo'lmasligi kerak — faqat runnerda."""
        from pathlib import Path

        source = (Path(settings.BASE_DIR) / "core" / "settings.py").read_text(encoding="utf-8")
        self.assertNotIn("MD5PasswordHasher", source)
