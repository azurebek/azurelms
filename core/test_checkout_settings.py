"""Checkout TTL uses the existing owner-only audited settings surface."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from aicontrol.models import SystemAuditEvent
from core.models import OperationalSettings
from core.operational_settings import current_thresholds
from core.runtime_settings_forms import CheckoutSettingsForm


class CheckoutSettingsTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_superuser('checkout-owner', 'owner@example.test', 'testpass')
        self.url = reverse('backoffice_runtime_settings')
        self.client.force_login(self.owner)

    def data(self, **extra):
        return dict(form_name='checkout', checkout_quote_minutes=60, change_reason='Sinov: uzoqroq tasdiq', confirm_change='on', **extra)

    def test_owner_form_and_audit_then_noop(self):
        self.assertContains(self.client.get(self.url), 'id_checkout_checkout_quote_minutes')
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 302)
        row = OperationalSettings.load()
        self.assertEqual(row.checkout_quote_minutes, 60)
        self.assertEqual(row.updated_by, self.owner)
        events = SystemAuditEvent.objects.filter(action='settings.checkout.update')
        self.assertEqual(events.count(), 1)
        self.assertTrue(events.get().reason)
        stamp = row.updated_at
        self.client.post(self.url, self.data())
        self.assertEqual(events.count(), 1)
        self.assertEqual(OperationalSettings.load().updated_at, stamp)

    def test_reason_and_confirmation_required(self):
        for field in ['change_reason', 'confirm_change']:
            data = self.data()
            data[field] = ''
            response = self.client.post(self.url, data)
            self.assertEqual(response.status_code, 200)
            self.assertIn(field, response.context['checkout_form'].errors)
        self.assertEqual(OperationalSettings.load().checkout_quote_minutes, 30)
        self.assertFalse(SystemAuditEvent.objects.filter(action='settings.checkout.update').exists())

    def test_staff_cannot_change_operational_checkout_value(self):
        teacher = get_user_model().objects.create_user('checkout-teacher', is_staff=True)
        self.client.force_login(teacher)
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 302)
        self.assertEqual(current_thresholds().checkout_quote_minutes, 30)

    def test_bounds_and_effective_fallback(self):
        self.assertEqual(current_thresholds().checkout_quote_minutes, 30)
        for value in [0, 1441]:
            data = self.data()
            data['checkout_quote_minutes'] = value
            form = CheckoutSettingsForm(data, instance=OperationalSettings.load())
            self.assertFalse(form.is_valid())
            self.assertIn('checkout_quote_minutes', form.errors)
        OperationalSettings.objects.filter(pk=1).update(checkout_quote_minutes=0)
        self.assertEqual(current_thresholds().checkout_quote_minutes, 1)

    def test_only_changed_fields_written_on_shared_singleton(self):
        stale = OperationalSettings.load()
        OperationalSettings.objects.filter(pk=1).update(queue_age_red_minutes=120)
        with patch.object(OperationalSettings, 'load', return_value=stale):
            self.assertEqual(self.client.post(self.url, self.data()).status_code, 302)
        self.assertEqual(OperationalSettings.load().queue_age_red_minutes, 120)
        self.assertEqual(OperationalSettings.load().checkout_quote_minutes, 60)
