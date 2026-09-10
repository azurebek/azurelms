"""Production runtime gate testlari.

Ikki qatlamda tekshiriladi:

1. **Sof mantiq** — `core/runtime_gate.py` funksiyalari. Tez, va gate'ning
   qaysi holatda ishlashini aniq yozib qo'yadi.
2. **Haqiqiy settings** — alohida processda `manage.py check`. Bu qatlam
   ataylab qo'shildi: mantiq to'g'ri bo'lib, `core/settings.py` uni chaqirmay
   qo'yishi mumkin, va o'shanda test yashil bo'lib turgan holda server jim
   ko'tarilib ketardi. Subprocess ishlatiladi, chunki settings modul
   darajasida bir marta yuklanadi — `override_settings` uni qayta
   hisoblamaydi.
"""

import subprocess
import sys

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from core.runtime_gate import (
    IN_MEMORY_BROKER,
    collect_service_problems,
    enforce_remote_services,
    is_local_profile,
    resolve_broker_url,
)


class RuntimeGateLogicTests(SimpleTestCase):
    def test_local_profile_allows_in_memory_fallbacks(self):
        """Lokal ishlab chiqish tashqi xizmatsiz ishlashda davom etsin."""
        problems = collect_service_problems(
            app_env="local", cache_url="", broker_url=IN_MEMORY_BROKER
        )
        self.assertEqual(problems, [])

    def test_non_local_without_cache_and_broker_reports_both(self):
        """Ikkala muammo birdaniga aytiladi — bittalab aylanish bo'lmasin."""
        problems = collect_service_problems(
            app_env="production", cache_url="", broker_url=IN_MEMORY_BROKER
        )
        self.assertEqual(len(problems), 2)
        self.assertIn("VALKEY_URL", problems[0])
        self.assertIn("CELERY_BROKER_URL", problems[1])

    def test_non_local_with_real_services_passes(self):
        problems = collect_service_problems(
            app_env="production",
            cache_url="redis://cache:6379/0",
            broker_url="redis://cache:6379/0",
        )
        self.assertEqual(problems, [])

    def test_enforce_raises_with_every_problem_listed(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            enforce_remote_services(
                app_env="staging", cache_url="", broker_url=""
            )
        message = str(ctx.exception)
        self.assertIn("staging", message)
        self.assertIn("VALKEY_URL", message)
        self.assertIn("CELERY_BROKER_URL", message)

    def test_local_use_remote_services_does_not_disable_the_gate(self):
        """`LOCAL_USE_REMOTE_SERVICES` lokal profilga xizmat qo'shadi, gate'ni
        o'chirmaydi — CI'ning PostgreSQL+Valkey ishi aynan shu holatda."""
        self.assertTrue(is_local_profile("local"))
        self.assertFalse(is_local_profile("production"))
        self.assertFalse(is_local_profile("ci"))

    def test_broker_resolution_prefers_explicit_value(self):
        self.assertEqual(
            resolve_broker_url(
                app_env="production",
                explicit_broker="redis://ochiq:6379/2",
                remote_redis_url="redis://cache:6379/0",
                local_use_remote_services=False,
            ),
            "redis://ochiq:6379/2",
        )

    def test_broker_resolution_local_default_is_in_memory(self):
        self.assertEqual(
            resolve_broker_url(
                app_env="local",
                explicit_broker=None,
                remote_redis_url=None,
                local_use_remote_services=False,
            ),
            IN_MEMORY_BROKER,
        )

    def test_broker_resolution_non_local_falls_back_to_shared_redis(self):
        self.assertEqual(
            resolve_broker_url(
                app_env="production",
                explicit_broker=None,
                remote_redis_url="redis://cache:6379/0",
                local_use_remote_services=False,
            ),
            "redis://cache:6379/0",
        )

    def test_broker_resolution_non_local_without_redis_stays_catchable(self):
        """Redis'siz non-local `memory://` qaytaradi — jim `None` emas.

        Shu qiymat gate'ga kirib xato beradi. `None` qaytarilsa Celery o'zining
        default `amqp://localhost` iga tushib, mavjud bo'lmagan RabbitMQ'ga
        ulanishga urinib turardi.
        """
        self.assertEqual(
            resolve_broker_url(
                app_env="production",
                explicit_broker=None,
                remote_redis_url=None,
                local_use_remote_services=False,
            ),
            IN_MEMORY_BROKER,
        )


class SettingsWiringTests(SimpleTestCase):
    """Gate haqiqiy `core/settings.py` da ulanganini tekshiradi."""

    BASE_ENV = {
        "AZURELMS_SKIP_ENV_FILE": "1",
        "DJANGO_SETTINGS_MODULE": "core.settings",
        "SECRET_KEY": "test-only-placeholder-key-long-enough-000000000000",
        # Soxta qiymat: subprocess hech qayerga ulanmaydi, `manage.py check`
        # faqat konfiguratsiyani o‘qiydi.
        "DATABASE_URL": "postgresql://u:p@db:5432/azurelms",  # secret-scan: allow
        "APP_DOMAIN": "lms.invalid",
        "GEMINI_API_KEY": "",
        "TELEGRAM_BOT_TOKEN": "",
    }

    def _run_check(self, **extra_env):
        env = dict(self.BASE_ENV)
        env.update(extra_env)
        # `PATH`/`SYSTEMROOT` bo'lmasa Windowsda process umuman ko'tarilmaydi.
        import os

        for name in ("PATH", "SYSTEMROOT", "SystemRoot", "TEMP", "TMP", "COMSPEC"):
            if name in os.environ:
                env.setdefault(name, os.environ[name])
        return subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=str(settings.BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )

    def test_local_profile_boots_without_redis(self):
        result = self._run_check(APP_ENV="local")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_production_without_redis_refuses_to_boot(self):
        result = self._run_check(APP_ENV="production", DEBUG="False")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("ImproperlyConfigured", result.stderr)
        self.assertIn("VALKEY_URL", result.stderr)

    def test_production_with_redis_boots(self):
        result = self._run_check(
            APP_ENV="production",
            DEBUG="False",
            VALKEY_URL="redis://cache:6379/0",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_celery_broker_url_is_exported_by_settings(self):
        """Broker settingsda hisoblanadi va `core/celery.py` shundan oladi."""
        self.assertTrue(hasattr(settings, "CELERY_BROKER_URL"))
        from core.celery import app

        self.assertEqual(app.conf.broker_url, settings.CELERY_BROKER_URL)


class ObjectStorageSettingsTests(SimpleTestCase):
    """`USE_S3` bloki AWS S3 bilan ham ishlashini tekshiradi.

    Ilgari bu blok DigitalOcean Spaces'ga qattiq bog'langan edi: region
    literal `'fra1'` bo'lib, `AWS_S3_ENDPOINT_URL` bo'sh bo'lsa
    `None.replace(...)` bilan settings import paytidayoq `AttributeError`
    berardi — ya'ni haqiqiy AWS S3 bilan loyiha umuman ko'tarilmasdi.
    """

    def _dump_storage_settings(self, **extra_env):
        import json
        import os

        env = dict(SettingsWiringTests.BASE_ENV)
        env.update(
            {
                "APP_ENV": "production",
                "DEBUG": "False",
                "VALKEY_URL": "redis://cache:6379/0",
                "USE_S3": "1",
            }
        )
        env.update(extra_env)
        for name in ("PATH", "SYSTEMROOT", "SystemRoot", "TEMP", "TMP", "COMSPEC"):
            if name in os.environ:
                env.setdefault(name, os.environ[name])
        script = (
            "import django, json;"
            "django.setup();"
            "from django.conf import settings as s;"
            "print(json.dumps({"
            "'region': s.AWS_S3_REGION_NAME,"
            "'endpoint': s.AWS_S3_ENDPOINT_URL,"
            "'custom_domain': s.AWS_S3_CUSTOM_DOMAIN,"
            "'acl': s.AWS_DEFAULT_ACL,"
            "'object_parameters': s.AWS_S3_OBJECT_PARAMETERS,"
            "'media_url': s.MEDIA_URL}))"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(settings.BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_plain_aws_bucket_needs_no_endpoint(self):
        config = self._dump_storage_settings(
            AWS_STORAGE_BUCKET_NAME="azurelms-media",
            AWS_REGION="eu-central-1",
        )
        self.assertEqual(config["region"], "eu-central-1")
        self.assertIsNone(config["endpoint"])
        # Custom domen yo'q — django-storages regional manzilni o'zi quradi.
        self.assertIsNone(config["custom_domain"])
        self.assertEqual(
            config["media_url"],
            "https://azurelms-media.s3.eu-central-1.amazonaws.com/media/",
        )

    def test_aws_upload_sends_no_acl_by_default(self):
        """ACL default `None`.

        Yangi AWS bucketlarida Object Ownership "Bucket owner enforced"
        bo'lib, ACL yuborilgan har qanday PUT `AccessControlListNotSupported`
        (400) bilan rad etiladi — ya'ni har bir upload yiqilardi.
        """
        config = self._dump_storage_settings(
            AWS_STORAGE_BUCKET_NAME="azurelms-media",
            AWS_REGION="eu-central-1",
        )
        self.assertIsNone(config["acl"])
        self.assertNotIn("ACL", config["object_parameters"])

    def test_s3_compatible_endpoint_still_supported(self):
        """DigitalOcean Spaces yo'li o'chib qolmagan."""
        config = self._dump_storage_settings(
            AWS_STORAGE_BUCKET_NAME="azurelms-media",
            AWS_S3_ENDPOINT_URL="https://fra1.digitaloceanspaces.com",
            AWS_DEFAULT_ACL="public-read",
        )
        self.assertEqual(
            config["custom_domain"], "azurelms-media.fra1.digitaloceanspaces.com"
        )
        self.assertEqual(config["object_parameters"].get("ACL"), "public-read")

    def test_bucket_without_region_or_endpoint_is_refused(self):
        """Yarim sozlangan storage jim ishlamasin."""
        import os

        env = dict(SettingsWiringTests.BASE_ENV)
        env.update(
            {
                "APP_ENV": "production",
                "DEBUG": "False",
                "VALKEY_URL": "redis://cache:6379/0",
                "USE_S3": "1",
                "AWS_STORAGE_BUCKET_NAME": "azurelms-media",
            }
        )
        for name in ("PATH", "SYSTEMROOT", "SystemRoot", "TEMP", "TMP", "COMSPEC"):
            if name in os.environ:
                env.setdefault(name, os.environ[name])
        result = subprocess.run(
            [sys.executable, "manage.py", "check"],
            cwd=str(settings.BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("AWS_S3_REGION_NAME", result.stderr)
