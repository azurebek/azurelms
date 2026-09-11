"""Media zaxirasi — canonical mantiq (A1b).

**Nega kerak.** `backup_db` faqat bazani oladi. Baza esa fayllarning o'zini
saqlamaydi, ularga **yo'l** saqlaydi: to'lov cheki, vazifa fayli, chat
biriktirmasi va speaking audiosi diskda turadi. Bitta serverda disk yo'qolsa
baza tiklanadi, ammo har bir `PaymentReceipt` qatori mavjud bo'lmagan faylga
ishora qiladi — ya'ni tiklash **ishlagandek ko'rinadi**, aslida o'quvchining
cheki ham, topshirgan vazifasi ham qaytmaydi. Bu zaxira yo'qligining eng yomon
turi: u faqat kerak bo'lganda ochiladi.

**Nega public va private arxiv ichida ajratiladi.** `PRIVATE_MEDIA_ROOT`
ataylab `MEDIA_ROOT` dan tashqarida (A0b) — private fayllarga `/media/...`
orqali umuman yetib bo'lmaydi, yagona yo'l ruxsat tekshiradigan view. Agar
arxiv ikkala ildizni aralashtirib saqlasa, tiklashda bitta xato bilan hamma
to'lov cheki public `/media/` ostiga tushib qolardi va Caddy ularni hech
qanday tekshiruvsiz tarqatardi. Shu sabab arxivda `public/` va `private/`
prefikslari bor va tiklash ularni alohida papkalarga chiqaradi.

**Nega `extractall(filter="data")`.** Tar arxivi ichidagi nom `../../etc/...`
yoki absolut yo'l bo'lishi mumkin; eski `extractall` ularni aytganidek
yozardi. `data` filtri absolut yo'l, `..` va tashqariga ko'rsatuvchi linklarni
rad etadi. Zaxirani o'zimiz yozgan bo'lsak ham filtr qo'yiladi: tiklanadigan
fayl har doim o'zimizning arxividan kelishiga ishonib bo'lmaydi.
"""

import tarfile
from pathlib import Path

from django.conf import settings

#: Arxiv ichidagi bo'limlar. Tartib muhim: hisobotda ham shu tartibda chiqadi.
PUBLIC_SECTION = "public"
PRIVATE_SECTION = "private"

ARCHIVE_SUFFIX = ".tar.gz"


class MediaBackupError(RuntimeError):
    """Media zaxirasi yoki tiklash bajarilmadi."""


def media_roots():
    """Zaxiralanadigan ildizlar: `(bo'lim, yo'l)` juftliklari.

    Sozlanmagan yoki diskda yo'q ildiz tushib qoladi. `USE_S3=True` holatida
    public media bucketda bo'ladi va `MEDIA_ROOT` bo'sh qoladi — o'sha holda
    arxiv faqat `private/` dan iborat bo'ladi, chunki private media S3'ga
    **ko'chirilmagan** va har doim diskda turadi. Bucket versioning bu
    arxivning ishi emas.
    """
    candidates = (
        (PUBLIC_SECTION, getattr(settings, "MEDIA_ROOT", "")),
        (PRIVATE_SECTION, getattr(settings, "PRIVATE_MEDIA_ROOT", "")),
    )
    roots = []
    for section, raw in candidates:
        if not raw:
            continue
        path = Path(raw)
        if path.exists() and path.is_dir():
            roots.append((section, path))
    return tuple(roots)


def _count_files(root):
    return sum(1 for item in root.rglob("*") if item.is_file())


def describe_media_archive(path):
    """Arxiv ichidagi fayl soni — bo'limlar bo'yicha.

    `getmembers()` butun oqimni oxirigacha o'qiydi, ya'ni gzip'ning CRC va
    uzunlik tekshiruvi ham shu yerda ishlaydi. Kesilgan yoki buzilgan arxiv
    aynan shu chaqiruvda ochiladi — fayl hajmiga qarab emas.
    """
    counts = {PUBLIC_SECTION: 0, PRIVATE_SECTION: 0}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            head = member.name.split("/", 1)[0]
            if head in counts:
                counts[head] += 1
    counts["total"] = counts[PUBLIC_SECTION] + counts[PRIVATE_SECTION]
    return counts


def verify_media_archive(path):
    """`"ok"` yoki buzilish sababi."""
    try:
        counts = describe_media_archive(path)
    except (tarfile.TarError, OSError, EOFError) as exc:
        return f"o'qib bo'lmadi: {exc}"
    if counts["total"] == 0:
        # Bo'sh arxiv xato emas, lekin "zaxira bor" deb hisoblash xato:
        # bitta ham fayl yo'q arxivni tiklash hech narsa qaytarmaydi.
        return "arxivda bitta ham fayl yo'q"
    return "ok"


def create_media_backup(destination):
    """Media ildizlarini bitta `.tar.gz` ga yozadi va tekshiradi.

    Yozilgandan keyin darhol qayta o'qiladi. `pg_dump` dagi bilan bir xil
    sabab: disk to'lganda yoki process o'lganda yarim yozilgan arxiv qolib
    ketishi mumkin va buni faqat tiklash kunida bilib qolgan bo'lardik.
    Buzuq fayl o'chiriladi — "zaxira bor" degan yolg'on taassurot qolmasin.
    """
    destination = Path(destination)
    if destination.exists():
        raise MediaBackupError(f"Arxiv allaqachon mavjud: {destination}")

    roots = media_roots()
    if not roots:
        raise MediaBackupError(
            "Zaxiralanadigan media ildizi topilmadi (MEDIA_ROOT va "
            "PRIVATE_MEDIA_ROOT bo'sh yoki mavjud emas)."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(destination, "w:gz") as archive:
            for section, root in roots:
                archive.add(str(root), arcname=section, recursive=True)
    except (tarfile.TarError, OSError) as exc:
        destination.unlink(missing_ok=True)
        raise MediaBackupError(f"Arxiv yozilmadi: {exc}") from exc

    verdict = verify_media_archive(destination)
    if verdict != "ok":
        destination.unlink(missing_ok=True)
        raise MediaBackupError(f"Arxiv buzuq chiqdi: {verdict}")
    return destination


def _is_inside(candidate, parent):
    try:
        candidate.resolve().relative_to(parent.resolve())
    except (ValueError, OSError):
        return False
    return True


def restore_media_backup(source, into):
    """Arxivni **alohida** papkaga chiqaradi va bo'lim bo'yicha sanab beradi.

    Joriy media ildizlarining ustiga tiklash ataylab yo'q. `restore_db` dagi
    bilan bir xil sabab, ustiga media uchun yana bittasi: arxiv olingandan
    keyin yuklangan har bir fayl (yangi chek, yangi vazifa) jim yo'qolardi —
    tar `--overwrite` faqat mos kelganini almashtiradi, yo'qolganini esa
    qaytarmaydi. Qo'lda tiklash tartibi `deploy/README.md` §6 da.
    """
    source = Path(source)
    if not source.exists():
        raise MediaBackupError(f"Arxiv topilmadi: {source}")

    verdict = verify_media_archive(source)
    if verdict != "ok":
        raise MediaBackupError(f"Arxiv buzuq, tiklash to'xtatildi: {verdict}")

    if not into:
        raise MediaBackupError(
            "Joriy media ildizlari ustiga tiklash bu buyruq orqali qilinmaydi. "
            "Mashq uchun `--into <bo'sh-papka>` bering; haqiqiy tiklash qo'lda "
            "va app to'xtatilgan holda (`deploy/README.md` §6)."
        )

    target = Path(into)
    for _, root in media_roots():
        # Aks holda "mashq" yashiringan destruktiv tiklash bo'lib qolardi.
        if _is_inside(target, root) or target.resolve() == root.resolve():
            raise MediaBackupError(
                f"`--into` joriy media ildizi ichini ko'rsatyapti ({root}) — mashq emas."
            )
    if target.exists() and any(target.iterdir()):
        raise MediaBackupError(f"Papka bo'sh emas: {target}")
    target.mkdir(parents=True, exist_ok=True)

    try:
        with tarfile.open(source, "r:gz") as archive:
            # `filter="data"` absolut yo'l, `..` va tashqariga ko'rsatuvchi
            # linklarni rad etadi. Arxivni o'zimiz yozgan bo'lsak ham qo'yiladi:
            # offsite nusxadan qaytarilgan fayl ham shu yo'ldan o'tadi.
            archive.extractall(path=target, filter="data")
    except (tarfile.TarError, OSError) as exc:
        # Yarim chiqqan papkani qoldirmaymiz: `target` bo'sh bo'lishi
        # tekshirilgani uchun uni o'chirish xavfsiz, va keyingi urinish
        # "papka bo'sh emas" degan chalkash xatoga urilmaydi.
        import shutil

        shutil.rmtree(target, ignore_errors=True)
        raise MediaBackupError(f"Arxivni chiqarib bo'lmadi: {exc}") from exc

    restored = {}
    for section in (PUBLIC_SECTION, PRIVATE_SECTION):
        section_dir = target / section
        restored[section] = _count_files(section_dir) if section_dir.exists() else 0
    restored["total"] = restored[PUBLIC_SECTION] + restored[PRIVATE_SECTION]
    return target, restored


def live_media_counts():
    """Joriy ildizlardagi fayl soni — mashq natijasini solishtirish uchun."""
    counts = {PUBLIC_SECTION: 0, PRIVATE_SECTION: 0}
    for section, root in media_roots():
        counts[section] = _count_files(root)
    counts["total"] = counts[PUBLIC_SECTION] + counts[PRIVATE_SECTION]
    return counts
