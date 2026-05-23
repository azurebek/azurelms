import logging

from ai.agent.engine import AIEngine
from ai.agent.types import AIRequest
from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model

from courses.models import Lesson
from messenger.models import ChatRoom, Message
from messenger.rag import reindex_lessons


User = get_user_model()
logger = logging.getLogger(__name__)


def _broadcast_ai_message(ai_message):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{ai_message.room_id}",
        {
            "type": "chat_message",
            "message_id": ai_message.id,
            "message": ai_message.text,
            "sender_name": "Azure AI",
            "sender_id": None,
            "room_id": ai_message.room_id,
            "room_name": ai_message.room.name,
            "created_at": ai_message.created_at.strftime("%H:%M"),
        },
    )


@shared_task(ignore_result=True)
def generate_ai_response(room_id, student_id, user_question, context_lesson_id=None):
    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        logger.warning("Skipping AI response because room_id=%s no longer exists", room_id)
        return None

    try:
        student = User.objects.get(id=student_id)
    except User.DoesNotExist:
        logger.warning("Skipping AI response because student_id=%s no longer exists", student_id)
        return None

    context_lesson = None
    if context_lesson_id:
        try:
            context_lesson = Lesson.objects.get(id=context_lesson_id)
        except Lesson.DoesNotExist:
            logger.warning("Ignoring missing context lesson_id=%s for room_id=%s", context_lesson_id, room_id)

    response = AIEngine().generate_reply(
        AIRequest(
            room=room,
            student=student,
            user_question=user_question,
            context_lesson=context_lesson,
        )
    )

    ai_message = Message.objects.create(
        room=room,
        text=response.text,
        is_ai_response=True,
        context_lesson=context_lesson,
    )

    try:
        _broadcast_ai_message(ai_message)
    except Exception:
        logger.exception("AI websocket broadcast failed for room_id=%s message_id=%s", room.id, ai_message.id)

    return ai_message.id


@shared_task(ignore_result=True)
def reindex_lesson_rag(lesson_id, force=False):
    try:
        return reindex_lessons(lesson_ids=[lesson_id], force=force)
    except Exception:
        logger.exception("Lesson RAG reindex failed for lesson_id=%s", lesson_id)
        return None


@shared_task(ignore_result=True)
def reindex_course_rag(course_id, force=False):
    try:
        return reindex_lessons(course_ids=[course_id], force=force)
    except Exception:
        logger.exception("Course RAG reindex failed for course_id=%s", course_id)
        return None


@shared_task(ignore_result=True)
def send_telegram_notification(message_id):
    try:
        msg = Message.objects.get(id=message_id)
        room = msg.room
        sender = msg.sender

        if not sender:
            return

        recipients = room.participants.exclude(id=sender.id)

        for user in recipients:
            if user.telegram_id and (user.is_staff or room.room_type == "private"):
                notification_text = f"Yangi xabar ({room.name or 'Chat'}):\n"
                notification_text += f"{sender.get_full_name() or sender.username}:\n\n"
                notification_text += msg.text

                try:
                    import requests

                    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                    payload = {
                        "chat_id": user.telegram_id,
                        "text": notification_text,
                    }
                    requests.post(url, json=payload, timeout=5)
                except Exception as bot_err:
                    logger.warning("Telegram send failed for user=%s: %s", user.username, bot_err)
    except Exception:
        logger.exception("send_telegram_notification failed for message_id=%s", message_id)
