"""Media papkasi haqiqatan saqlanadimi — o'lchov, taxmin emas (A1b).

**Nima uchun kerak bo'ldi.** Control Center media probe'i ilgari shunday
o'ylardi: «`USE_S3=False` va profil local emas → demak fayllar ephemeral
konteyner ichida → RED». O'sha taxmin `deploy/docker-compose.prod.yml`
yozilgunga qadar to'g'ri edi. Compose esa media'ni **nomli volume** ga
mount qiladi (`media:/app/media`), ya'ni fayllar konteyner qayta
qurilganda ham qoladi.

Natija: birinchi deploy rejasi (`USE_S3=False`, persistent volume)
probe tomonidan RED deb baholanardi. `media_storage` esa `critical`, ya'ni
`/readyz` **doim `503`** qaytarardi — sayt aslida sog'lom bo'lsa ham.
Bu tashqi uptime tekshiruvi va load balancer uchun "instance yaroqsiz"
degani. Blocker sifatida deploy oldidan topildi (2026-09-13 auditi).

**Yechim: taxmin o'rniga o'lchov.** Saqlanish — kuzatiladigan xossa:

* Konteyner ichida emasmiz → oddiy VM diski, u saqlanadi.
* Konteyner ichidamiz va papka **mount nuqtasi** → volume yoki bind mount
  ulangan, ya'ni saqlanadi.
* Konteyner ichidamiz, papka esa oddiy katalog → image qatlamida yotibdi
  va konteyner bilan birga yo'qoladi. **Aynan shu holat RED.**

Shu bilan probe ikki xil xatoni ham qilmaydi: haqiqiy volume'ni ephemeral
deb qoralamaydi va mount unutilgan holatni yashil qilib qo'ymaydi.
"""

import os
from pathlib import Path

#: Docker konteynerda bu fayl mavjud bo'ladi. `/proc/1/cgroup` dan
#: ko'ra ishonchliroq: cgroup v2 da host bilan konteyner qatorlari
#: ajratib bo'lmaydigan darajada o'xshash bo'lishi mumkin.
DOCKER_ENV_MARKER = "/.dockerenv"

PERSISTENT = "persistent"
EPHEMERAL = "ephemeral"
#: Konteynerdan tashqarida — oddiy disk. Ajratilishining sababi: xabar
#: matni boshqacha bo'lishi kerak, «volume ulangan» deyish yolg'on bo'lardi.
HOST_DISK = "host-disk"


def in_container(marker=DOCKER_ENV_MARKER):
    return Path(marker).exists()


def is_mount_point(path):
    """Papka mount nuqtasimi (volume yoki bind mount shu yerga ulanganmi).

    `os.path.ismount` Windows'da ham mavjud, ammo u yerda ma'nosi boshqa —
    shuning uchun bu funksiya faqat konteyner aniqlangandan keyin
    chaqiriladi.
    """
    try:
        return os.path.ismount(str(path))
    except OSError:  # pragma: no cover — yo'l o'chirilgan bo'lsa
        return False


def classify_media_root(path, *, marker=DOCKER_ENV_MARKER):
    """`persistent` / `ephemeral` / `host-disk` — papkaning taqdiri."""
    if not in_container(marker):
        return HOST_DISK
    return PERSISTENT if is_mount_point(path) else EPHEMERAL


def describe_media_root(path, *, marker=DOCKER_ENV_MARKER):
    """`(holat, izoh)` — probe xabari uchun."""
    verdict = classify_media_root(path, marker=marker)
    if verdict == HOST_DISK:
        return verdict, "konteynerdan tashqarida, oddiy disk"
    if verdict == PERSISTENT:
        return verdict, "konteynerda, volume ulangan"
    return verdict, "konteynerda, volume ulanmagan"
