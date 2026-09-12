"""Zaxira papkasi yozilishga tayyormi — deploy oldi tekshiruvi (A1b).

Nuqson serverda, deploy kunida chiqadigan turdan: `deploy/backups` host
papkasi bind mount bilan konteynerga beriladi, bind mount esa host
egaligini saqlaydi. `git clone` qilgan foydalanuvchi (EC2 da `ubuntu`,
uid 1000) yaratgan `0755` papkaga konteynerdagi uid 10001 **yoza olmaydi**.

Natija chalg'ituvchi edi: cron har kuni ishlab turgandek ko'rinardi, xato
esa faqat log faylida qolardi va Control Center zaxira chirog'i sariq
bo'lguncha (default 7 kun) hech kim bilmasdi. Beta guruhi ishlab turgan
haftada bu qabul qilib bo'lmaydi.

Testlar `os.getuid` bo'lmagan Windows'da ham ishlashi kerak, shuning uchun
huquq bo'yicha tekshiruv POSIX'da bo'lgan holatda qo'shimcha yugurtiriladi.
"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings

from core.backup_target import CONTAINER_UID, describe_write_problem


class WritableTargetTests(SimpleTestCase):
    def test_a_writable_directory_reports_no_problem(self):
        with TemporaryDirectory() as tmp:
            self.assertIsNone(describe_write_problem(Path(tmp)))

    def test_a_missing_directory_is_created_rather_than_refused(self):
        """Birinchi zaxirada papka hali bo'lmasligi normal."""
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "backups"

            self.assertIsNone(describe_write_problem(target))
            self.assertTrue(target.is_dir())

    def test_the_message_names_the_exact_fix(self):
        """Xato matni alomatni emas, **tuzatishni** aytishi kerak.

        Bu testning butun mazmuni shu: serverda soat uchda cron logini
        o'qiyotgan odamga "Permission denied" hech narsa bermaydi, bitta
        `chown` buyrug'i esa hammasini beradi.
        """
        with TemporaryDirectory() as tmp:
            blocked = Path(tmp) / "not-a-dir"
            blocked.write_text("men fayl man, papka emas", encoding="utf-8")

            message = describe_write_problem(blocked)

        self.assertIsNotNone(message, "fayl ustiga papka yasab bo'lmaydi")
        self.assertIn("chown", message)
        self.assertIn(str(CONTAINER_UID), message)
        self.assertIn(str(blocked), message)

    def test_the_uid_matches_the_dockerfile(self):
        """Tuzatish buyrug'idagi uid image'dagi bilan bir xil bo'lishi shart.

        Ular ajralib ketsa xato matni **noto'g'ri** buyruqni tavsiya qiladi —
        bu tuzatishsizlikdan ham yomon, chunki owner uni bajarib, muammo
        davom etganini ko'radi va boshqa yerdan qidira boshlaydi.
        """
        import re

        from django.conf import settings

        dockerfile = (Path(settings.BASE_DIR) / "Dockerfile").read_text(encoding="utf-8")
        found = re.findall(r"--uid\s+(\d+)", dockerfile)

        # `assertIn` bilan yozgan edim va nazorat yugurishi uni **o'tkazib
        # yubordi**: `--uid 1000` matni `--uid 10001` ning ichida bor, ya'ni
        # noto'g'ri uid ham "topilgan" bo'lardi. Aynan shu sinf nuqson
        # kutilmaganda jim o'tadi — shuning uchun raqam butunligicha
        # solishtiriladi.
        self.assertEqual(found, [str(CONTAINER_UID)], "Dockerfile dagi uid boshqacha")


class PosixPermissionTests(SimpleTestCase):
    """Haqiqiy huquq holati — faqat POSIX'da ma'noli.

    **Bu testlar `os.access` bilan haqiqiy yozib ko'rish orasidagi farqni
    ajrata olmaydi** va buni bilib turib yozyapman: ikkisi ham mode bitlarini
    bir xil o'qiydi. Farq faqat real serverdagi holatlarda ko'rinadi —
    read-only mount, to'lgan disk, SELinux — ularni unit testda yasab
    bo'lmaydi. Ya'ni kimdir keyinroq `describe_write_problem()` ni
    `os.access` ga "soddalashtirsa", **testlar yashil qoladi**. Shuning
    uchun sabab kodda ham, shu yerda ham yozilgan: tanlov qamrov uchun,
    testlar uni qo'riqlay olmaydi.
    """

    def setUp(self):
        if not hasattr(os, "getuid"):
            self.skipTest("Windows'da fayl huquqi boshqacha ishlaydi")
        if os.getuid() == 0:
            self.skipTest("root hamma joyga yoza oladi")

    def test_a_read_only_directory_is_reported(self):
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "backups"
            target.mkdir()
            target.chmod(0o555)
            try:
                message = describe_write_problem(target)
            finally:
                target.chmod(0o755)

        self.assertIsNotNone(message)
        self.assertIn("chown", message)


class BackupCommandsRefuseEarlyTests(TestCase):
    """Buyruqlar yozishdan OLDIN to'xtashi kerak.

    Aks holda `pg_dump`/`tarfile` ning o'z xatosi chiqadi: u alomatni
    ko'rsatadi (`could not open output file`), serverdagi haqiqiy sababni —
    bind mount egaligini — emas.
    """

    def _blocked_target(self, tmp):
        blocked = Path(tmp) / "backups"
        blocked.write_text("papka emas", encoding="utf-8")
        return blocked

    def test_backup_db_refuses_with_an_actionable_message(self):
        with TemporaryDirectory() as tmp:
            self._blocked_target(tmp)
            with override_settings(BASE_DIR=Path(tmp)):
                with self.assertRaises(CommandError) as caught:
                    call_command("backup_db")

        self.assertIn("chown", str(caught.exception))

    def test_backup_media_refuses_with_an_actionable_message(self):
        with TemporaryDirectory() as tmp:
            self._blocked_target(tmp)
            with override_settings(BASE_DIR=Path(tmp)):
                with self.assertRaises(CommandError) as caught:
                    call_command("backup_media")

        self.assertIn("chown", str(caught.exception))

    def test_a_healthy_target_still_produces_a_backup(self):
        """Tekshiruv sog'lom yo'lni to'sib qo'ymasligi kerak.

        `backup_media` tanlandi, `backup_db` emas: test bazasi xotirada
        (SQLite `:memory:`) va uni zaxiralab bo'lmaydi — ya'ni u yerdagi
        xato tekshiruvimga emas, test muhitiga tegishli bo'lardi.
        """
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "media"
            root.mkdir()
            # Bo'sh arxiv ataylab rad etiladi (`core/media_backup.py`), ya'ni
            # sog'lom yo'lni ko'rsatish uchun kamida bitta fayl kerak.
            (root / "namuna.txt").write_text("fayl", encoding="utf-8")
            with override_settings(BASE_DIR=Path(tmp), MEDIA_ROOT=root):
                call_command("backup_media")

            written = list((Path(tmp) / "backups").glob("media-*"))

        self.assertEqual(len(written), 1, "zaxira yozilmadi")
