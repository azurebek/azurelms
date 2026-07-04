import logging
import time

from ai.agent.engine import AIEngine
from ai.agent.types import AIRequest
from ai.skills.registry import SkillRegistry
from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from courses.models import Lesson
from messenger.access import user_can_use_lesson_context
from messenger.models import AIResponseRun, ChatRoom, Message
from messenger.rag import reindex_lessons


User = get_user_model()
logger = logging.getLogger(__name__)


def _skill_label(slug):
    if not slug:
        return ""
    try:
        return SkillRegistry().get(slug).name
    except KeyError:
        return slug.replace("_", " ").title()


def _is_pdf_message(message):
    if not message or not message.attachment:
        return False
    name = (message.attachment_name or message.attachment.name or "").lower()
    content_type = (message.attachment_content_type or "").lower()
    return name.endswith(".pdf") or "pdf" in content_type


def _latest_document_context(room, current_message=None):
    """Xonadagi eng so'nggi PDF'dan AI uchun matn konteksti.

    Avval joriy xabarning o'zi tekshiriladi, keyin xonadagi oxirgi 30 xabar —
    foydalanuvchi odatda avval fayl yuklab, keyin savol yozadi.
    Natija: (matn, fayl_nomi) yoki ("", "").
    """
    from ai.documents import extract_pdf_text

    candidates = []
    if current_message is not None:
        candidates.append(current_message)
    candidates.extend(
        Message.objects.filter(room=room, is_deleted=False)
        .exclude(attachment="")
        .order_by("-created_at")[:30]
    )
    for message in candidates:
        if not _is_pdf_message(message):
            continue
        text = extract_pdf_text(message.attachment)
        name = message.attachment_name or message.attachment.name.rsplit("/", 1)[-1]
        return text, name
    return "", ""


def _attach_generated_pdf(ai_message, *, title, body, run_id):
    """<PDF_DOC> blokidan PDF yasab AI xabariga biriktiradi. Xato PDF'siz davom etadi."""
    from django.core.files.base import ContentFile

    from ai.documents import build_pdf

    try:
        pdf_bytes = build_pdf(title=title, body=body)
    except Exception:
        logger.exception("PDF yasash xatosi (run_id=%s)", run_id)
        return False
    safe_title = "".join(ch for ch in title if ch.isalnum() or ch in " -_").strip()[:60] or "hujjat"
    filename = f"{safe_title}.pdf"
    ai_message.attachment.save(f"ai_docs/{run_id}_{filename}", ContentFile(pdf_bytes), save=False)
    ai_message.attachment_name = filename
    ai_message.attachment_content_type = "application/pdf"
    ai_message.attachment_size = len(pdf_bytes)
    ai_message.save(
        update_fields=["attachment", "attachment_name", "attachment_content_type", "attachment_size"]
    )
    return True


def _attachment_broadcast_payload(message):
    if not message.attachment:
        return None
    return {
        "url": message.attachment_url,
        "name": message.attachment_name or message.attachment.name.rsplit("/", 1)[-1],
        "content_type": message.attachment_content_type,
        "size": message.attachment_size,
        "size_label": message.attachment_size_label,
        "is_image": message.is_image_attachment,
    }


def _broadcast_ai_message(ai_message, user_message_id=None, skill_slug="", used_tools=None, rag_sources=None):
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
            "ai_skill_slug": skill_slug or "",
            "ai_skill_label": _skill_label(skill_slug),
            "ai_used_tools": used_tools or [],
            "ai_rag_sources": rag_sources or [],
            "attachment": _attachment_broadcast_payload(ai_message),
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
    requested_skill_slug=None,
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
            candidate_lesson = Lesson.objects.select_related("module__course").get(id=context_lesson_id)
            if user_can_use_lesson_context(student, candidate_lesson):
                context_lesson = candidate_lesson
            else:
                logger.warning(
                    "Ignoring forbidden context lesson_id=%s for room_id=%s student_id=%s",
                    context_lesson_id,
                    room_id,
                    student_id,
                )
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
        # Xonadagi so'nggi PDF (bo'lsa) — AI'ga hujjat konteksti sifatida
        document_context, document_name = "", ""
        try:
            document_context, document_name = _latest_document_context(room, current_message=user_message)
        except Exception:
            logger.exception("Hujjat kontekstini yig'ish xatosi (room_id=%s)", room.id)

        response = AIEngine().generate_reply(
            AIRequest(
                room=room,
                student=student,
                user_question=user_question,
                context_lesson=context_lesson,
                requested_skill_slug=requested_skill_slug,
                document_context=document_context,
                document_name=document_name,
            )
        )

        # AI javobida <PDF_DOC> bloki bo'lsa — haqiqiy PDF yasab xabarga biriktiramiz
        from ai.documents import extract_pdf_doc_block

        reply_text, pdf_title, pdf_body = extract_pdf_doc_block(response.text)

        ai_message = Message.objects.create(
            room=room,
            text=reply_text,
            is_ai_response=True,
            context_lesson=context_lesson,
        )
        if pdf_body:
            _attach_generated_pdf(ai_message, title=pdf_title, body=pdf_body, run_id=run.id)

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
            _broadcast_ai_message(
                ai_message,
                user_message_id=user_message.id if user_message else user_message_id,
                skill_slug=run.skill_slug,
                used_tools=(run.metadata or {}).get("used_tools", []),
                rag_sources=(run.metadata or {}).get("rag_sources", []),
            )
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
