"""A0b/4 — ochiq WebSocket sessiya ruxsat o'zgarishini sezishi kerak.

Ilgari ruxsat faqat `connect()` da tekshirilardi. Ya'ni socket bir marta
ochilgach, o'quvchining obunasi tugasa yoki hisobi bloklansa ham u xonaga
yozishda davom etaverardi — qayta ulanmagunicha hech narsa o'zgarmasdi.

Endi har `receive()` da ruxsat DB holatidan qayta hisoblanadi va yo'qolgan
bo'lsa socket `4403` kodi bilan yopiladi.

Ikkinchi nozik nuqta: `self.user` — socket ochilgandagi nusxa. Undagi
`is_active` eskirgan bo'ladi, shuning uchun foydalanuvchi holati ham DB'dan
qayta o'qiladi.
"""

import datetime
import json

from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase

from core.asgi import application
from messenger.consumers import ChatConsumer

User = get_user_model()


class SocketAccessRecheckTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        from cohorts.models import Cohort, Enrollment
        from courses.models import Course
        from messenger.models import ChatRoom

        self.student = User.objects.create_user(
            username="ws_student", email="ws_student@t.uz", password="pass-12345")
        course = Course.objects.create(title="WS Course", description="d", level="beginner")
        self.cohort = Cohort.objects.create(
            name="WS Cohort", course=course, start_date=datetime.date(2026, 5, 1))
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status="active")

        self.room = ChatRoom.objects.create(
            room_type="group", name="WS room", cohort=self.cohort)
        self.room.participants.add(self.student)

    # --- yordamchi ---------------------------------------------------------

    async def _connect(self):
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.room.id}/")
        communicator.scope["user"] = self.student
        connected, _ = await communicator.connect()
        return communicator, connected

    async def _send(self, communicator, text="salom"):
        await communicator.send_to(text_data=json.dumps({
            "action": "message", "message": text,
        }))

    # --- testlar -----------------------------------------------------------

    async def test_active_student_can_send(self):
        communicator, connected = await self._connect()
        self.assertTrue(connected)
        try:
            await self._send(communicator)
            response = await communicator.receive_from(timeout=5)
            self.assertNotIn("access_revoked", response)
        finally:
            await communicator.disconnect()

    async def test_expired_enrollment_closes_the_open_socket(self):
        """Obuna socket ochiq turganda tugasa — keyingi xabar uni yopadi."""
        from asgiref.sync import sync_to_async
        from cohorts.models import Enrollment

        communicator, connected = await self._connect()
        self.assertTrue(connected)
        try:
            await sync_to_async(
                Enrollment.objects.filter(pk=self.enrollment.pk).update
            )(status=Enrollment.STATUS_EXPIRED)

            await self._send(communicator)
            payload = json.loads(await communicator.receive_from(timeout=5))
            self.assertEqual(payload["type"], "access_revoked")
            self.assertEqual(
                (await communicator.receive_output(timeout=5))["type"],
                "websocket.close",
            )
        finally:
            await communicator.disconnect()

    async def test_deactivated_account_closes_the_open_socket(self):
        """Bloklangan hisob: `self.user` dagi `is_active` eskirgan bo'lsa ham."""
        from asgiref.sync import sync_to_async

        communicator, connected = await self._connect()
        self.assertTrue(connected)
        try:
            await sync_to_async(
                User.objects.filter(pk=self.student.pk).update
            )(is_active=False)

            await self._send(communicator)
            payload = json.loads(await communicator.receive_from(timeout=5))
            self.assertEqual(payload["type"], "access_revoked")
        finally:
            await communicator.disconnect()

    async def test_no_message_is_stored_after_access_is_revoked(self):
        from asgiref.sync import sync_to_async
        from cohorts.models import Enrollment
        from messenger.models import Message

        communicator, _ = await self._connect()
        try:
            await sync_to_async(
                Enrollment.objects.filter(pk=self.enrollment.pk).update
            )(status=Enrollment.STATUS_EXPIRED)
            await self._send(communicator, text="ruxsatsiz xabar")
            await communicator.receive_from(timeout=5)
        finally:
            await communicator.disconnect()

        exists = await sync_to_async(
            Message.objects.filter(room=self.room, text="ruxsatsiz xabar").exists
        )()
        self.assertFalse(exists, "ruxsat bekor qilingandan keyin xabar saqlanib qoldi")

    def test_close_code_is_declared_on_the_consumer(self):
        self.assertEqual(ChatConsumer.ACCESS_REVOKED_CLOSE_CODE, 4403)
