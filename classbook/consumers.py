import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from bot.models import TelegramLessonSession

from .access import can_join_session, can_manage_cohort
from .realtime import session_group_name


class ClassbookConsumer(AsyncWebsocketConsumer):
    ACCESS_REVOKED_CLOSE_CODE = 4403

    async def connect(self):
        self.session_id = int(self.scope["url_route"]["kwargs"]["session_id"])
        self.room_group_name = session_group_name(self.session_id)
        if not await self.is_authorized():
            await self.close(code=self.ACCESS_REVOKED_CLOSE_CODE)
            return
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not await self.is_authorized():
            await self.send(text_data=json.dumps({"event_type": "access_revoked"}))
            await self.close(code=self.ACCESS_REVOKED_CLOSE_CODE)
            return
        await self.send(text_data=json.dumps({"event_type": "pong"}))

    async def classbook_event(self, event):
        if not await self.is_authorized():
            await self.close(code=self.ACCESS_REVOKED_CLOSE_CODE)
            return
        await self.send(text_data=json.dumps({
            "event_type": event.get("event_type"),
            "payload": event.get("payload") or {},
        }))

    @database_sync_to_async
    def is_authorized(self):
        scoped_user = self.scope.get("user")
        if not scoped_user or not scoped_user.is_authenticated:
            return False
        user = get_user_model().objects.filter(pk=scoped_user.pk, is_active=True).first()
        session = TelegramLessonSession.objects.select_related("cohort").filter(pk=self.session_id).first()
        if not user or not session:
            return False
        if can_manage_cohort(user, session.cohort):
            return True
        return session.status == TelegramLessonSession.STATUS_OPEN and can_join_session(user, session)
