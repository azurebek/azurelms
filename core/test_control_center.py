import json
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.control_center.registry import CAPABILITY_REGISTRY, capability_by_slug
from core.control_center.snapshot import (
    CapabilityResult,
    ControlCenterSnapshot,
    build_control_center_snapshot,
)


class ControlCenterViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_superuser(
            username="control_owner",
            email="owner@example.test",
            password="pass-12345",
        )
        self.staff = User.objects.create_user(
            username="control_staff",
            email="staff@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.student = User.objects.create_user(
            username="control_student",
            email="student@example.test",
            password="pass-12345",
        )

    def test_owner_can_open_control_center(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("backoffice_control"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backoffice/control_center.html")
        self.assertContains(response, "Platforma holati bitta nuqtada")
        self.assertContains(response, "CAPABILITY REGISTRY")
        self.assertEqual(len(response.context["snapshot"].results), len(CAPABILITY_REGISTRY))

    def test_staff_and_student_cannot_open_owner_control_center(self):
        for user in (self.staff, self.student):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                response = self.client.get(reverse("backoffice_control"))
                self.assertEqual(response.status_code, 302)
                self.assertIn("/users/login/", response["Location"])

    def test_control_center_navigation_is_visible_only_to_owner(self):
        self.client.force_login(self.owner)
        owner_response = self.client.get(reverse("backoffice_control"))
        self.assertContains(owner_response, "Control Center")

        self.client.force_login(self.staff)
        staff_response = self.client.get(reverse("backoffice_dashboard"))
        self.assertNotContains(staff_response, reverse("backoffice_control"))


class ControlCenterSnapshotTests(TestCase):
    def test_registry_slugs_are_unique_and_all_have_probes(self):
        from core.control_center.snapshot import PROBE_FUNCTIONS

        slugs = [capability.slug for capability in CAPABILITY_REGISTRY]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(set(slugs), set(PROBE_FUNCTIONS))

    def test_one_broken_probe_is_contained(self):
        def broken_probe(_definition):
            raise RuntimeError("secret infrastructure detail")

        snapshot = build_control_center_snapshot(probe_functions={"database": broken_probe})
        database = next(item for item in snapshot.results if item.definition.slug == "database")

        self.assertEqual(database.status, "red")
        self.assertEqual(database.summary, "Probe xavfsiz tarzda xatoga tushdi.")
        self.assertEqual(dict(database.details)["error_type"], "RuntimeError")
        self.assertNotIn("secret infrastructure detail", snapshot.as_dict().__str__())
        self.assertEqual(len(snapshot.results), len(CAPABILITY_REGISTRY))


class AIControlCenterSupplyTests(TestCase):
    @staticmethod
    def _supply(**overrides):
        snapshot = {
            "status": "green",
            "available": True,
            "enforcement": True,
            "bucket_date": "2026-08-14",
            "requests_used": 10,
            "requests_limit": 100,
            "requests_remaining": 90,
            "minute_requests_used": 2,
            "minute_requests_limit": 10,
            "minute_requests_remaining": 8,
            "tokens_used": 1_000,
            "tokens_limit": 250_000,
            "tokens_remaining": 249_000,
            "actual_attempts": 8,
            "reserved": 0,
            "failed": 1,
            "rejected": 0,
            "circuit_open": False,
            "circuit_open_until": "",
        }
        snapshot.update(overrides)
        return snapshot

    @override_settings(
        AI_CHAT_PROVIDER="gemini",
        GEMINI_API_KEY="test-key",
        AI_FREE_TIER_MODE=True,
        AI_ALLOW_DIGITALOCEAN=False,
        IS_LOCAL=True,
    )
    @patch("aicontrol.supply.supply_snapshot")
    def test_ai_supply_green_baseline_exposes_safe_budget_details(self, supply_snapshot):
        from core.control_center.snapshot import _ai_probe

        supply_snapshot.return_value = self._supply()
        result = _ai_probe(capability_by_slug("ai_provider"))
        details = dict(result.details)

        self.assertEqual(result.status, "green")
        self.assertEqual(details["requests_used"], "10")
        self.assertEqual(details["requests_limit"], "100")
        self.assertEqual(details["requests_remaining"], "90")
        self.assertEqual(details["minute_requests_remaining"], "8")
        self.assertEqual(details["tokens_remaining"], "249000")
        self.assertEqual(details["actual_attempts"], "8")
        self.assertEqual(details["free_tier_mode"], "on")
        self.assertEqual(details["api_grounding"], "disabled")
        self.assertEqual(details["supply_enforcement"], "on")
        self.assertEqual(details["circuit"], "closed")

    @override_settings(
        AI_CHAT_PROVIDER="gemini",
        GEMINI_API_KEY="test-key",
        AI_FREE_TIER_MODE=True,
        AI_ALLOW_DIGITALOCEAN=False,
        IS_LOCAL=True,
    )
    @patch("aicontrol.supply.supply_snapshot")
    def test_ai_supply_at_eighty_percent_is_amber(self, supply_snapshot):
        from core.control_center.snapshot import _ai_probe

        supply_snapshot.return_value = self._supply(
            status="amber",
            requests_used=80,
            requests_remaining=20,
        )

        result = _ai_probe(capability_by_slug("ai_provider"))

        self.assertEqual(result.status, "amber")
        self.assertIn("80%", result.summary)

    @override_settings(
        AI_CHAT_PROVIDER="gemini",
        GEMINI_API_KEY="test-key",
        AI_FREE_TIER_MODE=True,
        AI_ALLOW_DIGITALOCEAN=False,
        IS_LOCAL=True,
    )
    @patch("aicontrol.supply.supply_snapshot")
    def test_ai_supply_open_circuit_is_red_without_raw_reason(self, supply_snapshot):
        from core.control_center.snapshot import _ai_probe

        supply_snapshot.return_value = self._supply(
            status="red",
            circuit_open=True,
            circuit_open_until="2026-08-14T18:00:00+03:00",
            circuit_reason="secret-key raw provider failure",
        )

        result = _ai_probe(capability_by_slug("ai_provider"))
        rendered = str(result.as_dict())

        self.assertEqual(result.status, "red")
        self.assertEqual(dict(result.details)["circuit"], "open")
        self.assertIn("cooldown", result.summary.lower())
        self.assertNotIn("secret-key", rendered)
        self.assertNotIn("raw provider failure", rendered)

    @override_settings(
        AI_CHAT_PROVIDER="digitalocean",
        DIGITALOCEAN_INFERENCE_API_KEY="test-do-key",
        AI_FREE_TIER_MODE=True,
        AI_ALLOW_DIGITALOCEAN=False,
        IS_LOCAL=True,
    )
    @patch("aicontrol.supply.supply_snapshot")
    def test_digitalocean_owner_hold_is_red_even_with_credential(self, supply_snapshot):
        from core.control_center.snapshot import _ai_probe

        supply_snapshot.return_value = self._supply()
        result = _ai_probe(capability_by_slug("ai_provider"))

        self.assertEqual(result.status, "red")
        self.assertIn("HOLD", result.summary)
        self.assertEqual(dict(result.details)["digitalocean_admission"], "hold")

    @override_settings(
        AI_CHAT_PROVIDER="gemini",
        GEMINI_API_KEY="test-key",
        AI_FREE_TIER_MODE=True,
        IS_LOCAL=True,
    )
    @patch("aicontrol.supply.supply_snapshot")
    def test_unavailable_supply_snapshot_is_red_without_raw_error(self, supply_snapshot):
        from core.control_center.snapshot import _ai_probe

        supply_snapshot.return_value = {
            "status": "red",
            "available": False,
            "enforcement": True,
            "error": "database password=do-not-render",
        }

        result = _ai_probe(capability_by_slug("ai_provider"))
        rendered = str(result.as_dict())

        self.assertEqual(result.status, "red")
        self.assertIn("snapshot mavjud emas", result.summary)
        self.assertNotIn("do-not-render", rendered)


class SystemAuditCommandTests(TestCase):
    def _snapshot(self, status="green"):
        definition = capability_by_slug("database")
        result = CapabilityResult(definition, status, f"{status} test result")
        return ControlCenterSnapshot(
            generated_at=timezone.now(),
            environment="test",
            release_sha="abc123",
            overall_status=status,
            results=(result,),
            effective_config=(("Environment", "test"),),
        )

    @patch("aicontrol.management.commands.system_audit.build_control_center_snapshot")
    def test_text_output_uses_shared_snapshot(self, build_snapshot):
        build_snapshot.return_value = self._snapshot("green")
        stdout = StringIO()

        call_command("system_audit", "--fail-on", "never", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("AzureLMS system audit: GREEN", output)
        self.assertIn("Ma'lumotlar bazasi", output)

    @patch("aicontrol.management.commands.system_audit.build_control_center_snapshot")
    def test_json_output_is_machine_readable(self, build_snapshot):
        build_snapshot.return_value = self._snapshot("amber")
        stdout = StringIO()

        call_command("system_audit", "--json", "--fail-on", "never", stdout=stdout)

        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["overall_status"], "amber")
        self.assertEqual(payload["capabilities"][0]["slug"], "database")

    @patch("aicontrol.management.commands.system_audit.build_control_center_snapshot")
    def test_threshold_returns_non_zero(self, build_snapshot):
        build_snapshot.return_value = self._snapshot("red")

        with self.assertRaises(CommandError):
            call_command("system_audit", "--fail-on", "red", stdout=StringIO())
