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

import errno
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings

from core.backup_target import CONTAINER_UID, describe_write_problem, remediation


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

    def test_the_message_names_the_path_and_a_concrete_command(self):
        """Xato matni alomatni emas, **keyingi qadamni** aytishi kerak.

        Bu testning butun mazmuni shu: serverda soat uchda cron logini
        o'qiyotgan odamga "Permission denied" hech narsa bermaydi. Qaysi
        buyruq kerakligi sababga bog'liq (`RemediationTests`), ammo yo'l va
        bajariladigan bitta qator **har doim** bo'lishi kerak.
        """
        with TemporaryDirectory() as tmp:
            blocked = Path(tmp) / "not-a-dir"
            blocked.write_text("men fayl man, papka emas", encoding="utf-8")

            message = describe_write_problem(blocked)

        self.assertIsNotNone(message, "fayl ustiga papka yasab bo'lmaydi")
        self.assertIn(str(blocked), message)
        self.assertIn("ls -la", message, "bajariladigan buyruq yo'q")
        self.assertIn("fayl turibdi", message, "sabab aytilmagan")

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

    def test_postgres_client_major_matches_the_database_image(self):
        """Backup klienti serverdan yangi bo'lsa dump tiklanmay qolishi mumkin.

        PG17 `pg_dump` PG16 serverdan dump olishga ruxsat beradi, ammo dumpga
        PG16 tanimaydigan `SET transaction_timeout` yozadi. `pg_restore`
        qolgan obyektlarni tiklasa ham non-zero bilan tugaydi; canonical
        restore drill buni to'g'ri ravishda xato deb hisoblaydi.
        """
        import re

        from django.conf import settings

        root = Path(settings.BASE_DIR)
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        compose = (root / "deploy" / "docker-compose.prod.yml").read_text(
            encoding="utf-8"
        )
        client = re.search(r"postgresql-client-(\d+)", dockerfile)
        server = re.search(r"pgvector/pgvector:pg(\d+)", compose)

        self.assertIsNotNone(client, "Dockerfile PostgreSQL klient majorini pin qilmagan")
        self.assertIsNotNone(server, "Compose PostgreSQL server majorini pin qilmagan")
        self.assertEqual(
            client.group(1),
            server.group(1),
            "pg_dump/pg_restore majori PostgreSQL server bilan bir xil emas",
        )


class RemediationTests(SimpleTestCase):
    """Tavsiya sababga va yo'lga mos bo'lishi kerak (PR #110 review).

    Birinchi versiyada xato matni **har doim** `chown deploy/backups` deb
    yozardi. Bu uch holatda noto'g'ri edi: `--output` boshqa papkani
    ko'rsatganda, disk to'lganda va fayl tizimi read-only bo'lganda.
    Noto'g'ri tavsiya tavsiyasizlikdan yomonroq — operator uni bajaradi,
    muammo davom etadi va endi u xato matniga ham ishonmaydi.
    """

    def test_a_full_disk_is_not_an_ownership_problem(self):
        cause, command = remediation(Path("/app/backups"), errno.ENOSPC)

        self.assertIn("joy qolmagan", cause)
        self.assertIn("df -h", command)
        self.assertNotIn("chown", command)

    def test_a_read_only_filesystem_is_not_an_ownership_problem(self):
        cause, command = remediation(Path("/app/backups"), errno.EROFS)

        self.assertIn("o'qish uchun", cause)
        self.assertIn("mount", command)
        self.assertNotIn("chown", command)

    def test_the_bind_mount_gets_the_host_side_command(self):
        """Konteyner ichidagi yo'lni `chown` qilib bo'lmaydi — host tuzatiladi."""
        cause, command = remediation(Path("/app/backups"), errno.EACCES)

        self.assertIn("host tomonda", cause)
        self.assertIn("deploy", command)
        self.assertIn("chown", command)
        self.assertNotIn("/app/backups", command)

    def test_a_custom_output_path_gets_that_path_not_deploy_backups(self):
        """`--output` boshqa joyni ko'rsatsa, tavsiya o'sha joy haqida bo'lsin."""
        cause, command = remediation(Path("/srv/zaxira"), errno.EACCES)

        self.assertIn("/srv/zaxira", command)
        self.assertNotIn("deploy", command)

    def test_a_path_inside_the_bind_mount_still_counts_as_the_bind_mount(self):
        _, command = remediation(Path("/app/backups/kunlik"), errno.EACCES)

        self.assertIn("deploy", command)

    def test_an_unknown_cause_does_not_invent_a_fix(self):
        cause, command = remediation(Path("/app/backups"), None)

        self.assertIn("noaniq", cause)
        self.assertNotIn("chown", command)


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
        self.assertIn(str(CONTAINER_UID), message)


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
            blocked = self._blocked_target(tmp)
            with override_settings(BASE_DIR=Path(tmp)):
                with self.assertRaises(CommandError) as caught:
                    call_command("backup_db")

        message = str(caught.exception)
        self.assertIn("Zaxira papkasi yozishga tayyor emas", message)
        self.assertIn(str(blocked), message)

    def test_backup_media_refuses_with_an_actionable_message(self):
        with TemporaryDirectory() as tmp:
            blocked = self._blocked_target(tmp)
            with override_settings(BASE_DIR=Path(tmp)):
                with self.assertRaises(CommandError) as caught:
                    call_command("backup_media")

        message = str(caught.exception)
        self.assertIn("Zaxira papkasi yozishga tayyor emas", message)
        self.assertIn(str(blocked), message)

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
