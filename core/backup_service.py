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

**PostgreSQL (2026-09-10, A1b).** Server PostgreSQL'da ishlagani uchun bu
modul endi dispatcher: SQLite yo'li o'zgarmadi, PG yo'li esa
`core/pg_backup.py` da (`pg_dump`/`pg_restore`). Ilgari PG backendida
`backup_db` shunchaki xato berardi — ya'ni serverda zaxira olishning
canonical yo'li umuman yo'q edi va Control Center backup probe'i doim
qizil turardi.
"""

import shutil
import sqlite3
from pathlib import Path

from django.db import connections

from core import pg_backup


class BackupError(RuntimeError):
    """Zaxira yoki tiklash bajarilmadi."""


def engine_of(alias="default"):
    return connections[alias].settings_dict.get("ENGINE", "")


def is_postgres(alias="default"):
    return "postgresql" in engine_of(alias)


def default_backup_suffix(alias="default"):
    """Zaxira faylining kengaytmasi.

    Nomi backendni aytib turishi kerak: `.dump` faylni SQLite deb ochishga
    urinish chalkash xato beradi, va aksincha.
    """
    return ".dump" if is_postgres(alias) else ".sqlite3"


def _sqlite_path(alias="default"):
    """Berilgan alias SQLite bo'lsa fayl yo'lini qaytaradi, aks holda xato."""
    settings_dict = connections[alias].settings_dict
    engine = settings_dict.get("ENGINE", "")
    if "sqlite" not in engine:
        raise BackupError(
            f"Bu yo'l faqat SQLite uchun (joriy backend: {engine}). "
            "PostgreSQL yo'li `core/pg_backup.py` da."
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

    Backendga qarab yo'l tanlanadi. Chaqiruvchi (management buyruq, test,
    Control Center) qaysi baza ekanini bilishi shart emas.
    """
    if is_postgres(alias):
        return _create_backup_postgres(destination, alias)
    return _create_backup_sqlite(destination, alias)


def _create_backup_postgres(destination, alias="default"):
    """`pg_dump -Fc` bilan zaxira; keyin `pg_restore --list` bilan tekshiruv.

    Tekshiruv ataylab: `pg_dump` disk to'lganda yoki ulanish uzilganda ham
    yarim yozilgan fayl qoldirib ketishi mumkin, va buni faqat tiklash
    kunida bilib qolgan bo'lardik. Buzuq fayl o'chiriladi — "zaxira bor"
    degan yolg'on taassurot qolmasin.
    """
    destination = Path(destination)
    if destination.exists():
        raise BackupError(f"Zaxira fayli allaqachon mavjud: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    params = pg_backup.connection_params(alias)
    try:
        failure = pg_backup.dump(params, destination)
    except pg_backup.PgToolMissing as exc:
        raise BackupError(str(exc)) from exc
    if failure:
        destination.unlink(missing_ok=True)
        raise BackupError(f"pg_dump yiqildi: {failure}")

    verdict = pg_backup.verify_dump(destination, params)
    if verdict != "ok":
        destination.unlink(missing_ok=True)
        raise BackupError(f"Zaxira buzuq chiqdi: {verdict}")
    return destination


def _create_backup_sqlite(destination, alias="default"):
    """`VACUUM INTO` ataylab tanlangan: u ishlab turgan bazadan ham izchil
    nusxa oladi va WAL'dagi commitlarni qoldirib ketmaydi."""
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


def describe_backup(target, alias="default"):
    """Tiklangan nusxaning holati — backendga qarab.

    SQLite'da `target` fayl yo'li, PostgreSQL'da esa baza nomi.
    """
    if is_postgres(alias):
        return pg_backup.describe_database(pg_backup.connection_params(alias), str(target))
    return describe_sqlite(target)


def restore_backup(source, alias="default", into=None):
    """Zaxirani tiklaydi.

    `into` berilmasa — joriy bazaning **ustiga** yoziladi.
    `into` berilsa — alohida joyga tiklanadi va joriy bazaga tegilmaydi
    (restore drill). SQLite'da bu alohida **fayl**, PostgreSQL'da alohida
    **baza**. Drill hech narsa yo'qotmasligi kerak, aks holda uni hech kim
    qilmaydi va zaxira sinalmagan holda qolaveradi.

    Har ikki holatda avval zaxiraning o'zi tekshiriladi — buzuq faylni
    ishlayotgan bazaning ustiga yozib qo'yish eng yomon natija bo'lardi.
    """
    if is_postgres(alias):
        return _restore_backup_postgres(source, alias, into)
    return _restore_backup_sqlite(source, alias, into)


def _restore_backup_postgres(source, alias="default", into=None):
    """PostgreSQL drill: zaxirani **alohida** bazaga tiklaydi.

    Joriy bazaning ustiga tiklash bu yerda ataylab **rad etiladi**. U
    `pg_restore --clean --if-exists` bilan ishlab turgan bazadagi hamma
    obyektni tashlab qaytadan yozish degani; sinalmagan destruktiv yo'l
    falokat kunida birinchi marta yugurtiriladigan kod bo'lardi va u
    ishlamasa na zaxira, na baza qoladi. Operator uchun aniq qo'lda
    buyruq beriladi (`deploy/README.md` §6).
    """
    source = Path(source)
    if not source.exists():
        raise BackupError(f"Zaxira fayli topilmadi: {source}")

    params = pg_backup.connection_params(alias)
    try:
        verdict = pg_backup.verify_dump(source, params)
    except pg_backup.PgToolMissing as exc:
        raise BackupError(str(exc)) from exc
    if verdict != "ok":
        raise BackupError(f"Zaxira buzuq, tiklash to'xtatildi: {verdict}")

    if not into:
        raise BackupError(
            "PostgreSQL'da joriy bazani ustidan tiklash bu buyruq orqali "
            "qilinmaydi. Drill uchun `--into <yangi-baza-nomi>` bering. "
            "Haqiqiy falokat tiklashi qo'lda va app to'xtatilgan holda: "
            "`pg_restore --clean --if-exists --no-owner -d <baza> <fayl>` "
            "(`deploy/README.md` §6)."
        )

    if str(into) == params["name"]:
        # Aks holda "drill" yashiringan destruktiv tiklash bo'lib qolardi.
        raise BackupError("`--into` joriy bazani ko'rsatyapti — drill emas.")

    try:
        pg_backup.create_database(params, str(into))
    except Exception as exc:
        raise BackupError(f"Drill bazasini yaratib bo'lmadi: {exc}") from exc

    failure = pg_backup.restore_into(params, source, str(into))
    if failure:
        raise BackupError(f"pg_restore yiqildi: {failure}")
    return into


def _restore_backup_sqlite(source, alias="default", into=None):
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
