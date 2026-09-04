from django.core.management.base import BaseCommand

from cohorts.enrollment_service import run_daily_subscription_lifecycle


class Command(BaseCommand):
    help = "Run the daily subscription lifecycle: expire overdue, activate due plans, notify."

    def handle(self, *args, **options):
        result = run_daily_subscription_lifecycle()
        self.stdout.write(
            self.style.SUCCESS(
                f"Subscription notifications generated successfully. "
                f"Expired {result.expired} overdue enrollments. "
                f"Promoted {result.promoted} due plans."
            )
        )
