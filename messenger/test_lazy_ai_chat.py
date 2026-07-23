from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from messenger.access import create_user_ai_room, get_or_create_ai_draft_room
from messenger.models import ChatRoom, Message


User = get_user_model()


class LazyAiChatTests(TestCase):
    """"Yangi suhbat" har bosilganda bo'sh xona to'planmasin.

    Bo'sh (xabarsiz) xona qayta ishlatiladi; ilk xabar yuborilgandagina
    xona ro'yxatda saqlanadi.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="lazy", email="lazy@example.test", password="x"
        )
        self.client.force_login(self.user)

    def _ai_room_count(self):
        return ChatRoom.objects.filter(room_type="ai", participants=self.user).count()

    # --- helper -----------------------------------------------------

    def test_draft_reuses_existing_empty_room(self):
        first = create_user_ai_room(self.user)
        reused = get_or_create_ai_draft_room(self.user)
        self.assertEqual(reused.id, first.id)
        self.assertEqual(self._ai_room_count(), 1)

    def test_draft_creates_when_all_rooms_have_messages(self):
        room = create_user_ai_room(self.user)
        Message.objects.create(room=room, sender=self.user, text="salom")
        fresh = get_or_create_ai_draft_room(self.user)
        self.assertNotEqual(fresh.id, room.id)
        self.assertEqual(self._ai_room_count(), 2)

    # --- view: clicking "new chat" repeatedly ------------------------

    def test_clicking_new_chat_twice_does_not_accumulate_empty_rooms(self):
        self.client.post(reverse("messenger:new_ai_chat"))
        self.client.post(reverse("messenger:new_ai_chat"))
        self.client.post(reverse("messenger:new_ai_chat"))
        # Bir nechта bosish — lekin bitta bo'sh xona
        self.assertEqual(self._ai_room_count(), 1)

    def test_new_chat_after_first_message_creates_a_second_room(self):
        r1 = self.client.post(reverse("messenger:new_ai_chat"))
        room_id = r1.url.rstrip("/").split("/")[-1]
        room = ChatRoom.objects.get(id=room_id)
        Message.objects.create(room=room, sender=self.user, text="birinchi xabar")
        # Endi yangi suhbat — bo'sh yo'q, yangisi yaratiladi
        self.client.post(reverse("messenger:new_ai_chat"))
        self.assertEqual(self._ai_room_count(), 2)

    # --- list hides empty non-active rooms ---------------------------

    def test_empty_room_hidden_from_list_unless_active(self):
        # Xabarli xona
        active_room = create_user_ai_room(self.user)
        Message.objects.create(room=active_room, sender=self.user, text="bor")
        # Bo'sh xona (faol emas)
        empty_room = create_user_ai_room(self.user)

        # Xabarli xonani ochamiz — bo'sh xona ro'yxatda ko'rinmasligi kerak
        response = self.client.get(reverse("messenger:ai_room", args=[active_room.id]))
        html = response.content.decode()
        self.assertIn(f'data-sidebar-room-id="{active_room.id}"', html)
        self.assertNotIn(f'data-sidebar-room-id="{empty_room.id}"', html)

    def test_empty_room_shown_when_it_is_active(self):
        empty_room = create_user_ai_room(self.user)
        response = self.client.get(reverse("messenger:ai_room", args=[empty_room.id]))
        html = response.content.decode()
        # Ochiq turgan bo'sh xona ro'yxatda ko'rinadi
        self.assertIn(f'data-sidebar-room-id="{empty_room.id}"', html)
