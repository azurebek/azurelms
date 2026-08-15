"""Redis/Valkey ulanish parametrlari (A1a integration smoke bilan birga).

Bu qoida CI ning PostgreSQL+Valkey ishida ochildi: `ssl_cert_reqs` kwargi
sxemadan qat'i nazar uzatilar edi, redis-py esa uni TLS'siz `redis://`
Connection konstruktorida qabul qilmaydi. Xato faqat birinchi cache
chaqirig'ida ko'rinadi, ya'ni sozlama tekshiruvidan jimgina o'tib ketadi.
"""

from django.test import SimpleTestCase

from core.cache_config import redis_connection_pool_kwargs


class RedisConnectionPoolKwargsTests(SimpleTestCase):
    def test_plain_redis_gets_no_tls_kwargs(self):
        """`redis://` uchun `ssl_cert_reqs` yuborilsa redis-py TypeError beradi."""
        self.assertEqual(redis_connection_pool_kwargs("redis://localhost:6379/0"), {})

    def test_tls_redis_disables_certificate_verification(self):
        """Managed Valkey o'z CA'si bilan keladi; tekshiruv o'chiriladi."""
        self.assertEqual(
            redis_connection_pool_kwargs("rediss://user:pw@db.example.com:25061/0"),  # secret-scan: allow
            {"ssl_cert_reqs": None},
        )

    def test_an_absent_url_is_handled(self):
        self.assertEqual(redis_connection_pool_kwargs(None), {})
        self.assertEqual(redis_connection_pool_kwargs(""), {})
