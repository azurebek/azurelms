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
    }
