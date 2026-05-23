import logging
import time

from ai.agent.engine import AIEngine
from ai.agent.types import AIRequest
from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from courses.models import Lesson
from messenger.models import AIResponseRun, ChatRoom, Message
from messenger.rag import reindex_lessons


User = get_user_model()
logger = logging.getLogger(__name__)


def _broadcast_ai_message(ai_message, user_message_id=None):
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
            "is_ai": True,
            "feedback": None,
            "feedback_totals": {"positive": 0, "negative": 0},
            "regenerate_user_message_id": user_message_id,
        },
    )


def _broadcast_ai_status(*, room_id, status, run=None, user_message_id=None, message="", error_message=""):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{room_id}",
        {
            "type": "ai_status",
            "status": status,
            "run_id": run.id if run else None,
            "user_message_id": user_message_id,
            "message": message,
            "error_message": error_message,
        },
    )


def _short_error(error) -> str:
    return str(error or "").strip()[:500]


@shared_task(ignore_result=True)
def generate_ai_response(
    room_id,
    student_id,
    user_question,
    context_lesson_id=None,
    user_message_id=None,
    client_message_id=None,
):
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

    user_message = None
    if user_message_id:
        user_message = Message.objects.filter(id=user_message_id, room=room, sender=student).first()

    run = AIResponseRun.objects.create(
        room=room,
        student=student,
        user_message=user_message,
        context_lesson=context_lesson,
        client_message_id=(client_message_id or "")[:80],
        user_question=user_question or "",
        status=AIResponseRun.STATUS_RUNNING,
        started_at=timezone.now(),
    )
    started = time.perf_counter()

    try:
        _broadcast_ai_status(
            room_id=room.id,
            status=AIResponseRun.STATUS_RUNNING,
            run=run,
            user_message_id=user_message.id if user_message else user_message_id,
            message="Azure AI javob tayyorlayapti...",
        )
    except Exception:
        logger.exception("AI status broadcast failed at start for run_id=%s", run.id)

    try:
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
        status = AIResponseRun.STATUS_SUCCEEDED if response.model_name else AIResponseRun.STATUS_FALLBACK
        run.status = status
        run.ai_message = ai_message
        run.model_name = response.model_name or ""
        run.skill_slug = response.skill_slug or ""
        run.duration_ms = int((time.perf_counter() - started) * 1000)
        run.metadata = response.metadata or {}
        run.completed_at = timezone.now()
        run.save(
            update_fields=[
                "status",
                "ai_message",
                "model_name",
                "skill_slug",
                "duration_ms",
                "metadata",
                "completed_at",
                "updated_at",
            ]
        )

        try:
            _broadcast_ai_message(ai_message, user_message_id=user_message.id if user_message else user_message_id)
            _broadcast_ai_status(
                room_id=room.id,
                status=status,
                run=run,
                user_message_id=user_message.id if user_message else user_message_id,
                message="Javob tayyor.",
            )
        except Exception:
            logger.exception("AI websocket broadcast failed for room_id=%s message_id=%s", room.id, ai_message.id)

        return ai_message.id
    except Exception as exc:
        error_text = _short_error(exc)
        logger.exception("AI response task failed for room_id=%s student_id=%s run_id=%s", room.id, student.id, run.id)
        run.status = AIResponseRun.STATUS_FAILED
        run.error_message = error_text
        run.duration_ms = int((time.perf_counter() - started) * 1000)
        run.completed_at = timezone.now()
        run.save(update_fields=["status", "error_message", "duration_ms", "completed_at", "updated_at"])
        try:
            _broadcast_ai_status(
                room_id=room.id,
                status=AIResponseRun.STATUS_FAILED,
                run=run,
                user_message_id=user_message.id if user_message else user_message_id,
                message="AI javob bera olmadi.",
                error_message=error_text,
            )
        except Exception:
            logger.exception("AI failure status broadcast failed for run_id=%s", run.id)
        return None


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
