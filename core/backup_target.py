"""Zaxira papkasi yozilishga tayyormi — deploy oldidan tekshiruv (A1b).

**Nega alohida modul.** Bu tekshiruv ikki buyruqqa ham kerak (`backup_db` va
`backup_media`), ammo ularning xato sinflari alohida (`BackupError`,
`MediaBackupError`). Umumiy qism — savol va javob matni, ya'ni tekshiruvning
o'zi; uni ikki joyda yozish bittasini eskirtirish yo'li bo'lardi.

**Qanday nuqsonni yopadi.** `deploy/docker-compose.prod.yml` da zaxira papkasi
**bind mount**: `./backups:/app/backups`. Bind mount host papkasining
egaligini o'zgartirmaydi — `git clone` qilgan foydalanuvchi (EC2 da odatda
`ubuntu`, uid 1000) yaratgan papka o'sha egalikda qoladi. Konteyner esa
ataylab root emas: `Dockerfile` da `useradd --uid 10001`. Ya'ni uid 10001
uid 1000 ga tegishli `0755` papkaga **yoza olmaydi**.

Oqibati jim emas, lekin chalg'ituvchi edi: `pg_dump` "could not open output
file: Permission denied" deb yiqilardi va bu xabar cron logiga tushardi.
Owner uni ertasi kuni emas, **Control Center zaxira chirog'i sariq bo'lganda**
ko'rardi — ya'ni sozlamadagi `backup_stale_after_days` (default 7) o'tgach.
Beta guruhi ishlab turgan haftada bu qabul qilib bo'lmaydi.

Shuning uchun tekshiruv yozishdan **oldin** bajariladi va javob aniq
buyruqni aytadi. Xato matni — 2 daqiqalik tuzatish bilan 2 soatlik
qidiruv orasidagi farq.
"""

import os
import tempfile
from pathlib import Path

#: Konteyner ichidagi ilova foydalanuvchisi — `Dockerfile` dagi
#: `useradd --uid 10001` bilan bir xil bo'lishi shart.
CONTAINER_UID = 10001


def describe_write_problem(directory):
    """Papkaga yozib bo'lmasa sababni va tuzatishni qaytaradi, aks holda `None`.

    Ataylab **haqiqiy yozib ko'rish** bilan tekshiriladi, `os.access()` bilan
    emas: `os.access` faqat huquq bitlariga qaraydi va read-only mount,
    to'lgan disk yoki SELinux kabi holatlarni ko'rmaydi — ya'ni u "yozsa
    bo'ladi" deb aytib, keyin yozuv baribir yiqilishi mumkin.
    """
    directory = Path(directory)
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return _message(directory, f"papka yaratib bo'lmadi: {exc}")

    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".write-test-"):
            pass
    except OSError as exc:
        return _message(directory, f"papkaga yozib bo'lmadi: {exc}")
    return None


def _message(directory, reason):
    owner = _owner_hint(directory)
    return (
        f"Zaxira papkasi yozishga tayyor emas — {reason}\n"
        f"  papka : {directory}{owner}\n"
        f"  jarayon: uid={os.getuid() if hasattr(os, 'getuid') else 'n/a'}\n"
        "\n"
        "Serverda (docker compose) sabab odatda bitta: `deploy/backups` host\n"
        "papkasi `git clone` qilgan foydalanuvchiga tegishli, konteyner esa\n"
        f"uid {CONTAINER_UID} ostida ishlaydi. Tuzatish — `deploy/` ichidan:\n"
        f"\n"
        f"  sudo chown -R {CONTAINER_UID}:{CONTAINER_UID} backups\n"
    )


def _owner_hint(directory):
    """Papka egaligi — Windows'da `st_uid` ma'nosiz, shuning uchun ixtiyoriy."""
    if not hasattr(os, "getuid"):
        return ""
    try:
        stat = directory.stat()
    except OSError:
        return ""
    return f" (egasi uid={stat.st_uid}, huquq={oct(stat.st_mode)[-3:]})"
