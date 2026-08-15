"""Loyiha test runneri — test fayllari repo ichiga tushmasin.

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
"""

import shutil
import tempfile

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class MediaIsolatedTestRunner(DiscoverRunner):
    """`MEDIA_ROOT` ni vaqtinchalik papkaga olib, yakunda tozalaydigan runner."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._temp_media_root = tempfile.mkdtemp(prefix="azurelms-test-media-")
        self._media_override = override_settings(MEDIA_ROOT=self._temp_media_root)
        self._media_override.enable()

    def teardown_test_environment(self, **kwargs):
        media_override = getattr(self, "_media_override", None)
        if media_override is not None:
            media_override.disable()
        temp_root = getattr(self, "_temp_media_root", None)
        if temp_root:
            # Test fayllari o'chirilmasa ham suite natijasi buzilmasligi kerak.
            shutil.rmtree(temp_root, ignore_errors=True)
        super().teardown_test_environment(**kwargs)
