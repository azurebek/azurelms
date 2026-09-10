from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction


def session_group_name(session_id):
    return f"classbook_{int(session_id)}"


def broadcast_session_event(session_id, event_type, payload=None):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        session_group_name(session_id),
        {
            "type": "classbook_event",
            "event_type": event_type,
            "payload": payload or {},
        },
    )


def broadcast_after_commit(session_id, event_type, payload=None):
    transaction.on_commit(lambda: broadcast_session_event(session_id, event_type, payload))
