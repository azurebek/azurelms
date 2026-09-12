"""Media saqlanishi taxmin emas, o'lchov bo'lishi kerak (A1b deploy blocker).

2026-09-13 deploy oldi auditi topgan **P1**: probe `USE_S3=False` va non-local
profilni ko'rib darhol RED berardi — "production media ephemeral local
filesystemda". O'sha taxmin `deploy/docker-compose.prod.yml` yozilgunga qadar
to'g'ri edi; compose esa media'ni nomli volume ga mount qiladi.

Oqibati: birinchi deploy rejasi aynan `USE_S3=False` + persistent volume, va
`media_storage` `critical` bo'lgani uchun **`/readyz` doim `503`** qaytarardi.
Sayt sog'lom, tashqi uptime tekshiruvi esa instance'ni yaroqsiz deb
hisoblardi.

Nuqson `_media_probe` uchun **birorta test bo'lmagani** uchun o'tib ketgan.
Shu fayl o'sha bo'shliqni yopadi va uchta holatni ham qulflaydi: volume
ulangan, volume unutilgan, konteynerdan tashqarida.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, TestCase, override_settings

from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import _media_probe
from core.storage_persistence import (
    EPHEMERAL,
    HOST_DISK,
    PERSISTENT,
    classify_media_root,
    describe_media_root,
)

DEFINITION = capability_by_slug("media_storage")


class ClassificationTests(SimpleTestCase):
    """Saqlanish uchta kuzatiladigan holatga bo'linadi."""

    def test_outside_a_container_the_disk_is_the_hosts(self):
        with TemporaryDirectory() as tmp:
            missing_marker = str(Path(tmp) / "yoq-dockerenv")

            verdict = classify_media_root(tmp, marker=missing_marker)

        self.assertEqual(verdict, HOST_DISK)

    def test_inside_a_container_a_plain_directory_is_ephemeral(self):
        """Volume unutilgan holat — aynan shu RED bo'lishi kerak."""
        with TemporaryDirectory() as tmp:
            marker = Path(tmp) / ".dockerenv"
            marker.write_text("", encoding="utf-8")
            plain = Path(tmp) / "media"
            plain.mkdir()

            verdict = classify_media_root(plain, marker=str(marker))

        self.assertEqual(verdict, EPHEMERAL)

    def test_inside_a_container_a_mount_point_is_persistent(self):
        """Volume ulangan holat.

        Haqiqiy mount yasab bo'lmaydi (root kerak), shuning uchun mount
        aniqlash funksiyasi almashtiriladi — tekshirilayotgan narsa
        **qaror**, `os.path.ismount` ning o'zi emas.
        """
        from unittest.mock import patch

        with TemporaryDirectory() as tmp:
            marker = Path(tmp) / ".dockerenv"
            marker.write_text("", encoding="utf-8")
            mounted = Path(tmp) / "media"
            mounted.mkdir()

            with patch("core.storage_persistence.is_mount_point", return_value=True):
                verdict = classify_media_root(mounted, marker=str(marker))

        self.assertEqual(verdict, PERSISTENT)

    def test_every_verdict_carries_a_human_note(self):
        with TemporaryDirectory() as tmp:
            verdict, note = describe_media_root(
                tmp, marker=str(Path(tmp) / "yoq")
            )

        self.assertEqual(verdict, HOST_DISK)
        self.assertTrue(note, "izohsiz holat owner uchun ma'nosiz")


class MediaProbeTests(TestCase):
    def _probe(self, **settings_kwargs):
        with override_settings(**settings_kwargs):
            return _media_probe(DEFINITION)

    def test_the_capability_is_readiness_critical(self):
        """Bu testning maqsadi — nima uchun yuqoridagilar muhimligini yozib qo'yish.

        `media_storage` `critical`, ya'ni bu probe RED bo'lsa `/readyz`
        `503` qaytaradi va instance trafikdan chiqadi. Shuning uchun bu
        yerdagi yolg'on RED oddiy noqulaylik emas.
        """
        self.assertEqual(DEFINITION.criticality, "critical")

    def test_local_development_is_green(self):
        result = self._probe(IS_LOCAL=True, USE_S3=False)

        self.assertEqual(result.status, "green")

    def test_production_with_a_persistent_volume_is_green(self):
        """Birinchi deploy rejasi aynan shu: `USE_S3=False` + volume."""
        from unittest.mock import patch

        with patch("core.storage_persistence.in_container", return_value=True), patch(
            "core.storage_persistence.is_mount_point", return_value=True
        ):
            result = self._probe(
                IS_LOCAL=False, USE_S3=False,
                MEDIA_ROOT="/app/media", PRIVATE_MEDIA_ROOT="/app/private-media",
            )

        details = dict(result.details)
        self.assertEqual(result.status, "green")
        self.assertEqual(details["public_persistence"], PERSISTENT)
        self.assertEqual(details["private_persistence"], PERSISTENT)

    def test_production_without_a_volume_is_red(self):
        """Mount unutilgan bo'lsa fayllar haqiqatan yo'qoladi — RED to'g'ri."""
        from unittest.mock import patch

        with patch("core.storage_persistence.in_container", return_value=True), patch(
            "core.storage_persistence.is_mount_point", return_value=False
        ):
            result = self._probe(
                IS_LOCAL=False, USE_S3=False,
                MEDIA_ROOT="/app/media", PRIVATE_MEDIA_ROOT="/app/private-media",
            )

        self.assertEqual(result.status, "red")
        self.assertIn("volume ulanmagan", result.summary)

    def test_production_on_a_plain_vm_is_green(self):
        """Konteynersiz serverda oddiy disk saqlanadi — RED bermaslik kerak."""
        from unittest.mock import patch

        with patch("core.storage_persistence.in_container", return_value=False):
            result = self._probe(
                IS_LOCAL=False, USE_S3=False,
                MEDIA_ROOT="/srv/media", PRIVATE_MEDIA_ROOT="/srv/private",
            )

        self.assertEqual(result.status, "green")
        self.assertEqual(dict(result.details)["public_persistence"], HOST_DISK)

    def test_a_missing_private_volume_is_red_even_when_public_is_mounted(self):
        """PR #111 review: eng nozik fayllar aynan `private-media` da.

        To'lov cheki, vazifa fayli, chat biriktirmasi va speaking audiosi
        ataylab `MEDIA_ROOT` dan tashqarida. Public volume ulanib, private
        mount unutilsa, probe yashil turib ular konteyner bilan birga
        yo'qolardi.
        """
        from unittest.mock import patch

        def only_public_mounted(path):
            return str(path) == "/app/media"

        with patch("core.storage_persistence.in_container", return_value=True), patch(
            "core.storage_persistence.is_mount_point", side_effect=only_public_mounted
        ):
            result = self._probe(
                IS_LOCAL=False, USE_S3=False,
                MEDIA_ROOT="/app/media", PRIVATE_MEDIA_ROOT="/app/private-media",
            )

        self.assertEqual(result.status, "red")
        self.assertIn("private", result.summary)

    def test_s3_still_checks_the_private_root(self):
        """`USE_S3=True` faqat **public** media'ni uzoqqa ko'chiradi.

        Private media dizayn bo'yicha lokal diskda qoladi va Django view
        orqali beriladi. Ilgari S3 rejimida probe uni umuman tekshirmay
        yashil qaytarardi.
        """
        from unittest.mock import patch

        with patch("core.storage_persistence.in_container", return_value=True), patch(
            "core.storage_persistence.is_mount_point", return_value=False
        ):
            result = self._probe(
                IS_LOCAL=False, USE_S3=True, AWS_DEFAULT_ACL=None,
                PRIVATE_MEDIA_ROOT="/app/private-media",
            )

        self.assertEqual(result.status, "red")
        self.assertIn("private", result.summary)

    def test_s3_with_a_mounted_private_volume_is_green(self):
        from unittest.mock import patch

        with patch("core.storage_persistence.in_container", return_value=True), patch(
            "core.storage_persistence.is_mount_point", return_value=True
        ):
            result = self._probe(
                IS_LOCAL=False, USE_S3=True, AWS_DEFAULT_ACL=None,
                PRIVATE_MEDIA_ROOT="/app/private-media",
            )

        self.assertEqual(result.status, "green")

    def test_public_read_s3_is_still_red(self):
        """Eski himoya buzilmasligi kerak — private fayllar uchun xavfli."""
        result = self._probe(
            IS_LOCAL=False, USE_S3=True, AWS_DEFAULT_ACL="public-read"
        )

        self.assertEqual(result.status, "red")
        self.assertIn("public-read", result.summary)

    def test_private_s3_is_green(self):
        result = self._probe(IS_LOCAL=False, USE_S3=True, AWS_DEFAULT_ACL=None)

        self.assertEqual(result.status, "green")


class ReadinessTests(TestCase):
    """Blocker'ning o'zi: `/readyz` deploy sozlamasida `503` bermasligi kerak."""

    def test_readyz_is_healthy_with_the_planned_deploy_shape(self):
        from unittest.mock import patch

        with patch("core.storage_persistence.in_container", return_value=True), patch(
            "core.storage_persistence.is_mount_point", return_value=True
        ):
            with override_settings(
                IS_LOCAL=False, USE_S3=False,
                MEDIA_ROOT="/app/media", PRIVATE_MEDIA_ROOT="/app/private-media",
            ):
                result = _media_probe(DEFINITION)

        self.assertNotEqual(
            result.status, "red", "`/readyz` shu sababli 503 qaytarardi"
        )
