from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import BillingAccount, Transaction


@login_required
def payment_center_view(request):
    account, _ = BillingAccount.objects.get_or_create(user=request.user)
    transactions = account.transactions.order_by("-created_at")

    if request.method == "POST":
        amount_raw = (request.POST.get("amount") or "").strip()
        month_number_raw = (request.POST.get("month_number") or "").strip()
        receipt = request.FILES.get("receipt_image")

        try:
            amount = Decimal(amount_raw)
        except (InvalidOperation, TypeError):
            amount = None

        if amount is None or amount <= 0:
            messages.error(request, "To‘lov summasini to‘g‘ri kiriting.")
            return render(
                request,
                "billing/payment_center.html",
                {"account": account, "transactions": transactions},
            )

        if not receipt:
            messages.error(request, "Chek skrinshotini yuklang.")
            return render(
                request,
                "billing/payment_center.html",
                {"account": account, "transactions": transactions},
            )

        try:
            month_number = int(month_number_raw) if month_number_raw else (transactions.count() + 1)
        except ValueError:
            month_number = transactions.count() + 1

        Transaction.objects.create(
            account=account,
            amount=amount,
            receipt_image=receipt,
            month_number=max(1, month_number),
        )
        messages.success(request, "Chekingiz qabul qilindi. Tez orada tekshiriladi.")
        return redirect("billing:payment_center")

    return render(
        request,
        "billing/payment_center.html",
        {"account": account, "transactions": transactions},
    )
