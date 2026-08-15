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
    "Bu imkoniyat ataylab faqat SQLite uchun qurilgan (joriy backend: {vendor}). "
    "PostgreSQL varianti provayder tanlangandan keyin alohida quriladi."
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
