from django.db import models
from django.conf import settings
from core.models import TimeStampedModel

class BillingAccount(TimeStampedModel):
    MONTHLY = "MONTHLY"
    FULL = "FULL"
    PAYMENT_MODE_CHOICES = [(MONTHLY, "Monthly"), (FULL, "Full")]

    ACTIVE = "ACTIVE"
    GRACE = "GRACE"
    FROZEN = "FROZEN"
    STATUS_CHOICES = [(ACTIVE, "Active"), (GRACE, "Grace"), (FROZEN, "Frozen")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="billing_account")
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default=MONTHLY)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_so_far = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    next_due_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE)

    def __str__(self):
        return f"{self.user} billing"

class Transaction(TimeStampedModel):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    STATUS_CHOICES = [(PENDING, "Pending"), (APPROVED, "Approved"), (REJECTED, "Rejected")]

    account = models.ForeignKey(BillingAccount, on_delete=models.CASCADE, related_name="transactions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    receipt_image = models.ImageField(upload_to="receipts/")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    month_number = models.PositiveIntegerField(default=1)
    admin_note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.account.user} {self.amount} {self.status}"
