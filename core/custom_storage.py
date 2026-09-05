from whitenoise.storage import CompressedManifestStaticFilesStorage
from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """
    DigitalOcean Spaces uchun media fayl storage.
    - location: Barcha media fayllar 'media/' papkasiga yuklanadi
    - file_overwrite: HeadObject so'rovini o'tkazib yuboradi (403 xatosini oldini oladi)
    - ACL: Bucket darajasida boshqariladi (File Listing = Enabled), per-object ACL o'rnatilmaydi
    """
    location = 'media'
    file_overwrite = False
    object_parameters = {
        'CacheControl': 'max-age=86400',
        'ACL': 'public-read',
    }


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
