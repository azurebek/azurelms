from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from .models import Enrollment


@dataclass
class DailyLifecycleResult:
    expired: int
    promoted: int


def run_daily_subscription_lifecycle(*, today=None):
    """Kunlik obuna xizmati — yagona ta'rif.

    Ilgari bu ish uchta joyda alohida yozilgan edi va uchtasi uch xil
    qadamni bajarardi: Celery vazifasi muddatni yopib bildirishnoma
    yuborardi, `expire_overdue_enrollments` buyrug'i esa tarifni ko'chirardi
    va bildirishnoma yubormasdi. Production'da faqat Celery yuguradi, ya'ni
    buyruqqa qo'shilgan qadam hech qachon ishlamasdi.

    Bu "bir boshqaruv nuqtasi, ko'p adapter" qoidasining buzilishi edi:
    adapterlar qadamlarni o'zlari sanab chiqardi. Endi qadamlar shu yerda,
    adapterlar esa faqat chaqiradi va natijani ko'rsatadi.

    Tartib ataylab: avval muddati o'tganini yopish, keyin davri kelgan
    tarifni yoqish, oxirida bildirishnoma — shunda o'quvchi eng so'nggi
    holat bo'yicha xabar oladi.
    """
    from users.notification_service import ensure_subscription_notifications_for_all_users

    expired = expire_overdue_enrollments(today=today)
    promoted = promote_due_plans(today=today)
    ensure_subscription_notifications_for_all_users()
    return DailyLifecycleResult(expired=expired, promoted=promoted)


def promote_due_plans(*, queryset=None, today=None):
    """Davri boshlangan tarifni `Enrollment.plan` ustuniga ko'chiradi.

    `active_plan()` o'qishda allaqachon to'g'ri javob beradi, ya'ni bu ish
    kirish huquqi uchun shart emas. Lekin denormalizatsiyalangan ustunni
    to'g'ri holatga keltiradi: backoffice ro'yxatlari va plan bo'yicha
    ommaviy amallar (`aicontrol` plan-scope reset) uni to'g'ridan-to'g'ri
    o'qiydi.
    """
    today = today or timezone.localdate()
    base_queryset = queryset if queryset is not None else Enrollment.objects.all()
    candidates = (
        base_queryset.filter(
            receipts__is_verified=True,
            receipts__plan__isnull=False,
            receipts__period_start__lte=today,
        )
        .select_related("plan")
        .distinct()
    )
    promoted = 0
    for enrollment in candidates:
        plan = enrollment.active_plan(today=today)
        if plan is not None and plan.pk != enrollment.plan_id:
            enrollment.plan = plan
            # Faqat shu ustun: parallel to'lov/transfer natijasi bosilmasin.
            enrollment.save(update_fields=["plan"])
            promoted += 1
    return promoted


def expire_overdue_enrollments(*, queryset=None, today=None, grace_days=Enrollment.ACCESS_GRACE_DAYS):
    base_queryset = queryset if queryset is not None else Enrollment.objects.all()
    overdue_enrollments = list(
        base_queryset.overdue_for_expiration(today=today, grace_days=grace_days).select_related("student")
    )
    if not overdue_enrollments:
        return 0

    enrollment_ids = [enrollment.id for enrollment in overdue_enrollments]
    with transaction.atomic():
        Enrollment.objects.filter(id__in=enrollment_ids).update(status=Enrollment.STATUS_EXPIRED)

    from messenger.access import sync_student_chat_access

    synced_student_ids = set()
    for enrollment in overdue_enrollments:
        enrollment.status = Enrollment.STATUS_EXPIRED
        if enrollment.student_id in synced_student_ids:
            continue
        sync_student_chat_access(enrollment.student)
        synced_student_ids.add(enrollment.student_id)

    return len(enrollment_ids)
