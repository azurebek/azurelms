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
