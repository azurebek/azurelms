from django.core.management.base import BaseCommand

from cohorts.enrollment_service import expire_overdue_enrollments


class Command(BaseCommand):
    help = "Expire active enrollments whose payment deadline is past the grace period."

    def handle(self, *args, **options):
        expired_count = expire_overdue_enrollments()
        self.stdout.write(
            self.style.SUCCESS(f"Expired {expired_count} overdue enrollments.")
        )
