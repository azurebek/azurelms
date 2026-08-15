"""Redis/Valkey ulanish parametrlari (settings tomonidan chaqiriladi).

Alohida modul, chunki bu qoida sozlama emas — sinovdan o'tishi kerak bo'lgan
mantiq: TLS kwarg'ini noto'g'ri sxemaga uzatish ulanishni butunlay buzadi va
xato faqat birinchi cache chaqirig'ida ko'rinadi.
"""

# TLS sertifikatini tekshirmaslik kerak bo'ladigan sxema. Managed Valkey/Redis
# (DigitalOcean) o'z CA'si bilan keladi; oddiy `redis://` esa TLS'siz.
TLS_SCHEME = "rediss://"


def redis_connection_pool_kwargs(url):
    """django-redis `CONNECTION_POOL_KWARGS` qiymati.

    `ssl_cert_reqs` faqat TLS ulanishida mavjud: redis-py uni oddiy
    `redis://` Connection konstruktoriga uzatilganda `TypeError` beradi.
    """
    if url and url.startswith(TLS_SCHEME):
        return {"ssl_cert_reqs": None}
    return {}
