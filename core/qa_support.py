"""Testlar uchun umumiy yordamchilar.

Fayl nomi ataylab `test*` bilan boshlanmaydi — aks holda Django uni test
moduli deb topib olardi.

Ikki xil backend farqi bu yerda jamlangan:

1. Test bazasi haqiqiy fayldami yoki shared-cache in-memory SQLite'mi. Farq
   muhim, chunki in-memory variantning qulflash semantikasi boshqacha
   (`SQLITE_LOCKED` darhol qaytadi, `busy_timeout` ishlamaydi), shuning uchun
   contention testlari faqat fayl bazasida haqiqatni ko'rsatadi.
2. Backend umuman SQLite'mi. Suite endi CI'da PostgreSQL'da ham yugiradi, va
   ayrim imkoniyatlar (masalan `VACUUM INTO` ga asoslangan zaxira) ataylab
   faqat SQLite uchun qurilgan.
"""

from django.db import connection

FILE_DB_HINT = (
    "Bu test real fayl bazasini talab qiladi (shared-cache in-memory SQLite "
    "qulflash semantikasi boshqacha). Ishga tushirish: "
    "AZURELMS_TEST_FILE_DB=1 python manage.py test <modul>"
)
SQLITE_ONLY_HINT = (
    "Bu yo'l ataylab faqat SQLite uchun qurilgan (joriy backend: {vendor}). "
    "PostgreSQL varianti `core/pg_backup.py` da va o'z testlarida sinaladi."
)
POSTGRES_ONLY_HINT = (
    "Bu test haqiqiy PostgreSQL talab qiladi (joriy backend: {vendor}). "
    "CI ning `integration` ishida yuguradi."
)


def is_file_backed_sqlite():
    """Joriy test bazasi diskdagi SQLite faylimi?"""
    if connection.vendor != "sqlite":
        return False
    name = str(connection.settings_dict.get("NAME") or "")
    return bool(name) and name != ":memory:" and "mode=memory" not in name


def skip_unless_file_backed_db(testcase):
    """SQLite in-memory rejimida testni sabab bilan skip qiladi."""
    if connection.vendor == "sqlite" and not is_file_backed_sqlite():
        testcase.skipTest(FILE_DB_HINT)


def skip_unless_sqlite(testcase):
    """SQLite'ga xos imkoniyat testini boshqa backendlarda skip qiladi."""
    if connection.vendor != "sqlite":
        testcase.skipTest(SQLITE_ONLY_HINT.format(vendor=connection.vendor))


def skip_unless_postgres(testcase):
    """PostgreSQL'ga xos yo'l testini boshqa backendlarda skip qiladi.

    Ishlab chiqish mashinasida PostgreSQL yo'q, shuning uchun bu testlar
    lokalda skip bo'ladi va haqiqiy dalil CI ning `integration` ishidan
    keladi. Skip sababi ataylab matnli — "0 test yugurdi" jimgina
    "hammasi yashil" ga aylanmasin.
    """
    if connection.vendor != "postgresql":
        testcase.skipTest(POSTGRES_ONLY_HINT.format(vendor=connection.vendor))
