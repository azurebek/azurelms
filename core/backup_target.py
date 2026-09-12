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

**Tavsiya sababga qarab o'zgaradi.** Huquq, to'lgan disk va read-only mount —
uch xil nosozlik, va ularning hech biri boshqasining yechimi bilan
tuzalmaydi. Hammasiga bitta `chown` ko'rsatish operatorni noto'g'ri yo'lga
boshlardi, bu esa tavsiyasizlikdan ham yomon: u buyruqni bajaradi, muammo
davom etadi va endi ishonchi ham yo'qoladi (PR #110 review topilmasi).
"""

import errno
import os
import tempfile
from pathlib import Path, PurePosixPath

#: Konteyner ichidagi ilova foydalanuvchisi — `Dockerfile` dagi
#: `useradd --uid 10001` bilan bir xil bo'lishi shart.
CONTAINER_UID = 10001

#: Compose bind mount konteyner ichida shu yo'lda ko'rinadi. Faqat shu yo'l
#: (yoki uning ichidagi papka) uchun **host tomonidagi** `chown` tavsiya
#: qilinadi: `--output` bilan boshqa joy berilgan bo'lsa, o'sha yerdagi
#: papkani tuzatish kerak, `deploy/backups` ni emas.
BIND_MOUNT_PATH = "/app/backups"


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
        return _message(directory, f"papka yaratib bo'lmadi: {exc}", exc)

    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".write-test-"):
            pass
    except OSError as exc:
        return _message(directory, f"papkaga yozib bo'lmadi: {exc}", exc)
    return None


def remediation(directory, code):
    """`(sabab, buyruq)` — `errno` ga mos tavsiya. Sof funksiya, test qilinadi.

    Buyruqlardagi yo'l har doim POSIX shaklida: ular serverda, konteyner
    ichida (Linux) bajariladi. Windows'dagi ishlab chiqish mashinasida `Path`
    teskari chiziq qo'yardi va natija nusxa-ko'chirib bajarib bo'lmaydigan
    buyruq bo'lardi.
    """
    shown = _posix(directory)
    if code == errno.ENOSPC:
        return (
            "Diskda joy qolmagan.",
            "df -h\n  # eski zaxiralarni boshqa joyga ko'chiring yoki o'chiring",
        )
    if code == errno.EROFS:
        return (
            "Fayl tizimi faqat o'qish uchun mount qilingan.",
            f"mount | grep {_mount_hint(directory)}",
        )
    if code in (errno.EACCES, errno.EPERM):
        return _ownership_remedy(directory)
    if code in (errno.ENOTDIR, errno.EEXIST):
        # `mkdir(exist_ok=True)` yo'lda **fayl** turgan bo'lsa `EEXIST`
        # beradi (Windows'da `WinError 183` ham shunga xaritalanadi), papka
        # ichidagi bo'lak fayl bo'lsa `ENOTDIR`. Ikkisi ham bitta savolga
        # olib keladi: u yerda aslida nima turibdi?
        return (
            "Yo'lda papka emas, fayl turibdi.",
            f"ls -la {shown}",
        )
    return (
        "Sabab noaniq — yuqoridagi tizim xatosiga qarang.",
        f"ls -la {shown}",
    )


def _ownership_remedy(directory):
    """Huquq nosozligi: bind mount bo'lsa host tomonini tuzatish kerak.

    Farq muhim: konteyner ichida yo'l `/app/backups`, ammo `chown` **host**
    papkasiga qilinadi. Konteyner ichidagi yo'lni ko'rsatish operatorni
    bajarib bo'lmaydigan buyruqqa yo'naltirardi.
    """
    if _is_bind_mount(directory):
        return (
            "Papka konteyner foydalanuvchisiga tegishli emas. Bu compose "
            "bind mount'i: host papkasining egaligi saqlanadi, ya'ni tuzatish "
            "**host tomonda** qilinadi.",
            f"cd ~/azurelms/deploy && sudo chown -R {CONTAINER_UID}:{CONTAINER_UID} backups",
        )
    return (
        "Papkaga yozish huquqi yo'q.",
        f"sudo chown -R {CONTAINER_UID}:{CONTAINER_UID} {_posix(directory)}\n"
        "  # yoki `--output` bilan yoza oladigan boshqa papkani bering",
    )


def _posix(directory):
    """Yo'lning POSIX shakli — buyruq matnlari uchun."""
    return Path(directory).as_posix()


def _is_bind_mount(directory):
    try:
        path = PurePosixPath(Path(directory).as_posix())
    except (TypeError, ValueError):  # pragma: no cover — himoya
        return False
    mount = PurePosixPath(BIND_MOUNT_PATH)
    return path == mount or mount in path.parents


def _mount_hint(directory):
    """`mount | grep` uchun foydali bo'lak — to'liq yo'l odatda mos kelmaydi."""
    parts = PurePosixPath(Path(directory).as_posix()).parts
    return parts[1] if len(parts) > 1 else str(directory)


def _message(directory, reason, exc=None):
    code = getattr(exc, "errno", None)
    cause, command = remediation(directory, code)
    owner = _owner_hint(directory)
    uid = os.getuid() if hasattr(os, "getuid") else "n/a"
    return (
        f"Zaxira papkasi yozishga tayyor emas — {reason}\n"
        f"  papka  : {directory}{owner}\n"
        f"  jarayon: uid={uid}\n"
        "\n"
        f"{cause}\n"
        "\n"
        f"  {command}\n"
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
