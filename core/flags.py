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
        slug="frontend_v1_exam_review",
        label="Frontend V1 — ustoz imtihon tekshiruvi",
        description="Qoralama va alohida e’lon qilish; eski forma yangi bahoni bosmaydi.",
        default=False, category="Frontend",
        runbook="OFF legacy renderer; in-flight V1 POST rad etiladi. courses0024 migration kerak. Baholar/publication saqlanadi, AWS qabuli alohida.",
    ),
    FlagDefinition(
        slug="frontend_v1_exam_attempt",
        label="Frontend V1 — imtihon topshirish",
        description="Explicit savol saqlash, versiya va topshirish tasdig‘i bilan exam-focus.",
        default=False, category="Frontend",
        runbook="OFF eski rendererga qaytaradi, V1 javob/start/submit yopiladi; state/receipt va explicit reconcile identity barrier qoladi. Additive schema saqlanadi; AWS/native audio qabuli alohida.",
    ),
    FlagDefinition(
        slug="frontend_v1_exams",
        label="Frontend V1 — imtihonlar markazi va natija",
        description="Imtihonlar ro‘yxati va tasdiqlangan natija; topshirish uchun alohida exam_attempt flag, teacher review hali legacy.",
        default=False,
        category="Frontend",
        runbook="OFF markaz/natija/navni eski ko‘rinishga qaytaradi; publication privacy himoyasi qoladi. Urinish, ball va taymer o‘zgarmaydi. courses0021 migration va AWS release alohida.",
    ),
    FlagDefinition(
        slug="frontend_v1_checkout",
        label="Frontend V1 — checkout va chek holati",
        description="Tarif/promo tekshirish, chek yuborish va pending/success V1 ko‘rinishi.",
        default=False,
        category="Frontend",
        runbook="OFF eski rendererga qaytaradi, to‘lov/accessni emas. In-flight V1 POST yozilmaydi: sahifani qayta ochish kerak. AWS release alohida.",
    ),
    FlagDefinition(
        slug="frontend_v1_editors",
        label="Frontend V1 — kurs va dars muharrirlari",
        description="Kurs list/create/edit, aniq dars tanlovi va dars materiallari uchun V1.",
        default=False,
        category="Frontend",
        runbook="OFF eski rendererga qaytaradi, kontentni emas. In-flight V1 POST snapshot himoyasi qoladi; AWS release qabuli alohida.",
    ),
    FlagDefinition(
        slug="frontend_v1_library",
        label="Frontend V1 — material kutubxonasi",
        description="Kutubxona list/create/edit va scoped lesson picker V1 rendererlarini yoqadi.",
        default=False,
        category="Frontend",
        runbook="OFF eski rendererga qaytaradi; file/link/archive ma’lumotini qaytarmaydi. In-flight V1 POST snapshot himoyasi qoladi. File replacement rollbacki backup talab qiladi.",
    ),
    FlagDefinition(
        slug="frontend_v1_records",
        label="Frontend V1 — yozuvlar va yordam",
        description="Sertifikatlar, davomat, obunalar, reyting, bildirishnomalar va yordam rendererlariga V1.",
        default=False,
        category="Frontend",
        runbook="OFF olti yuzani legacyga qaytaradi; read belgisi, to‘lov/fayl yoki access yozuvi o‘chmaydi. Native POST va eski URLlar ishlashda qoladi. Release qabuli bilan yoqing.",
    ),
    FlagDefinition(
        slug="frontend_v1_auth",
        label="Frontend V1 — ro‘yxatdan o‘tish va tiklash",
        description="Register/onboarding/password-reset va mavjud V1 login ko‘rinishi; canonical auth saqlanadi.",
        default=False,
        category="Frontend",
        runbook="OFF qolgan auth sahifalarini legacyga qaytaradi; login learning flag ON bo‘lsa V1da qoladi. Hisob/parol/token o‘zgarmaydi. SMTP va auth release tekshiruvlaridan keyin yoqing.",
    ),
    FlagDefinition(
        slug="frontend_v1_settings",
        label="Frontend V1 — qolgan sozlamalar",
        description="Maxfiylik, To‘lov va Imkoniyatlar; canonical xotira/preference/quota saqlanadi.",
        default=False,
        category="Frontend",
        runbook="OFF uch settings sahifasining legacy rendererini qaytaradi; ma’lumot saqlanadi. Account/AI flaglaridan mustaqil. ON faqat settings release tekshiruvidan keyin.",
    ),
    FlagDefinition(
        slug="frontend_v1_account",
        label="Frontend V1 — profil va hisob",
        description="Profil va Hisob ko‘rinishi; mavjud profil/avatar/parol endpointlari.",
        default=False,
        category="Frontend",
        runbook="OFF legacy profil/Hisobni qaytaradi, ma’lumot saqlanadi. Boshqa settings mustaqil. ON faqat account release tekshiruvidan keyin.",
    ),
    FlagDefinition(
        slug="frontend_v1_ai_messenger",
        label="Frontend V1 — Azure AI chati",
        description="Keng Messenger B AI ko‘rinishi; mavjud provider va quota o‘zgarmaydi.",
        default=False,
        category="Frontend",
        runbook="OFF eski AI rendererini qaytaradi; xabar/preference saqlanadi. Human chat flagidan mustaqil. ON faqat AI chat release tekshiruvlaridan keyin.",
    ),
    FlagDefinition(
        slug="frontend_v1_public",
        label="Frontend V1 — public sahifalar",
        description="Bosh sahifa, katalog/tarif, about/legal, blog va SIT uchun V1 renderer.",
        default=False,
        category="Frontend",
        runbook="OFF eski public template va assetlarni qaytaradi. Kontent, tarif, publication va access o‘zgarmaydi. ON faqat public release tekshiruvlaridan keyin.",
    ),
    FlagDefinition(
        slug="frontend_v1_messenger",
        label="Frontend V1 — guruh va ustoz chati",
        description="Tasdiqlangan keng Messenger B; AI sahifasi alohida renderer flagi bilan boshqariladi.",
        default=False,
        category="Frontend",
        runbook="OFF eski guruh/ustoz rendererini qaytaradi; xabar va fayllarni o‘chirmaydi. ON faqat chat release tekshiruvlaridan keyin.",
    ),
    FlagDefinition(
        slug="frontend_v1_learning",
        label="Frontend V1 — kirish va kurslarim",
        description="Kirish, o‘quvchi bosh sahifasi va kurslarim uchun V1 ko‘rinishi.",
        default=False,
        category="Frontend",
        runbook=(
            "OFF: dashboard/kurslarim legacy; login auth flag ham OFF bo‘lsa legacy. "
            "ON: Eleventh Trial V1 ko‘rinishi, haqiqiy Django auth/enrollment context. "
            "Ruxsat, progress, baho va ma’lumotlar o‘zgarmaydi. "
            "Faqat tegishli release tekshiruvlaridan keyin yoqing; xatoda o‘chiring."
        ),
    ),
    FlagDefinition(
        slug="frontend_v1_lesson",
        label="Frontend V1 — dars va material",
        description="Matn/video/material, topshiriq va quizli darsning V1 ko‘rinishi.",
        default=False,
        category="Frontend",
        runbook="ON faqat tegishli release tekshiruvidan keyin. OFF eski dars ko‘rinishini qaytaradi; access/material/progress o‘zgarmaydi.",
    ),
    FlagDefinition(
        slug="frontend_v1_teacher",
        label="Frontend V1 — ustoz maydoni",
        description="Ustoz bosh sahifasi, dars ruxsati, yozma ish tekshiruvi, kurs/guruh/o‘quvchi ro‘yxatlari va davomatning V1 ko‘rinishi.",
        default=False,
        category="Frontend",
        runbook="OFF eski ustoz sahifalarini qaytaradi. Release/review yozuvlari saqlanadi. Noto‘g‘ri guruhga fallback hech qaysi variantda ruxsat etilmaydi.",
    ),
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
    FlagDefinition(
        slug="reminder_payment_due",
        label="To'lov muddati eslatmasi",
        description="To'lov muddati yaqinlashganda o'quvchiga eslatma yuboriladimi.",
        default=True,
        category="Eslatmalar",
        runbook=(
            "O'chirilganda eslatma **yaratilmaydi** — obuna muzlagani yoki "
            "muddati tugagani haqidagi xabarlar esa hodisaga javob bo'lgani "
            "uchun ishlashda davom etadi. Necha kun oldin eslatish "
            "sozlamada (`/backoffice/control/runtime-settings/`), bu yerda "
            "faqat yoqish/o'chirish."
        ),
    ),
    FlagDefinition(
        slug="reminder_teacher_review",
        label="O'qituvchi navbati eslatmasi",
        description="Uzoq tekshirilmagan topshiriqlar haqida o'qituvchiga kunlik eslatma.",
        default=True,
        category="Eslatmalar",
        runbook=(
            "O'chirilganda o'qituvchi eslatma olmaydi; navbatning o'zi "
            "(`/baholash` va web teacher paneli) o'zgarmaydi. "
            "Necha kundan keyin eslatish sozlamada."
        ),
    ),
    FlagDefinition(
        slug="ai_onboarding_context",
        label="AI uchun onboarding konteksti",
        description="Xotira yoqilganida foydalanuvchi bildirgan maqsad va darajani AI izohlarida hisobga olish.",
        default=True,
        category="AI",
        runbook=(
            "O'chirilsa onboarding javoblari AI promptiga qo'shilmaydi. "
            "Javoblar profilda saqlanadi; baho, progress va kurs tartibi o'zgarmaydi. "
            "Qo'shimcha provider so'rovi yo'q."
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
