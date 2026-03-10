import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # 1. Autentifikatsiya tekshiruvi
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # 2. Avtorizatsiya tekshiruvi (Xonaga kirish ruxsati)
        if not await self.is_authorized():
            await self.close()
            return

        # Guruhga obuna bo'lish
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Guruhdan chiqish
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Socketdan xabar qabul qilish
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message')
        
        # Xavfsizlik: sender_id ni clientdan emas, scopeden olamiz
        user = self.scope['user']

        # Bazaga saqlash
        saved_msg = await self.save_message(user, self.room_id, message)

        if saved_msg:
            # Guruhga tarqatish
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': user.id,
                    'sender_name': user.get_full_name() or user.username
                }
            )

            # --- Yangi: Adminga Telegram notification yuborish ---
            # AI chatlariga admin aralashmaydi, shuning uchun room_type 'ai' bo'lmasa jo'natamiz
            room = await database_sync_to_async(ChatRoom.objects.get)(id=self.room_id)
            if room.room_type != 'ai':
                from .tasks import send_telegram_notification
                send_telegram_notification.delay(saved_msg.id)

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
    def is_authorized(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            
            # Agar user xona ishtirokchisi bo'lsa
            if room.participants.filter(id=self.user.id).exists():
                return True
            
            # Agar guruh chati bo'lsa, cohort a'zoligini tekshirish
            if room.room_type == 'group' and room.cohort:
                from cohorts.models import Enrollment
                return Enrollment.objects.filter(
                    student=self.user, 
                    cohort=room.cohort, 
                    status='active'
                ).exists()
            
            return False
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, user, room_id, text):
        try:
            room = ChatRoom.objects.get(id=room_id)
            msg = Message.objects.create(room=room, sender=user, text=text)
            return msg
        except Exception as e:
            print(f"WebSocket saqlashda xatolik: {e}")
            return None
