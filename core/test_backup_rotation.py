"""Zaxira rotatsiyasi (PR #111 review).

Ikki topilma bir yechimga olib keldi:

1. **Huquq.** Host crontab'idagi `find -delete` ishlamaydi: faylni
   o'chirish uchun **papkaga yozish** huquqi kerak, `backups/` esa
   konteyner foydalanuvchisiga (uid 10001) tegishli va `0755`. `ubuntu`
   uni o'chira olmasdi va rotatsiya faqat qog'ozda qolardi — ya'ni bu
   tuzatishning o'zi to'sishi kerak bo'lgan disk to'lishi baribir sodir
   bo'lardi.
2. **Owner qoidasi.** Saqlash muddati crontabda qotib turardi; uni
   o'zgartirish uchun SSH kerak bo'lardi.

Yechim: management buyruq (konteyner ichida yuguradi) + muddat
`OperationalSettings` da.
"""

from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings

from core.backup_rotation import (
    apply_rotation,
    backup_files,
    backup_taken_at,
    plan_rotation,
)

NOW = datetime(2026, 9, 13, 3, 30, tzinfo=dt_timezone.utc)


def make_backup(directory, name, *, age_days=0):
    """Nomida vaqt tamg'asi bo'lgan zaxira fayli."""
    stamp = (NOW - timedelta(days=age_days)).strftime("%Y%m%d-%H%M%S")
    path = Path(directory) / f"{name}-{stamp}.dump"
    path.write_bytes(b"x" * 64)
    return path


class TakenAtTests(SimpleTestCase):
    def test_the_timestamp_comes_from_the_name(self):
        """Fayl `mtime` i nusxa ko'chirilganda o'zgaradi, nom esa o'zgarmaydi."""
        with TemporaryDirectory() as tmp:
            path = make_backup(tmp, "db", age_days=5)

            taken = backup_taken_at(path)

        self.assertEqual(taken.date(), (NOW - timedelta(days=5)).date())

    def test_a_name_without_a_stamp_falls_back_to_the_file_time(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "db-qoldalgan.dump"
            path.write_bytes(b"x")

            self.assertIsNotNone(backup_taken_at(path))


class PlanTests(SimpleTestCase):
    def test_only_backup_files_are_considered(self):
        """Operator qo'lda qo'ygan fayl rotatsiyaga tushmasligi kerak."""
        with TemporaryDirectory() as tmp:
            make_backup(tmp, "db", age_days=100)
            (Path(tmp) / "muhim-eslatma.txt").write_text("tegmang", encoding="utf-8")
            (Path(tmp) / "backup-cron.log").write_text("log", encoding="utf-8")

            names = {item.name for item in backup_files(tmp)}

        self.assertEqual(len(names), 1)
        self.assertTrue(next(iter(names)).startswith("db-"))

    def test_files_inside_the_window_are_kept(self):
        with TemporaryDirectory() as tmp:
            make_backup(tmp, "db", age_days=3)
            make_backup(tmp, "media", age_days=10)

            plan = plan_rotation(tmp, retention_days=14, now=NOW)

        self.assertEqual(plan.delete, [])
        self.assertEqual(len(plan.keep), 2)

    def test_files_outside_the_window_are_deleted(self):
        with TemporaryDirectory() as tmp:
            fresh = make_backup(tmp, "db", age_days=1)
            stale = make_backup(tmp, "db", age_days=40)

            plan = plan_rotation(tmp, retention_days=14, now=NOW)

        self.assertEqual([item.name for item in plan.delete], [stale.name])
        self.assertIn(fresh, plan.keep)

    def test_the_newest_backup_is_never_deleted(self):
        """Zaxira bir hafta yiqilib tursa hammasi 'eski' bo'lib qoladi.

        O'shanda rotatsiya oxirgi tiklash nuqtasini ham olib tashlardi.
        Eski zaxira yo'qdan yaxshi.
        """
        with TemporaryDirectory() as tmp:
            make_backup(tmp, "db", age_days=100)
            newest = make_backup(tmp, "db", age_days=30)

            plan = plan_rotation(tmp, retention_days=14, now=NOW)

        self.assertEqual(plan.kept_newest, newest)
        self.assertNotIn(newest, plan.delete)
        self.assertEqual(len(plan.delete), 1)

    def test_an_empty_directory_is_not_an_error(self):
        with TemporaryDirectory() as tmp:
            plan = plan_rotation(tmp, retention_days=14, now=NOW)

        self.assertEqual(plan.delete, [])
        self.assertIsNone(plan.kept_newest)

    def test_planning_touches_nothing(self):
        """Reja diskka tegmaydi — `--dry-run` shunga tayanadi."""
        with TemporaryDirectory() as tmp:
            make_backup(tmp, "db", age_days=1)
            stale = make_backup(tmp, "db", age_days=40)

            plan_rotation(tmp, retention_days=14, now=NOW)

            self.assertTrue(stale.exists())

    def test_applying_removes_exactly_the_planned_files(self):
        with TemporaryDirectory() as tmp:
            keep = make_backup(tmp, "db", age_days=1)
            drop = make_backup(tmp, "db", age_days=40)
            plan = plan_rotation(tmp, retention_days=14, now=NOW)

            removed = apply_rotation(plan)

            self.assertEqual(removed, [drop])
            self.assertTrue(keep.exists())
            self.assertFalse(drop.exists())


class CommandTests(TestCase):
    def test_the_retention_window_comes_from_the_owner_setting(self):
        """Crontabda emas, sozlamada — SSH'siz o'zgaradi."""
        from core.models import OperationalSettings

        row = OperationalSettings.load()
        row.backup_retention_days = 3
        row.save()

        with TemporaryDirectory() as tmp:
            make_backup(tmp, "db", age_days=0)
            recent = make_backup(tmp, "db", age_days=2)
            stale = make_backup(tmp, "db", age_days=9)

            call_command("prune_backups", directory=tmp)

            self.assertTrue(recent.exists(), "3 kunlik oyna ichidagi fayl o'chdi")
            self.assertFalse(stale.exists())

    def test_dry_run_deletes_nothing(self):
        with TemporaryDirectory() as tmp:
            make_backup(tmp, "db", age_days=0)
            stale = make_backup(tmp, "db", age_days=60)

            call_command("prune_backups", directory=tmp, dry_run=True)

            self.assertTrue(stale.exists())

    def test_an_explicit_days_flag_overrides_the_setting(self):
        with TemporaryDirectory() as tmp:
            make_backup(tmp, "db", age_days=0)
            stale = make_backup(tmp, "db", age_days=20)

            call_command("prune_backups", directory=tmp, days=90)
            self.assertTrue(stale.exists(), "90 kunlik oynada 20 kunlik fayl qoladi")

            call_command("prune_backups", directory=tmp, days=10)
            self.assertFalse(stale.exists())

    def test_a_zero_window_is_refused(self):
        """`--days 0` hamma zaxirani o'chirishga urinardi."""
        with TemporaryDirectory() as tmp:
            with self.assertRaises(CommandError):
                call_command("prune_backups", directory=tmp, days=0)

    def test_an_unwritable_directory_stops_the_command(self):
        """O'chirish ham papkaga yozish huquqini talab qiladi."""
        with TemporaryDirectory() as tmp:
            blocked = Path(tmp) / "backups"
            blocked.write_text("papka emas", encoding="utf-8")

            with self.assertRaises(CommandError) as caught:
                call_command("prune_backups", directory=str(blocked))

        self.assertIn("Zaxira papkasi", str(caught.exception))

    def test_the_default_directory_is_the_backup_root(self):
        """Cron buyruqni argumentsiz chaqiradi."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "backups"
            root.mkdir()
            make_backup(root, "db", age_days=0)
            stale = make_backup(root, "db", age_days=400)

            with override_settings(BASE_DIR=Path(tmp)):
                call_command("prune_backups")

            self.assertFalse(stale.exists())
