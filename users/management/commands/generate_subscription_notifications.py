from django.core.management.base import BaseCommand

from users.notification_service import ensure_subscription_notifications_for_all_users


class Command(BaseCommand):
    help = "Generate subscription reminder/frozen/expired notifications for all active users."

    def handle(self, *args, **options):
        ensure_subscription_notifications_for_all_users()
        self.stdout.write(self.style.SUCCESS("Subscription notifications generated successfully."))
