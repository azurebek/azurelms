from aicontrol.models import SystemAuditEvent
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.landing_forms import LANDING_SECTIONS
from frontend.models import LandingPage


class BackofficeLandingEditorTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_superuser(
            username="landing_owner",
            email="landing-owner@example.test",
            password="pass-12345",
        )
        self.staff = User.objects.create_user(
            username="landing_staff",
            email="landing-staff@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.landing = LandingPage.load()

    def _payload(self, **overrides):
        """To'liq form payload (barcha tahrirlanadigan maydonlar joriy qiymatda)."""
        payload = {}
        for section in LANDING_SECTIONS:
            for name in section["fields"]:
                payload[name] = getattr(self.landing, name)
        payload["change_reason"] = "Hero matni yangilandi"
        payload["confirm_change"] = "on"
        payload.update(overrides)
        return payload

    def test_only_owner_can_open_editor(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("backoffice_landing"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backoffice/landing_editor.html")
        self.assertContains(response, "Bosh sahifa matnlari")

        self.client.force_login(self.staff)
        response = self.client.get(reverse("backoffice_landing"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response["Location"])

    def test_save_requires_confirmation(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("backoffice_landing"),
            self._payload(hero_title_start="Tasdiqsiz sarlavha", confirm_change=""),
        )
        self.assertEqual(response.status_code, 200)
        self.landing.refresh_from_db()
        self.assertNotEqual(self.landing.hero_title_start, "Tasdiqsiz sarlavha")

    def test_save_requires_reason(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("backoffice_landing"),
            self._payload(hero_title_start="Sababsiz", change_reason=""),
        )
        self.assertEqual(response.status_code, 200)
        self.landing.refresh_from_db()
        self.assertNotEqual(self.landing.hero_title_start, "Sababsiz")

    def test_owner_change_is_saved_and_audited(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("backoffice_landing"),
            self._payload(hero_title_start="Yangi hero", cert_sample_name="Test Ism"),
        )
        self.assertRedirects(response, reverse("backoffice_landing"))
        self.landing.refresh_from_db()
        self.assertEqual(self.landing.hero_title_start, "Yangi hero")
        self.assertEqual(self.landing.cert_sample_name, "Test Ism")
        # Audit endi append-only `SystemAuditEvent` ledgerida (A2).
        entry = SystemAuditEvent.objects.get(action="landing.update")
        self.assertEqual(entry.actor_label, self.owner.username)
        self.assertIn("Hero matni yangilandi", entry.reason)

    def test_no_op_save_writes_no_audit(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("backoffice_landing"), self._payload())
        self.assertRedirects(response, reverse("backoffice_landing"))
        self.assertFalse(SystemAuditEvent.objects.exists())

    def test_edited_value_appears_on_landing(self):
        self.client.force_login(self.owner)
        self.client.post(
            reverse("backoffice_landing"),
            self._payload(hero_title_highlight="BENZERSIZ-XYZ"),
        )
        # Landing anonim mehmon uchun render bo'ladi (login qilingan user dashboardga ketadi).
        self.client.logout()
        response = self.client.get("/")
        self.assertContains(response, "BENZERSIZ-XYZ")
