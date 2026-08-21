"""Local baza zaxirasi va tiklash — canonical mantiq (A1a).

Nega oddiy fayl nusxasi yetarli emas: `db.sqlite3` endi **WAL rejimida**
ishlaydi (A8 concurrency tuzatishi). WAL'da so'nggi commitlar hali asosiy
faylga ko'chmagan bo'lishi mumkin — ular yonidagi `-wal` faylida turadi.
Shu paytda faylni `copy` qilsangiz, nusxada eng oxirgi yozuvlar **bo'lmaydi**
va buni faqat tiklaganda bilib qolasiz.

Shuning uchun zaxira SQLite'ning o'z `VACUUM INTO` buyrug'i bilan olinadi: u
baza ishlab turganda ham izchil (consistent) nusxa yozadi va WAL'dagi
commitlarni ham qamrab oladi.

Mantiq management buyruqlarida emas, shu yerda — shunda uni test to'g'ridan
to'g'ri chaqira oladi va `backup_db`/`restore_db` buyruqlari yupqa qobiq
bo'lib qoladi.
"""

import shutil
import sqlite3
from pathlib import Path

from django.db import connections


class BackupError(RuntimeError):
    """Zaxira yoki tiklash bajarilmadi."""


def _sqlite_path(alias="default"):
    """Berilgan alias SQLite bo'lsa fayl yo'lini qaytaradi, aks holda xato."""
    settings_dict = connections[alias].settings_dict
    engine = settings_dict.get("ENGINE", "")
    if "sqlite" not in engine:
        raise BackupError(
            f"Bu buyruq faqat SQLite uchun (joriy backend: {engine}). "
            "PostgreSQL uchun `pg_dump`/`pg_restore` ishlatiladi — u production "
            "provayderi tanlangandan keyin alohida quriladi."
        )
    name = str(settings_dict.get("NAME") or "")
    if not name or name == ":memory:" or "mode=memory" in name:
        raise BackupError("In-memory bazani zaxiralab bo'lmaydi.")
    return Path(name)


def check_sqlite_integrity(path):
    """`PRAGMA integrity_check` natijasi; 'ok' bo'lsa sog'lom.

    Umuman SQLite bo'lmagan fayl `DatabaseError` ko'taradi — uni ham verdict
    sifatida qaytaramiz, chunki chaqiruvchi uchun bu ham "buzuq" degani.
    """
    try:
        connection = sqlite3.connect(str(path))
    except sqlite3.Error as exc:
        return f"ochib bo'lmadi: {exc}"
    try:
        return connection.execute("PRAGMA integrity_check;").fetchone()[0]
    except sqlite3.DatabaseError as exc:
        return f"SQLite fayli emas yoki buzuq: {exc}"
    finally:
        connection.close()


def create_backup(destination, alias="default"):
    """Izchil zaxira yozadi va uni tekshiradi. Yozilgan yo'lni qaytaradi.

    `VACUUM INTO` ataylab tanlangan: u ishlab turgan bazadan ham izchil nusxa
    oladi va WAL'dagi commitlarni qoldirib ketmaydi.
    """
    source = _sqlite_path(alias)
    destination = Path(destination)
    if destination.exists():
        raise BackupError(f"Zaxira fayli allaqachon mavjud: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Django connection'i orqali bajariladi — o'sha sessiya WAL holatini ko'radi.
    with connections[alias].cursor() as cursor:
        cursor.execute("VACUUM INTO %s", [str(destination)])

    verdict = check_sqlite_integrity(destination)
    if verdict != "ok":
        destination.unlink(missing_ok=True)
        raise BackupError(f"Zaxira buzuq chiqdi: {verdict}")
    return destination


def describe_sqlite(path):
    """Tiklangan nusxaning holati: butunlik, jadval soni va migratsiya sathi.

    Drill'ning ma'nosi shu: nusxa ochilishi kam, uning **sxemasi** kod
    kutayotganiga mos kelishi kerak. Aks holda zaxira bor, tiklash esa
    ishlamaydi va buni faqat falokat kunida bilib qolasiz.
    """
    path = Path(path)
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        cursor = conn.cursor()
        integrity = cursor.execute("PRAGMA integrity_check").fetchone()[0]
        tables = cursor.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        try:
            migrations = cursor.execute("SELECT count(*) FROM django_migrations").fetchone()[0]
            latest_row = cursor.execute(
                "SELECT app, name FROM django_migrations ORDER BY id DESC LIMIT 1"
            ).fetchone()
            latest = f"{latest_row[0]} {latest_row[1]}" if latest_row else ""
        except sqlite3.Error:
            # Migratsiya jadvali yo'q — bu Django bazasi emas yoki juda eski.
            migrations, latest = 0, ""
        return {
            "integrity": integrity,
            "tables": tables,
            "migrations": migrations,
            "latest_migration": latest,
        }
    finally:
        conn.close()


def restore_backup(source, alias="default", into=None):
    """Zaxirani tiklaydi.

    `into` berilmasa — joriy bazaning **ustiga** yoziladi.
    `into` berilsa — alohida faylga tiklanadi va joriy bazaga tegilmaydi
    (restore drill). Drill hech narsa yo'qotmasligi kerak, aks holda uni
    hech kim qilmaydi va zaxira sinalmagan holda qolaveradi.

    Har ikki holatda avval zaxiraning o'zi tekshiriladi — buzuq faylni
    ishlayotgan bazaning ustiga yozib qo'yish eng yomon natija bo'lardi.
    """
    source = Path(source)
    if not source.exists():
        raise BackupError(f"Zaxira fayli topilmadi: {source}")

    verdict = check_sqlite_integrity(source)
    if verdict != "ok":
        raise BackupError(f"Zaxira buzuq, tiklash to'xtatildi: {verdict}")

    if into is not None:
        target = Path(into)
        live = Path(_sqlite_path(alias))
        # Aks holda "drill" yashiringan destruktiv tiklash bo'lib qolardi.
        if target.resolve() == live.resolve():
            raise BackupError(
                "`--into` joriy bazani ko'rsatyapti. Ustiga yozish uchun "
                "`--into` siz, `--yes` bilan chaqiring."
            )
        if target.exists():
            raise BackupError(f"Fayl allaqachon mavjud: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        return target

    target = _sqlite_path(alias)
    connections[alias].close()

    shutil.copyfile(source, target)
    # WAL yon fayllari eski bazaga tegishli — qolsa yangi fayl bilan
    # nomuvofiq bo'lib, ma'lumot buzilishi mumkin.
    for suffix in ("-wal", "-shm"):
        Path(str(target) + suffix).unlink(missing_ok=True)
    return target
