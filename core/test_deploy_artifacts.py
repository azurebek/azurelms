"""`deploy/` artefaktlari uchun gigiyena testlari.

Bu fayllar **hech qachon test bilan qoplanmagan** va shu sababli to'rtta
haqiqiy nuqson ishlab chiqargan, har biri bir xil shaklda: runbook to'g'ri
ko'rinadi, buyruq xatosiz yuguradi, natija esa yo'q.

| Qachon | Nuqson |
|---|---|
| PR #97 → #100 | `backups/` mount qilinmagan — zaxira ephemeral konteynerga yozilardi |
| PR #110 | Bind mount egaligi — konteyner yoza olmasdi |
| PR #110 review | `chown` cron logini o'ldirardi |
| 2026-09-13 audit | Media restore ikki konteynerga bo'lingan — ikkinchisi bo'sh `/tmp` ko'rardi |

Ularning hech biri Python kodida emas edi, ya'ni butun test to'plami yashil
turaverardi. Shu fayl o'sha bo'shliqni yopadi.

**Testlar matn ustida ishlaydi va bu ataylab.** `pyyaml` loyiha
bog'liqligi emas (image'ga keraksiz vazn qo'shardi), va tekshirilayotgan
narsa YAML strukturasi emas — runbookdagi **buyruqlar** va compose'dagi
**shartlar**. Har test o'zi qaytarib kelishini oldini olayotgan nuqsonni
nomlaydi.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

DEPLOY = Path(settings.BASE_DIR) / "deploy"
COMPOSE = DEPLOY / "docker-compose.prod.yml"
README = DEPLOY / "README.md"
CADDYFILE = DEPLOY / "Caddyfile"
ENV_EXAMPLE = DEPLOY / "env.example"


def compose_text():
    return COMPOSE.read_text(encoding="utf-8")


def readme_text():
    return README.read_text(encoding="utf-8")


def service_blocks():
    r"""`{servis: matni}` — `services:` bo'limidagi bloklar.

    Oddiy `^  \w+:$` regexi ishlamaydi: `depends_on:` ostidagi `db:` va
    `cache:` ham xuddi shu chuqurlikda turadi. Birinchi urinishda test
    aynan shuning uchun 20 ta "servis" sanagan edi.
    """
    text = compose_text()
    marker = "\nservices:"
    body = text[text.index(marker) + len(marker) :]
    blocks = {}
    name = None
    for line in body.splitlines():
        match = re.match(r"^  ([A-Za-z][\w-]*):\s*$", line)
        if match:
            name = match.group(1)
            blocks[name] = ""
        elif line and not line.startswith(" ") and not line.startswith("#"):
            break  # `volumes:` ildiz kaliti — servislar tugadi
        elif name:
            blocks[name] += line + "\n"
    return blocks


def anchor_block():
    """`x-app` bloki — servislar undan `<<: *app` bilan meros oladi."""
    text = compose_text()
    start = text.index("x-app:")
    end = text.index("\nservices:")
    return text[start:end]


def strip_yaml_comments(text):
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("#")
    )


def fenced_blocks(text):
    """Markdown ```-bloklari — runbookdagi bajariladigan buyruqlar."""
    return re.findall(r"```(?:bash)?\n(.*?)```", text, re.S)


#: Konteynerda saqlanadigan yo'llar: compose ularni volume yoki bind mount
#: bilan beradi, ya'ni `run --rm` dan keyin ham qoladi.
MOUNTED_PREFIXES = ("/app/backups", "/app/media", "/app/private-media", "backups/")


def _is_persistent(target):
    return target.startswith(MOUNTED_PREFIXES)


def strip_caddy_comments(text):
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("#")
    )


class ComposeTests(SimpleTestCase):
    def test_the_backups_directory_is_mounted(self):
        """PR #97 nuqsoni: mount bo'lmasa zaxira konteyner bilan yo'qoladi."""
        self.assertIn("./backups:/app/backups", compose_text())

    def test_every_service_limits_its_log_size(self):
        """Cheksiz `json-file` logi 30 GB diskni sekin-asta yeydi.

        Nuqson jim: hech narsa yiqilmaydi, disk shunchaki to'ladi va bu
        avval zaxirani (`pg_dump` yozolmaydi), keyin bazani to'xtatadi.
        """
        blocks = service_blocks()
        self.assertGreaterEqual(len(blocks), 8, "servislar topilmadi")

        # Log sozlamasi ikki yo'l bilan kelishi mumkin: to'g'ridan-to'g'ri
        # (`logging:`) yoki `x-app` dan meros (`<<: *app`). Merosni
        # **tekshirmasdan** qabul qilish yetarli emas: nazorat yugurishi
        # `x-app` dagi `logging:` ni olib tashlaganda test yashil qolgan
        # edi, chunki servislarda `<<: *app` markeri joyida turardi.
        anchor_has_logging = "logging:" in anchor_block()

        missing = [
            name
            for name, body in blocks.items()
            if "logging:" not in body
            and not ("<<: *app" in body and anchor_has_logging)
        ]

        self.assertEqual(missing, [], f"log hajmi cheklanmagan servislar: {missing}")

    def test_the_release_sha_reaches_the_containers(self):
        """Usiz Control Center release identity'ni `unknown` ko'rsatadi.

        Nosozlik paytida «serverda qaysi kod turibdi?» degan savolga javob
        bo'lmaydi, rollback esa qaysi versiyaga qaytishni bilmaydi.
        """
        # Izohlar olib tashlanadi: nazorat yugurishi kalitni o'chirganda
        # test yashil qolgan edi, chunki uning **ustidagi izohda**
        # "SOURCE_VERSION" so'zi turardi.
        self.assertRegex(strip_yaml_comments(compose_text()), r"SOURCE_VERSION:\s")

    def test_private_media_is_never_handed_to_caddy(self):
        """A0b: to'lov cheki va vazifa fayli faqat ruxsat tekshiruvi orqali.

        Caddy'ga bitta `private-media` mount qilinsa, butun private media
        ishi bir qatorda bekor bo'lardi.
        """
        text = compose_text()
        caddy_block = text[text.index("  caddy:"):]
        self.assertNotIn("private-media:/srv", caddy_block)
        self.assertIn("media:/srv/media:ro", caddy_block)

    def test_the_database_port_is_not_published(self):
        """Baza faqat compose tarmog'idan ko'rinadi; security group'ga ishonmaymiz."""
        text = compose_text()
        db_block = text[text.index("  db:"):text.index("  cache:")]
        self.assertNotIn("5432:", db_block)


class RunbookTests(SimpleTestCase):
    def test_the_media_restore_runs_in_one_container(self):
        """2026-09-13 blocker: ikki `run --rm` orasida `/tmp` saqlanmaydi.

        `run --rm` konteynerni va uning yoziladigan qatlamini o'chiradi.
        Arxiv `/tmp` ga chiqarilib, keyingi buyruq **yangi** konteynerda
        yugursa, u bo'sh `/tmp` ni ko'radi va hech narsa ko'chirmaydi.
        Oraliq papka mount qilingan joyda bo'lishi shart.
        """
        offenders = []
        for block in fenced_blocks(readme_text()):
            # Faqat `restore_media` — `restore_db --into` argumenti fayl yo'li
            # emas, **baza nomi**, ya'ni mount masalasiga aloqasi yo'q.
            for target in re.findall(r"restore_media[^\n]*?--into\s+(\S+)", block):
                if _is_persistent(target):
                    continue
                # Mount qilinmagan yo'l faqat **bitta** buyruq ichida
                # ishlatilsa xavfsiz: konteyner o'chguncha fayl joyida
                # turadi. Xavf u keyingi buyruqqa uzatilganda paydo
                # bo'ladi — o'shanda yangi konteyner bo'sh papka ko'radi.
                users = [b for b in fenced_blocks(readme_text()) if target in b]
                if len(users) > 1:
                    offenders.append(target)

        self.assertEqual(
            offenders, [],
            "mount qilinmagan oraliq papka ikki buyruq orasida uzatilyapti — "
            f"ikkinchisi bo'sh papka ko'radi: {offenders}",
        )

    def test_the_disaster_restore_extracts_into_a_mounted_path(self):
        """Falokat tiklashi ko'chirish qadamini ham o'z ichiga oladi."""
        text = readme_text()
        recovery = text[text.index("### Haqiqiy falokat tiklashi"):]

        self.assertIn("--into /app/backups/", recovery)

    def test_the_cron_log_lives_outside_the_backups_directory(self):
        """PR #110 review: `>>` redirectni host shelli `ubuntu` ostida ochadi.

        `backups/` konteyner foydalanuvchisiga (uid 10001) tegishli, ya'ni
        log o'sha yerda bo'lsa redirect yiqiladi va zaxira buyrug'i
        **umuman ishga tushmaydi**.
        """
        for line in readme_text().splitlines():
            if "manage.py backup_" in line and ">>" in line:
                target = line.split(">>", 1)[1].strip().split()[0]
                self.assertNotIn(
                    "/backups/", target,
                    f"cron logi zaxira papkasida: {target}",
                )

    def test_the_backups_directory_is_chowned_to_the_container_user(self):
        """Bind mount host egaligini saqlaydi — konteyner yoza olmaydi."""
        from core.backup_target import CONTAINER_UID

        text = readme_text()
        self.assertRegex(
            text, rf"chown -R {CONTAINER_UID}:{CONTAINER_UID}\s+backups"
        )

    def test_old_backups_are_rotated(self):
        """Rotatsiyasiz disk to'ladi va buni zaxirasiz qolganda bilib qolasiz."""
        self.assertIn("prune_backups", readme_text(), "rotatsiya qatori yo'q")

    def test_rotation_does_not_delete_from_the_host(self):
        """Host'dagi `find -delete` ishlamaydi (PR #111 review).

        Faylni o'chirish uchun **papkaga yozish** huquqi kerak. `backups/`
        konteyner foydalanuvchisiga (uid 10001) tegishli va `0755`, ya'ni
        `ubuntu` undan fayl o'chira olmaydi — rotatsiya "Permission denied"
        bilan chiqib, faqat qog'ozda qolardi.
        """
        for block in fenced_blocks(readme_text()):
            for line in block.splitlines():
                if "-delete" not in line:
                    continue
                self.assertIn(
                    "docker compose", line,
                    f"o'chirish host'dan bajarilyapti: {line.strip()}",
                )

    def test_the_retention_window_is_owner_configurable(self):
        """Operatsion qiymat crontabda qotib qolmasligi kerak."""
        from core.operational_settings import DEFAULTS

        self.assertIn("backup_retention_days", DEFAULTS)
        self.assertIn("runtime-settings", readme_text())

    def test_every_compose_up_exports_the_release_sha(self):
        """Aks holda keyingi deploy release identity'ni `unknown` qiladi.

        Birinchi versiyada `SOURCE_VERSION` faqat birinchi ishga tushirish
        buyrug'ida bor edi; yangilash va rollback yo'llari uni bermay,
        konteynerlarni bo'sh qiymat bilan qayta yaratardi.
        """
        offenders = []
        for block in fenced_blocks(readme_text()):
            for line in block.splitlines():
                if "compose" not in line or " up -d" not in line:
                    continue
                if "SOURCE_VERSION" not in line:
                    offenders.append(line.strip()[:70])

        self.assertEqual(
            offenders, [], f"SOURCE_VERSION berilmagan `up -d` buyruqlari: {offenders}"
        )

    def test_the_runbook_uses_the_webhook_command_without_dropping_updates(self):
        """`--drop-pending` ataylab so'raladi; runbook uni tavsiya qilmasin."""
        for line in readme_text().splitlines():
            if "manage.py setwebhook" in line:
                self.assertNotIn("--drop-pending", line)


class CaddyTests(SimpleTestCase):
    def test_www_has_tls_site_and_redirects_to_the_canonical_domain(self):
        """DNS aliasning o'zi HTTPS bermaydi; Caddy SNI hostni bilishi kerak."""
        text = strip_caddy_comments(CADDYFILE.read_text(encoding="utf-8"))

        self.assertRegex(text, r"(?m)^www\.azurebek\.me\s*\{")
        self.assertIn("redir https://azurebek.me{uri} permanent", text)

    def test_websockets_are_not_cut_off_mid_lesson(self):
        """Classbook darsi bir soatdan oshadi va jim daqiqalar normal.

        `read_timeout 300s` bo'sh turgan ulanishni besh daqiqada uzardi —
        klient qayta ulanadi, ya'ni bu blocker emas, lekin jonli darsda
        ko'rinadigan sifat muammosi.
        """
        # Izohlar olib tashlanadi: birinchi urinishda regex o'zim yozgan
        # **izohdagi** `read_timeout 300s` ni topib, yolg'on qizil bergan edi.
        text = strip_caddy_comments(CADDYFILE.read_text(encoding="utf-8"))
        match = re.search(r"read_timeout\s+(\S+)", text)

        self.assertIsNotNone(match, "read_timeout topilmadi")
        self.assertEqual(match.group(1), "0", "bo'sh WebSocket uziladi")

    def test_private_media_is_not_served_as_files(self):
        text = CADDYFILE.read_text(encoding="utf-8")
        self.assertNotIn("private-media", text.replace("# ", "").split("handle_path")[-1])


class EnvExampleTests(SimpleTestCase):
    def test_no_real_secret_is_committed(self):
        """Namunada to'ldirilgan sir qolib ketmasin."""
        for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
            if line.startswith(("SECRET_KEY=", "TELEGRAM_BOT_TOKEN=",
                                "TELEGRAM_WEBHOOK_SECRET=", "POSTGRES_PASSWORD=",
                                "GEMINI_API_KEY=")):
                self.assertTrue(
                    line.endswith("="), f"namunada qiymat qolgan: {line.split('=')[0]}"
                )

    def test_the_webhook_mode_matches_the_runbook(self):
        """Runbook `setwebhook` ni yugurtiradi, ya'ni rejim webhook bo'lishi kerak."""
        self.assertIn("TELEGRAM_MODE=webhook", ENV_EXAMPLE.read_text(encoding="utf-8"))
