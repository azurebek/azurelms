"""T4 — `telegram_dispatcher` chirog'i.

Outbox chirog'i navbatni ko'rsatadi, bu esa **kiruvchi** yo'lni: bot tirikmi
va update'larga qancha vaqtda javob beryapti. Audit (2026-09-11) aynan shu
bo'shliqni yozgan: «Outbox navbati ko'rinadi, handler yo'li ko'rinmaydi.»

Bu faylning vazifasi uchta soxta-yashil va bitta soxta-qizilni qulflash:

* **soxta-qizil** — tunda trafik yo'q, bot esa sog'lom;
* **soxta-yashil** — bot ataylab to'xtatilgan, lekin to'xtatish yozuvining
  o'zi yangi, ya'ni yosh bo'yicha u tirik ko'rinardi;
* **soxta-yashil** — jarayon o'lgan, ammo oxirgi update yozuvi yangi;
* **soxta-qizil** — owner yozuv oralig'ini oshirgan va chiroq abadiy sariq
  bo'lib qolgan.
"""

import datetime

from django.test import TestCase, override_settings
from django.utils import timezone

from aicontrol.models import WorkerHeartbeat
from bot.metrics import MIN_ERROR_SAMPLES, WORKER_NAME
from core.control_center.registry import capability_by_slug
from core.control_center.snapshot import _dispatcher_probe

DEFINITION = capability_by_slug("telegram_dispatcher")


def write_beat(*, age_seconds=0, **detail):
    """Heartbeat qatorini berilgan yosh va `detail` bilan yozadi."""
    detail.setdefault("flush_seconds", 30)
    detail.setdefault("window_seconds", 300)
    detail.setdefault("samples", 0)
    detail.setdefault("errors", 0)
    detail.setdefault("unhandled", 0)
    detail.setdefault("updates_total", 0)
    detail.setdefault("errors_total", 0)
    beat = WorkerHeartbeat.record(WORKER_NAME, detail=detail)
    if age_seconds:
        WorkerHeartbeat.objects.filter(pk=beat.pk).update(
            last_seen_at=timezone.now() - datetime.timedelta(seconds=age_seconds)
        )
    return beat


class RegistrationTests(TestCase):
    def test_the_capability_exists_and_is_not_readiness_critical(self):
        """Bot ishlamayotgani web instance'ni trafikdan chiqarmasligi kerak.

        `/readyz` faqat `critical` probe'larni yugurtiradi. Bu chiroqni
        critical qilish butun saytni `503` qilardi — nosozlikni tuzatmay,
        ko'paytirardi.
        """
        self.assertEqual(DEFINITION.criticality, "high")

    def test_it_has_its_own_probe(self):
        from core.control_center.snapshot import PROBE_FUNCTIONS

        self.assertIn("telegram_dispatcher", PROBE_FUNCTIONS)

    def test_it_is_not_double_counted_in_the_workers_light(self):
        """Bitta uzilish ikkita qizil chiroq bermasligi kerak."""
        from core.control_center.snapshot import EXPECTED_WORKERS

        self.assertNotIn(WORKER_NAME, EXPECTED_WORKERS)


class NeverStartedTests(TestCase):
    def test_locally_a_missing_bot_is_amber_not_red(self):
        """Lokalda bot odatda ishlamaydi — bu sozlanmagan holat."""
        with override_settings(IS_LOCAL=True):
            result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "amber")

    def test_in_production_a_missing_bot_is_red(self):
        with override_settings(IS_LOCAL=False):
            result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "red")

    def test_it_never_reports_green_without_a_heartbeat(self):
        for is_local in (True, False):
            with self.subTest(is_local=is_local), override_settings(IS_LOCAL=is_local):
                self.assertNotEqual(_dispatcher_probe(DEFINITION).status, "green")


class LivenessTests(TestCase):
    def test_a_quiet_but_alive_bot_is_green(self):
        """Eng muhim soxta-qizil: tunda trafik yo'q, bot sog'lom."""
        write_beat(samples=0, last_update_at=None)

        result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "green")
        self.assertIn("update bo'lmagan", result.summary)

    def test_traffic_is_not_used_as_a_liveness_signal(self):
        """`last_update_at` yangi bo'lsa ham o'lik jarayon yashil bo'lmaydi.

        Teskarisi ham shu testning mazmuni: tiriklik faqat `last_seen_at` dan
        o'qiladi, ya'ni oxirgi update vaqtiga suyanish taqiqlangan.
        """
        write_beat(age_seconds=4000, last_update_at=timezone.localtime().isoformat())

        result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "red")

    def test_a_late_heartbeat_is_amber_before_it_is_red(self):
        write_beat(age_seconds=200)

        result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "amber")

    def test_a_dead_heartbeat_is_red(self):
        write_beat(age_seconds=1200)

        result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "red")

    def test_a_planned_stop_is_not_green_even_though_the_write_is_fresh(self):
        """To'xtatish yozuvining `last_seen_at` i yangi — bayroq yoshdan kuchli."""
        write_beat(age_seconds=0, stopped_at=timezone.localtime().isoformat())

        with override_settings(IS_LOCAL=False):
            result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "red")
        self.assertIn("to'xtatilgan", result.summary)

    def test_a_planned_stop_says_it_was_planned(self):
        """Owner mavjud bo'lmagan nosozlikni qidirmasligi kerak."""
        write_beat(stopped_at=timezone.localtime().isoformat())

        result = _dispatcher_probe(DEFINITION)

        self.assertIn("halokat emas", result.summary)


class StaleThresholdFloorTests(TestCase):
    """Sozlama o'zini nosozlikka aylantirmasligi kerak."""

    def test_a_long_write_interval_raises_the_stale_threshold_automatically(self):
        from core.models import OperationalSettings

        row = OperationalSettings.load()
        row.dispatcher_stale_after_seconds = 30
        row.dispatcher_dead_after_seconds = 60
        row.save()
        # Jarayon har 120 soniyada yozadi, ya'ni 70 soniyalik yosh normal.
        write_beat(age_seconds=70, flush_seconds=120)

        result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "green")
        self.assertEqual(dict(result.details)["stale_after_seconds"], "240")

    def test_the_owner_threshold_still_applies_when_it_is_the_larger_one(self):
        from core.models import OperationalSettings

        row = OperationalSettings.load()
        row.dispatcher_stale_after_seconds = 600
        row.dispatcher_dead_after_seconds = 3600
        row.save()
        write_beat(age_seconds=300, flush_seconds=30)

        result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "green", "owner chegarasi kengaytirilgan")

    def test_the_dead_threshold_never_falls_below_the_stale_one(self):
        from core.models import OperationalSettings

        row = OperationalSettings.load()
        row.dispatcher_stale_after_seconds = 30
        row.dispatcher_dead_after_seconds = 60
        row.save()
        write_beat(age_seconds=1, flush_seconds=600)

        details = dict(_dispatcher_probe(DEFINITION).details)

        self.assertGreater(
            int(details["dead_after_seconds"]), int(details["stale_after_seconds"])
        )


class LatencyTests(TestCase):
    def test_a_fast_bot_is_green(self):
        write_beat(samples=50, avg_ms=80.0, p95_ms=140.0, max_ms=400.0)

        result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "green")
        self.assertIn("p95 140.0 ms", result.summary)

    def test_a_slow_bot_is_amber(self):
        write_beat(samples=50, avg_ms=900.0, p95_ms=2000.0, max_ms=2500.0)

        result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "amber")

    def test_a_very_slow_bot_is_red(self):
        write_beat(samples=50, avg_ms=3000.0, p95_ms=9000.0, max_ms=12000.0)

        result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "red")

    def test_without_samples_latency_cannot_colour_the_light(self):
        """Namuna yo'q bo'lsa javob «bilmayman», «tez» emas."""
        write_beat(samples=0)

        details = dict(_dispatcher_probe(DEFINITION).details)

        self.assertEqual(details["p95_ms"], "namuna yo'q")
        self.assertEqual(details["avg_ms"], "namuna yo'q")

    def test_the_owner_can_move_the_latency_threshold_without_a_deploy(self):
        from core.models import OperationalSettings

        write_beat(samples=50, p95_ms=2000.0)
        self.assertEqual(_dispatcher_probe(DEFINITION).status, "amber")

        row = OperationalSettings.load()
        row.handler_latency_amber_ms = 2500
        row.handler_latency_red_ms = 6000
        row.save()

        self.assertEqual(_dispatcher_probe(DEFINITION).status, "green")


class ErrorRateTests(TestCase):
    def test_one_error_out_of_one_update_does_not_turn_the_light_red(self):
        """Aks holda bot ishga tushgan zahoti qizil chiroq berardi."""
        write_beat(samples=1, errors=1, p95_ms=10.0, avg_ms=10.0, max_ms=10.0)

        result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "green")

    def test_a_high_error_share_over_enough_samples_is_red(self):
        samples = MIN_ERROR_SAMPLES * 2
        write_beat(
            samples=samples,
            errors=samples // 2,
            p95_ms=10.0,
            avg_ms=10.0,
            max_ms=10.0,
        )

        result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "red")
        self.assertIn("xato", result.summary.lower())

    def test_a_small_error_share_is_amber(self):
        samples = 100
        write_beat(samples=samples, errors=8, p95_ms=10.0, avg_ms=10.0, max_ms=10.0)

        result = _dispatcher_probe(DEFINITION)

        self.assertEqual(result.status, "amber")

    def test_the_error_percent_is_reported_even_below_the_sample_floor(self):
        """Rang bermaydi, lekin raqam owner uchun ko'rinadi."""
        write_beat(samples=2, errors=1, p95_ms=10.0, avg_ms=10.0, max_ms=10.0)

        details = dict(_dispatcher_probe(DEFINITION).details)

        self.assertEqual(details["error_percent"], "50.0")


class SnapshotIntegrationTests(TestCase):
    def test_the_light_appears_in_the_control_center_snapshot(self):
        from core.control_center import build_control_center_snapshot

        write_beat(samples=10, avg_ms=50.0, p95_ms=90.0, max_ms=120.0)

        snapshot = build_control_center_snapshot()
        result = next(
            (item for item in snapshot.results if item.definition.slug == "telegram_dispatcher"),
            None,
        )

        self.assertIsNotNone(result, "chiroq snapshotda yo'q")
        self.assertEqual(result.status, "green")

    def test_a_broken_detail_payload_does_not_take_the_page_down(self):
        """`detail` JSON'i kutilmagan shaklda bo'lsa ham sahifa ochilishi kerak.

        Eski jarayon yozgan yozuv yangi probe bilan uchrashishi mumkin.
        """
        WorkerHeartbeat.record(WORKER_NAME, detail={"samples": "ko'p"})

        result = _dispatcher_probe(DEFINITION)

        self.assertIn(result.status, {"green", "amber", "red"})
