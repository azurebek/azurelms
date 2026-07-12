"""users.Notification → TelegramOutbox ko'zgusi.

Har yangi platforma-bildirishnoma, agar qabul qiluvchining telegram_id'si
bo'lsa, outbox'ga tushadi. Yuborishni worker qiladi (bot/outbox.py) —
sayt so'rovi hech qachon Telegram API kutmaydi.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from users.models import Notification


@receiver(post_save, sender=Notification, dispatch_uid="bot_notification_to_outbox")
def mirror_notification_to_outbox(sender, instance, created, **kwargs):
    if not created:
        return
    telegram_id = getattr(instance.recipient, "telegram_id", None)
    if not telegram_id:
        return
    from bot.models import TelegramOutbox

    TelegramOutbox.objects.get_or_create(
        notification=instance,
        defaults={"telegram_id": telegram_id},
    )
