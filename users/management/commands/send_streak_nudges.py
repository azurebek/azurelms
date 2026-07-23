from django.core.management.base import BaseCommand

from users.streak_nudge import send_streak_nudges


class Command(BaseCommand):
    help = "Xavf ostidagi/uzilgan seriyalar uchun mascot undash bildirishnomalarini yuboradi."

    def handle(self, *args, **options):
        sent = send_streak_nudges()
        self.stdout.write(self.style.SUCCESS(f"Streak nudges sent: {sent}"))
