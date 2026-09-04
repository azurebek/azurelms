"""Guruh a'zoligi bo'yicha owner qarori — joyni bo'shatish va qaytarish.

Audit paytida topilgan bo'shliq: joyni band qiladigan a'zolik faqat
**avtomatik** o'zgarardi. To'lov tasdiqlansa `active`, muddati o'tsa
`expired` — ikkalasi ham kod tomonidan. Odam qaror qiladigan yagona yo'l
eski Django admin edi, u esa default o'chiq (`ENABLE_LEGACY_ADMIN=False`,
`/admin/` → 404). `frozen` holati esa faqat guruhdan guruhga ko'chirishning
yon ta'siri sifatida qo'yilardi.

Oqibati: muddati o'tgan a'zolik joyni saqlab qolardi (bu ataylab — bir kun
kechikkan o'quvchi o'rnini yo'qotmasligi kerak), ammo qaytmaydigan
o'quvchining joyini **hech kim** bo'shata olmasdi. Guruh to'lib qolib
sotuvni jimgina to'xtatardi.

Bu servis qaror nuqtasini owner qo'liga qaytaradi. Ikkita himoya ataylab:

* **kirishi ochiq a'zolik bo'shatilmaydi** — to'lagan o'quvchining kirishi
  tasodifan uzilmasin. Muddati tugashini kutish yoki pulni qaytarish
  boshqa qaror;
* **qaytarish joyni tekshiradi** — bo'shatilgan joy boshqasiga sotilgan
  bo'lsa, a'zolik jimgina sig'imdan oshib ketmaydi.
"""

from dataclasses import dataclass

from django.db import transaction

from aicontrol.models import SystemAuditEvent
from core.audit import record_audit_event
from users.models import Notification


@dataclass
class MembershipDecision:
    ok: bool
    code: str
    message: str


def _actor_may_decide(actor):
    """Faol staff yoki superuser — `receipt_service` bilan bir xil qoida."""
    return bool(actor and actor.is_active and (actor.is_staff or actor.is_superuser))


def _display_name(user):
    full = f"{user.first_name} {user.last_name}".strip()
    return full or user.username


def _denied(action, enrollment_id, actor, request):
    record_audit_event(
        action=action,
        request=request,
        actor=actor if getattr(actor, "pk", None) else None,
        source=SystemAuditEvent.SOURCE_WEB,
        outcome=SystemAuditEvent.OUTCOME_DENIED,
        target_label=f"A'zolik #{enrollment_id}",
        error="Ruxsat yo'q.",
    )
    return MembershipDecision(ok=False, code="forbidden", message="Ruxsat yo'q.")


@transaction.atomic
def release_seat(enrollment_id, actor, *, reason="", request=None):
    """A'zolikni muzlatadi va joyni bo'shatadi."""
    from .delivery_service import lock_enrollment
    from .models import Enrollment

    if not _actor_may_decide(actor):
        return _denied("membership.release", enrollment_id, actor, request)

    enrollment = lock_enrollment(enrollment_id)
    if enrollment.status == Enrollment.STATUS_FROZEN:
        return MembershipDecision(
            ok=True, code="already", message="Bu a'zolik allaqachon muzlatilgan."
        )
    if enrollment.has_active_access():
        # To'lagan o'quvchining kirishini tasodifan uzib qo'ymaslik uchun.
        return MembershipDecision(
            ok=False,
            code="access_open",
            message=(
                "Bu o'quvchining to'lovi hali amal qiladi. Muddati tugashini kuting "
                "yoki pulni qaytarish masalasini alohida hal qiling."
            ),
        )

    status_before = enrollment.status
    enrollment.status = Enrollment.STATUS_FROZEN
    enrollment.save(update_fields=["status"])
    record_audit_event(
        action="membership.release",
        request=request,
        actor=actor,
        source=SystemAuditEvent.SOURCE_WEB,
        target=enrollment,
        target_label=f"A'zolik #{enrollment.id} — {enrollment.student.username}",
        reason=reason,
        before={"status": status_before},
        after={"status": enrollment.status, "cohort": enrollment.cohort.name},
    )
    Notification.objects.create(
        recipient=enrollment.student,
        title="Guruhdagi o'rningiz bo'shatildi",
        message=(
            f"\"{enrollment.cohort.course.title}\" kursidagi a'zoligingiz to'xtatildi, "
            f"chunki obuna uzoq vaqt yangilanmadi. Qaytishni istasangiz, qayta "
            f"yozilishingiz mumkin — joy bo'lsa o'rin ajratiladi."
        ),
        icon="pause-circle",
        category=Notification.CATEGORY_SUBSCRIPTION,
    )
    return MembershipDecision(
        ok=True,
        code="released",
        message=f"Joy bo'shatildi: {_display_name(enrollment.student)}",
    )


@transaction.atomic
def transfer_member(
    enrollment_id, target_cohort_id, actor, *, reason="", request=None, allow_tier_change=False,
):
    """O'quvchini shu kursning boshqa guruhiga ko'chiradi.

    Ilgari bu amal faqat eski Django adminda bor edi, u esa o'chiq. Ya'ni
    checkout "Tarifni almashtirish uchun administrator orqali mos guruhga
    o'ting" deb yozardi, administratorda esa hech qanday yo'l yo'q edi.

    `allow_tier_change` — narx qaroriga tegadigan qadam, shuning uchun
    ataylab beriladi. Tizim narx farqini **hisoblamaydi**: yangi tarif
    joriy davr oxirigacha ishlaydi va farqni owner odatdagi to'lov oqimi
    orqali oladi.
    """
    from .models import Cohort, Enrollment
    from .transition_service import EnrollmentTransitionError, transfer_enrollment_to_cohort

    if not _actor_may_decide(actor):
        return _denied("membership.transfer", enrollment_id, actor, request)

    enrollment = Enrollment.objects.filter(pk=enrollment_id).select_related("cohort").first()
    target = Cohort.objects.filter(pk=target_cohort_id).select_related("plan").first()
    if enrollment is None or target is None:
        return MembershipDecision(ok=False, code="missing", message="Guruh yoki a'zolik topilmadi.")

    try:
        result = transfer_enrollment_to_cohort(
            source_enrollment=enrollment, target_cohort=target,
            created_by=actor, note=reason, allow_tier_change=allow_tier_change,
        )
    except EnrollmentTransitionError as exc:
        record_audit_event(
            action="enrollment.transfer",
            request=request,
            actor=actor,
            source=SystemAuditEvent.SOURCE_WEB,
            outcome=SystemAuditEvent.OUTCOME_FAILURE,
            target=enrollment,
            target_label=f"A'zolik #{enrollment_id} → {target.name}",
            reason=reason,
            error=str(exc),
        )
        return MembershipDecision(ok=False, code="refused", message=str(exc))

    suffix = " (tarif ham o'zgardi)" if allow_tier_change else ""
    return MembershipDecision(
        ok=True,
        code="transferred",
        message=f"Ko'chirildi: {_display_name(enrollment.student)} → {target.name}{suffix}",
    )


def suggest_difference_amount(enrollment, *, today=None):
    """Tarif farqi uchun taklif qilinadigan summa (yoki `None`).

    Hisob oddiy va tushuntirsa bo'ladigan: qolgan kunlar × (yangi tarif
    kunlik narxi − eski tarif kunlik narxi), 30 kunlik davr bo'yicha, 1000
    so'mgacha yaxlitlanadi. Bu **taklif**, majburiy raqam emas — owner
    formada o'zgartira oladi, chunki chegirma yoki kelishuv bo'lishi mumkin.

    Eski tarif muzlatilgan a'zolikdan olinadi: ko'chirishda manba a'zolik
    o'z tarifi bilan qoladi (`transition_service`).
    """
    from decimal import Decimal

    from django.utils import timezone

    from .models import Enrollment

    previous = (
        Enrollment.objects.filter(
            student_id=enrollment.student_id,
            cohort__course_id=enrollment.cohort.course_id,
            status=Enrollment.STATUS_FROZEN,
            plan__isnull=False,
        )
        .exclude(pk=enrollment.pk)
        .select_related("plan")
        .order_by("-id")
        .first()
    )
    return difference_between(
        new_plan=enrollment.active_plan(),
        previous_plan=previous.plan if previous else None,
        deadline=enrollment.next_payment_deadline,
        today=today,
    )


def difference_between(*, new_plan, previous_plan, deadline, today=None):
    """Hisobning o'zi — ro'yxat sahifasi uni ommaviy ma'lumot bilan chaqiradi.

    Alohida turishining sababi: a'zolar ro'yxatida har bir qator uchun
    alohida so'rov yugurtirmaslik kerak, shuning uchun eski tarif va muddat
    tashqaridan beriladi.
    """
    from decimal import Decimal

    from django.utils import timezone

    today = today or timezone.localdate()
    if new_plan is None or previous_plan is None or not deadline:
        return None
    if previous_plan.pk == new_plan.pk:
        return None
    days_left = (deadline - today).days
    if days_left <= 0:
        return None
    gap = Decimal(new_plan.price) - Decimal(previous_plan.price)
    if gap <= 0:
        return None
    amount = gap / Decimal(30) * Decimal(min(days_left, 30))
    return int(amount / 1000) * 1000


@transaction.atomic
def request_tier_difference(enrollment_id, actor, *, amount, reason="", request=None):
    """Tarif farqi uchun to'lov so'rovini yaratadi.

    So'rov — bu chekning o'zi: summasi ma'lum, rasmi hali yo'q. O'quvchi
    to'lovlar sahifasida chek rasmini yuklaydi, owner esa odatdagi to'lov
    cheklari sahifasida tasdiqlaydi. Ya'ni yangi qaror yuzasi yaratilmaydi.

    Farq to'lovi davrni uzaytirmaydi va tarifni o'zgartirmaydi
    (`PaymentReceipt.save`): tarif allaqachon ko'chirishda o'zgargan.
    """
    from django.db import IntegrityError

    from .delivery_service import lock_enrollment
    from .models import PaymentReceipt

    if not _actor_may_decide(actor):
        return _denied("receipt.difference.request", enrollment_id, actor, request)

    amount = int(amount or 0)
    if amount <= 0:
        return MembershipDecision(ok=False, code="amount", message="Summa musbat bo'lishi kerak.")

    enrollment = lock_enrollment(enrollment_id)
    plan = enrollment.active_plan()
    try:
        with transaction.atomic():
            receipt = PaymentReceipt.objects.create(
                enrollment=enrollment,
                plan=plan,
                kind=PaymentReceipt.KIND_DIFFERENCE,
                amount=amount,
                base_amount=amount,
            )
    except IntegrityError:
        # `unique_pending_receipt_per_enrollment` endi turni ham hisobga
        # oladi: bitta a'zolikda bir vaqtda bitta ochiq farq so'rovi.
        return MembershipDecision(
            ok=False, code="already",
            message="Bu o'quvchida ochiq farq to'lovi allaqachon bor.",
        )

    record_audit_event(
        action="receipt.difference.request",
        request=request,
        actor=actor,
        source=SystemAuditEvent.SOURCE_WEB,
        target=receipt,
        target_label=f"Farq #{receipt.id} — {enrollment.student.username}",
        reason=reason,
        after={"amount": str(amount), "plan": getattr(plan, "code", "")},
    )
    Notification.objects.create(
        recipient=enrollment.student,
        title="Tarif farqi uchun to'lov",
        message=(
            f"\"{enrollment.cohort.course.title}\" kursida tarifingiz o'zgardi. "
            f"Farq uchun {amount} so'm to'lash kerak. To'lovlar sahifasida chekni yuklang."
        ),
        icon="cash-coin",
        url="/users/subscriptions/",
        category=Notification.CATEGORY_SUBSCRIPTION,
    )
    return MembershipDecision(
        ok=True,
        code="requested",
        message=f"Farq so'rovi yuborildi: {_display_name(enrollment.student)} — {amount} so'm",
    )


@transaction.atomic
def restore_seat(enrollment_id, actor, *, reason="", request=None):
    """Muzlatilgan a'zolikni guruhga qaytaradi — joy bo'lsa."""
    from django.core.exceptions import ValidationError

    from .delivery_service import lock_enrollment
    from .models import Enrollment

    if not _actor_may_decide(actor):
        return _denied("membership.restore", enrollment_id, actor, request)

    enrollment = lock_enrollment(enrollment_id)
    if enrollment.status != Enrollment.STATUS_FROZEN:
        return MembershipDecision(
            ok=False, code="not_frozen", message="Bu a'zolik muzlatilgan emas."
        )

    # To'lov qilinmagani uchun `expired`: qayta to'lov oqimi uni `active`
    # qiladi. `save()` sig'imni tekshiradi — bo'shagan joy sotilgan bo'lishi
    # mumkin.
    enrollment.status = Enrollment.STATUS_EXPIRED
    try:
        enrollment.save(update_fields=["status"])
    except ValidationError as exc:
        message = " ".join(exc.messages)
        record_audit_event(
            action="membership.restore",
            request=request,
            actor=actor,
            source=SystemAuditEvent.SOURCE_WEB,
            outcome=SystemAuditEvent.OUTCOME_FAILURE,
            target=enrollment,
            target_label=f"A'zolik #{enrollment_id}",
            reason=reason,
            error=message,
        )
        return MembershipDecision(ok=False, code="cohort_full", message=message)

    record_audit_event(
        action="membership.restore",
        request=request,
        actor=actor,
        source=SystemAuditEvent.SOURCE_WEB,
        target=enrollment,
        target_label=f"A'zolik #{enrollment.id} — {enrollment.student.username}",
        reason=reason,
        before={"status": Enrollment.STATUS_FROZEN},
        after={"status": enrollment.status, "cohort": enrollment.cohort.name},
    )
    return MembershipDecision(
        ok=True,
        code="restored",
        message=f"A'zolik qaytarildi: {_display_name(enrollment.student)}",
    )
