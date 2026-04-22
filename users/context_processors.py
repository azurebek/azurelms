from users.models import Notification
from cohorts.models import enrollment_active_access_q


def notification_context(request):
    if not request.user.is_authenticated:
        return {
            "notifications": [],
            "unread_notifications_count": 0,
            "sidebar_current_plan": None,
        }

    notifications = list(
        Notification.objects.filter(recipient=request.user)
        .order_by("-created_at")[:8]
    )
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    sidebar_plan_enrollment = (
        request.user.enrollments.filter(enrollment_active_access_q(), plan__isnull=False)
        .select_related("plan")
        .order_by("-joined_at")
        .first()
    )
    if not sidebar_plan_enrollment:
        sidebar_plan_enrollment = (
            request.user.enrollments.filter(plan__isnull=False)
            .select_related("plan")
            .order_by("-joined_at")
            .first()
        )

    return {
        "notifications": notifications,
        "unread_notifications_count": unread_count,
        "sidebar_current_plan": sidebar_plan_enrollment.plan if sidebar_plan_enrollment else None,
    }
