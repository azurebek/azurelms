import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Max, Count, Q
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from cohorts.models import Enrollment, enrollment_active_access_q
from .access import user_can_access_room
from .models import ChatRoom, Message, AIFeedback


class MessengerShellView(LoginRequiredMixin, TemplateView):
    """Render the messenger shell (contacts + chat + detail panes).

    For now the page ships with prototype mock data and inline JS.
    Real room/message loading goes through the existing JSON APIs
    (get_user_rooms, get_room_messages) and the WebSocket consumer.
    """

    template_name = "messenger/shell.html"

@login_required
@never_cache
def get_user_rooms(request):
    """
    Foydalanuvchining barcha chat xonalarini qaytaradi (Guruh, Tutor, AzureAI).
    """
    rooms = list(
        ChatRoom.objects.filter(participants=request.user)
        .select_related("cohort")
        .annotate(
            last_message_at=Max("messages__created_at"),
            message_count=Count("messages"),
        )
    )
    rooms = [room for room in rooms if user_can_access_room(request.user, room)]

    rooms_by_type = {}
    for room in rooms:
        rooms_by_type.setdefault(room.room_type, []).append(room)

    active_cohort_id = (
        Enrollment.objects.filter(enrollment_active_access_q(), student=request.user)
        .order_by("-joined_at")
        .values_list("cohort_id", flat=True)
        .first()
    )

    def room_rank(item):
        return (item.last_message_at or item.created_at, item.created_at, item.id)

    selected_rooms = []

    # Group: avval aktiv cohort xonasi, bo'lmasa eng oxirgi faol xona.
    group_candidates = rooms_by_type.get("group", [])
    if group_candidates:
        preferred_group = None
        if active_cohort_id:
            preferred_group = next(
                (g for g in group_candidates if g.cohort_id == active_cohort_id),
                None,
            )
        selected_rooms.append(preferred_group or max(group_candidates, key=room_rank))

    # Private va AI: eng oxirgi faol xona.
    for room_type in ("private", "ai"):
        candidates = rooms_by_type.get(room_type, [])
        if candidates:
            selected_rooms.append(max(candidates, key=room_rank))

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
        
        msgs_data = []
        for m in recent_messages:
            user_feedback = feedback_map.get(m.id)
            totals = feedback_totals.get(m.id, {"positive": 0, "negative": 0})
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
