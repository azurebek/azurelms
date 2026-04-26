from django.db import transaction
from django.utils import timezone

from cohorts.models import Enrollment
from users.models import CustomUser, Notification, NotificationBroadcast


def create_notification(
    *,
    recipient,
    message,
    title="",
    icon="bell",
    url="",
    category=Notification.CATEGORY_SYSTEM,
    external_key=None,
):
    defaults = {
        "title": title,
        "message": message,
        "icon": icon,
        "url": url,
        "category": category,
        "is_read": False,
    }

    if external_key:
        notif, created = Notification.objects.get_or_create(
            recipient=recipient,
            external_key=external_key,
            defaults=defaults,
        )
        return notif, created

    notif = Notification.objects.create(
        recipient=recipient,
        external_key=None,
        **defaults,
    )
    return notif, True


def _subscription_due_message(enrollment, days_left):
    course_name = enrollment.cohort.course.title
    if days_left == 0:
        return (
            f"{course_name} kursi bo'yicha to'lov muddati bugun tugaydi. "
            "To'lovni yangilab obunani faol saqlang."
        )
    return (
        f"{course_name} kursi bo'yicha to'lov muddati {days_left} kundan so'ng tugaydi. "
        "Muddatidan oldin to'lovni yangilashni unutmang."
    )


def ensure_subscription_notifications_for_user(user):
    today = timezone.localdate()
    enrollments = (
        Enrollment.objects.filter(student=user)
        .select_related("cohort", "cohort__course")
    )

    for enrollment in enrollments:
        effective_status = enrollment.get_effective_status(today=today)
        deadline = enrollment.next_payment_deadline
        if deadline:
            days_left = (deadline - today).days

            if effective_status == Enrollment.STATUS_ACTIVE and days_left in {3, 1, 0}:
                key = f"sub-due-{enrollment.id}-{deadline.isoformat()}-{days_left}"
                create_notification(
                    recipient=user,
                    title="To'lov eslatmasi",
                    message=_subscription_due_message(enrollment, days_left),
                    icon="clock-history",
                    url="/users/subscriptions/",
                    category=Notification.CATEGORY_SUBSCRIPTION,
                    external_key=key,
                )

        if effective_status == Enrollment.STATUS_FROZEN:
            key = f"sub-frozen-{enrollment.id}"
            create_notification(
                recipient=user,
                title="Obuna muzlatildi",
                message=(
                    f"{enrollment.cohort.course.title} kursi bo'yicha obunangiz muzlatildi. "
                    "Qayta faollashtirish uchun to'lovni yangilang."
                ),
                icon="snow",
                url="/users/subscriptions/",
                category=Notification.CATEGORY_SUBSCRIPTION,
                external_key=key,
            )

        if effective_status == Enrollment.STATUS_EXPIRED:
            key = f"sub-expired-{enrollment.id}-{enrollment.next_payment_deadline or today}"
            create_notification(
                recipient=user,
                title="Obuna muddati tugagan",
                message=(
                    f"{enrollment.cohort.course.title} kursi bo'yicha obuna muddati tugagan. "
                    "Davom etish uchun obunani yangilang."
                ),
                icon="exclamation-circle",
                url="/users/subscriptions/",
                category=Notification.CATEGORY_SUBSCRIPTION,
                external_key=key,
            )


def ensure_subscription_notifications_for_all_users():
    for user in CustomUser.objects.filter(is_active=True).only("id"):
        ensure_subscription_notifications_for_user(user)


@transaction.atomic
def send_broadcast(broadcast: NotificationBroadcast):
    if broadcast.is_sent:
        return 0

    if broadcast.target_type == NotificationBroadcast.TARGET_ALL:
        recipients_qs = CustomUser.objects.filter(is_active=True)
    elif broadcast.target_type == NotificationBroadcast.TARGET_USERS:
        recipients_qs = broadcast.recipients.filter(is_active=True)
    else:
        recipients_qs = CustomUser.objects.filter(
            is_active=True,
            enrollments__cohort__in=broadcast.cohorts.all(),
        ).distinct()

    notifications = [
        Notification(
            recipient=user,
            title=broadcast.title,
            message=broadcast.message,
            icon=broadcast.icon or "megaphone",
            url=broadcast.url or "/users/dashboard/",
            category=Notification.CATEGORY_MANUAL,
            external_key=None,
        )
        for user in recipients_qs
    ]
    Notification.objects.bulk_create(notifications)

    broadcast.is_sent = True
    broadcast.sent_at = timezone.now()
    broadcast.save(update_fields=["is_sent", "sent_at"])
    return len(notifications)
