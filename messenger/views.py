from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Count
from cohorts.models import Enrollment
from .models import ChatRoom, Message

@login_required
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

    rooms_by_type = {}
    for room in rooms:
        rooms_by_type.setdefault(room.room_type, []).append(room)

    active_cohort_id = (
        Enrollment.objects.filter(student=request.user, status="active")
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
def get_room_messages(request, room_id):
    """
    Ma'lum bir chat xonasining eski xabarlarini qaytaradi.
    Faqatgina o'qish huquqi bor xonalar ruxsat etiladi.
    """
    try:
        room = ChatRoom.objects.get(id=room_id, participants=request.user)
        # Oxirgi 100 ta xabarni olib, keyin UI uchun kronologik tartibda qaytaramiz.
        recent_messages = list(
            room.messages.select_related('sender').order_by('-created_at')[:100]
        )
        recent_messages.reverse()
        
        msgs_data = []
        for m in recent_messages:
            msgs_data.append({
                'id': m.id,
                'text': m.text,
                'sender_id': m.sender.id if m.sender else None,
                'sender_name': m.sender.get_full_name() or m.sender.username if m.sender else "Azure AI",
                'is_ai': m.is_ai_response,
                'created_at': m.created_at.strftime('%H:%M')
            })
            
        return JsonResponse({'status': 'success', 'messages': msgs_data})
        
    except ChatRoom.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Chat xonasi topilmadi yoki huquq yo\'q'}, status=403)
