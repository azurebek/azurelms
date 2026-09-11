"""Media zaxirasi testlari (A1b).

Zaxirani olish oson tekshiriladi; bu yerdagi testlarning ko'pi **tiklash**
xavfsizligi haqida, chunki aynan shu yo'lda xato qaytarib bo'lmaydigan
zarar beradi:

* private fayl public ildizga tushib qolsa, har bir to'lov cheki
  tekshiruvsiz tarqatiladigan URL bo'lib qoladi (A0b bekor bo'ladi);
* tar ichidagi `..` nomi arxivni papkadan tashqariga yozdira oladi;
* "mashq" joriy media ildizining ichiga chiqarilsa, u yashiringan
  destruktiv tiklash bo'lib qoladi.
"""

import tarfile
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import _backup_probe, _media_backup_probe
from core.media_backup import (
    MediaBackupError,
    create_media_backup,
    describe_media_archive,
    live_media_counts,
    media_roots,
    restore_media_backup,
    verify_media_archive,
)


class MediaBackupTestBase(SimpleTestCase):
    """Vaqtinchalik public/private ildizlar bilan izolyatsiya."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="azurelms-media-test-"))
        self.addCleanup(self._cleanup)
        self.public = self.tmp / "media"
        self.private = self.tmp / "private-media"
        (self.public / "avatars").mkdir(parents=True)
        (self.private / "receipts").mkdir(parents=True)
        (self.public / "avatars" / "user.jpg").write_bytes(b"public-avatar")
        (self.private / "receipts" / "chek.png").write_bytes(b"private-receipt")
        (self.private / "receipts" / "chek2.png").write_bytes(b"private-receipt-2")

        patcher = override_settings(
            MEDIA_ROOT=str(self.public), PRIVATE_MEDIA_ROOT=str(self.private)
        )
        patcher.enable()
        self.addCleanup(patcher.disable)

    def _cleanup(self):
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _archive(self, name="media.tar.gz"):
        return create_media_backup(self.tmp / name)


class MediaBackupCreationTests(MediaBackupTestBase):
    def test_archive_keeps_public_and_private_in_separate_sections(self):
        """Aralashtirilsa tiklashda chek public `/media/` ostiga tushib qolardi."""
        archive = self._archive()
        with tarfile.open(archive, "r:gz") as handle:
            names = [m.name for m in handle.getmembers() if m.isfile()]
        self.assertIn("public/avatars/user.jpg", names)
        self.assertIn("private/receipts/chek.png", names)
        # Bitta ham fayl prefikssiz qolmasligi kerak.
        for name in names:
            self.assertRegex(name, r"^(public|private)/")

    def test_counts_are_reported_per_section(self):
        counts = describe_media_archive(self._archive())
        self.assertEqual(counts["public"], 1)
        self.assertEqual(counts["private"], 2)
        self.assertEqual(counts["total"], 3)

    def test_refuses_to_overwrite_an_existing_archive(self):
        target = self.tmp / "media.tar.gz"
        target.write_bytes(b"eski")
        with self.assertRaises(MediaBackupError):
            create_media_backup(target)
        self.assertEqual(target.read_bytes(), b"eski")

    def test_s3_public_media_leaves_only_the_private_section(self):
        """`USE_S3=True` da `MEDIA_ROOT` bo'sh; private media baribir diskda."""
        with override_settings(MEDIA_ROOT=""):
            self.assertEqual(
                [section for section, _ in media_roots()], ["private"]
            )
            counts = describe_media_archive(self._archive("faqat-private.tar.gz"))
        self.assertEqual(counts["public"], 0)
        self.assertEqual(counts["private"], 2)

    def test_no_media_root_at_all_is_an_error_not_an_empty_archive(self):
        """Bo'sh arxiv "zaxira bor" deb hisoblanmasin."""
        with override_settings(MEDIA_ROOT="", PRIVATE_MEDIA_ROOT=""):
            with self.assertRaises(MediaBackupError) as ctx:
                create_media_backup(self.tmp / "bosh.tar.gz")
        self.assertIn("topilmadi", str(ctx.exception))

    def test_live_counts_match_the_archive(self):
        live = live_media_counts()
        self.assertEqual(live["public"], 1)
        self.assertEqual(live["private"], 2)


class MediaArchiveVerificationTests(MediaBackupTestBase):
    def test_truncated_archive_is_detected(self):
        """Disk to'lganda yarim yozilgan arxiv qolishi mumkin."""
        archive = self._archive()
        raw = archive.read_bytes()
        archive.write_bytes(raw[: len(raw) // 2])
        self.assertNotEqual(verify_media_archive(archive), "ok")

    def test_non_archive_file_is_detected(self):
        broken = self.tmp / "broken.tar.gz"
        broken.write_bytes(b"bu tar.gz emas")
        self.assertNotEqual(verify_media_archive(broken), "ok")

    def test_archive_without_files_is_not_accepted(self):
        empty = self.tmp / "empty.tar.gz"
        with tarfile.open(empty, "w:gz"):
            pass
        self.assertIn("bitta ham fayl", verify_media_archive(empty))


class MediaRestoreDrillTests(MediaBackupTestBase):
    def test_drill_restores_into_a_separate_directory(self):
        archive = self._archive()
        target, restored = restore_media_backup(archive, self.tmp / "mashq")
        self.assertEqual(restored["public"], 1)
        self.assertEqual(restored["private"], 2)
        self.assertTrue((Path(target) / "public" / "avatars" / "user.jpg").exists())
        self.assertTrue((Path(target) / "private" / "receipts" / "chek.png").exists())
        # Joriy ildizlar tegilmagan.
        self.assertTrue((self.public / "avatars" / "user.jpg").exists())
        self.assertEqual(live_media_counts()["total"], 3)

    def test_private_files_never_land_in_the_public_section(self):
        """A0b ning butun ma'nosi shu: chek public ildizda bo'lmasligi kerak."""
        target, _ = restore_media_backup(self._archive(), self.tmp / "mashq")
        public_names = [
            p.name for p in (Path(target) / "public").rglob("*") if p.is_file()
        ]
        self.assertNotIn("chek.png", public_names)
        self.assertNotIn("chek2.png", public_names)

    def test_refuses_to_restore_inside_the_live_media_root(self):
        """Aks holda "mashq" yashiringan destruktiv tiklash bo'lardi."""
        archive = self._archive()
        for inside in (self.public, self.public / "mashq", self.private / "mashq"):
            with self.assertRaises(MediaBackupError) as ctx:
                restore_media_backup(archive, inside)
            self.assertIn("mashq emas", str(ctx.exception))

    def test_refuses_a_non_empty_target(self):
        archive = self._archive()
        target = self.tmp / "band"
        target.mkdir()
        (target / "allaqachon.txt").write_text("bor")
        with self.assertRaises(MediaBackupError) as ctx:
            restore_media_backup(archive, target)
        self.assertIn("bo'sh emas", str(ctx.exception))

    def test_in_place_restore_is_refused_with_a_reason(self):
        with self.assertRaises(MediaBackupError) as ctx:
            restore_media_backup(self._archive(), into=None)
        self.assertIn("--into", str(ctx.exception))

    def test_missing_and_corrupt_archives_are_refused_before_extracting(self):
        with self.assertRaises(MediaBackupError):
            restore_media_backup(self.tmp / "yoq.tar.gz", self.tmp / "m1")
        broken = self.tmp / "broken.tar.gz"
        broken.write_bytes(b"tar emas")
        with self.assertRaises(MediaBackupError):
            restore_media_backup(broken, self.tmp / "m2")
        self.assertFalse((self.tmp / "m2" / "public").exists())

    def test_path_traversal_member_cannot_escape_the_target(self):
        """Tar ichidagi `..` nomi papkadan tashqariga yozdira olmaydi.

        Arxivni o'zimiz yozgan bo'lsak ham filtr qo'yiladi: tiklanadigan fayl
        har doim o'zimizning arxividan kelishiga ishonib bo'lmaydi (masalan
        offsite nusxadan qaytarilgan fayl).
        """
        evil = self.tmp / "evil.tar.gz"
        with tarfile.open(evil, "w:gz") as handle:
            payload = b"qochgan"
            for name in ("public/ok.txt", "../qochdi.txt"):
                info = tarfile.TarInfo(name=name)
                info.size = len(payload)
                import io

                handle.addfile(info, io.BytesIO(payload))

        target = self.tmp / "mashq-evil"
        with self.assertRaises(MediaBackupError) as ctx:
            restore_media_backup(evil, target)
        # Sababi aynan filtr bo'lishi kerak, tasodifiy boshqa xato emas.
        self.assertIn("chiqarib bo'lmadi", str(ctx.exception))
        self.assertIsInstance(ctx.exception.__cause__, tarfile.FilterError)
        # Eng muhimi: tashqariga hech narsa yozilmagan.
        self.assertFalse((self.tmp / "qochdi.txt").exists())


class MediaBackupCommandTests(MediaBackupTestBase):
    def test_backup_then_drill_through_the_commands(self):
        archive = self.tmp / "cli.tar.gz"
        call_command("backup_media", "--output", str(archive))
        self.assertTrue(archive.exists())
        call_command("restore_media", "--input", str(archive), "--into", str(self.tmp / "cli-mashq"))
        self.assertTrue((self.tmp / "cli-mashq" / "private" / "receipts" / "chek.png").exists())

    def test_restore_command_requires_into(self):
        """`--into` siz chaqirish umuman mumkin emas."""
        archive = self.tmp / "cli.tar.gz"
        call_command("backup_media", "--output", str(archive))
        with self.assertRaises(CommandError):
            call_command("restore_media", "--input", str(archive))


class MediaBackupProbeTests(TestCase):
    """Control Center media zaxirasini alohida chiroq bilan ko'rsatadi."""

    def setUp(self):
        self.definition = capability_by_slug("media_backup")

    def _probe_with(self, names, ages=None):
        import os

        ages = ages or [0] * len(names)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "backups").mkdir()
            for name, age in zip(names, ages):
                path = root / "backups" / name
                path.write_bytes(b"x" * 1024)
                stamp = (timezone.now() - timezone.timedelta(days=age)).timestamp()
                os.utime(path, (stamp, stamp))
            with override_settings(BASE_DIR=root):
                return _media_backup_probe(self.definition), _backup_probe(self.definition)

    def test_no_media_archive_is_not_green(self):
        media, _ = self._probe_with([])
        self.assertNotEqual(media.status, "green")

    def test_a_fresh_media_archive_is_green(self):
        media, _ = self._probe_with(["media-20260911.tar.gz"])
        self.assertEqual(media.status, "green")

    def test_a_stale_media_archive_is_amber(self):
        media, _ = self._probe_with(["media-20260801.tar.gz"], ages=[30])
        self.assertEqual(media.status, "amber")

    def test_a_database_dump_alone_does_not_make_the_media_light_green(self):
        """Aks holda "baza qaytdi, cheklar qaytmadi" holati ko'rinmay ketardi."""
        media, database = self._probe_with(["db-20260911.dump"])
        self.assertEqual(database.status, "green")
        self.assertNotEqual(media.status, "green")

    def test_a_media_archive_alone_does_not_make_the_database_light_green(self):
        media, database = self._probe_with(["media-20260911.tar.gz"])
        self.assertEqual(media.status, "green")
        self.assertNotEqual(database.status, "green")
