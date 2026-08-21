"""AI xarajat ledgeri (A2).

`AISupplyEvent` so'rov va tokenni hisoblaydi, ammo ular **pulga** aylantirilmasdi.
Reja talabi: "provider/model price snapshot, estimated cost".

Uchta qaror bu testlarda majburlanadi:

1. **Narx qattiq yozilmaydi.** U owner kiritadigan, sanali snapshot. Bugungi
   narxlar kodda ma'lum emas, o'zgaradi va hisobga bog'liq — qattiq yozilgan
   raqam aynan o'lik model va noto'g'ri deadline kabi jim eskirardi.
2. **Narxlanmagan sarf nol deb yozilmaydi.** Reja buni ochiq talab qiladi:
   "«Bepul» cost=0 deb yozilmaydi — quota ham scarcity". Snapshot topilmasa
   chaqiruv `unpriced` deb sanaladi, jamiga `0` qo'shilmaydi.
3. **Pul `Decimal` da.** Float bilan pul hisoblash yaxlitlash xatosini beradi.
"""

import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from aicontrol.models import AIModelPrice, AISupplyEvent, SystemAuditEvent
from core.ai_cost import cost_for_event, cost_rollup, price_for, record_price


def _event(*, model="gemini-3.1-flash-lite", prompt=1000, completion=500, day=None, status=None):
    return AISupplyEvent.objects.create(
        request_key=f"k-{timezone.now().timestamp()}-{prompt}-{completion}",
        bucket_date=day or timezone.localdate(),
        call_type=AISupplyEvent.CALL_CHAT,
        provider="gemini",
        model_name=model,
        status=status or AISupplyEvent.STATUS_SUCCEEDED,
        reserved_requests=1,
        reserved_tokens=4000,
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=prompt + completion,
        accounted_requests=1,
        accounted_tokens=prompt + completion,
    )


class PriceSnapshotTests(TestCase):
    def test_latest_snapshot_on_or_before_the_date_is_used(self):
        AIModelPrice.objects.create(
            provider="gemini", model_name="m", input_per_million=Decimal("1.00"),
            output_per_million=Decimal("2.00"), effective_from=datetime.date(2026, 1, 1),
        )
        AIModelPrice.objects.create(
            provider="gemini", model_name="m", input_per_million=Decimal("3.00"),
            output_per_million=Decimal("4.00"), effective_from=datetime.date(2026, 6, 1),
        )

        older = price_for("m", on=datetime.date(2026, 3, 1), provider="gemini")
        newer = price_for("m", on=datetime.date(2026, 7, 1), provider="gemini")

        self.assertEqual(older.input_per_million, Decimal("1.00"))
        self.assertEqual(newer.input_per_million, Decimal("3.00"))

    def test_no_snapshot_returns_none_not_zero(self):
        self.assertIsNone(price_for("narxsiz-model", on=timezone.localdate(), provider="gemini"))

    def test_a_snapshot_from_the_future_does_not_apply_retroactively(self):
        AIModelPrice.objects.create(
            provider="gemini", model_name="m", input_per_million=Decimal("5.00"),
            output_per_million=Decimal("6.00"), effective_from=datetime.date(2026, 12, 1),
        )
        self.assertIsNone(price_for("m", on=datetime.date(2026, 6, 1), provider="gemini"))


class EventCostTests(TestCase):
    def setUp(self):
        AIModelPrice.objects.create(
            provider="gemini", model_name="gemini-3.1-flash-lite",
            input_per_million=Decimal("0.10"), output_per_million=Decimal("0.40"),
            effective_from=datetime.date(2026, 1, 1),
        )

    def test_input_and_output_are_priced_separately(self):
        event = _event(prompt=1_000_000, completion=1_000_000)
        self.assertEqual(cost_for_event(event), Decimal("0.50"))

    def test_cost_is_decimal_not_float(self):
        self.assertIsInstance(cost_for_event(_event()), Decimal)

    def test_unpriced_model_returns_none(self):
        self.assertIsNone(cost_for_event(_event(model="boshqa-model")))


class RollupTests(TestCase):
    def test_priced_and_unpriced_usage_are_reported_separately(self):
        AIModelPrice.objects.create(
            provider="gemini", model_name="narxlangan",
            input_per_million=Decimal("1.00"), output_per_million=Decimal("1.00"),
            effective_from=datetime.date(2026, 1, 1),
        )
        _event(model="narxlangan", prompt=1_000_000, completion=0)
        _event(model="narxsiz", prompt=500, completion=500)

        rollup = cost_rollup()

        self.assertEqual(rollup["total"], Decimal("1.00"))
        self.assertEqual(rollup["unpriced_events"], 1)
        self.assertEqual(rollup["unpriced_tokens"], 1000)

    def test_free_tier_usage_is_not_reported_as_costing_nothing(self):
        """Reja: «Bepul» cost=0 deb yozilmaydi — quota ham scarcity."""
        _event(model="narxsiz", prompt=2000, completion=1000)

        rollup = cost_rollup()

        self.assertEqual(rollup["total"], Decimal("0"))
        self.assertEqual(rollup["priced_events"], 0)
        self.assertGreater(
            rollup["unpriced_tokens"], 0,
            "narxlanmagan sarf ko'rinmasa, hisobot «hech narsa sarflanmadi» deb chalg'itadi",
        )

    def test_failed_calls_are_excluded(self):
        """Yuborilmagan chaqiruv uchun pul to'lanmaydi."""
        AIModelPrice.objects.create(
            provider="gemini", model_name="gemini-3.1-flash-lite",
            input_per_million=Decimal("1.00"), output_per_million=Decimal("1.00"),
            effective_from=datetime.date(2026, 1, 1),
        )
        _event(prompt=1_000_000, completion=0, status=AISupplyEvent.STATUS_REJECTED)

        self.assertEqual(cost_rollup()["total"], Decimal("0"))

    def test_rollup_breaks_down_by_model(self):
        AIModelPrice.objects.create(
            provider="gemini", model_name="a", input_per_million=Decimal("2.00"),
            output_per_million=Decimal("0.00"), effective_from=datetime.date(2026, 1, 1),
        )
        _event(model="a", prompt=1_000_000, completion=0)
        _event(model="b", prompt=1_000, completion=0)

        by_model = {row["model_name"]: row for row in cost_rollup()["by_model"]}

        self.assertEqual(by_model["a"]["cost"], Decimal("2.00"))
        self.assertIsNone(by_model["b"]["cost"], "narxsiz model uchun 0 emas, None")


class RecordPriceTests(TestCase):
    def test_recording_a_price_is_audited(self):
        record_price(
            provider="gemini", model_name="m",
            input_per_million=Decimal("0.10"), output_per_million=Decimal("0.40"),
            effective_from=datetime.date(2026, 8, 1),
            note="aistudio narx sahifasi",
            reason="birinchi snapshot",
        )

        event = SystemAuditEvent.objects.filter(action="ai_price.record").first()
        self.assertIsNotNone(event, "narx kiritish auditlanmagan")
        self.assertIn("m", event.target_label)

    def test_prices_are_append_only_never_edited(self):
        """Tarixiy xarajat keyingi narx bilan qayta yozilmasin."""
        first = record_price(
            provider="gemini", model_name="m",
            input_per_million=Decimal("0.10"), output_per_million=Decimal("0.40"),
            effective_from=datetime.date(2026, 8, 1), reason="birinchi",
        )
        second = record_price(
            provider="gemini", model_name="m",
            input_per_million=Decimal("0.20"), output_per_million=Decimal("0.80"),
            effective_from=datetime.date(2026, 9, 1), reason="ikkinchi",
        )

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(AIModelPrice.objects.filter(model_name="m").count(), 2)
