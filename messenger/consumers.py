import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # Guruhga obuna bo'lish
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Guruhdan chiqish
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Socketdan xabar qabul qilish
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        sender_id = data.get('sender_id')

        # Bazaga saqlash
        saved_msg = await self.save_message(sender_id, self.room_id, message)

        if saved_msg:
            # Guruhga tarqatish
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': sender_id,
                    'sender_name': saved_msg.sender.get_full_name() or saved_msg.sender.username if saved_msg.sender else "Noma'lum"
                }
            )

    # Guruhdan kelgan xabarni WebSocket orqali jo'natish
    async def chat_message(self, event):
        message = event['message']
        sender_id = event['sender_id']
        sender_name = event.get('sender_name', "User")

        await self.send(text_data=json.dumps({
            'message': message,
            'sender_id': sender_id,
            'sender_name': sender_name
        }))

    @database_sync_to_async
    def save_message(self, user_id, room_id, text):
        try:
            room = ChatRoom.objects.get(id=room_id)
            user = User.objects.get(id=user_id) if user_id else None
            msg = Message.objects.create(room=room, sender=user, text=text)
            return msg
        except Exception as e:
            print(f"WebSocket saqlashda xatolik: {e}")
            return None
