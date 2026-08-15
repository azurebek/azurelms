"""Private fayllar uchun alohida storage — `MEDIA_ROOT` dan tashqarida (A0b).

Nega alohida ildiz kerak: to'lov cheki, vazifa fayli, chat biriktirmasi va
speaking yozuvi `MEDIA_ROOT` ichida turganida ular oddiy `/media/...` havolasi
bilan ochilardi. Lokalda buni `urls.py` dagi `static()` handleri, kelajakdagi
production'da esa web server yoki object storage'ning public prefiksi
uzatib yuborardi. Ya'ni himoyani faqat view qatlamiga qo'yish yetarli emas:
fayl **jismonan** public ildizdan chiqarilishi kerak.

`upload_to` yo'llari o'zgarmaydi — faqat ildiz boshqa. Fayllarga yagona kirish
nuqtasi `core/private_media_views.py` dagi ruxsat tekshiradigan view'lar.

**Nega `location` dinamik o'qiladi.** Django `FileField(storage=...)` ga
berilgan callable'ni model klassi yaratilayotganda bir marta chaqiradi, oddiy
`FileSystemStorage(location=...)` esa yo'lni o'sha paytda keshlab qo'yadi.
Natijada `override_settings(PRIVATE_MEDIA_ROOT=...)` (masalan test runnerida)
hech qanday ta'sir qilmasdi va testlar haqiqiy papkaga yozib ketardi. Shuning
uchun `base_location` har murojaatda sozlamadan o'qiladi.
"""

import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateMediaStorage(FileSystemStorage):
    """`PRIVATE_MEDIA_ROOT` ustidagi storage; public URL bermaydi."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("base_url", None)
        super().__init__(*args, **kwargs)

    # `FileSystemStorage`da bular `cached_property` — sozlama o'zgarishini
    # ko'rishi uchun oddiy property bilan almashtiriladi.
    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        # Public URL yo'q: havola faqat ruxsat tekshiradigan view orqali.
        return None

    @base_url.setter
    def base_url(self, value):  # FileSystemStorage.__init__ yozmoqchi bo'ladi
        pass

    def url(self, name):
        raise ValueError(
            "Private fayl uchun to'g'ridan-to'g'ri URL yo'q — "
            "`core/private_media_views.py` dagi view'dan foydalaning."
        )


def private_media_storage():
    """`FileField(storage=...)` uchun callable — dinamik storage qaytaradi."""
    return PrivateMediaStorage()
