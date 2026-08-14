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
from django.db import IntegrityError, transaction
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


_RASTER_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")


def _is_raster_image_message(message):
    """Foydalanuvchi yuborgan rastr rasm (AI'ning o'z SVG'lari hisobga olinmaydi)."""
    if not message or not message.attachment or message.is_ai_response:
        return False
    name = (message.attachment_name or message.attachment.name or "").lower()
    content_type = (message.attachment_content_type or "").lower()
    if "svg" in content_type or name.endswith(".svg"):
        return False
    return content_type.startswith("image/") or name.endswith(_RASTER_EXTENSIONS)


def _latest_image_context(room, current_message=None):
    """Xonadagi eng so'nggi rastr rasmni vision uchun data-URL'ga tayyorlaydi.

    Natija: (data_url, fayl_nomi) yoki ("", "").
    """
    from ai.documents import image_to_data_url

    candidates = []
    if current_message is not None:
        candidates.append(current_message)
    candidates.extend(
        Message.objects.filter(room=room, is_deleted=False, is_ai_response=False)
        .exclude(attachment="")
        .order_by("-created_at")[:30]
    )
    for message in candidates:
        if not _is_raster_image_message(message):
            continue
        data_url = image_to_data_url(message.attachment)
        if not data_url:
            continue
        name = message.attachment_name or message.attachment.name.rsplit("/", 1)[-1]
        return data_url, name
    return "", ""


def _attach_generated_svg(ai_message, *, title, svg_text, run_id):
    """<SVG_IMAGE> blokidan zararsizlantirilgan SVG yasab xabarga biriktiradi."""
    from django.core.files.base import ContentFile

    from ai.documents import sanitize_svg

    clean_svg = sanitize_svg(svg_text)
    if not clean_svg:
        logger.warning("SVG sanitizatsiyadan o'tmadi (run_id=%s)", run_id)
        return False
    payload = clean_svg.encode("utf-8")
    safe_title = "".join(ch for ch in title if ch.isalnum() or ch in " -_").strip()[:60] or "rasm"
    filename = f"{safe_title}.svg"
    ai_message.attachment.save(f"ai_docs/{run_id}_{filename}", ContentFile(payload), save=False)
    ai_message.attachment_name = filename
    ai_message.attachment_content_type = "image/svg+xml"
    ai_message.attachment_size = len(payload)
    ai_message.save(
        update_fields=["attachment", "attachment_name", "attachment_content_type", "attachment_size"]
    )
    return True


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


def _ai_run_idempotency_key(*, room_id, student_id, user_message_id, client_message_id):
    client_value = str(client_message_id or "").strip()[:80]
    # WebSocket reconnect/resend creates a fresh Message row, but the stable
    # client_message_id must still identify the same logical AI request. An
    # intentional retry receives a fresh server-generated `retry:` client id.
    if client_value:
        suffix = f"client:{client_value}"
    elif user_message_id:
        suffix = f"message:{user_message_id}"
    else:
        return ""
    return f"chat:{room_id}:{student_id}:{suffix}"[:180]


def _existing_run_result(idempotency_key):
    if not idempotency_key:
        return None, False
    existing = (
        AIResponseRun.objects.filter(idempotency_key=idempotency_key)
        .select_related("ai_message")
        .first()
    )
    if existing is None:
        return None, False
    return existing.ai_message_id, True


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

    idempotency_key = _ai_run_idempotency_key(
        room_id=room.id,
        student_id=student.id,
        user_message_id=user_message.id if user_message else user_message_id,
        client_message_id=client_message_id,
    )
    existing_result, duplicate = _existing_run_result(idempotency_key)
    if duplicate:
        logger.info("Skipping duplicate AI task idempotency_key=%s", idempotency_key)
        return existing_result

    # --- AI token limiti (5 soatlik + haftalik) ---
    # Fail-open: limiter'da xato bo'lsa foydalanuvchi bloklanmaydi (nazorat, devor emas).
    try:
        from aicontrol.service import get_quota_status, limit_message

        quota = get_quota_status(student)
        if not quota.allowed:
            notice = limit_message(quota)
            blocked_message = Message.objects.create(room=room, text=notice, is_ai_response=True)
            AIResponseRun.objects.create(
                room=room,
                student=student,
                user_message=user_message,
                ai_message=blocked_message,
                idempotency_key=idempotency_key,
                user_question=user_question or "",
                status=AIResponseRun.STATUS_FALLBACK,
                skill_slug="quota_block",
                started_at=timezone.now(),
                completed_at=timezone.now(),
            )
            try:
                _broadcast_ai_message(
                    blocked_message,
                    user_message_id=user_message.id if user_message else user_message_id,
                )
                _broadcast_ai_status(
                    room_id=room.id,
                    status=AIResponseRun.STATUS_FALLBACK,
                    user_message_id=user_message.id if user_message else user_message_id,
                    message="Limit tugadi.",
                )
            except Exception:
                logger.exception("Quota-block broadcast failed for room_id=%s", room.id)
            return None
    except Exception:
        logger.exception("AI quota check failed (fail-open) for student_id=%s", student_id)

    try:
        with transaction.atomic():
            run = AIResponseRun.objects.create(
                room=room,
                student=student,
                user_message=user_message,
                context_lesson=context_lesson,
                client_message_id=(client_message_id or "")[:80],
                idempotency_key=idempotency_key,
                user_question=user_question or "",
                status=AIResponseRun.STATUS_RUNNING,
                started_at=timezone.now(),
            )
    except IntegrityError:
        existing_result, duplicate = _existing_run_result(idempotency_key)
        if duplicate:
            logger.info("Parallel duplicate AI task stopped idempotency_key=%s", idempotency_key)
            return existing_result
        raise

    from aicontrol.models import AISupplyEvent
    from aicontrol.supply import SupplyError, reserve_supply

    try:
        main_reservation = reserve_supply(
            request_key=f"{idempotency_key or f'ai-run:{run.id}'}:provider",
            call_type=AISupplyEvent.CALL_CHAT,
            provider=str(getattr(settings, "AI_CHAT_PROVIDER", "gemini") or "gemini"),
            model_name=str(getattr(student, "ai_model", "") or ""),
            user=student,
            reserved_requests=2,
            metadata={"ai_response_run_id": run.id},
        )
    except SupplyError as exc:
        notice = (
            "AI bepul budjeti vaqtincha mavjud emas. Asosiy LMS funksiyalari ishlashda davom etadi; "
            "birozdan keyin qayta urinib ko'ring."
        )
        blocked_message = Message.objects.create(room=room, text=notice, is_ai_response=True)
        run.status = AIResponseRun.STATUS_FALLBACK
        run.ai_message = blocked_message
        run.skill_slug = "supply_block"
        run.error_message = _short_error(exc)
        run.completed_at = timezone.now()
        run.save(
            update_fields=[
                "status",
                "ai_message",
                "skill_slug",
                "error_message",
                "completed_at",
                "updated_at",
            ]
        )
        try:
            _broadcast_ai_message(
                blocked_message,
                user_message_id=user_message.id if user_message else user_message_id,
            )
            _broadcast_ai_status(
                room_id=room.id,
                status=AIResponseRun.STATUS_FALLBACK,
                run=run,
                user_message_id=user_message.id if user_message else user_message_id,
                message="AI supply budjeti vaqtincha yopiq.",
            )
        except Exception:
            logger.exception("Supply-block broadcast failed for run_id=%s", run.id)
        return blocked_message.id
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

        # Xonadagi so'nggi rasm (bo'lsa) — vision-model'ga to'g'ridan yuboriladi
        image_data_url, image_name = "", ""
        try:
            image_data_url, image_name = _latest_image_context(room, current_message=user_message)
        except Exception:
            logger.exception("Rasm kontekstini yig'ish xatosi (room_id=%s)", room.id)

        response = AIEngine().generate_reply(
            AIRequest(
                room=room,
                student=student,
                user_question=user_question,
                context_lesson=context_lesson,
                requested_skill_slug=requested_skill_slug,
                document_context=document_context,
                document_name=document_name,
                image_data_url=image_data_url,
                image_name=image_name,
                supply_request_key=f"{idempotency_key or f'ai-run:{run.id}'}:provider",
                supply_reservation=main_reservation,
            )
        )

        # A mocked/custom engine may not own the provider wrapper. Never leave
        # the pre-reserved main slot dangling; the canonical AIEngine normally
        # reconciles it before returning, so this branch is a no-op in runtime.
        pending_supply = AISupplyEvent.objects.filter(
            pk=main_reservation.event_id,
            status=AISupplyEvent.STATUS_RESERVED,
        ).exists()
        if pending_supply:
            from aicontrol.supply import reconcile_supply

            response_usage = (response.metadata or {}).get("usage") or {}
            reconcile_supply(
                main_reservation,
                succeeded=bool(response.model_name),
                actual_requests=1 if response.model_name else 0,
                usage=response_usage,
                model_name=response.model_name or "",
                error_kind="" if response.model_name else "engine_fallback",
            )

        # AI javobida <PDF_DOC>/<SVG_IMAGE> bloklari bo'lsa — fayl yasab xabarga biriktiramiz
        from ai.documents import extract_pdf_doc_block, extract_svg_block

        reply_text, pdf_title, pdf_body = extract_pdf_doc_block(response.text)
        reply_text, svg_title, svg_body = extract_svg_block(reply_text)

        ai_message = Message.objects.create(
            room=room,
            text=reply_text,
            is_ai_response=True,
            context_lesson=context_lesson,
        )
        if pdf_body:
            _attach_generated_pdf(ai_message, title=pdf_title, body=pdf_body, run_id=run.id)
        elif svg_body:
            _attach_generated_svg(ai_message, title=svg_title, svg_text=svg_body, run_id=run.id)

        status = AIResponseRun.STATUS_SUCCEEDED if response.model_name else AIResponseRun.STATUS_FALLBACK
        run.status = status
        run.ai_message = ai_message
        run.model_name = response.model_name or ""
        run.skill_slug = response.skill_slug or ""
        run.duration_ms = int((time.perf_counter() - started) * 1000)
        run.metadata = response.metadata or {}
        # Token hisobi — AI limit-boshqaruvi shu maydonlar yig'indisiga tayanadi
        usage = (response.metadata or {}).get("usage") or {}
        run.prompt_tokens = int(usage.get("prompt_tokens") or 0)
        run.completion_tokens = int(usage.get("completion_tokens") or 0)
        run.total_tokens = int(usage.get("total_tokens") or 0)
        run.completed_at = timezone.now()
        run.save(
            update_fields=[
                "status",
                "ai_message",
                "model_name",
                "skill_slug",
                "duration_ms",
                "metadata",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
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
        # Constructor/integration failures can happen before AIEngine receives
        # the pre-reserved slot. Release that slot conservatively instead of
        # leaving a stale daily reservation behind.
        try:
            pending_supply = AISupplyEvent.objects.filter(
                pk=main_reservation.event_id,
                status=AISupplyEvent.STATUS_RESERVED,
            ).exists()
            if pending_supply:
                from aicontrol.supply import reconcile_supply

                reconcile_supply(
                    main_reservation,
                    succeeded=False,
                    actual_requests=0,
                    error=exc,
                    error_kind="pre_engine_error",
                )
        except Exception:
            logger.exception("Failed AI task reservation reconciliation for run_id=%s", run.id)
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
