"""Umumiy feature flag registri (A2).

Ilgari loyihada yagona flag `AISettings.ai_remote_calls_enabled` edi — qattiq
yozilgan bitta maydon. `05-launch-ops.md` §2 esa har capability uchun
flag/kill switch talab qiladi.

**Registr kodda, override DB'da.** Sabab uchta:

* kodda e'lon qilingan flag topiladigan bo'ladi — grep bilan ham, Control
  Center'da ham; DB'dagi erkin qatorlar esa nomi bo'yicha taxmin qilinadi;
* har flagga hujjatlangan default va izoh biriktiriladi, ya'ni uni ko'rgan
  odam nima o'chirayotganini biladi;
* registrdan olib tashlangan flagning eski DB qatori **jim ta'sir qilmaydi**.

Kesh ataylab qo'yilmadi: eskirgan kesh tufayli o'chirilmay qolgan capability
har so'rovdagi bitta arzon so'rovdan yomonroq.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import DatabaseError, transaction


class UnknownFlag(LookupError):
    """Registrda yo'q slug.

    Jim `False` qaytarish xavfli bo'lardi: xato yozilgan slug capabilityni
    jimgina o'chirib qo'yardi va buni hech kim sezmasdi.
    """


@dataclass(frozen=True)
class FlagDefinition:
    slug: str
    label: str
    description: str
    default: bool
    category: str = "Umumiy"
    #: Nima uchun o'chirish kerak bo'lishi mumkin va o'chirilganda nima bo'ladi.
    runbook: str = ""


FLAG_REGISTRY: tuple[FlagDefinition, ...] = (
    FlagDefinition(
        slug="public_registration",
        label="Ochiq ro'yxatdan o'tish",
        description="Yangi foydalanuvchilar o'zi hisob ocha oladimi.",
        default=True,
        category="Acquisition",
        runbook=(
            "Yopilganda ro'yxatdan o'tish sahifasi xabar ko'rsatadi va hisob "
            "yaratilmaydi. Mavjud foydalanuvchilar kirishda davom etadi. "
            "Demo yoki nazoratli beta paytida yopiladi."
        ),
    ),
    FlagDefinition(
        slug="telegram_outbox_sending",
        label="Telegram xabar yuborish",
        description="Outbox navbatidagi xabarlar Telegramga yuboriladimi.",
        default=True,
        category="Telegram",
        runbook=(
            "Yopilganda xabarlar navbatda **saqlanib turadi**, yo'qolmaydi — "
            "worker ularni olmaydi. Worker heartbeat'i yozilishda davom etadi, "
            "aks holda pauza worker o'lgandek ko'rinardi. "
            "Bot noto'g'ri xabar yuborayotganda yoki Telegram tomonida muammo bo'lganda yopiladi."
        ),
    ),
)

_BY_SLUG = {flag.slug: flag for flag in FLAG_REGISTRY}


def flag_definitions() -> tuple[FlagDefinition, ...]:
    return FLAG_REGISTRY


def flag_by_slug(slug: str) -> FlagDefinition:
    try:
        return _BY_SLUG[slug]
    except KeyError as exc:
        raise UnknownFlag(f"Registrda bunday flag yo'q: {slug}") from exc


def flag_enabled(slug: str) -> bool:
    """Flagning joriy holati: DB override, bo'lmasa e'lon qilingan default.

    Baza o'qilmasa e'lon qilingan default qaytariladi — capability hujjatlangan
    holatida qoladi va flag o'qish nosozligi butun oqimni to'xtatmaydi.
    """
    definition = flag_by_slug(slug)

    from aicontrol.models import FeatureFlag

    try:
        row = FeatureFlag.objects.filter(slug=slug).values("enabled").first()
    except DatabaseError:
        return definition.default
    return definition.default if row is None else bool(row["enabled"])


def set_flag(slug: str, *, enabled: bool, reason: str, request=None, actor=None) -> bool:
    """Flagni o'zgartiradi va auditlaydi. Qaytaradi: o'zgarish bo'ldimi.

    O'zgarish bo'lmasa hech narsa yozilmaydi — append-only ledger bosilmagan
    tugmalar bilan to'lmasligi kerak.
    """
    definition = flag_by_slug(slug)

    from aicontrol.models import FeatureFlag
    from core.audit import record_audit_event

    with transaction.atomic():
        row = FeatureFlag.objects.select_for_update().filter(slug=slug).first()
        previous = definition.default if row is None else bool(row.enabled)
        if previous == bool(enabled):
            return False

        if row is None:
            FeatureFlag.objects.create(slug=slug, enabled=bool(enabled))
        else:
            row.enabled = bool(enabled)
            row.save(update_fields=["enabled", "updated_at"])

        record_audit_event(
            action="feature_flag.update",
            request=request,
            actor=actor,
            # Slug yorliq ichida: ledgerni slug bo'yicha qidirish mumkin bo'lsin.
            target_label=f"Feature flag: {definition.label} ({slug})",
            reason=reason.strip(),
            before={"enabled": previous},
            after={"enabled": bool(enabled)},
        )
    return True
