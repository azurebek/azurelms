"""Chat presentation; access and mutations remain canonical."""
from urllib.parse import urlencode
from django.http import Http404
from django.urls import reverse
from django.utils.crypto import salted_hmac

from core.frontend_v1 import FrontendV1Mixin, teacher_v1_navigation
from core.flags import flag_enabled


class HumanMessengerV1Mixin(FrontendV1Mixin):
    frontend_v1_flag = "frontend_v1_messenger"
    frontend_v1_template = "frontend_v1/messenger.html"
    frontend_v1_title = "Xabarlar"
    chat_active_nav = "messenger:group"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.frontend_v1_enabled:
            context["active_nav"] = self.chat_active_nav
            if self.request.user.is_staff and flag_enabled("frontend_v1_teacher"):
                context.update(teacher_v1_navigation(self.chat_active_nav))
            context["chat_scope"] = salted_hmac(
                "frontend-v1-messenger", f"{self.request.user.pk}:{self.request.session.session_key}",
            ).hexdigest()
            context["ai_v1_enabled"] = flag_enabled("frontend_v1_ai_messenger")
        return context


class AIMessengerV1Mixin(HumanMessengerV1Mixin):
    frontend_v1_flag = "frontend_v1_ai_messenger"
    frontend_v1_template = "frontend_v1/ai_messenger.html"
    frontend_v1_title = "Azure AI"
    chat_active_nav = "messenger:ai"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.frontend_v1_enabled:
            lesson = context.get("active_context_lesson")
            suffix = "?" + urlencode({"lesson": lesson.pk}) if lesson else ""
            context["ai_context_query"] = suffix
            context["human_v1_enabled"] = flag_enabled("frontend_v1_messenger")
            context["ai_skill_choices"] = self.request.user.effective_ai_skill_choices()
            context["v1_ai_rooms"] = [r for r in context["ai_rooms"] if r.message_count or r.pk == context["active_ai_room_id"]]
            for room in context["v1_ai_rooms"]:
                room.v1_url = reverse("messenger:ai_room", args=[room.pk]) + suffix
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
