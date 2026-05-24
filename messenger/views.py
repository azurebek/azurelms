import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max, Count, Q, OuterRef, Subquery
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from ai.skills.registry import SkillRegistry
from cohorts.models import Enrollment, enrollment_active_access_q
from courses.models import Lesson
from .access import (
    create_user_ai_room,
    ensure_user_ai_room,
    sync_student_chat_access,
    user_can_access_room,
    user_can_use_lesson_context,
    user_has_active_enrollment,
)
from .models import AIResponseRun, ChatRoom, Message, AIFeedback


def _room_rank(item):
    return (item.last_message_at or item.created_at, item.created_at, item.id)


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
        ai_candidates = sorted(ai_candidates, key=_room_rank, reverse=True)
        ai_room = ai_candidates[0]
    else:
        ai_room = ensure_user_ai_room(user)
        ai_room.last_message_at = None
        ai_room.last_message_text = None
        ai_room.message_count = 0
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


def _room_messages(room, user=None):
    if not room:
        return []
    messages = list(room.messages.select_related("sender").order_by("created_at")[:100])
    ai_message_ids = [message.id for message in messages if message.is_ai_response]
    if not ai_message_ids:
        return messages

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
        context["chat_messages"] = _room_messages(active_chat_room, self.request.user)
        context["chat_locked"] = self.active_room in {"group", "tutor"} and active_chat_room is None
        if self.active_room == "ai":
            context["ai_skills"] = SkillRegistry().all()
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
    room = create_user_ai_room(request.user)
    return redirect("messenger:ai_room", room_id=room.id)


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
            msgs_data.append({
                'id': m.id,
                'text': m.text,
                'sender_id': m.sender.id if m.sender else None,
                'sender_name': m.sender.get_full_name() or m.sender.username if m.sender else "Azure AI",
                'is_ai': m.is_ai_response,
                'created_at': m.created_at.strftime('%H:%M'),
                'feedback': (
                    {
                        'rating': user_feedback.rating,
                        'comment': user_feedback.comment,
                    }
                    if user_feedback
                    else None
                ),
                'feedback_totals': totals if m.is_ai_response else None,
                'regenerate_user_message_id': (
                    (run.user_message_id if run else None) or last_user_message_id if m.is_ai_response else None
                ),
                'ai_skill_slug': run.skill_slug if run else "",
                'ai_skill_label': _skill_label(run.skill_slug) if run else "",
                'ai_used_tools': _run_used_tools(run),
                'ai_rag_sources': _run_rag_sources(run),
            })

        return JsonResponse({'status': 'success', 'messages': msgs_data})

    except ChatRoom.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Chat xonasi topilmadi yoki huquq yo\'q'}, status=403)

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
