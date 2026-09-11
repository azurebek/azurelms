import logging

from celery import shared_task

from users.streak_nudge import send_streak_nudges


logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def run_streak_nudges():
    """Kunlik seriya undash bildirishnomalarini yuboradi (Celery beat)."""
    try:
        sent = send_streak_nudges()
        logger.info("Streak nudges sent: %s", sent)
        return sent
    except Exception:
        logger.exception("run_streak_nudges failed")
        raise


@shared_task(ignore_result=True)
def run_teacher_review_reminders():
    """Uzoq tekshirilmagan topshiriqlar haqida kunlik eslatma (Celery beat, T2)."""
    from users.reminder_service import send_teacher_review_reminders

    try:
        sent = send_teacher_review_reminders()
        logger.info("Teacher review reminders sent: %s", sent)
        return sent
    except Exception:
        logger.exception("run_teacher_review_reminders failed")
        raise
