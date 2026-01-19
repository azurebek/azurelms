from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from billing.models import BillingAccount


class Command(BaseCommand):
    help = "BillingAccount holatlarini yangilash (Grace/Frozen)."

    def handle(self, *args, **options):
        today = timezone.localdate()
        grace_count = 0
        frozen_count = 0

        accounts = BillingAccount.objects.exclude(next_due_date__isnull=True)
        for account in accounts:
            if account.payment_mode != BillingAccount.MONTHLY:
                continue
            if account.next_due_date == today and account.status != BillingAccount.GRACE:
                account.status = BillingAccount.GRACE
                account.save(update_fields=["status"])
                grace_count += 1
                continue
            grace_end = account.next_due_date + timedelta(days=3)
            if today > grace_end and account.status != BillingAccount.FROZEN:
                account.status = BillingAccount.FROZEN
                account.save(update_fields=["status"])
                frozen_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Grace: {grace_count}, Frozen: {frozen_count} hisob yangilandi."
            )
        )
