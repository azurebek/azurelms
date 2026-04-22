from django.core.management.base import BaseCommand

from cohorts.enrollment_service import expire_overdue_enrollments
from users.notification_service import ensure_subscription_notifications_for_all_users


class Command(BaseCommand):
    help = "Generate subscription reminder/frozen/expired notifications for all active users."

    def handle(self, *args, **options):
        expired_count = expire_overdue_enrollments()
        ensure_subscription_notifications_for_all_users()
        self.stdout.write(
            self.style.SUCCESS(
                f"Subscription notifications generated successfully. Expired {expired_count} overdue enrollments."
            )
        )
