"""Typed entitlement — "bu o'quvchi nimaga haqli?" (A4).

Ilgari bu savol ikkiga bo'lingan edi: enrollment faolmi
(`Enrollment.has_active_access`) va AI token limiti (`aicontrol`). Plan esa
kirish uchun **umuman o'qilmasdi** — Premium to'lagan o'quvchi Starter bilan
bir xil huquq olardi va buni so'raydigan yagona joy yo'q edi.

Ikkita qoida:

* **Plan kodi bo'yicha, nomi bo'yicha emas.** `Plan.name` — ko'rsatiladigan
  matn va uni owner istalgan payt o'zgartiradi; huquq esa `Plan.code` ga
  bog'lanadi. Aks holda nomni tahrirlash kirishni jimgina buzardi.
* **Faollik bitta manbadan.** "Enrollment faolmi" savoli shu yerda qayta
  yozilmaydi — `has_active_access()` chaqiriladi, ya'ni grace day va muddat
  qoidasi bitta joyda qoladi.

**Bu modul narx qarorini qabul qilmaydi.** Qaysi plan nimaga haqli ekani
owner qarori (`rules-for-agents.md`: scope va pricing agentga o'tmaydi).
Shuning uchun hozircha barcha planlar bir xil to'plamni oladi va mavjud xulq
aynan saqlanadi. Mexanizm tayyor; matritsa ownerdan kelganda `PLAN_MATRIX`
to'ldiriladi va o'sha paytda farq testlar bilan mahkamlanadi.
"""

from __future__ import annotations

from enum import Enum


class UnknownCapability(LookupError):
    """Registrda yo'q qobiliyat.

    Jim `False` qaytarish xavfli: xato yozilgan nom huquqni jimgina
    yo'qotardi va buni hech kim sezmasdi.
    """


class Capability(Enum):
    """O'quvchi ega bo'lishi mumkin bo'lgan nomlangan qobiliyatlar."""

    COURSE_CONTENT = ("Dars materiallari", "Ochilgan darslarni ko'rish va o'qish.")
    ASSIGNMENTS = ("Vazifalar", "Vazifa topshirish va baho olish.")
    QUIZZES = ("Testlar", "Dars testlarini yechish.")
    EXAMS = ("Imtihonlar", "Oraliq va yakuniy imtihonlarga kirish.")
    CERTIFICATE = ("Sertifikat", "Kurs tugagach sertifikat olish.")
    AI_TUTOR = ("AI repetitor", "AzureAI bilan suhbat va dars yordami.")
    LIVE_LESSONS = ("Jonli darslar", "Guruh darslari va davomat.")
    TUTOR_CHAT = ("Tutor chati", "O'qituvchi bilan bevosita yozishma.")

    def __init__(self, label, description):
        self.label = label
        self.description = description


#: Kod bilan berilmagan yoki xaritada yo'q plan uchun asos to'plam.
#: Yangi plan qo'shilganda kirish **jimgina yopilib qolmasligi** kerak —
#: kutilmagan yopilish kutilmagan ochilishdan ko'ra ko'proq shikoyat keltiradi
#: va uni topish qiyinroq.
BASELINE = frozenset(Capability)

#: Plan kodi → qobiliyatlar. **Ataylab bo'sh**: farqlash narx qarori.
#: Owner matritsani berganda shu yerga yoziladi.
PLAN_MATRIX: dict[str, frozenset[Capability]] = {}


def plan_entitlements(plan) -> frozenset[Capability]:
    """Plan beradigan qobiliyatlar. Xaritada yo'q bo'lsa — asos to'plam."""
    if plan is None:
        return BASELINE
    return PLAN_MATRIX.get(getattr(plan, "code", "") or "", BASELINE)


def _resolve(capability) -> Capability:
    if isinstance(capability, Capability):
        return capability
    try:
        return Capability[str(capability).upper()]
    except KeyError as exc:
        raise UnknownCapability(f"Bunday qobiliyat yo'q: {capability}") from exc


def entitlements_for(user, *, course=None, today=None) -> frozenset[Capability]:
    """O'quvchining joriy huquqlari.

    `course` berilsa — faqat o'sha kursdagi enrollment hisobga olinadi.
    Faol enrollment bo'lmasa bo'sh to'plam qaytadi.
    """
    if not getattr(user, "is_authenticated", False):
        return frozenset()

    from cohorts.models import Enrollment

    enrollments = (
        Enrollment.objects.filter(student=user)
        .select_related("plan", "cohort")
        .with_active_access(today=today)
    )
    if course is not None:
        enrollments = enrollments.filter(cohort__course=course)

    granted: set[Capability] = set()
    for enrollment in enrollments:
        # `active_plan()`: oldindan to'langan tarif davri boshlanmaguncha
        # huquq bermaydi (`cohorts.models.Enrollment.active_plan`).
        granted |= plan_entitlements(enrollment.active_plan(today=today))
    return frozenset(granted)


def has_entitlement(user, capability, *, course=None, today=None) -> bool:
    """Bitta qobiliyat tekshiruvi. Noma'lum nom `UnknownCapability` beradi."""
    wanted = _resolve(capability)
    return wanted in entitlements_for(user, course=course, today=today)
