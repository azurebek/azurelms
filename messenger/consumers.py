import json
import re
import asyncio
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from courses.models import Lesson
from .access import maybe_name_ai_room_from_first_prompt, user_can_access_room, user_can_use_lesson_context
from .models import AIResponseRun, ChatRoom, ChatRoomUserState, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.background_tasks = set()

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
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
        action = data.get("action")
        message = data.get('message')
        context_lesson_id = data.get("context_lesson_id")
        client_message_id = data.get("client_message_id")
        requested_skill_slug = data.get("ai_skill")

        # Xavfsizlik: sender_id ni clientdan emas, scopeden olamiz
        user = self.scope['user']

        if action == "retry_ai_response":
            retry_message_id = data.get("user_message_id")
            retry_payload = await self.get_retry_payload(user, self.room_id, retry_message_id)
            if not retry_payload:
                await self.send_ai_status(
                    status="failed",
                    user_message_id=retry_message_id,
                    message="Qayta urinish uchun xabar topilmadi.",
                )
                return

            self.enqueue_background_task(
                self.dispatch_ai_response(
                    room_id=retry_payload["room_id"],
                    student_id=user.id,
                    user_question=retry_payload["text"],
                    context_lesson_id=retry_payload["context_lesson_id"],
                    user_message_id=retry_payload["message_id"],
                    client_message_id=(
                        f"retry:{retry_payload['message_id']}:{uuid.uuid4().hex[:20]}"
                    ),
                    requested_skill_slug=retry_payload["requested_skill_slug"],
                )
            )
            return

        try:
            context_lesson_id = int(context_lesson_id) if context_lesson_id is not None else None
        except (TypeError, ValueError):
            context_lesson_id = None

        if not isinstance(client_message_id, str):
            client_message_id = None
        elif client_message_id:
            client_message_id = client_message_id.strip()[:80] or None

        if not isinstance(requested_skill_slug, str):
            requested_skill_slug = None
        else:
            requested_skill_slug = requested_skill_slug.strip()[:80] or None
            if requested_skill_slug == "auto":
                requested_skill_slug = None

        if not isinstance(message, str) or not message.strip():
            return

        # Bazaga saqlash
        saved_msg = await self.save_message(user, self.room_id, message, context_lesson_id=context_lesson_id)

        if saved_msg:
            # Guruhga tarqatish
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'message_id': saved_msg.id,
                    'created_at': saved_msg.created_at.strftime("%H:%M"),
                    'sender_id': user.id,
                    'sender_name': user.get_full_name() or user.username,
                    'client_message_id': client_message_id,
                    'room_id': saved_msg.room_id,
                    'room_name': saved_msg.room.name,
                }
            )

            # Chat real-time oqimi buzilmasligi uchun Telegram dispatch xatolarini yutamiz.
            room_type = await self.get_room_type(self.room_id)
            if room_type != 'ai':
                await self.dispatch_telegram_notification(saved_msg.id)
            if room_type == 'ai' or '@azure' in (message or '').lower():
                user_question = re.sub(r"@azure", "", message or "", flags=re.IGNORECASE).strip()
                self.enqueue_background_task(
                    self.dispatch_ai_response(
                        room_id=saved_msg.room_id,
                        student_id=user.id,
                        user_question=user_question,
                        context_lesson_id=saved_msg.context_lesson_id,
                        user_message_id=saved_msg.id,
                        client_message_id=client_message_id,
                        requested_skill_slug=requested_skill_slug,
                    )
                )

    # Guruhdan kelgan xabarni WebSocket orqali jo'natish
    async def chat_message(self, event):
        message = event['message']
        sender_id = event['sender_id']
        sender_name = event.get('sender_name', "User")
        message_id = event.get('message_id') or event.get('id')
        created_at = event.get('created_at')
        client_message_id = event.get("client_message_id")
        room_id = event.get("room_id")
        room_name = event.get("room_name")
        is_ai = event.get("is_ai", False)
        feedback = event.get("feedback")
        feedback_totals = event.get("feedback_totals")
        regenerate_user_message_id = event.get("regenerate_user_message_id")
        ai_skill_slug = event.get("ai_skill_slug", "")
        ai_skill_label = event.get("ai_skill_label", "")
        ai_used_tools = event.get("ai_used_tools", [])
        ai_rag_sources = event.get("ai_rag_sources", [])
        attachment = event.get("attachment")
        is_deleted = event.get("is_deleted", False)
        edited_at = event.get("edited_at", "")

        await self.send(text_data=json.dumps({
            'event_type': 'message',
            'message': message,
            'sender_id': sender_id,
            'sender_name': sender_name,
            'message_id': message_id,
            'created_at': created_at,
            'client_message_id': client_message_id,
            'room_id': room_id,
            'room_name': room_name,
            'is_ai': is_ai,
            'feedback': feedback,
            'feedback_totals': feedback_totals,
            'regenerate_user_message_id': regenerate_user_message_id,
            'ai_skill_slug': ai_skill_slug,
            'ai_skill_label': ai_skill_label,
            'ai_used_tools': ai_used_tools,
            'ai_rag_sources': ai_rag_sources,
            'attachment': attachment,
            'is_deleted': is_deleted,
            'edited_at': edited_at,
        }))

    async def message_update(self, event):
        payload = event.get("payload") or {}
        payload["event_type"] = event.get("event_type") or "message_update"
        await self.send(text_data=json.dumps(payload))

    async def ai_status(self, event):
        await self.send(text_data=json.dumps({
            'event_type': 'ai_status',
            'status': event.get('status'),
            'run_id': event.get('run_id'),
            'user_message_id': event.get('user_message_id'),
            'message': event.get('message') or '',
            'error_message': event.get('error_message') or '',
        }))

    async def send_ai_status(self, *, status, user_message_id=None, message="", error_message=""):
        await self.send(text_data=json.dumps({
            'event_type': 'ai_status',
            'status': status,
            'user_message_id': user_message_id,
            'message': message,
            'error_message': error_message,
        }))

    def enqueue_background_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    @database_sync_to_async
    def is_authorized(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return user_can_access_room(self.user, room)
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, user, room_id, text, context_lesson_id=None):
        try:
            room = ChatRoom.objects.get(id=room_id)
            context_lesson = None
            if context_lesson_id:
                lesson = Lesson.objects.filter(id=context_lesson_id).select_related("module__course").first()
                if lesson and user_can_use_lesson_context(user, lesson):
                    context_lesson = lesson
            from .signals import suppress_ai_signal

            with suppress_ai_signal():
                msg = Message.objects.create(room=room, sender=user, text=text, context_lesson=context_lesson)
            ChatRoomUserState.objects.update_or_create(
                room=room,
                user=user,
                defaults={"last_read_at": timezone.now()},
            )
            maybe_name_ai_room_from_first_prompt(room, text)
            return msg
        except Exception as e:
            print(f"WebSocket saqlashda xatolik: {e}")
            return None

    @database_sync_to_async
    def get_room_type(self, room_id):
        room = ChatRoom.objects.filter(id=room_id).only('room_type').first()
        return room.room_type if room else None

    @database_sync_to_async
    def get_retry_payload(self, user, room_id, message_id):
        try:
            message_id = int(message_id)
        except (TypeError, ValueError):
            return None
        message = (
            Message.objects.filter(id=message_id, room_id=room_id, sender=user, is_ai_response=False)
            .only("id", "room_id", "text", "context_lesson_id")
            .first()
        )
        if not message:
            return None
        latest_run = (
            AIResponseRun.objects.filter(user_message=message)
            .exclude(skill_slug="")
            .order_by("-created_at")
            .only("skill_slug")
            .first()
        )
        return {
            "message_id": message.id,
            "room_id": message.room_id,
            "text": message.text,
            "context_lesson_id": message.context_lesson_id,
            "requested_skill_slug": latest_run.skill_slug if latest_run else None,
        }

    @sync_to_async
    def dispatch_telegram_notification(self, message_id):
        try:
            from .tasks import send_telegram_notification
            send_telegram_notification.delay(message_id)
        except Exception as e:
            print(f"Telegram task dispatch xatosi: {e}")

    @sync_to_async
    def dispatch_ai_response(
        self,
        room_id,
        student_id,
        user_question,
        context_lesson_id=None,
        user_message_id=None,
        client_message_id=None,
        requested_skill_slug=None,
    ):
        from .tasks import generate_ai_response

        try:
            generate_ai_response.delay(
                room_id=room_id,
                student_id=student_id,
                user_question=user_question,
                context_lesson_id=context_lesson_id,
                user_message_id=user_message_id,
                client_message_id=client_message_id,
                requested_skill_slug=requested_skill_slug,
            )
        except Exception as e:
            print(f"AI task dispatch xatosi: {e}")
            generate_ai_response.run(
                room_id=room_id,
                student_id=student_id,
                user_question=user_question,
                context_lesson_id=context_lesson_id,
                user_message_id=user_message_id,
                client_message_id=client_message_id,
                requested_skill_slug=requested_skill_slug,
            )
