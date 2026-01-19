from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from courses.models import Batch
from education.models import Enrollment

from .models import ChatRoom


@receiver(post_save, sender=Batch)
def create_group_chat(sender, instance, created, **kwargs):
    if not created:
        return

    room, _ = ChatRoom.objects.get_or_create(
        batch=instance,
        type=ChatRoom.GROUP,
        defaults={"last_activity": instance.created_at},
    )
    _add_teachers_to_room(room)


@receiver(post_save, sender=Enrollment)
def add_student_to_group_chat(sender, instance, created, **kwargs):
    if not created or not instance.is_active:
        return

    room, _ = ChatRoom.objects.get_or_create(
        batch=instance.batch,
        type=ChatRoom.GROUP,
        defaults={"last_activity": instance.created_at},
    )
    room.participants.add(instance.user)
    _add_teachers_to_room(room)


def _add_teachers_to_room(room):
    User = get_user_model()
    teachers = User.objects.filter(is_staff=True)
    if teachers.exists():
        room.participants.add(*teachers)
