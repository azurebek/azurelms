"""O'quvchi tarif farqi uchun chek yuklaydi.

Ayrim yuza emas, mavjud oqimning davomi: so'rov `PaymentReceipt` sifatida
yaratilgan (summasi bor, rasmi yo'q), bu yerda unga rasm biriktiriladi,
tasdiqlash esa odatdagi to'lov cheklari sahifasida bo'ladi.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from core.upload_validation import validate_upload
from core.flags import flag_enabled

from .models import PaymentReceipt
from .delivery_service import lock_enrollment


@login_required
@require_POST
def upload_difference_receipt(request, receipt_id):
    receipt = get_object_or_404(
        PaymentReceipt,
        pk=receipt_id,
        kind=PaymentReceipt.KIND_DIFFERENCE,
        is_verified=False,
        enrollment__student=request.user,
    )
    v1 = flag_enabled('frontend_v1_checkout') or request.POST.get('frontend_v1_checkout') == '1'
    if v1 and not flag_enabled('frontend_v1_checkout'):
        messages.error(request, 'To‘lov sahifasi yangilandi. Chek yuborilmadi; qayta oching.')
        return redirect('subscriptions')
    upload = request.FILES.get("receipt_image")
    if not upload:
        messages.error(request, "Chek rasmini tanlang.")
        return redirect("subscriptions")
    try:
        validate_upload(upload, profile='image' if v1 else 'document')
    except Exception as exc:  # ValidationError va boshqa validator xatolari
        messages.error(request, str(exc))
        return redirect("subscriptions")

    if v1:
        # Keep the same writer, but never replace evidence from a second tab
        # or attach a file after the owner has already made a decision.
        with transaction.atomic():
            lock_enrollment(receipt.enrollment_id)
            receipt = get_object_or_404(PaymentReceipt.objects.select_for_update(),
                                      pk=receipt_id, is_verified=False,
                                      kind=PaymentReceipt.KIND_DIFFERENCE,
                                      enrollment__student=request.user)
            if not receipt.receipt_image:
                receipt.receipt_image = upload
                receipt.save(update_fields=['receipt_image'])
        return redirect('cohorts:checkout_pending', receipt_id=receipt.pk)
    receipt.receipt_image = upload
    # Faqat rasm: billing maydonlari o'zgarmas (`BILLING_FIELDS`).
    receipt.save(update_fields=["receipt_image"])
    messages.success(request, "Chek yuborildi. Tasdiqlanishini kuting.")
    return redirect("subscriptions")
