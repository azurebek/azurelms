from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from cohorts.models import Enrollment
from users.models import Notification
from users.notification_service import create_notification


@receiver(pre_save, sender=Enrollment)
def cache_old_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_status = None
        return
    old = Enrollment.objects.filter(pk=instance.pk).only("status").first()
    instance._old_status = old.status if old else None


@receiver(post_save, sender=Enrollment)
def create_status_change_notifications(sender, instance, created, **kwargs):
    if created:
        return
    if getattr(instance, "_suppress_status_change_notifications", False):
        return

    old_status = getattr(instance, "_old_status", None)
    if old_status == instance.status:
        return

    course_title = instance.cohort.course.title
    student = instance.student

    if instance.status == "frozen":
        create_notification(
            recipient=student,
            title="Obuna muzlatildi",
            message=(
                f"{course_title} kursi bo'yicha obunangiz muzlatildi. "
                "To'lovni yangilab obunani qayta faollashtiring."
            ),
            icon="snow",
            url="/users/subscriptions/",
            category=Notification.CATEGORY_SUBSCRIPTION,
            external_key=f"sub-frozen-{instance.id}",
        )
    elif instance.status == "active" and old_status in {"frozen", "expired", "pending"}:
        create_notification(
            recipient=student,
            title="Obuna faollashtirildi",
            message=f"{course_title} kursi bo'yicha obunangiz yana faol holatga o'tdi.",
            icon="check-circle",
            url="/users/subscriptions/",
            category=Notification.CATEGORY_SUBSCRIPTION,
            external_key=f"sub-active-{instance.id}-{instance.last_payment_date or 'na'}",
        )
