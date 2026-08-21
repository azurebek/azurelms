"""A1a — takrorlanadigan local zaxira va tiklash.

Asosiy da'vo: oddiy fayl nusxasi yetarli emas. `db.sqlite3` WAL rejimida
ishlaydi (A8 concurrency tuzatishidan keyin), WAL'da esa so'nggi commitlar
hali asosiy faylga ko'chmagan bo'lishi mumkin — ular yonidagi `-wal` faylida
turadi. O'sha paytda faylni `copy` qilsangiz, nusxada eng oxirgi yozuvlar
bo'lmaydi va buni faqat tiklaganda bilib qolasiz.

Shuning uchun quyidagi testlardan eng muhimi — `VACUUM INTO` bilan olingan
zaxira WAL'dagi commitni ham qamrab olishini ko'rsatuvchi test: u yonida
xuddi shu paytdagi xom fayl nusxasi bilan solishtiriladi.

WAL'ga bog'liq testlar fayl bazasini talab qiladi:

    AZURELMS_TEST_FILE_DB=1 python manage.py test core.test_backup_restore
"""

import shutil
import sqlite3
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.db import connection
from django.test import TransactionTestCase

from core.backup_service import BackupError, create_backup, restore_backup
from core.qa_support import skip_unless_file_backed_db, skip_unless_sqlite

User = get_user_model()


def _count_users(db_path):
    """Zaxira faylidagi foydalanuvchilar soni — Django'dan mustaqil o'qiladi."""
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute("SELECT COUNT(*) FROM users_customuser").fetchone()[0]
    finally:
        conn.close()


class BackupRestoreTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        # Zaxira `VACUUM INTO` ga quriladi va servis SQLite'dan boshqa backendni
        # ataylab rad etadi; CI'ning PostgreSQL ishida bu testlar skip bo'ladi.
        skip_unless_sqlite(self)
        skip_unless_file_backed_db(self)
        self.workdir = Path(tempfile.mkdtemp(prefix="azurelms-backup-test-"))
        self.addCleanup(shutil.rmtree, self.workdir, ignore_errors=True)
        User.objects.all().delete()

    def _make_users(self, count, prefix):
        for index in range(count):
            User.objects.create_user(
                username=f"{prefix}{index}",
                email=f"{prefix}{index}@t.uz",
                password="pass-12345",
            )

    # --- zaxira ------------------------------------------------------------

    def test_backup_is_readable_and_passes_integrity_check(self):
        self._make_users(3, "bk")
        target = create_backup(self.workdir / "snapshot.sqlite3")

        self.assertTrue(target.exists())
        self.assertEqual(_count_users(target), 3)

    def test_backup_captures_commits_that_a_plain_file_copy_would_miss(self):
        """WAL: `VACUUM INTO` so'nggi commitni oladi, xom nusxa olmasligi mumkin."""
        self._make_users(2, "wal")

        raw_copy = self.workdir / "raw-copy.sqlite3"
        shutil.copyfile(connection.settings_dict["NAME"], raw_copy)
        proper = create_backup(self.workdir / "proper.sqlite3")

        self.assertEqual(_count_users(proper), 2)
        # Xom nusxa ko'pi bilan shuncha ko'radi; WAL hali checkpoint bo'lmagan
        # bo'lsa kamroq. Zaxira esa hech qachon kamroq ko'rmasligi kerak.
        self.assertGreaterEqual(_count_users(proper), _count_users(raw_copy))

    def test_backup_refuses_to_overwrite_an_existing_file(self):
        target = self.workdir / "busy.sqlite3"
        target.write_bytes(b"")
        with self.assertRaises(BackupError):
            create_backup(target)

    # --- tiklash -----------------------------------------------------------

    def test_restore_brings_back_the_snapshot_state(self):
        self._make_users(2, "before")
        snapshot = create_backup(self.workdir / "before.sqlite3")

        self._make_users(3, "after")
        self.assertEqual(User.objects.count(), 5)

        restore_backup(snapshot)
        self.assertEqual(User.objects.count(), 2)
        self.assertTrue(User.objects.filter(username="before0").exists())
        self.assertFalse(User.objects.filter(username="after0").exists())

    def test_restore_rejects_a_corrupt_snapshot_without_touching_the_database(self):
        self._make_users(2, "safe")
        corrupt = self.workdir / "corrupt.sqlite3"
        corrupt.write_bytes(b"bu SQLite fayl emas")

        with self.assertRaises(BackupError):
            restore_backup(corrupt)
        self.assertEqual(User.objects.count(), 2)

    def test_restore_rejects_a_missing_file(self):
        with self.assertRaises(BackupError):
            restore_backup(self.workdir / "yoq.sqlite3")

    # --- buyruq qobig'i ----------------------------------------------------

    def test_backup_command_writes_a_file(self):
        target = self.workdir / "via-command.sqlite3"
        call_command("backup_db", output=str(target))
        self.assertTrue(target.exists())

    def test_restore_command_requires_explicit_confirmation(self):
        """Joriy bazani ustidan yozadigan amal tasodifan bajarilmasligi kerak."""
        snapshot = create_backup(self.workdir / "confirm.sqlite3")
        with self.assertRaises(CommandError):
            call_command("restore_db", input=str(snapshot))

        # `--yes` bilan o'tadi.
        call_command("restore_db", input=str(snapshot), yes=True)


class RestoreDrillTests(TransactionTestCase):
    """`--into` — zaxirani **alohida** faylga tiklash (A2 restore drill).

    Ilgari `restore_db` faqat joriy bazani ustidan yozardi. Ya'ni zaxirani
    sinab ko'rishning yagona yo'li ishlayotgan bazani almashtirish edi va
    hech kim buni qilmasdi. Hech qachon tiklanmagan zaxira — umid, zaxira emas.
    """

    def setUp(self):
        skip_unless_sqlite(self)
        # `create_backup` `VACUUM INTO` ishlatadi — xotiradagi bazada ishlamaydi.
        # Mavjud WAL testlari ham shu sababdan fayl bazasini talab qiladi.
        skip_unless_file_backed_db(self)
        self.tmp = Path(tempfile.mkdtemp())
        self.source = self.tmp / "snapshot.sqlite3"
        create_backup(self.source)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_restore_into_an_isolated_target_leaves_the_live_database_alone(self):
        User.objects.create_user(
            username="zaxiradan-keyin", email="keyin@example.com", password="testpass123"
        )
        before = User.objects.count()

        target = restore_backup(self.source, into=self.tmp / "drill.sqlite3")

        self.assertTrue(target.exists())
        self.assertEqual(
            User.objects.count(), before,
            "drill joriy bazaga tegmasligi kerak — aks holda uni hech kim qilmaydi",
        )

    def test_restore_into_refuses_to_overwrite_an_existing_file(self):
        target = self.tmp / "band.sqlite3"
        target.write_bytes(b"tegilmasin")

        with self.assertRaises(BackupError):
            restore_backup(self.source, into=target)
        self.assertEqual(target.read_bytes(), b"tegilmasin")

    def test_restore_into_refuses_to_target_the_live_database(self):
        """Aks holda «drill» yashiringan destruktiv tiklash bo'lib qolardi.

        Xabar aynan shu holatni ko'rsatishi tekshiriladi: joriy baza fayli
        mavjud bo'lgani uchun umumiy "fayl allaqachon bor" tekshiruvi ham
        xato beradi, ya'ni faqat `assertRaises` himoyani isbotlamaydi —
        u olib tashlanganda ham test o'tib ketardi.
        """
        live = Path(connection.settings_dict["NAME"])

        with self.assertRaises(BackupError) as caught:
            restore_backup(self.source, into=live)

        self.assertIn(
            "--into", str(caught.exception),
            "xato joriy bazaga qaratilganini aytishi kerak, shunchaki «fayl bor» emas",
        )

    def test_restore_into_rejects_a_corrupt_source_before_writing(self):
        broken = self.tmp / "buzuq.sqlite3"
        broken.write_bytes(b"bu sqlite emas")
        target = self.tmp / "chiqish.sqlite3"

        with self.assertRaises(BackupError):
            restore_backup(broken, into=target)
        self.assertFalse(target.exists(), "buzuq manbadan hech narsa yozilmasligi kerak")

    def test_drill_reports_the_schema_state_of_the_restored_copy(self):
        """Drill nafaqat nusxa oladi — tiklangan nusxa sxemasini ham ko'rsatadi."""
        from core.backup_service import describe_sqlite

        target = restore_backup(self.source, into=self.tmp / "drill.sqlite3")
        report = describe_sqlite(target)

        self.assertEqual(report["integrity"], "ok")
        self.assertGreater(report["tables"], 0)
        self.assertGreater(report["migrations"], 0)
        self.assertTrue(report["latest_migration"])


class RestoreDrillCommandTests(TransactionTestCase):
    def setUp(self):
        skip_unless_sqlite(self)
        # `create_backup` `VACUUM INTO` ishlatadi — xotiradagi bazada ishlamaydi.
        # Mavjud WAL testlari ham shu sababdan fayl bazasini talab qiladi.
        skip_unless_file_backed_db(self)
        self.tmp = Path(tempfile.mkdtemp())
        self.source = self.tmp / "snapshot.sqlite3"
        create_backup(self.source)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_into_does_not_require_confirmation(self):
        """`--yes` joriy bazani yo'qotishga rozilik; drill hech narsa yo'qotmaydi."""
        target = self.tmp / "drill.sqlite3"

        call_command("restore_db", input=str(self.source), into=str(target))

        self.assertTrue(target.exists())

    def test_without_into_confirmation_is_still_required(self):
        with self.assertRaises(CommandError):
            call_command("restore_db", input=str(self.source))
