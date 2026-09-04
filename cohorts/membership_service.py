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
