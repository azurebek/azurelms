"""PostgreSQL zaxira/tiklash testlari (A1b).

Ikki qatlam:

1. **Backendsiz** — buyruq qurilishi va parol uzatilishi. Har joyda yuguradi,
   `pg_dump` o'rnatilmagan mashinada ham (`shutil.which` patch qilinadi).
2. **Haqiqiy PostgreSQL** — dump → tekshiruv → alohida bazaga drill →
   sxema hisoboti. Ishlab chiqish mashinasida PostgreSQL yo'q, shuning uchun
   bu qatlam lokalda **skip** bo'ladi va dalil CI ning `integration` ishidan
   keladi. Skip sababi matnli — "0 test yugurdi" jimgina "yashil" ga
   aylanmasin.
"""

import os
import uuid
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TransactionTestCase

from core import pg_backup
from core.backup_service import (
    BackupError,
    create_backup,
    default_backup_suffix,
    describe_backup,
    is_postgres,
    restore_backup,
)
from core.qa_support import skip_unless_postgres

FAKE_PARAMS = {
    "name": "azurelms",
    "user": "azurelms",
    "password": "juda-maxfiy",
    "host": "db",
    "port": "5432",
}


class CommandBuildingTests(SimpleTestCase):
    """Buyruq qurilishi — haqiqiy `pg_dump` shart emas."""

    def setUp(self):
        patcher = mock.patch.object(
            pg_backup.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_dump_uses_custom_format(self):
        """`-Fc` — tanlab tiklash mumkin va fayl siqiladi."""
        argv = pg_backup.build_dump_command(FAKE_PARAMS, "/backups/x.dump")
        self.assertIn("--format=custom", argv)
        self.assertIn("--no-owner", argv)
        self.assertIn("/backups/x.dump", argv)

    def test_password_never_reaches_the_command_line(self):
        """Parol `PGPASSWORD` da bo'lishi shart.

        Buyruq qatoriga qo'yilsa u `ps` chiqishida va shell tarixida ko'rinib
        qolardi — bitta `docker compose exec` bilan boshqa jarayon uni
        o'qiy olardi.
        """
        argv = pg_backup.build_dump_command(FAKE_PARAMS, "/backups/x.dump")
        self.assertNotIn(FAKE_PARAMS["password"], " ".join(argv))

        env = pg_backup._env_with_password(FAKE_PARAMS["password"])
        self.assertEqual(env["PGPASSWORD"], FAKE_PARAMS["password"])

    def test_empty_password_sets_no_variable(self):
        """Parolsiz ulanishda `PGPASSWORD=''` qoldirilmaydi."""
        env = pg_backup._env_with_password("")
        self.assertNotIn("PGPASSWORD", {k: v for k, v in env.items() if k == "PGPASSWORD"})

    def test_restore_targets_the_named_database(self):
        argv = pg_backup.build_restore_command(FAKE_PARAMS, "/backups/x.dump", "drill_db")
        self.assertIn("--dbname", argv)
        self.assertEqual(argv[argv.index("--dbname") + 1], "drill_db")

    def test_missing_tool_is_reported_clearly(self):
        with mock.patch.object(pg_backup.shutil, "which", return_value=None):
            with self.assertRaises(pg_backup.PgToolMissing) as ctx:
                pg_backup.build_dump_command(FAKE_PARAMS, "/backups/x.dump")
        self.assertIn("postgresql-client", str(ctx.exception))


class BackendDispatchTests(SimpleTestCase):
    """`core/backup_service.py` backendni to'g'ri tanlaydimi."""

    def test_suffix_follows_the_backend(self):
        """Fayl nomi backendni aytib tursin.

        `.dump` faylni SQLite deb ochishga urinish chalkash xato beradi, va
        aksincha — operator falokat kunida shu bilan vaqt yo'qotardi.
        """
        expected = ".dump" if connection.vendor == "postgresql" else ".sqlite3"
        self.assertEqual(default_backup_suffix(), expected)

    def test_is_postgres_matches_the_connection(self):
        self.assertEqual(is_postgres(), connection.vendor == "postgresql")


class PostgresBackupTests(TransactionTestCase):
    """Haqiqiy `pg_dump`/`pg_restore` yo'li."""

    def setUp(self):
        skip_unless_postgres(self)
        self.tmp = Path(os.environ.get("TEMP") or "/tmp") / f"azurelms-pg-{uuid.uuid4().hex[:8]}"
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.drill_databases = []
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        params = pg_backup.connection_params()
        for name in self.drill_databases:
            pg_backup.drop_database(params, name)
        for item in self.tmp.glob("*"):
            item.unlink(missing_ok=True)
        self.tmp.rmdir()

    def _drill_name(self):
        name = f"azurelms_drill_{uuid.uuid4().hex[:10]}"
        self.drill_databases.append(name)
        return name

    def test_backup_is_written_and_readable(self):
        target = self.tmp / "snapshot.dump"
        written = create_backup(target)
        self.assertTrue(Path(written).exists())
        self.assertGreater(Path(written).stat().st_size, 0)
        params = pg_backup.connection_params()
        self.assertEqual(pg_backup.verify_dump(written, params), "ok")

    def test_backup_refuses_to_overwrite_an_existing_file(self):
        target = self.tmp / "snapshot.dump"
        target.write_bytes(b"eski")
        with self.assertRaises(BackupError):
            create_backup(target)
        # Mavjud fayl o'zgarmagan bo'lishi kerak.
        self.assertEqual(target.read_bytes(), b"eski")

    def test_corrupt_dump_is_rejected_before_restore(self):
        broken = self.tmp / "broken.dump"
        broken.write_bytes(b"bu pg_dump fayli emas")
        with self.assertRaises(BackupError) as ctx:
            restore_backup(broken, into=self._drill_name())
        self.assertIn("buzuq", str(ctx.exception))

    def test_missing_dump_is_rejected(self):
        with self.assertRaises(BackupError):
            restore_backup(self.tmp / "yoq.dump", into=self._drill_name())

    def test_drill_restores_into_a_separate_database(self):
        """Drill joriy bazaga tegmaydi va sxemani ko'rsatadi."""
        target = self.tmp / "snapshot.dump"
        create_backup(target)

        drill = self._drill_name()
        restored = restore_backup(target, into=drill)
        self.assertEqual(restored, drill)

        report = describe_backup(drill)
        self.assertEqual(report["integrity"], "ok")
        self.assertGreater(report["tables"], 0)
        self.assertGreater(report["migrations"], 0)

        # Joriy baza hamon o'z o'rnida.
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_drill_refuses_to_target_the_live_database(self):
        """Aks holda "drill" yashiringan destruktiv tiklash bo'lib qolardi."""
        target = self.tmp / "snapshot.dump"
        create_backup(target)
        live = pg_backup.connection_params()["name"]
        with self.assertRaises(BackupError) as ctx:
            restore_backup(target, into=live)
        self.assertIn("joriy bazani", str(ctx.exception))

    def test_in_place_restore_is_refused_with_a_manual_recipe(self):
        """Sinalmagan destruktiv yo'l kodga qo'yilmadi — sabab xabarda."""
        target = self.tmp / "snapshot.dump"
        create_backup(target)
        with self.assertRaises(BackupError) as ctx:
            restore_backup(target, into=None)
        message = str(ctx.exception)
        self.assertIn("--into", message)
        self.assertIn("pg_restore --clean", message)

    def test_backup_command_writes_a_dump_file(self):
        output = self.tmp / "cli.dump"
        call_command("backup_db", "--output", str(output))
        self.assertTrue(output.exists())

    def test_restore_command_drill_reports_schema(self):
        output = self.tmp / "cli.dump"
        call_command("backup_db", "--output", str(output))
        drill = self._drill_name()
        call_command("restore_db", "--input", str(output), "--into", drill)

    def test_restore_command_without_into_fails_even_with_yes(self):
        """`--yes` PostgreSQL'da ham destruktiv yo'lni ochmaydi."""
        output = self.tmp / "cli.dump"
        call_command("backup_db", "--output", str(output))
        with self.assertRaises(CommandError) as ctx:
            call_command("restore_db", "--input", str(output), "--yes")
        self.assertIn("--into", str(ctx.exception))
