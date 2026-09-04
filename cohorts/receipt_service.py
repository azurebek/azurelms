"""To'lov chekini tasdiqlash va rad etish — yagona canonical qaror nuqtasi.

Bu mantiq `bot/services.py` da yashagan edi, ya'ni **pulga tegadigan yagona
qaror adapter ichida** turardi. Oqibati amaliy bo'lib chiqdi: Django admin
default o'chiq (`ENABLE_LEGACY_ADMIN=False`, `/admin/` → 404), backoffice esa
kutayotgan cheklarni faqat **ko'rsatardi**. Ya'ni chekni tasdiqlashning
yagona yo'li Telegram bot edi — bot ishlamasa yoki owner hisobi ulanmagan
bo'lsa, kelgan pulni qabul qilib bo'lmasdi.

Endi qaror shu yerda, `source` esa kim chaqirganini bildiradi (bot yoki web).
Ikkala yuza ham bir xil ruxsat tekshiruvi, bir xil audit yozuvi va bir xil
bildirishnomani oladi.

Uchta xususiyat ataylab saqlangan:

* **ruxsatsiz urinish ham auditga tushadi** — pulga tegadigan qarorga kim
  urinib ko'rgani ko'rinishi kerak;
* **idempotent** — allaqachon tasdiqlangan chek qayta tasdiqlanmaydi va
  ikkinchi marta muddat uzaytirmaydi;
* **rad etishda promo bo'shatiladi** — `PaymentReceipt.delete()` band
  qilingan promo kodni qaytaradi, ya'ni kod yana ishlatilishi mumkin.
"""

from dataclasses import dataclass

from django.db import transaction
from django.core.exceptions import ValidationError

from users.models import Notification


@dataclass
class ReceiptDecision:
    ok: bool
    code: str
    message: str


def _display_name(user):
    full = f"{user.first_name} {user.last_name}".strip()
    return full or user.username


def _actor_may_decide(actor):
    """Faol staff yoki superuser.

    `is_active` ataylab tekshiriladi: bloklangan xodim to'lov qarorini
    qabul qila olmasligi kerak (A0a).
    """
    return bool(actor and actor.is_active and (actor.is_staff or actor.is_superuser))


def _decision_receipt(receipt_id, *, lock):
    """Bir qaror g'olib bo'ladi: cohort -> enrollment -> receipt."""
    from cohorts.models import Enrollment, PaymentReceipt

    enrollment_id = PaymentReceipt.objects.filter(pk=receipt_id).values_list("enrollment_id", flat=True).first()
    if enrollment_id is None:
        return None
    if lock:
        from .delivery_service import lock_enrollment
        lock_enrollment(enrollment_id)
    receipts = PaymentReceipt.objects.all()
    if lock:
        receipts = receipts.select_for_update()
    return receipts.filter(pk=receipt_id).first()


@transaction.atomic
def verify_receipt(receipt_id, actor, *, source=None, reason="", request=None):
    """Chekni tasdiqlaydi. `PaymentReceipt.save()` enrollmentni faollashtiradi."""
    from aicontrol.models import SystemAuditEvent
    from cohorts.models import PaymentReceipt
    from core.audit import record_audit_event

    source = source or SystemAuditEvent.SOURCE_BOT
    receipt = _decision_receipt(receipt_id, lock=_actor_may_decide(actor))

    if not _actor_may_decide(actor):
        # Ruxsatsiz urinish ham izsiz qolmaydi: pulga tegadigan yagona qaror
        # shu, va kim urinib ko'rgani ko'rinishi kerak (A2 / §3).
        record_audit_event(
            action="receipt.verify",
            request=request,
            actor=actor if getattr(actor, "pk", None) else None,
            source=source,
            outcome=SystemAuditEvent.OUTCOME_DENIED,
            target=receipt,
            target_label=f"Chek #{receipt_id}",
            error="Ruxsat yo'q.",
        )
        return ReceiptDecision(ok=False, code="forbidden", message="Ruxsat yo'q.")
    if not receipt:
        return ReceiptDecision(ok=False, code="missing", message="Chek topilmadi.")
    if receipt.is_verified:
        return ReceiptDecision(
            ok=True, code="already", message="Bu chek allaqachon tasdiqlangan."
        )

    enrollment_status_before = receipt.enrollment.status
    plan_before = receipt.enrollment.plan_id
    try:
        with transaction.atomic():
            receipt.is_verified = True
            receipt.save()
    except ValidationError as exc:
        message = " ".join(exc.messages)
        record_audit_event(
            action="receipt.verify", request=request, actor=actor, source=source,
            outcome=SystemAuditEvent.OUTCOME_DENIED, target=receipt,
            target_label=f"Chek #{receipt.id}", reason=reason, error=message,
        )
        return ReceiptDecision(ok=False, code=getattr(exc, "code", None) or "unavailable", message=message)
    with transaction.atomic():
        receipt.enrollment.refresh_from_db()
        record_audit_event(
            action="receipt.verify",
            request=request,
            actor=actor,
            source=source,
            target=receipt,
            target_label=f"Chek #{receipt.id} — {receipt.enrollment.student.username}",
            reason=reason,
            before={"is_verified": False, "enrollment_status": enrollment_status_before, "plan_id": plan_before},
            after={
                "is_verified": True,
                "enrollment_status": receipt.enrollment.status,
                "amount": str(receipt.amount),
                "plan_id": receipt.plan_id,
                "plan_code": receipt.plan_code_snapshot,
                "plan_name": receipt.plan_name_snapshot,
                "plan_snapshot_source": receipt.plan_snapshot_source,
            },
        )

    student = receipt.enrollment.student
    course_title = receipt.enrollment.cohort.course.title
    is_difference = receipt.kind == PaymentReceipt.KIND_DIFFERENCE
    Notification.objects.create(
        recipient=student,
        title="To'lov tasdiqlandi ✅",
        message=(
            # Farq to'lovi muddatni uzaytirmaydi — xabar buni va'da qilmasin.
            f"\"{course_title}\" kursi bo'yicha tarif farqi uchun "
            f"{int(receipt.amount)} so'mlik to'lovingiz tasdiqlandi."
            if is_difference else
            f"\"{course_title}\" kursi uchun {int(receipt.amount)} so'mlik to'lovingiz "
            f"tasdiqlandi. Kursga kirish ochiq — omad!"
        ),
        icon="check-circle",
        url=f"/courses/{receipt.enrollment.cohort.course_id}/",
        category=Notification.CATEGORY_SUBSCRIPTION,
    )
    return ReceiptDecision(
        ok=True,
        code="verified",
        message=f"✅ Tasdiqlandi: {_display_name(student)} — {course_title}",
    )


@transaction.atomic
def reject_receipt(receipt_id, actor, *, source=None, reason="", request=None):
    """Chekni rad etadi — yozuv o'chadi, band qilingan promo bo'shatiladi."""
    from aicontrol.models import SystemAuditEvent
    from core.audit import record_audit_event

    source = source or SystemAuditEvent.SOURCE_BOT
    receipt = _decision_receipt(receipt_id, lock=_actor_may_decide(actor))

    if not _actor_may_decide(actor):
        record_audit_event(
            action="receipt.reject",
            request=request,
            actor=actor if getattr(actor, "pk", None) else None,
            source=source,
            outcome=SystemAuditEvent.OUTCOME_DENIED,
            target=receipt,
            target_label=f"Chek #{receipt_id}",
            error="Ruxsat yo'q.",
        )
        return ReceiptDecision(ok=False, code="forbidden", message="Ruxsat yo'q.")
    if not receipt or receipt.is_verified:
        return ReceiptDecision(
            ok=False,
            code="missing",
            message="Chek topilmadi yoki allaqachon tasdiqlangan.",
        )

    student = receipt.enrollment.student
    course_title = receipt.enrollment.cohort.course.title
    receipt_id_snapshot = receipt.id
    amount_snapshot = str(receipt.amount)

    with transaction.atomic():
        record_audit_event(
            action="receipt.reject",
            request=request,
            actor=actor,
            source=source,
            target=receipt,
            target_label=f"Chek #{receipt_id_snapshot} — {student.username}",
            reason=reason,
            before={
                "is_verified": False, "amount": amount_snapshot,
                "plan_code": receipt.plan_code_snapshot,
                "plan_name": receipt.plan_name_snapshot,
                "base_amount": str(receipt.base_amount),
                "discount_amount": str(receipt.discount_amount),
                "period_start": str(receipt.period_start), "period_end": str(receipt.period_end),
                "plan_snapshot_source": receipt.plan_snapshot_source,
            },
            after={"deleted": True},
        )
        # `delete()` band qilingan promo kodni bo'shatadi (`PaymentReceipt.delete`).
        receipt.delete()

    Notification.objects.create(
        recipient=student,
        title="To'lov cheki rad etildi",
        message=(
            f"\"{course_title}\" kursi uchun yuborgan chekingiz qabul qilinmadi. "
            f"To'lovni tekshirib, chekni qayta yuboring yoki administratorga murojaat qiling."
        ),
        icon="x-circle",
        category=Notification.CATEGORY_SUBSCRIPTION,
    )
    return ReceiptDecision(
        ok=True,
        code="rejected",
        message=f"❌ Rad etildi: {_display_name(student)} — {course_title}",
    )
