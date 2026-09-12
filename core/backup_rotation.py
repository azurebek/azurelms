"""Eski zaxiralarni o'chirish — canonical servis (A1b).

**Nega management buyruq, host crontab'idagi `find` emas.** Ikki sabab, va
ikkalasi ham PR #111 reviewda ko'rsatildi:

1. **Huquq.** `deploy/backups` konteyner foydalanuvchisiga (uid 10001)
   tegishli va `0755`. Faylni o'chirish uchun **papkaga yozish** huquqi
   kerak, ya'ni host'dagi `ubuntu` (uid 1000) uni o'chira olmaydi:
   `find -delete` "Permission denied" bilan chiqadi, eski zaxiralar
   to'planaveradi va rotatsiya faqat qog'ozda qoladi. Buyruq esa
   konteyner ichida, o'sha uid ostida yuguradi.
2. **Owner qoidasi.** Saqlash muddati — operatsion qiymat. Crontabda
   qotib turgan `-mtime +14` ni o'zgartirish uchun SSH kerak bo'lardi;
   endi u `core.OperationalSettings.backup_retention_days` da va
   `/backoffice/control/runtime-settings/` dan o'zgartiriladi.

**Nima o'chiriladi.** Faqat `backup_db` va `backup_media` yozadigan
naqshlar. Bu ataylab tor: papkada boshqa fayl (masalan operator qo'lda
ko'chirgan nusxa yoki `.gitkeep`) bo'lsa, unga tegilmaydi.

**Eng yangi zaxira hech qachon o'chirilmaydi**, muddati o'tgan bo'lsa ham.
Sabab: rotatsiya nol zaxira qoldirishi mumkin bo'lgan holat bor —
masalan zaxira olish bir hafta yiqilib turgan bo'lsa, hammasi "eski"
bo'lib qoladi va rotatsiya oxirgi tiklash nuqtasini ham olib tashlardi.
Eski zaxira yo'qdan yaxshi.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path

#: `backup_db` va `backup_media` yozadigan fayl nomlari.
BACKUP_PATTERNS = ("db-*", "media-*")

#: Nomdagi vaqt tamg'asi: `db-20260913-030000.dump`. Fayl vaqtidan ko'ra
#: ishonchliroq — nusxa ko'chirish `mtime` ni o'zgartirishi mumkin, nom esa
#: zaxira **qachon olinganini** aytadi.
STAMP_RE = re.compile(r"-(\d{8})-(\d{6})")


@dataclass
class RotationPlan:
    keep: list = field(default_factory=list)
    delete: list = field(default_factory=list)
    kept_newest: Path | None = None

    @property
    def deleted_count(self):
        return len(self.delete)


def backup_files(directory):
    """Papkadagi zaxira fayllari, eng yangisidan boshlab."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    found = []
    for pattern in BACKUP_PATTERNS:
        found.extend(item for item in directory.glob(pattern) if item.is_file())
    return sorted(found, key=lambda item: (backup_taken_at(item), item.name), reverse=True)


def backup_taken_at(path):
    """Zaxira qachon olingan — avval nomdan, bo'lmasa fayl vaqtidan."""
    match = STAMP_RE.search(Path(path).name)
    if match:
        try:
            return datetime.strptime(
                match.group(1) + match.group(2), "%Y%m%d%H%M%S"
            ).replace(tzinfo=dt_timezone.utc)
        except ValueError:
            pass
    return datetime.fromtimestamp(Path(path).stat().st_mtime, tz=dt_timezone.utc)


def plan_rotation(directory, *, retention_days, now=None):
    """Nimani o'chirish, nimani qoldirishni hisoblaydi. Diskka tegmaydi."""
    now = now or datetime.now(dt_timezone.utc)
    cutoff = now - timedelta(days=max(1, int(retention_days)))
    files = backup_files(directory)
    plan = RotationPlan()
    if not files:
        return plan

    # Eng yangisi har doim qoladi — hatto muddati o'tgan bo'lsa ham.
    plan.kept_newest = files[0]
    plan.keep.append(files[0])
    for item in files[1:]:
        (plan.delete if backup_taken_at(item) < cutoff else plan.keep).append(item)
    return plan


def apply_rotation(plan):
    """Rejadagi fayllarni o'chiradi; o'chirilganlar ro'yxatini qaytaradi."""
    removed = []
    for item in plan.delete:
        try:
            item.unlink()
        except OSError:
            # Bitta fayl o'chmasa qolganini davom ettiramiz: yarim
            # bajarilgan rotatsiya hech narsa qilmaganidan yaxshiroq va
            # buyruq oxirida farqni ko'rsatadi.
            continue
        removed.append(item)
    return removed
