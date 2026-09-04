"""O'quvchi tarif farqi uchun chek yuklaydi.

Ayrim yuza emas, mavjud oqimning davomi: so'rov `PaymentReceipt` sifatida
yaratilgan (summasi bor, rasmi yo'q), bu yerda unga rasm biriktiriladi,
tasdiqlash esa odatdagi to'lov cheklari sahifasida bo'ladi.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from core.upload_validation import validate_upload

from .models import PaymentReceipt


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
    upload = request.FILES.get("receipt_image")
    if not upload:
        messages.error(request, "Chek rasmini tanlang.")
        return redirect("subscriptions")
    try:
        validate_upload(upload)
    except Exception as exc:  # ValidationError va boshqa validator xatolari
        messages.error(request, str(exc))
        return redirect("subscriptions")

    receipt.receipt_image = upload
    # Faqat rasm: billing maydonlari o'zgarmas (`BILLING_FIELDS`).
    receipt.save(update_fields=["receipt_image"])
    messages.success(request, "Chek yuborildi. Tasdiqlanishini kuting.")
    return redirect("subscriptions")
