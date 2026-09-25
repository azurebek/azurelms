"""Human-chat presentation; access and mutations remain canonical."""
from django.http import Http404
from django.urls import reverse
from django.utils.crypto import salted_hmac

from core.frontend_v1 import FrontendV1Mixin, teacher_v1_navigation
from core.flags import flag_enabled


class HumanMessengerV1Mixin(FrontendV1Mixin):
    frontend_v1_flag = "frontend_v1_messenger"
    frontend_v1_template = "frontend_v1/messenger.html"
    frontend_v1_title = "Xabarlar"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.frontend_v1_enabled:
            context["active_nav"] = "messenger:group"
            if self.request.user.is_staff and flag_enabled("frontend_v1_teacher"):
                context.update(teacher_v1_navigation("messenger:group"))
            context["chat_scope"] = salted_hmac(
                "frontend-v1-messenger", f"{self.request.user.pk}:{self.request.session.session_key}",
            ).hexdigest()
        return context


def select_human_room(request, context, active_room, default, *, sort_key):
    room_type = "group" if active_room == "group" else "private"
    human_rooms = sorted(
        (r for r in context["messenger_rooms"] if r.room_type in {"group", "private"}),
        key=sort_key, reverse=True,
    )
    for room in human_rooms:
        name = "messenger:group" if room.room_type == "group" else "messenger:tutor"
        room.v1_url = f"{reverse(name)}?room={room.pk}"
    context["human_rooms"] = human_rooms
    if "room" not in request.GET:
        return default
    values = request.GET.getlist("room")
    if len(values) != 1 or not values[0].isascii() or not values[0].isdigit():
        raise Http404("Suhbat topilmadi")
    chosen = next((r for r in human_rooms if str(r.pk) == values[0] and r.room_type == room_type), None)
    if chosen is None:
        raise Http404("Suhbat topilmadi")
    return chosen
