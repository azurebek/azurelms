import json
from pathlib import Path

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.test import SimpleTestCase, TransactionTestCase

from core.asgi import application

from .tests import ClassbookFixtureMixin


class ClassbookSocketTests(ClassbookFixtureMixin, TransactionTestCase):
    reset_sequences = True

    async def test_active_student_can_connect_and_revocation_closes_live_socket(self):
        session = await database_sync_to_async(self.start)()
        communicator = WebsocketCommunicator(application, f"/ws/classbook/{session.id}/")
        communicator.scope["user"] = self.student
        connected, code = await communicator.connect()
        self.assertTrue(connected, f"socket ulanmadi: {code}")

        await database_sync_to_async(type(self.enrollment).objects.filter(pk=self.enrollment.pk).update)(
            status="frozen"
        )
        await communicator.send_to(text_data=json.dumps({"action": "ping"}))
        payload = await communicator.receive_json_from()
        self.assertEqual(payload["event_type"], "access_revoked")

    async def test_outsider_is_rejected(self):
        session = await database_sync_to_async(self.start)()
        communicator = WebsocketCommunicator(application, f"/ws/classbook/{session.id}/")
        communicator.scope["user"] = self.outsider
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4403)

    async def test_student_cannot_open_socket_after_session_finishes(self):
        session = await database_sync_to_async(self.start)()
        await database_sync_to_async(type(session).objects.filter(pk=session.pk).update)(status="closed")
        communicator = WebsocketCommunicator(application, f"/ws/classbook/{session.id}/")
        communicator.scope["user"] = self.student

        connected, code = await communicator.connect()

        self.assertFalse(connected)
        self.assertEqual(code, 4403)


class ReconnectContractTests(SimpleTestCase):
    def setUp(self):
        self.js = (Path(settings.BASE_DIR) / "static" / "classbook" / "socket.js").read_text(encoding="utf-8")

    def test_reconnect_is_bounded_and_access_revocation_stops_it(self):
        self.assertIn("MAX_RECONNECT_ATTEMPTS", self.js)
        self.assertIn("RECONNECT_MAX_DELAY", self.js)
        self.assertIn("Math.min", self.js)
        self.assertIn("ACCESS_REVOKED_CLOSE_CODE = 4403", self.js)
        self.assertIn("event.code === ACCESS_REVOKED_CLOSE_CODE", self.js)

    def test_mobile_resume_and_network_recovery_wake_the_socket(self):
        self.assertIn("'online'", self.js)
        self.assertIn("visibilitychange", self.js)
