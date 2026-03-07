from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """
    Faqat media fayllar (avatar, kurs rasmlari, PDF) uchun.
    Barcha fayllarni 'media/' papkasiga joylaydi va ommaviy o'qishga ochadi.
    """
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False  # Bir xil nomli fayllar ustiga yozmaslik uchun
    object_parameters = {
        'CacheControl': 'max-age=86400',
    }
