from datetime import timedelta

from django.contrib import admin, messages
from django.utils import timezone

from .models import BillingAccount, Transaction


@admin.register(BillingAccount)
class BillingAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "payment_mode", "status", "total_price", "paid_so_far", "next_due_date")
    list_filter = ("payment_mode", "status")
    search_fields = ("user__email",)


@admin.action(description="Tasdiqlash (to‘lovni qabul qilish)")
def approve_transactions(modeladmin, request, queryset):
    updated_count = 0
    for transaction in queryset.select_related("account"):
        if transaction.status == Transaction.APPROVED:
            continue
        transaction.status = Transaction.APPROVED
        transaction.save(update_fields=["status"])
        account = transaction.account
        account.paid_so_far = (account.paid_so_far or 0) + transaction.amount
        if account.payment_mode == BillingAccount.MONTHLY:
            account.next_due_date = (account.next_due_date or timezone.localdate()) + timedelta(days=30)
        account.status = BillingAccount.ACTIVE
        account.save(update_fields=["paid_so_far", "next_due_date", "status"])
        if transaction.batch:
             # Create enrollment
             from education.models import Enrollment
             Enrollment.objects.get_or_create(
                 user=account.user, 
                 batch=transaction.batch,
                 defaults={"is_active": True}
             )

        updated_count += 1
    if updated_count:
        modeladmin.message_user(
            request,
            f"{updated_count} ta chek tasdiqlandi.",
            messages.SUCCESS,
        )
    else:
        modeladmin.message_user(
            request,
            "Tasdiqlash uchun yangi chek topilmadi.",
            messages.WARNING,
        )


@admin.action(description="Rad etish (sababsiz)")
def reject_transactions(modeladmin, request, queryset):
    updated_count = queryset.exclude(status=Transaction.REJECTED).update(status=Transaction.REJECTED)
    if updated_count:
        modeladmin.message_user(
            request,
            f"{updated_count} ta chek rad etildi.",
            messages.WARNING,
        )
    else:
        modeladmin.message_user(request, "Rad etiladigan chek topilmadi.", messages.INFO)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("account", "amount", "status", "month_number", "created_at")
    list_filter = ("status",)
    search_fields = ("account__user__email",)
    actions = [approve_transactions, reject_transactions]
