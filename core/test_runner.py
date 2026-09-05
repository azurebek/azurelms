"""Loyiha test runneri — test muhitini xavfsiz va tez qiladi.

Muammo: `MEDIA_ROOT` default holatda `BASE_DIR / 'media'` ga ishora qiladi, ya'ni
haqiqiy ishchi papkaga. Test paytida `FileField.save()` chaqirilsa (checkout
cheki, Telegram chek testi, vazifa biriktirmasi, avatar, hujjat testlari) fayl
o'sha yerga yozilib qoladi va test tugagach ham qolib ketadi. Har to'liq
yugurish `media/` ichiga yangi axlat qo'shardi.

Yechim shu qatlamda: test muhiti tayyorlanayotganda `MEDIA_ROOT` vaqtinchalik
papkaga ko'chiriladi va yakunda o'chiriladi. Bir joyda hal bo'lgani uchun har
bir test moduliga alohida mixin yoki dekorator qo'shish shart emas — yangi
yoziladigan testlar ham avtomatik himoyalangan bo'ladi.

`override_settings` ishlatilgani muhim: u `setting_changed` signalini yuboradi,
Django esa shu signalda storage keshlarini tozalaydi. Oddiy
`settings.MEDIA_ROOT = ...` bilan `FileSystemStorage` eski yo'lni keshda
saqlab qolishi mumkin edi.

Alohida testlar o'z `override_settings(MEDIA_ROOT=...)` ini qo'llasa, u shunchaki
shu ustiga qo'yiladi — ziddiyat yo'q.

**Parol hasher'i.** Django default `PBKDF2` ataylab sekin — bu production
uchun to'g'ri, ammo suite yuzlab `create_user` chaqiradi va o'lchov shuni
ko'rsatdi: `users` app testlari 53.3s dan 2.1s ga tushdi, ya'ni vaqtning
deyarli hammasi hashlashga ketayotgan edi. Tez hasher shu yerda, runner
ichida qo'llanadi — `settings.py` da emas, shunda u production'ga sizib
chiqa olmaydi.
"""

import shutil
import tempfile

from django.conf import settings
from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


# Faqat test muhitida. Production sozlamalariga hech qachon tegmaydi.
FAST_TEST_PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


class AzureLmsTestRunner(DiscoverRunner):
    """Vaqtinchalik media ildizlari + tez parol hasher'i."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._temp_media_root = tempfile.mkdtemp(prefix="azurelms-test-media-")
        self._temp_private_root = tempfile.mkdtemp(prefix="azurelms-test-private-")
        self._media_override = override_settings(
            MEDIA_ROOT=self._temp_media_root,
            PRIVATE_MEDIA_ROOT=self._temp_private_root,
            PASSWORD_HASHERS=FAST_TEST_PASSWORD_HASHERS,
            # Ordinary unit tests need no collectstatic build. Manifest behavior
            # has its own integration test with a temporary asset build.
            STORAGES={
                **settings.STORAGES,
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            },
        )
        self._media_override.enable()

    def teardown_test_environment(self, **kwargs):
        media_override = getattr(self, "_media_override", None)
        if media_override is not None:
            media_override.disable()
        for attr in ("_temp_media_root", "_temp_private_root"):
            temp_root = getattr(self, attr, None)
            if temp_root:
                # Test fayllari o'chirilmasa ham suite natijasi buzilmasligi kerak.
                shutil.rmtree(temp_root, ignore_errors=True)
        super().teardown_test_environment(**kwargs)
