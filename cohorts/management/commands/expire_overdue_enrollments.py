from django.core.management.base import BaseCommand

from cohorts.enrollment_service import expire_overdue_enrollments, promote_due_plans


class Command(BaseCommand):
    help = "Expire active enrollments whose payment deadline is past the grace period."

    def handle(self, *args, **options):
        expired_count = expire_overdue_enrollments()
        # Kunlik obuna xizmati: muddati o'tganini yopadi, davri kelganini ochadi.
        promoted_count = promote_due_plans()
        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {expired_count} overdue enrollments. "
                f"Promoted {promoted_count} due plans."
            )
        )
