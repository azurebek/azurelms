from whitenoise.storage import CompressedManifestStaticFilesStorage
from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """Public media uchun S3-mos storage (AWS S3 yoki DigitalOcean Spaces).

    - `location`: barcha public media `media/` prefiksi ostiga yuklanadi.
    - `file_overwrite=False`: `HeadObject` so'rovi o'tkazib yuboriladi, ya'ni
      list ruxsati yo'q bucketda 403 bermaydi.

    `object_parameters` ataylab **bu yerda yo'q**. django-storages klass
    atributini settingsdan ustun qo'yadi (`BaseStorage.__init__` da
    `if not hasattr(self, name)`), shuning uchun bu yerda turgan
    `'ACL': 'public-read'` ni env bilan o'chirib bo'lmasdi — va aynan shu
    yangi AWS bucketida har bir uploadni `AccessControlListNotSupported`
    (400) bilan yiqitardi, chunki Object Ownership "Bucket owner enforced"
    da ACL umuman qabul qilinmaydi. Parametrlar endi
    `settings.AWS_S3_OBJECT_PARAMETERS` da quriladi.
    """

    location = 'media'
    file_overwrite = False


class HashedStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Hash'lash o'zimizniki uchun qat'iy, uchinchi tomon axlati uchun kechirimli.

    Manifest storage CSS/JS ichidagi havolalarni ham qayta yozadi. Bitta
    havola topilmasa `collectstatic` butunlay yiqiladi — va aynan shunday
    bo'ldi: `jazzmin` paketi o'zining Bootstrap bundle'ini `.map` fayliga
    ishora bilan yuboradi, `.map` faylning o'zini esa yubormaydi.

        MissingFileError: The file 'vendor/bootstrap/js/bootstrap.bundle.min.js.map'
        could not be found

    Ya'ni deploy admin mavzusi tufayli to'xtagan bo'lardi. Bu yerda faqat
    **ichki havola** kechiriladi: fayl topilmasa nom o'zgarishsiz qoladi.

    `manifest_strict` ataylab o'zgartirilmagan (`True` bo'lib qoladi):
    shablondagi `{% static %}` mavjud bo'lmagan faylni so'rasa, u avvalgidek
    baland ovozda yiqiladi. Xavfsizlik to'ri o'z joyida, faqat o'zga
    paketning o'lik ishorasi jim o'tkaziladi.
    """

    def hashed_name(self, name, content=None, filename=None):
        try:
            return super().hashed_name(name, content, filename)
        except ValueError:
            # `MissingFileError` ham `ValueError` — ikkalasi ham shu yerda.
            return name
