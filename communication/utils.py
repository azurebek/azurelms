from django.db.models import Prefetch

from .models import ChatRoom, Message


def get_user_rooms(user):
    if user.is_anonymous:
        return []
    return user.chat_rooms.select_related("batch").prefetch_related(
        "participants",
        Prefetch(
            "messages",
            queryset=Message.objects.select_related("sender").order_by("-created_at")[:1],
            to_attr="recent_messages",
        ),
    )


def build_room_groups(rooms):
    rooms = list(rooms)
    return {
        "rooms": rooms,
        "default_room": rooms[0] if rooms else None,
        "group_rooms": [room for room in rooms if room.type == ChatRoom.GROUP],
        "direct_rooms": [room for room in rooms if room.type == ChatRoom.DIRECT],
        "bot_rooms": [room for room in rooms if room.type == ChatRoom.BOT],
    }
