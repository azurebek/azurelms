import json
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Max, Count, Q, OuterRef, Subquery
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from ai.skills.registry import SkillRegistry
from cohorts.models import Enrollment, enrollment_active_access_q
from core.upload_validation import validate_upload
from courses.models import Lesson
from .access import (
    create_user_ai_room,
    get_or_create_ai_draft_room,
    ensure_user_ai_room,
    maybe_name_ai_room_from_first_prompt,
    sync_student_chat_access,
    user_can_access_room,
    user_can_use_lesson_context,
    user_has_active_enrollment,
)
from .models import AIResponseRun, ChatRoom, ChatRoomUserState, Message, AIFeedback


logger = logging.getLogger(__name__)


def _room_rank(item):
    return (item.last_message_at or item.created_at, item.created_at, item.id)


def _room_sort_key(item):
    return (
        1 if getattr(item, "is_pinned", False) else 0,
        item.last_message_at or item.created_at,
        item.created_at,
        item.id,
    )


def _ensure_room_states(user, rooms):
    if not user or not user.is_authenticated or not rooms:
        return {}

    room_ids = [room.id for room in rooms if room and room.id]
    existing = {
        state.room_id: state
        for state in ChatRoomUserState.objects.filter(user=user, room_id__in=room_ids)
    }
    missing = [
        ChatRoomUserState(user=user, room_id=room_id)
        for room_id in room_ids
        if room_id not in existing
    ]
    if missing:
        ChatRoomUserState.objects.bulk_create(missing, ignore_conflicts=True)
        existing = {
            state.room_id: state
            for state in ChatRoomUserState.objects.filter(user=user, room_id__in=room_ids)
        }
    return existing


def _attach_room_state(user, rooms):
    states = _ensure_room_states(user, rooms)
    for room in rooms:
        state = states.get(room.id)
        room.user_state = state
        room.is_pinned = bool(state and state.is_pinned)
        unread_qs = room.messages.exclude(sender=user)
        if state and state.last_read_at:
            unread_qs = unread_qs.filter(created_at__gt=state.last_read_at)
        room.unread_count = unread_qs.count()
    return rooms


def _mark_room_read(user, room):
    if not user or not user.is_authenticated or not room:
        return None
    state, _ = ChatRoomUserState.objects.get_or_create(user=user, room=room)
    state.mark_read()
    room.unread_count = 0
    room.user_state = state
    room.is_pinned = state.is_pinned
    return state


def _build_messenger_rooms(user):
    sync_student_chat_access(user)
    latest_message = Message.objects.filter(room=OuterRef("pk")).order_by("-created_at")

    rooms = list(
        ChatRoom.objects.filter(participants=user)
        .select_related("cohort")
        .annotate(
            last_message_at=Max("messages__created_at"),
            last_message_text=Subquery(latest_message.values("text")[:1]),
            message_count=Count("messages"),
        )
    )
    rooms = [room for room in rooms if user_can_access_room(user, room)]
    rooms = _attach_room_state(user, rooms)

    rooms_by_type = {}
    for room in rooms:
        rooms_by_type.setdefault(room.room_type, []).append(room)

    active_cohort_id = (
        Enrollment.objects.filter(enrollment_active_access_q(), student=user)
        .order_by("-joined_at")
        .values_list("cohort_id", flat=True)
        .first()
    )

    group_room = None
    group_candidates = rooms_by_type.get("group", [])
    if group_candidates:
        if active_cohort_id:
            group_room = next((g for g in group_candidates if g.cohort_id == active_cohort_id), None)
        group_room = group_room or max(group_candidates, key=_room_rank)

    tutor_room = None
    tutor_candidates = rooms_by_type.get("private", [])
    if tutor_candidates:
        tutor_room = max(tutor_candidates, key=_room_rank)

    ai_room = None
    ai_candidates = rooms_by_type.get("ai", [])
    if ai_candidates:
        ai_candidates = sorted(ai_candidates, key=_room_sort_key, reverse=True)
        ai_room = ai_candidates[0]
    else:
        ai_room = ensure_user_ai_room(user)
        ai_room.last_message_at = None
        ai_room.last_message_text = None
        ai_room.message_count = 0
        ai_room.unread_count = 0
        ai_room.is_pinned = False
        ai_candidates = [ai_room]

    return {
        "messenger_rooms": rooms,
        "group_room": group_room,
        "tutor_room": tutor_room,
        "ai_room": ai_room,
        "ai_rooms": ai_candidates,
        "has_active_enrollment": user_has_active_enrollment(user),
    }


def _skill_label(slug):
    if not slug:
        return ""
    try:
        return SkillRegistry().get(slug).name
    except KeyError:
        return slug.replace("_", " ").title()


def _run_used_tools(run):
    tools = (run.metadata or {}).get("used_tools", []) if run else []
    return tools if isinstance(tools, list) else []


def _run_rag_sources(run):
    sources = (run.metadata or {}).get("rag_sources", []) if run else []
    return sources if isinstance(sources, list) else []


def _rag_source_title(sources):
    if not sources:
        return ""
    lines = []
    for source in sources[:4]:
        number = source.get("number", "?")
        label = source.get("label") or " > ".join(
            part
            for part in [
                source.get("course_title", ""),
                source.get("module_title", ""),
                source.get("lesson_title", ""),
            ]
            if part
        )
        lines.append(f"Manba {number}: {label or 'RAG chunk'}")
    return "\n".join(lines)


def _can_manage_message(user, message):
    return (
        user
        and user.is_authenticated
        and message.sender_id == user.id
        and not message.is_ai_response
        and not message.is_deleted
    )


def _attachment_payload(message):
    if not message.attachment_url:
        return None
    return {
        "url": message.attachment_url,
        "name": message.attachment_name or message.attachment.name.rsplit("/", 1)[-1],
        "content_type": message.attachment_content_type,
        "size": message.attachment_size,
        "size_label": message.attachment_size_label,
        "is_image": message.is_image_attachment,
    }


def _message_payload(message, user, *, run=None, last_user_message_id=None):
    sender = message.sender
    is_ai = message.is_ai_response
    payload = {
        "id": message.id,
        "message_id": message.id,
        "text": message.display_text,
        "message": message.display_text,
        "sender_id": sender.id if sender else None,
        "sender_name": sender.get_full_name() or sender.username if sender else "Azure AI",
        "is_ai": is_ai,
        "created_at": message.created_at.strftime("%H:%M"),
        "edited_at": message.edited_at.strftime("%H:%M") if message.edited_at else "",
        "is_deleted": message.is_deleted,
        "can_edit": _can_manage_message(user, message),
        "attachment": _attachment_payload(message),
    }
    if is_ai:
        payload.update(
            {
                "regenerate_user_message_id": (
                    (run.user_message_id if run else None) or last_user_message_id
                ),
                "ai_skill_slug": run.skill_slug if run else "",
                "ai_skill_label": _skill_label(run.skill_slug) if run else "",
                "ai_used_tools": _run_used_tools(run),
                "ai_rag_sources": _run_rag_sources(run),
            }
        )
    return payload


def _broadcast_message_event(message, *, event_type="message_update", user=None):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    payload = _message_payload(message, user or message.sender)
    payload["room_id"] = message.room_id
    async_to_sync(channel_layer.group_send)(
        f"chat_{message.room_id}",
        {
            "type": "message_update",
            "event_type": event_type,
            "payload": payload,
        },
    )


def _room_messages(room, user=None):
    if not room:
        return []
    messages = list(room.messages.select_related("sender").order_by("created_at")[:100])
    ai_message_ids = [message.id for message in messages if message.is_ai_response]

    feedback_map = {}
    if user and user.is_authenticated:
        feedback_map = {
            feedback.message_id: feedback
            for feedback in AIFeedback.objects.filter(message_id__in=ai_message_ids, student=user)
        }
    feedback_totals = {
        row["message_id"]: {
            "positive": row["positive_count"],
            "negative": row["negative_count"],
        }
        for row in AIFeedback.objects.filter(message_id__in=ai_message_ids)
        .values("message_id")
        .annotate(
            positive_count=Count("id", filter=Q(rating=AIFeedback.RATING_POSITIVE)),
            negative_count=Count("id", filter=Q(rating=AIFeedback.RATING_NEGATIVE)),
        )
    }
    run_map = {}
    for run in (
        AIResponseRun.objects.filter(ai_message_id__in=ai_message_ids)
        .order_by("-created_at")
        .only("ai_message_id", "user_message_id", "skill_slug", "metadata")
    ):
        run_map.setdefault(run.ai_message_id, run)
    last_user_message_id = None
    for message in messages:
        if not message.is_ai_response and message.sender_id:
            last_user_message_id = message.id
        feedback = feedback_map.get(message.id)
        totals = feedback_totals.get(message.id, {"positive": 0, "negative": 0})
        run = run_map.get(message.id)
        message.display_body = message.display_text
        message.can_manage = _can_manage_message(user, message)
        message.attachment_payload = _attachment_payload(message)
        message.user_feedback_rating = feedback.rating if feedback else None
        message.feedback_positive_count = totals["positive"]
        message.feedback_negative_count = totals["negative"]
        message.ai_regenerate_user_message_id = (run.user_message_id if run else None) or (
            last_user_message_id if message.is_ai_response else None
        )
        message.ai_skill_slug = run.skill_slug if run else ""
        message.ai_skill_label = _skill_label(message.ai_skill_slug)
        message.ai_used_tools = _run_used_tools(run)
        message.ai_rag_sources = _run_rag_sources(run)
        message.ai_rag_source_title = _rag_source_title(message.ai_rag_sources)
    return messages


class _MessengerRoomView(LoginRequiredMixin, TemplateView):
    """Base for the three messenger shell variants (AI / group / tutor).

    For now each page ships with prototype mock data and inline JS;
    real room/message loading goes through the existing JSON APIs
    (get_user_rooms, get_room_messages) and the WebSocket consumer.
    """

    active_room = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_build_messenger_rooms(self.request.user))
        context["active_room"] = self.active_room
        if self.active_room == "ai":
            room_id = self.kwargs.get("room_id")
            if room_id is not None:
                active_chat_room = next((room for room in context["ai_rooms"] if room.id == room_id), None)
                if active_chat_room is None:
                    raise Http404("AI chat topilmadi")
            else:
                active_chat_room = context["ai_room"]
        else:
            active_room_map = {
                "group": context["group_room"],
                "tutor": context["tutor_room"],
            }
            active_chat_room = active_room_map.get(self.active_room)
        context["active_chat_room"] = active_chat_room
        context["active_ai_room_id"] = active_chat_room.id if self.active_room == "ai" and active_chat_room else None
        if active_chat_room:
            _mark_room_read(self.request.user, active_chat_room)
        context["chat_messages"] = _room_messages(active_chat_room, self.request.user)
        context["chat_locked"] = self.active_room in {"group", "tutor"} and active_chat_room is None
        if self.active_room == "ai":
            context["ai_skills"] = SkillRegistry().all()
            context["ai_model_choices"] = self.request.user.effective_ai_model_choices()
            context["active_context_lesson"] = self._active_context_lesson()
        return context

    def _active_context_lesson(self):
        lesson_id = self.request.GET.get("lesson")
        try:
            lesson_id = int(lesson_id)
        except (TypeError, ValueError):
            return None
        lesson = Lesson.objects.select_related("module__course").filter(id=lesson_id).first()
        if lesson and user_can_use_lesson_context(self.request.user, lesson):
            return lesson
        return None


class MessengerAIView(_MessengerRoomView):
    template_name = "messenger/ai.html"
    active_room = "ai"


class MessengerGroupView(_MessengerRoomView):
    template_name = "messenger/group.html"
    active_room = "group"


class MessengerTutorView(_MessengerRoomView):
    template_name = "messenger/tutor.html"
    active_room = "tutor"


@login_required
@require_POST
def create_ai_chat(request):
    # Bo'sh xona bo'lsa qayta ishlatiladi — har bosishda yangi bo'sh chat
    # yaralib qolmaydi (ilk xabar yuborilguncha bitta bo'sh xona yetadi).
    room = get_or_create_ai_draft_room(request.user)
    return redirect("messenger:ai_room", room_id=room.id)


@login_required
@require_POST
def widget_ai_message(request):
    """Floating AzureAI widget xabarini qabul qiladi.

    Lazy room creation: AI xonasi FAQAT haqiqiy xabar yuborilganda yaratiladi.
    Widget ochilib, hech narsa yozilmasa hech qanday xona/yozuv saqlanmaydi.
    Birinchi xabar `room_id` siz keladi → yangi xona yaratiladi va qaytariladi;
    keyingi xabarlar o'sha `room_id` bilan kelib bitta suhbatda davom etadi.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    message_text = str(data.get("message", "") or "").strip()
    if not message_text:
        return JsonResponse({"status": "error", "message": "Bo'sh xabar yuborib bo'lmaydi."}, status=400)

    room = None
    raw_room_id = data.get("room_id")
    if raw_room_id is not None:
        try:
            room = ChatRoom.objects.filter(
                id=int(raw_room_id),
                room_type="ai",
                participants=request.user,
            ).first()
        except (TypeError, ValueError):
            room = None

    # Lazy: faqat shu nuqtada (haqiqiy xabar bilan) yangi xona yaratiladi.
    created_room = False
    if room is None:
        room = create_user_ai_room(request.user)
        created_room = True

    from .signals import suppress_ai_signal
    from .tasks import generate_ai_response

    with suppress_ai_signal():
        user_message = Message.objects.create(room=room, sender=request.user, text=message_text)
    maybe_name_ai_room_from_first_prompt(room, message_text)
    room.refresh_from_db(fields=["name"])

    ai_message_id = generate_ai_response.run(
        room_id=room.id,
        student_id=request.user.id,
        user_question=message_text,
        user_message_id=user_message.id,
    )
    ai_message = Message.objects.filter(id=ai_message_id).first() if ai_message_id else None

    return JsonResponse(
        {
            "status": "success",
            "room_id": room.id,
            "room_name": room.name,
            "created_room": created_room,
            "room_url": f"/messenger/ai/{room.id}/",
            "user_message": {
                "id": user_message.id,
                "text": user_message.text,
                "created_at": user_message.created_at.strftime("%H:%M"),
            },
            "ai_message": {
                "id": ai_message.id if ai_message else None,
                "text": (
                    ai_message.text
                    if ai_message
                    else "Kechirasiz, hozir javob bera olmadim. Birozdan so'ng qayta urinib ko'ring."
                ),
                "created_at": (ai_message.created_at if ai_message else timezone.now()).strftime("%H:%M"),
            },
        }
    )


@login_required
@never_cache
def get_user_rooms(request):
    """
    Foydalanuvchining barcha chat xonalarini qaytaradi (Guruh, Tutor, AzureAI).
    """
    room_context = _build_messenger_rooms(request.user)
    selected_rooms = [
        room
        for room in (
            room_context["group_room"],
            room_context["tutor_room"],
        )
        if room is not None
    ] + list(room_context["ai_rooms"])

    data = []
    for r in selected_rooms:
        data.append(
            {
                "id": r.id,
                "name": r.name,
                "type": r.room_type,
                "cohort_id": r.cohort.id if r.cohort else None,
                "message_count": r.message_count,
                "last_message_at": r.last_message_at.isoformat() if r.last_message_at else None,
                "last_message_text": r.last_message_text or "",
                "unread_count": getattr(r, "unread_count", 0),
                "is_pinned": getattr(r, "is_pinned", False),
            }
        )

    return JsonResponse({'status': 'success', 'rooms': data})


@login_required
@never_cache
def get_room_messages(request, room_id):
    """
    Ma'lum bir chat xonasining eski xabarlarini qaytaradi.
    Faqatgina o'qish huquqi bor xonalar ruxsat etiladi.
    """
    try:
        room = ChatRoom.objects.get(id=room_id)
        if not user_can_access_room(request.user, room):
            return JsonResponse({'status': 'error', 'message': 'Chat xonasi topilmadi yoki huquq yo\'q'}, status=403)
        _mark_room_read(request.user, room)
        # Oxirgi 100 ta xabarni olib, keyin UI uchun kronologik tartibda qaytaramiz.
        recent_messages = list(
            room.messages.select_related('sender').order_by('-created_at')[:100]
        )
        recent_messages.reverse()

        ai_message_ids = [message.id for message in recent_messages if message.is_ai_response]
        feedback_map = {
            feedback.message_id: feedback
            for feedback in AIFeedback.objects.filter(
                message_id__in=ai_message_ids,
                student=request.user,
            )
        }
        feedback_totals = {
            row["message_id"]: {
                "positive": row["positive_count"],
                "negative": row["negative_count"],
            }
            for row in AIFeedback.objects.filter(message_id__in=ai_message_ids)
            .values("message_id")
            .annotate(
                positive_count=Count("id", filter=Q(rating=AIFeedback.RATING_POSITIVE)),
                negative_count=Count("id", filter=Q(rating=AIFeedback.RATING_NEGATIVE)),
            )
        }
        run_map = {}
        for run in (
        AIResponseRun.objects.filter(ai_message_id__in=ai_message_ids)
            .order_by("-created_at")
            .only("ai_message_id", "user_message_id", "skill_slug", "metadata")
        ):
            run_map.setdefault(run.ai_message_id, run)

        msgs_data = []
        last_user_message_id = None
        for m in recent_messages:
            if not m.is_ai_response and m.sender_id:
                last_user_message_id = m.id
            user_feedback = feedback_map.get(m.id)
            totals = feedback_totals.get(m.id, {"positive": 0, "negative": 0})
            run = run_map.get(m.id)
            payload = _message_payload(m, request.user, run=run, last_user_message_id=last_user_message_id)
            payload.update({
                'feedback': (
                    {
                        'rating': user_feedback.rating,
                        'comment': user_feedback.comment,
                    }
                    if user_feedback
                    else None
                ),
                'feedback_totals': totals if m.is_ai_response else None,
            })
            msgs_data.append(payload)

        return JsonResponse({'status': 'success', 'messages': msgs_data})

    except ChatRoom.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Chat xonasi topilmadi yoki huquq yo\'q'}, status=403)


@login_required
@require_POST
def toggle_room_pin(request, room_id):
    room = ChatRoom.objects.filter(id=room_id).first()
    if not room or not user_can_access_room(request.user, room):
        return JsonResponse({"status": "error", "message": "Chat xonasi topilmadi"}, status=404)

    state, _ = ChatRoomUserState.objects.get_or_create(user=request.user, room=room)
    state.is_pinned = not state.is_pinned
    state.save(update_fields=["is_pinned", "updated_at"])
    return JsonResponse({"status": "success", "room_id": room.id, "is_pinned": state.is_pinned})


@login_required
@require_POST
def edit_message(request, message_id):
    message = Message.objects.select_related("room", "sender").filter(id=message_id).first()
    if not message or not user_can_access_room(request.user, message.room):
        return JsonResponse({"status": "error", "message": "Xabar topilmadi"}, status=404)
    if not _can_manage_message(request.user, message):
        return JsonResponse({"status": "error", "message": "Bu xabarni tahrirlab bo'lmaydi"}, status=403)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        data = {}
    text = str(data.get("text", "") or "").strip()
    if not text:
        return JsonResponse({"status": "error", "message": "Xabar matni bo'sh bo'lmasin"}, status=400)

    message.text = text[:4000]
    message.edited_at = timezone.now()
    message.save(update_fields=["text", "edited_at"])
    _broadcast_message_event(message, event_type="message_edited", user=request.user)
    return JsonResponse({"status": "success", "message": _message_payload(message, request.user)})


@login_required
@require_POST
def delete_message(request, message_id):
    message = Message.objects.select_related("room", "sender").filter(id=message_id).first()
    if not message or not user_can_access_room(request.user, message.room):
        return JsonResponse({"status": "error", "message": "Xabar topilmadi"}, status=404)
    if not _can_manage_message(request.user, message):
        return JsonResponse({"status": "error", "message": "Bu xabarni o'chirib bo'lmaydi"}, status=403)

    message.is_deleted = True
    message.deleted_at = timezone.now()
    message.edited_at = None
    message.text = ""
    message.save(update_fields=["is_deleted", "deleted_at", "edited_at", "text"])
    _broadcast_message_event(message, event_type="message_deleted", user=request.user)
    return JsonResponse({"status": "success", "message": _message_payload(message, request.user)})


@login_required
@require_POST
def upload_message_attachment(request):
    room_id = request.POST.get("room_id")
    room = ChatRoom.objects.filter(id=room_id).first()
    if not room or not user_can_access_room(request.user, room):
        return JsonResponse({"status": "error", "message": "Chat xonasi topilmadi"}, status=404)

    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"status": "error", "message": "Fayl tanlanmagan"}, status=400)
    # Hajm va tur tekshiruvi baytlar bo'yicha: `attachment_content_type` brauzer
    # yuboradigan qiymat va unga ishonib bo'lmaydi (A0b).
    try:
        validate_upload(upload, profile="document")
    except ValidationError as exc:
        return JsonResponse({"status": "error", "message": exc.messages[0]}, status=400)

    text = str(request.POST.get("text", "") or "").strip()[:1000]
    from .signals import suppress_ai_signal

    with suppress_ai_signal():
        message = Message.objects.create(
            room=room,
            sender=request.user,
            text=text,
            attachment=upload,
            attachment_name=upload.name[:255],
            attachment_content_type=getattr(upload, "content_type", "")[:120],
            attachment_size=upload.size,
        )
    _mark_room_read(request.user, room)
    _broadcast_message_event(message, event_type="message_uploaded", user=request.user)

    # AI xonasiga PDF/rasm yuklansa (yoki izohli fayl kelsa) — AI o'zi javob boshlaydi.
    upload_name = (upload.name or "").lower()
    upload_type = (getattr(upload, "content_type", "") or "").lower()
    is_pdf = upload_name.endswith(".pdf") or "pdf" in upload_type
    is_image = upload_type.startswith("image/") or upload_name.endswith(
        (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
    )
    if room.room_type == "ai" and (is_pdf or is_image or text):
        from .tasks import generate_ai_response

        if text:
            question = text
        elif is_pdf:
            question = "Men PDF hujjat yukladim — qisqacha mazmunini aytib bera olasanmi?"
        else:
            question = "Men rasm yubordim — unda nima ko'rinayotganini aytib bera olasanmi?"
        try:
            generate_ai_response.delay(
                room_id=room.id,
                student_id=request.user.id,
                user_question=question,
                user_message_id=message.id,
            )
        except Exception as exc:  # Celery yo'q bo'lsa lokal thread fallback (signal bilan bir xil)
            logger.warning("Celery dispatch error on upload, falling back to thread: %s", exc)
            import threading

            threading.Thread(
                target=generate_ai_response.run,
                kwargs={
                    "room_id": room.id,
                    "student_id": request.user.id,
                    "user_question": question,
                    "user_message_id": message.id,
                },
                daemon=True,
            ).start()

    return JsonResponse({"status": "success", "message": _message_payload(message, request.user)})


@login_required
@require_POST
def submit_ai_feedback(request, message_id):
    try:
        msg = Message.objects.select_related("room").get(id=message_id, is_ai_response=True)
        if not user_can_access_room(request.user, msg.room):
            return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)

        data = json.loads(request.body)
        rating = data.get('rating')
        comment = str(data.get('comment', '') or '').strip()

        if rating not in [AIFeedback.RATING_POSITIVE, AIFeedback.RATING_NEGATIVE]:
            return JsonResponse({'status': 'error', 'message': 'Invalid rating'}, status=400)

        feedback, _ = AIFeedback.objects.update_or_create(
            message=msg,
            student=request.user,
            defaults={
                'rating': rating,
                'comment': comment
            }
        )
        totals = AIFeedback.objects.filter(message=msg).aggregate(
            positive_count=Count("id", filter=Q(rating=AIFeedback.RATING_POSITIVE)),
            negative_count=Count("id", filter=Q(rating=AIFeedback.RATING_NEGATIVE)),
        )
        return JsonResponse(
            {
                'status': 'success',
                'feedback': {
                    'rating': feedback.rating,
                    'comment': feedback.comment,
                },
                'feedback_totals': {
                    'positive': totals["positive_count"],
                    'negative': totals["negative_count"],
                },
            }
        )
    except Message.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Message not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
