from users.models import Notification
from users.notification_service import ensure_subscription_notifications_for_user


def notification_context(request):
    if not request.user.is_authenticated:
        return {
            "notifications": [],
            "unread_notifications_count": 0,
        }

    ensure_subscription_notifications_for_user(request.user)

    notifications = list(
        Notification.objects.filter(recipient=request.user)
        .order_by("-created_at")[:8]
    )
    unread_count = sum(1 for n in notifications if not n.is_read)

    return {
        "notifications": notifications,
        "unread_notifications_count": unread_count,
    }
