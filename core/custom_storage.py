from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """
    Faqat media fayllar (avatar, kurs rasmlari, PDF) uchun.
    Barcha fayllarni 'media/' papkasiga joylaydi va ommaviy o'qishga ochadi.
    """
    location = 'media'
    default_acl = 'public-read'
    # file_overwrite=True: HeadObject so'rovini o'tkazib yuboradi (403 xatosini oldini oladi)
    # Django o'zi fayl nomiga avtomat ravishda qo'shimcha qo'shadi, shuning uchun ustiga yozilmaydi
    file_overwrite = True
    object_parameters = {
        'CacheControl': 'max-age=86400',
    }
