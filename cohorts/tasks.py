import logging

from celery import shared_task

from users.notification_service import ensure_subscription_notifications_for_all_users

from .enrollment_service import expire_overdue_enrollments


logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def run_subscription_lifecycle():
    try:
        expired_count = expire_overdue_enrollments()
        ensure_subscription_notifications_for_all_users()
        logger.info("Subscription lifecycle completed. Expired overdue enrollments: %s", expired_count)
        return expired_count
    except Exception:
        logger.exception("Subscription lifecycle task failed")
        return None
