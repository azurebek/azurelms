from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import ChatRoom, Message

@login_required
def inbox(request):
    # Foydalanuvchining barcha chatlari
    rooms = request.user.chat_rooms.select_related('batch').prefetch_related('participants')
    
    selected_room = None
    messages = []
    
    # Agar chat tanlangan bo'lsa (URL da ?room=ID bo'lsa)
    room_id = request.GET.get('room')
    if room_id:
        try:
            selected_room = rooms.get(id=room_id)
            messages = selected_room.messages.select_related('sender').order_by('created_at')
            # O'qildi qilish (faqat boshqalar yozganini)
            selected_room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        except ChatRoom.DoesNotExist:
            pass

    return render(request, 'communication/inbox.html', {
        'rooms': rooms,
        'selected_room': selected_room,
        'messages': messages,
    })

@login_required
@require_POST
def send_message(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    content = request.POST.get('content')
    
    if content:
        Message.objects.create(room=room, sender=request.user, content=content)
    
    return redirect(f"{request.path.replace('send/', '')}?room={room_id}")

@login_required
def check_new_messages(request, room_id):
    # HTMX polling uchun
    room = get_object_or_404(ChatRoom, id=room_id, participants=request.user)
    messages = room.messages.select_related('sender').order_by('created_at')
    return render(request, 'communication/components/message_list.html', {
        'messages': messages,
        'selected_room': room
    })

@login_required
def message_stream(request):
    room_id = request.GET.get('room')
    messages = []
    selected_room = None
    
    if room_id:
        try:
            selected_room = request.user.chat_rooms.get(id=room_id)
            messages = selected_room.messages.select_related('sender').order_by('created_at')
        except ChatRoom.DoesNotExist:
            pass
            
    return render(request, 'communication/components/message_list.html', {
        'messages': messages,
        'selected_room': selected_room
    })
