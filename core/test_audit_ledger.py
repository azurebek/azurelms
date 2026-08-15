"""A2 — append-only audit ledgeri.

Nega Django'ning `LogEntry` si yetarli emas edi: u admin uchun mo'ljallangan,
o'chirilishi va tahrirlanishi mumkin, `source`/`outcome`/`before-after` kabi
operatsion maydonlari yo'q. `05-launch-ops.md` §3 esa aniq talab qo'ygan:
kim, qayerdan, nima qildi, qanday sabab bilan, natija nima va qaysi release'da.

Eng muhim da'vo — **append-only**: yozuvni o'zgartirib yoki o'chirib bo'lmaydi,
va bu model darajasida majburlanadi. Admin ruxsatlari faqat oxirgi to'siq;
ular kod orqali chetlab o'tilsa ham model rad etishi kerak.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from aicontrol.models import AISettings, SystemAuditEvent
from core.audit import audit_trail_for, record_audit_event, redact

User = get_user_model()


class AppendOnlyTests(TestCase):
    def setUp(self):
        self.event = SystemAuditEvent.objects.create(action="test.create")

    def test_an_existing_event_cannot_be_edited(self):
        self.event.reason = "keyin o'zgartirdim"
        with self.assertRaises(ValidationError):
            self.event.save()

    def test_an_event_cannot_be_deleted(self):
        with self.assertRaises(ValidationError):
            self.event.delete()

    def test_new_events_are_still_allowed(self):
        SystemAuditEvent.objects.create(action="test.second")
        self.assertEqual(SystemAuditEvent.objects.count(), 2)

    def test_admin_exposes_the_ledger_read_only(self):
        from django.contrib.admin.sites import AdminSite

        from aicontrol.admin import SystemAuditEventAdmin

        model_admin = SystemAuditEventAdmin(SystemAuditEvent, AdminSite())
        request = type("R", (), {"user": None, "GET": {}, "method": "GET"})()
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))


class RedactionTests(TestCase):
    def test_secret_keys_are_masked(self):
        cleaned = redact({"password": "maxfiy", "token": "abc", "username": "admin"})
        self.assertEqual(cleaned["password"], "***")
        self.assertEqual(cleaned["token"], "***")
        self.assertEqual(cleaned["username"], "admin")

    def test_nested_dictionaries_are_masked_too(self):
        cleaned = redact({"payload": {"api_key": "abc", "model": "gemini"}})
        self.assertEqual(cleaned["payload"]["api_key"], "***")
        self.assertEqual(cleaned["payload"]["model"], "gemini")

    def test_long_values_are_truncated(self):
        cleaned = redact({"note": "x" * 500})
        self.assertLessEqual(len(cleaned["note"]), 301)


class RecordAuditEventTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser(
            username="audit_owner", email="audit@t.uz", password="pass-12345")
        AISettings.objects.all().delete()
        self.policy = AISettings.load()

    def test_actor_name_survives_the_user_being_deleted(self):
        """Audit yozuvi foydalanuvchi hayotidan uzoqroq yashashi kerak."""
        record_audit_event(action="test.actor", actor=self.owner, target=self.policy)
        self.owner.delete()

        event = SystemAuditEvent.objects.get(action="test.actor")
        self.assertIsNone(event.actor)
        self.assertEqual(event.actor_label, "audit_owner")

    def test_target_is_captured_from_the_object(self):
        record_audit_event(action="test.target", target=self.policy)
        event = SystemAuditEvent.objects.get(action="test.target")
        self.assertEqual(event.target_type, "AISettings")
        self.assertEqual(event.target_id, str(self.policy.pk))

    def test_before_and_after_are_redacted(self):
        record_audit_event(
            action="test.redact", target=self.policy,
            before={"secret": "eski"}, after={"secret": "yangi"},
        )
        event = SystemAuditEvent.objects.get(action="test.redact")
        self.assertEqual(event.before["secret"], "***")
        self.assertEqual(event.after["secret"], "***")

    def test_trail_returns_only_this_object_newest_first(self):
        other = User.objects.create_user(username="audit_other", email="o@t.uz")
        record_audit_event(action="test.one", target=self.policy)
        record_audit_event(action="test.two", target=self.policy)
        record_audit_event(action="test.other", target=other)

        actions = [event.action for event in audit_trail_for(self.policy)]
        self.assertEqual(actions, ["test.two", "test.one"])

    def test_display_message_includes_reason_and_outcome(self):
        record_audit_event(
            action="test.display", target=self.policy, target_label="AI",
            reason="sinov", outcome=SystemAuditEvent.OUTCOME_DENIED,
        )
        message = SystemAuditEvent.objects.get(action="test.display").display_message
        self.assertIn("test.display", message)
        self.assertIn("sinov", message)
        self.assertIn("Rad etildi", message)


class OwnerSurfacesWriteToTheLedgerTests(TestCase):
    """Uchala owner mutation yuzasi endi `LogEntry` emas, ledgerga yozadi."""

    def setUp(self):
        AISettings.objects.all().delete()
        AISettings.load()
        self.owner = User.objects.create_superuser(
            username="ledger_owner", email="ledger@t.uz", password="pass-12345")
        self.client.force_login(self.owner)

    def test_kill_switch_writes_an_audit_event_with_before_and_after(self):
        self.client.post(reverse("backoffice_ai_kill_switch"), {
            "change_reason": "kvota tekshiruvi",
            "confirm_change": "on",
        })
        event = SystemAuditEvent.objects.get(action="ai.kill_switch.disable")
        self.assertEqual(event.actor_label, "ledger_owner")
        self.assertEqual(event.reason, "kvota tekshiruvi")
        self.assertEqual(event.before["ai_remote_calls_enabled"], True)
        self.assertEqual(event.after["ai_remote_calls_enabled"], False)
        self.assertEqual(event.source, SystemAuditEvent.SOURCE_WEB)

    def test_the_request_ip_is_recorded(self):
        self.client.post(
            reverse("backoffice_ai_kill_switch"),
            {"change_reason": "ip sinovi", "confirm_change": "on"},
            REMOTE_ADDR="10.1.2.3",
        )
        event = SystemAuditEvent.objects.get(action="ai.kill_switch.disable")
        self.assertEqual(event.ip_address, "10.1.2.3")

    def test_the_page_shows_its_own_trail(self):
        self.client.post(reverse("backoffice_ai_kill_switch"), {
            "change_reason": "tarixda korinadigan sabab",
            "confirm_change": "on",
        })
        response = self.client.get(reverse("backoffice_ai_kill_switch"))
        # Apostrofsiz matn: shablon HTML-escape qiladi va xom qidiruv topmasdi.
        self.assertContains(response, "tarixda korinadigan sabab")
        self.assertContains(response, "ai.kill_switch.disable")

    def test_a_failed_mutation_leaves_no_audit_event(self):
        """Sababsiz yuborilgan forma ham amalni, ham yozuvni qoldirmasligi kerak."""
        self.client.post(reverse("backoffice_ai_kill_switch"), {"confirm_change": "on"})
        self.assertEqual(SystemAuditEvent.objects.count(), 0)
        self.assertTrue(AISettings.load().ai_remote_calls_enabled)
