from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import ChatRoom, Message

@login_required
def get_user_rooms(request):
    """
    Foydalanuvchining barcha chat xonalarini qaytaradi (Guruh, Tutor, AzureAI).
    """
    rooms = ChatRoom.objects.filter(participants=request.user)
    
    data = []
    for r in rooms:
        data.append({
            'id': r.id,
            'name': r.name,
            'type': r.room_type,
            'cohort_id': r.cohort.id if r.cohort else None
        })
        
    return JsonResponse({'status': 'success', 'rooms': data})


@login_required
def get_room_messages(request, room_id):
    """
    Ma'lum bir chat xonasining eski xabarlarini qaytaradi.
    Faqatgina o'qish huquqi bor xonalar ruxsat etiladi.
    """
    try:
        room = ChatRoom.objects.get(id=room_id, participants=request.user)
        # Optimize: Fetch sender information in the same query to prevent N+1 loop
        messages = room.messages.select_related('sender').order_by('created_at')[:100]  # oxirgi 100 ta xabar
        
        msgs_data = []
        for m in messages:
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
