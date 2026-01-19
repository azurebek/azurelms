from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
<<<<<<< ours
from .models import Message

@login_required
def inbox(request):
    return render(request, 'communication/inbox.html')

@login_required
def message_stream(request):
    messages = (
        Message.objects.filter(room__participants=request.user)
        .select_related("sender", "room")
        .order_by("-created_at")[:20]
    )
    messages = list(messages)[::-1]
    return render(request, "communication/components/message_list.html", {"messages": messages})
=======
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from education.models import Enrollment

from .models import ChatRoom, Message

@login_required
def inbox(request):
    rooms = (
        ChatRoom.objects.filter(participants=request.user)
        .select_related("batch")
        .prefetch_related("participants")
        .order_by("-last_activity")
    )
    room_cards = [_build_room_card(room, request.user) for room in rooms]
    return render(
        request,
        "communication/inbox.html",
        {
            "rooms": rooms,
            "room_cards": room_cards,
            "selected_room": None,
            "selected_room_card": None,
            "messages": [],
        },
    )


@login_required
def chat_detail(request, room_uuid):
    room = get_object_or_404(
        ChatRoom.objects.select_related("batch").prefetch_related("participants"),
        pk=room_uuid,
        participants=request.user,
    )
    messages = (
        room.messages.select_related("sender", "sender__profile")
        .order_by("created_at")
    )
    if request.headers.get("HX-Request") == "true":
        return render(
            request,
            "communication/components/message_list.html",
            {"room": room, "messages": messages, "user": request.user},
        )

    rooms = (
        ChatRoom.objects.filter(participants=request.user)
        .select_related("batch")
        .prefetch_related("participants")
        .order_by("-last_activity")
    )
    room_cards = [_build_room_card(room_item, request.user) for room_item in rooms]
    return render(
        request,
        "communication/inbox.html",
        {
            "rooms": rooms,
            "room_cards": room_cards,
            "selected_room": room,
            "selected_room_card": _build_room_card(room, request.user),
            "messages": messages,
        },
    )


@login_required
def send_message(request, room_uuid):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method.")

    room = get_object_or_404(ChatRoom, pk=room_uuid, participants=request.user)
    content = (request.POST.get("content") or "").strip()
    if not content:
        return HttpResponseBadRequest("Message cannot be empty.")

    message = Message.objects.create(room=room, sender=request.user, content=content)
    ChatRoom.objects.filter(pk=room.pk).update(last_activity=timezone.now())

    return render(
        request,
        "communication/components/message_item.html",
        {"message": message, "user": request.user},
    )


@login_required
def start_direct_chat(request, user_id):
    User = get_user_model()
    target_user = get_object_or_404(User.objects.select_related("profile"), pk=user_id)

    if target_user == request.user:
        return redirect("communication:inbox")

    if not _users_share_batch(request.user, target_user):
        return HttpResponseBadRequest("Users are not in the same batch.")

    room = (
        ChatRoom.objects.filter(type=ChatRoom.DIRECT, participants=request.user)
        .filter(participants=target_user)
        .first()
    )
    if not room:
        room = ChatRoom.objects.create(type=ChatRoom.DIRECT, last_activity=timezone.now())
        room.participants.add(request.user, target_user)

    return redirect("communication:chat_detail", room_uuid=room.pk)


def _users_share_batch(user, target_user):
    user_batches = set(
        Enrollment.objects.filter(user=user, is_active=True).values_list("batch_id", flat=True)
    )
    target_batches = set(
        Enrollment.objects.filter(user=target_user, is_active=True).values_list("batch_id", flat=True)
    )

    if user.is_staff:
        return bool(target_batches)
    if target_user.is_staff:
        return bool(user_batches)
    return bool(user_batches.intersection(target_batches))


def _build_room_card(room, current_user):
    other_user = None
    display_name = ""
    subtitle = ""
    avatar_url = ""

    if room.type == ChatRoom.DIRECT:
        other_user = next(
            (participant for participant in room.participants.all() if participant != current_user),
            None,
        )
        if other_user:
            display_name = _display_name(other_user)
            subtitle = other_user.email
            if hasattr(other_user, "profile") and other_user.profile.avatar:
                avatar_url = other_user.profile.avatar.url
    else:
        display_name = room.batch.title if room.batch else "Group chat"
        subtitle = "Batch group chat" if room.batch else "Group chat"

    return {
        "room": room,
        "display_name": display_name,
        "subtitle": subtitle,
        "avatar_url": avatar_url,
        "other_user": other_user,
    }


def _display_name(user):
    if hasattr(user, "profile") and user.profile.display_name:
        return user.profile.display_name
    full_name = user.get_full_name()
    return full_name or user.email
>>>>>>> theirs
