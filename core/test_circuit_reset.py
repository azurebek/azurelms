"""A2 — owner circuit breaker cooldown'ini qo'lda tozalay olishi kerak.

A8 circuit breaker ketma-ket provider xatolaridan keyin ochiladi va bir soat
yopiq turadi. Bu to'g'ri himoya, ammo **sabab bartaraf etilganda ham** owner
kuta turishdan boshqa yo'lga ega emas edi: Django admin holatni faqat
ko'rsatadi, o'chirmaydi — admin esa default o'chiq (`ENABLE_LEGACY_ADMIN=False`).

2026-08-19 da aynan shu holat yuz berdi: o'lik model va juda qisqa deadline
circuit'ni ochdi; ikkala sabab ham tuzatildi, AI esa hali ham "mavjud emas"
deb turdi. Demo yoki dars paytida bu qabul qilib bo'lmaydigan holat.

Kill switch bilan bir xil mutation qoidalari: majburiy sabab, majburiy
tasdiqlash, audit yozuvi va o'zgarish bo'lmasa hech narsa yozmaydigan no-op.
"""

import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import AISupplyState, SystemAuditEvent

User = get_user_model()


class CircuitResetAccessTests(TestCase):
    def setUp(self):
        self.url = reverse("backoffice_ai_circuit_reset")
        self.student = User.objects.create_user(
            username="cb-student", email="cb-student@example.com", password="x")

    def test_a_student_cannot_reach_the_page(self):
        self.client.force_login(self.student)
        self.assertNotEqual(self.client.get(self.url).status_code, 200)

    def test_an_anonymous_visitor_cannot_reach_the_page(self):
        self.assertNotEqual(self.client.get(self.url).status_code, 200)


class CircuitResetTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="cb-owner", email="cb-owner@example.com", password="x")
        self.client.force_login(self.owner)
        self.url = reverse("backoffice_ai_circuit_reset")
        self.state = AISupplyState.load()
        self.state.circuit_open_until = timezone.now() + datetime.timedelta(minutes=45)
        self.state.save(update_fields=["circuit_open_until"])

    def _post(self, **overrides):
        payload = {"change_reason": "model tuzatildi", "confirm_change": "on"}
        payload.update(overrides)
        return self.client.post(self.url, payload)

    def test_the_owner_clears_an_open_circuit(self):
        self._post()

        self.assertIsNone(AISupplyState.load().circuit_open_until)

    def test_clearing_is_written_to_the_audit_ledger(self):
        self._post(change_reason="deadline sozlamasi tuzatildi")

        event = SystemAuditEvent.objects.get(action="ai.circuit.reset")
        self.assertEqual(event.actor_label, "cb-owner")
        self.assertEqual(event.reason, "deadline sozlamasi tuzatildi")
        self.assertIsNone(event.after["circuit_open_until"])

    def test_a_reason_is_required(self):
        self._post(change_reason="")

        self.assertIsNotNone(AISupplyState.load().circuit_open_until)
        self.assertEqual(SystemAuditEvent.objects.count(), 0)

    def test_confirmation_is_required(self):
        self.client.post(self.url, {"change_reason": "sababsiz tasdiq yo'q"})

        self.assertIsNotNone(AISupplyState.load().circuit_open_until)
        self.assertEqual(SystemAuditEvent.objects.count(), 0)

    def test_clearing_an_already_closed_circuit_writes_nothing(self):
        """No-op yo'l: yopiq circuit'ni yana tozalash ledgerni ifloslantirmaydi."""
        self.state.circuit_open_until = None
        self.state.save(update_fields=["circuit_open_until"])

        self._post()

        self.assertEqual(SystemAuditEvent.objects.count(), 0)

    def test_the_page_shows_whether_the_circuit_is_open(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ochiq")

    def test_the_page_is_reachable_from_the_control_center(self):
        """Shoshilinch paytda sahifa mavjud bo'lishining o'zi yetarli emas."""
        response = self.client.get(reverse("backoffice_control"))

        self.assertContains(response, self.url)
