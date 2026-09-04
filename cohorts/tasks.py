import logging

from celery import shared_task

from .enrollment_service import run_daily_subscription_lifecycle


logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def run_subscription_lifecycle():
    """Beat adapteri. Qadamlar `cohorts.enrollment_service` da."""
    try:
        result = run_daily_subscription_lifecycle()
        logger.info(
            "Subscription lifecycle completed. Expired: %s, promoted plans: %s",
            result.expired, result.promoted,
        )
        return result.expired
    except Exception:
        logger.exception("Subscription lifecycle task failed")
        return None
