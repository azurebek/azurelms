"""A1a — liveness va readiness endpointlari.

Kontrakt ataylab ikkiga bo'lingan:

* `/healthz` hech qanday tashqi bog'liqlikka tegmaydi — baza yiqilganda ham
  `200` qaytaradi, chunki processni o'ldirish vaziyatni yaxshilamaydi;
* `/readyz` **critical** capability'larni tekshiradi va birortasi `red` bo'lsa
  `503` beradi, ya'ni orkestrator bu instance'ga trafik yubormaydi.

Tekshiruv mantig'i Control Center registry/probe'laridan olinadi, shuning uchun
web sahifa, `system_audit` CLI va bu endpoint bir xil haqiqatni ko'radi.
"""

from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.control_center.registry import CAPABILITY_REGISTRY
from core.control_center.snapshot import CapabilityResult


def _red(definition):
    return CapabilityResult(definition=definition, status="red", summary="sun'iy nosozlik")


class LivenessTests(SimpleTestCase):
    def test_healthz_is_open_and_returns_alive(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "alive")

    def test_healthz_does_not_touch_the_database(self):
        """Baza yiqilsa ham liveness `200` qolishi kerak."""
        with patch("django.db.backends.utils.CursorWrapper.execute") as execute:
            response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        execute.assert_not_called()

    def test_healthz_is_not_cached(self):
        response = self.client.get(reverse("healthz"))
        self.assertIn("no-cache", response["Cache-Control"])


class ReadinessTests(TestCase):
    def test_readyz_reports_ready_on_a_healthy_local_profile(self):
        response = self.client.get(reverse("readyz"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ready")
        self.assertTrue(payload["checks"])

    def test_readyz_only_runs_critical_capabilities(self):
        """Readiness har necha soniyada so'raladi — hamma probe emas."""
        expected = {
            definition.slug
            for definition in CAPABILITY_REGISTRY
            if definition.criticality == "critical"
        }
        slugs = {check["slug"] for check in self.client.get(reverse("readyz")).json()["checks"]}
        self.assertEqual(slugs, expected)

    def test_readyz_returns_503_when_a_critical_capability_is_red(self):
        with patch.dict(
            "core.control_center.snapshot.PROBE_FUNCTIONS", {"database": _red}, clear=False
        ):
            response = self.client.get(reverse("readyz"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "not-ready")

    def test_a_broken_probe_is_treated_as_not_ready_instead_of_crashing(self):
        def explode(definition):
            raise RuntimeError("probe yiqildi")

        with patch.dict(
            "core.control_center.snapshot.PROBE_FUNCTIONS", {"database": explode}, clear=False
        ):
            response = self.client.get(reverse("readyz"))
        self.assertEqual(response.status_code, 503)
        self.assertIn("database", [c["slug"] for c in response.json()["checks"]])

    def test_readyz_is_reachable_without_authentication(self):
        self.assertEqual(self.client.get(reverse("readyz")).status_code, 200)


class HealthEndpointConfigTests(SimpleTestCase):
    def test_probes_are_exempt_from_the_https_redirect(self):
        """Cluster ichidagi probe http bilan keladi; `301` uni ko'r qilardi.

        Sozlama strict profilga bog'liq emas — u doim ta'riflanadi, shuning
        uchun bu qo'riqchi har yugurishda ishlaydi.
        """
        from django.conf import settings

        exempt = getattr(settings, "SECURE_REDIRECT_EXEMPT", [])
        self.assertIn(r"^healthz$", exempt)
        self.assertIn(r"^readyz$", exempt)
