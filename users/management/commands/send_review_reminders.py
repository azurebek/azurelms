"""Uzoq tekshirilmagan topshiriqlar haqida o'qituvchiga eslatma yuboradi (T2).

    python manage.py send_review_reminders

Beat adapteri `users/tasks.py::run_teacher_review_reminders`; mantiq
`users/reminder_service.py` da. Buyruq qo'lda tekshirish va serverda bir
martalik yugurtirish uchun.
"""

from django.core.management.base import BaseCommand

from users.reminder_service import send_teacher_review_reminders


class Command(BaseCommand):
    help = "Tekshiruv navbati bo'yicha o'qituvchilarga kunlik eslatma"

    def handle(self, *args, **options):
        sent = send_teacher_review_reminders()
        self.stdout.write(self.style.SUCCESS(f"Tekshiruv eslatmalari: {sent}"))
