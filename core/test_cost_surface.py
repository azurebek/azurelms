"""Owner uchun AI xarajat sahifasi (A2).

Sahifaning eng muhim vazifasi raqam ko'rsatish emas, **chalg'itmaslik**:
narxlanmagan sarf "0 so'm" bo'lib ko'rinmasligi kerak. Free-tier'da aynan shu
holat: pul sarflanmaydi, ammo kvota yeyiladi va u ham cheklov.
"""

import datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import AIModelPrice, AISupplyEvent, SystemAuditEvent
from users.models import CustomUser as User


def _event(model="gemini-3.1-flash-lite", prompt=1000, completion=500):
    return AISupplyEvent.objects.create(
        request_key=f"c-{timezone.now().timestamp()}-{prompt}",
        bucket_date=timezone.localdate(),
        call_type=AISupplyEvent.CALL_CHAT,
        provider="gemini",
        model_name=model,
        status=AISupplyEvent.STATUS_SUCCEEDED,
        reserved_requests=1,
        reserved_tokens=4000,
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
        accounted_requests=1,
        accounted_tokens=prompt + completion,
    )


class CostSurfaceAccessTests(TestCase):
    def setUp(self):
        self.url = reverse("backoffice_ai_cost")

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response.url)

    def test_student_cannot_open_it(self):
        User.objects.create_user(username="oquvchi", email="o@example.com", password="testpass123")
        self.client.login(username="oquvchi", password="testpass123")
        self.assertIn(self.client.get(self.url).status_code, (302, 403))

    def test_staff_without_superuser_cannot_open_it(self):
        User.objects.create_user(
            username="xodim", email="x@example.com", password="testpass123", is_staff=True
        )
        self.client.login(username="xodim", password="testpass123")
        self.assertIn(self.client.get(self.url).status_code, (302, 403))


class CostSurfaceTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(
            username="owner", email="owner@example.com", password="testpass123"
        )
        self.client.login(username="owner", password="testpass123")
        self.url = reverse("backoffice_ai_cost")

    def test_unpriced_usage_is_shown_as_unpriced_not_as_zero_cost(self):
        """Sahifaning asosiy da'vosi shu."""
        _event(model="narxsiz-model", prompt=3000, completion=1000)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["rollup"]["unpriced_events"], 1)
        self.assertContains(response, "narxlanmagan")

    def test_priced_usage_shows_a_total(self):
        AIModelPrice.objects.create(
            provider="gemini", model_name="gemini-3.1-flash-lite",
            input_per_million=Decimal("1.00"), output_per_million=Decimal("1.00"),
            effective_from=datetime.date(2026, 1, 1),
        )
        _event(prompt=1_000_000, completion=0)

        response = self.client.get(self.url)

        self.assertEqual(response.context["rollup"]["total"], Decimal("1.00"))
        self.assertEqual(response.context["rollup"]["unpriced_events"], 0)

    def test_owner_can_record_a_price_and_it_is_audited(self):
        response = self.client.post(self.url, {
            "provider": "gemini",
            "model_name": "gemini-3.1-flash-lite",
            "input_per_million": "0.10",
            "output_per_million": "0.40",
            "currency": "USD",
            "effective_from": "2026-08-01",
            "note": "aistudio narx sahifasi",
            "change_reason": "birinchi snapshot",
            "confirm_change": "on",
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(AIModelPrice.objects.filter(model_name="gemini-3.1-flash-lite").exists())
        self.assertTrue(SystemAuditEvent.objects.filter(action="ai_price.record").exists())

    def test_reason_is_required(self):
        self.client.post(self.url, {
            "provider": "gemini", "model_name": "m",
            "input_per_million": "0.10", "output_per_million": "0.40",
            "currency": "USD", "effective_from": "2026-08-01",
            "confirm_change": "on",
        })
        self.assertFalse(AIModelPrice.objects.exists())

    def test_confirmation_is_required(self):
        self.client.post(self.url, {
            "provider": "gemini", "model_name": "m",
            "input_per_million": "0.10", "output_per_million": "0.40",
            "currency": "USD", "effective_from": "2026-08-01",
            "change_reason": "tasdiqsiz",
        })
        self.assertFalse(AIModelPrice.objects.exists())

    def test_page_is_reachable_from_the_control_center(self):
        response = self.client.get(reverse("backoffice_control"))
        self.assertContains(response, self.url)
