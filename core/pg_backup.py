"""PostgreSQL zaxira va tiklash — `core/backup_service.py` ning PG yarmi (A1b).

Nega alohida modul: SQLite yo'li `VACUUM INTO` bilan bitta SQL buyrug'i,
PostgreSQL yo'li esa tashqi process (`pg_dump`/`pg_restore`), maintenance
ulanish va boshqa xato sinflari. Ikkalasini bitta faylga tiqish
`core/backup_service.py` ni har bir funksiyada shoxlanadigan qilib
qo'yardi; endi u dispatcher bo'lib qoladi.

**Ataylab qilinmagan narsa — joriy bazani ustidan tiklash.** SQLite'da bu
fayl nusxasi, PostgreSQL'da esa `pg_restore --clean --if-exists` bilan
ishlab turgan bazadagi hamma obyektni tashlab, qaytadan yozish degani.
Sinalmagan destruktiv yo'lni kodga qo'yish — falokat kunida birinchi marta
yugurtiriladigan kod degani, va u ishlamasa zaxira ham, baza ham qolmaydi.
Shu sabab bu yerda u **rad etiladi** va operatorga aniq qo'lda buyruq
beriladi (`deploy/README.md` §6). Drill (alohida bazaga tiklash) esa to'liq
qurilgan — GO checklistidagi "isolated restore" aynan shu.
"""

import os
import shutil
import subprocess

from django.db import connections

#: `pg_dump`/`pg_restore` uchun kutish chegarasi. Baza kattalashsa oshiriladi;
#: chegarasiz qoldirilsa buzilgan ulanishda buyruq abadiy osilib turardi.
SUBPROCESS_TIMEOUT_SECONDS = 60 * 30


class PgToolMissing(RuntimeError):
    """`pg_dump` yoki `pg_restore` PATH'da yo'q."""


def connection_params(alias="default"):
    """Django ulanish sozlamalaridan `pg_dump` uchun parametrlar."""
    settings_dict = connections[alias].settings_dict
    return {
        "name": settings_dict.get("NAME") or "",
        "user": settings_dict.get("USER") or "",
        "password": settings_dict.get("PASSWORD") or "",
        "host": settings_dict.get("HOST") or "localhost",
        "port": str(settings_dict.get("PORT") or "5432"),
    }


def _tool(name):
    path = shutil.which(name)
    if not path:
        raise PgToolMissing(
            f"`{name}` PATH'da topilmadi. Konteynerda `postgresql-client` "
            "o'rnatilganini tekshiring (Dockerfile'da bor)."
        )
    return path


def _env_with_password(password):
    """Parol `PGPASSWORD` orqali uzatiladi.

    Buyruq qatoriga qo'yilsa u `ps` chiqishida va shell tarixida ko'rinib
    qolardi — bitta `docker compose exec` bilan boshqa jarayon uni o'qiy
    olardi.
    """
    env = dict(os.environ)
    if password:
        env["PGPASSWORD"] = password
    return env


def _run(argv, password, timeout=SUBPROCESS_TIMEOUT_SECONDS):
    return subprocess.run(
        argv,
        env=_env_with_password(password),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def build_dump_command(params, destination):
    """`pg_dump` argumentlari.

    `-Fc` (custom format) ataylab: `pg_restore` bilan tanlab tiklash mumkin
    va fayl siqilgan bo'ladi. `--no-owner`/`--no-privileges` — tiklangan
    baza boshqa rolga tegishli bo'lsa ham ishlashi uchun; drill odatda
    boshqa foydalanuvchi ostida bo'ladi.
    """
    return [
        _tool("pg_dump"),
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--host", params["host"],
        "--port", params["port"],
        "--username", params["user"],
        "--dbname", params["name"],
        "--file", str(destination),
    ]


def build_restore_command(params, source, target_dbname):
    return [
        _tool("pg_restore"),
        "--no-owner",
        "--no-privileges",
        "--host", params["host"],
        "--port", params["port"],
        "--username", params["user"],
        "--dbname", target_dbname,
        str(source),
    ]


def verify_dump(path, params):
    """Dump o'qiladimi — `pg_restore --list` bilan.

    SQLite'dagi `PRAGMA integrity_check` ning ekvivalenti. Nol baytli yoki
    yarim yozilgan fayl aynan shu yerda ushlanadi: `pg_dump` disk to'lganda
    ham fayl qoldirib ketishi mumkin.
    """
    result = _run([_tool("pg_restore"), "--list", str(path)], params["password"], timeout=120)
    if result.returncode != 0:
        return f"o'qib bo'lmadi: {(result.stderr or '').strip()[:300]}"
    if not (result.stdout or "").strip():
        return "dump bo'sh"
    return "ok"


def dump(params, destination):
    """Zaxira yozadi. Xato bo'lsa `stderr` ni qaytaradi, aks holda `None`."""
    result = _run(build_dump_command(params, destination), params["password"])
    if result.returncode != 0:
        return (result.stderr or "").strip()[:500] or f"pg_dump exit {result.returncode}"
    return None


def create_database(params, dbname):
    """Drill uchun bo'sh baza yaratadi.

    `createdb` binarysi emas, `psycopg2` ishlatiladi: klient paketining
    qaysi qismi o'rnatilganiga bog'liqlik kamayadi va xato Python
    exception sifatida keladi. `autocommit` majburiy — `CREATE DATABASE`
    tranzaksiya ichida ishlamaydi.
    """
    import psycopg2

    connection = psycopg2.connect(
        dbname="postgres",
        user=params["user"],
        password=params["password"],
        host=params["host"],
        port=params["port"],
    )
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            # Identifikator foydalanuvchi kiritmasi bo'lishi mumkin, shuning
            # uchun `psycopg2.sql` bilan to'g'ri qochiriladi — f-string bilan
            # yozilsa bu SQL injection nuqtasi bo'lardi.
            from psycopg2 import sql

            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname))
            )
    finally:
        connection.close()


def drop_database(params, dbname):
    """Drill bazasini tozalaydi. Xato jim yutiladi — tozalash asosiy ish emas."""
    import psycopg2

    try:
        connection = psycopg2.connect(
            dbname="postgres",
            user=params["user"],
            password=params["password"],
            host=params["host"],
            port=params["port"],
        )
    except Exception:
        return False
    try:
        connection.autocommit = True
        with connection.cursor() as cursor:
            from psycopg2 import sql

            cursor.execute(
                sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(dbname))
            )
        return True
    except Exception:
        return False
    finally:
        connection.close()


def restore_into(params, source, dbname):
    """Zaxirani `dbname` bazasiga tiklaydi. Xato matnini yoki `None` qaytaradi.

    `pg_restore` ba'zi obyektlar uchun ogohlantirish bilan nolga teng
    bo'lmagan kod qaytarishi mumkin (masalan mavjud bo'lmagan rol uchun
    `GRANT`). Shuning uchun exit kodi emas, tiklangan bazaning **holati**
    hukm chiqaradi — `describe_database` chaqiruvchida tekshiriladi.
    """
    result = _run(build_restore_command(params, source, dbname), params["password"])
    if result.returncode != 0:
        return (result.stderr or "").strip()[:500] or f"pg_restore exit {result.returncode}"
    return None


def describe_database(params, dbname):
    """Tiklangan bazaning sxema holati: jadval soni va migratsiya sathi.

    Drill'ning ma'nosi shu: dump ochilishi kam, uning **sxemasi** kod
    kutayotganiga mos kelishi kerak.
    """
    import psycopg2

    connection = psycopg2.connect(
        dbname=dbname,
        user=params["user"],
        password=params["password"],
        host=params["host"],
        port=params["port"],
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
            tables = cursor.fetchone()[0]
            migrations, latest = 0, ""
            try:
                cursor.execute("SELECT count(*) FROM django_migrations")
                migrations = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT app, name FROM django_migrations ORDER BY id DESC LIMIT 1"
                )
                row = cursor.fetchone()
                if row:
                    latest = f"{row[0]} {row[1]}"
            except Exception:
                # Migratsiya jadvali yo'q — Django bazasi emas yoki juda eski.
                connection.rollback()
            return {
                "integrity": "ok",
                "tables": tables,
                "migrations": migrations,
                "latest_migration": latest,
            }
    finally:
        connection.close()
