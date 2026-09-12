"""T4 — dispatcher kuzatuvi: o'lchov, yozuv va ularning narxi.

Audit (2026-09-11) yozgan bo'shliq: «Launch kuni bot holatini ko'rsatadigan
hech narsa yo'q… "Bot sekinlashdimi?" savoliga bugun javob beradigan o'lchov
yo'q.» Bu fayl shu o'lchovni va uning **ikki chegarasini** qulflaydi:

1. O'lchash handler yo'lini sekinlashtirmasligi kerak — shuning uchun asosiy
   test `SimpleTestCase` da yuguradi. U DB so'rovini **taqiqlaydi**: agar
   kimdir o'lchovga DB yozuvi qo'shsa, test o'z-o'zidan yiqiladi.
2. Trafiksizlik nosozlik emas — o'lchov oynasi bo'sh bo'lsa javob «namuna
   yo'q» bo'lishi kerak, «hammasi tez» emas.
"""

import asyncio
import datetime

from aiogram.dispatcher.event.bases import UNHANDLED, SkipHandler
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone

from aicontrol.models import WorkerHeartbeat
from bot import metrics
from bot.metrics import DispatcherMetrics, percentile
from bot.middleware import IdentityMiddleware, MetricsMiddleware
from bot.models import BotRuntimeSettings
from bot.runtime_settings import DeliveryPolicy


class PercentileTests(SimpleTestCase):
    def test_single_sample_is_its_own_p95(self):
        """Bitta namunada p95 = shu namuna — interpolatsiya qilinmaydi."""
        self.assertEqual(percentile([42.0], 0.95), 42.0)

    def test_nearest_rank_picks_a_real_measurement(self):
        values = [float(n) for n in range(1, 21)]  # 1..20
        # ceil(0.95 * 20) = 19 → 19-chi qiymat
        self.assertEqual(percentile(values, 0.95), 19.0)

    def test_p95_ignores_the_single_worst_outlier_in_twenty(self):
        values = sorted([5.0] * 19 + [9000.0])
        self.assertEqual(percentile(values, 0.95), 5.0)
        self.assertEqual(values[-1], 9000.0, "eng yomoni max'da ko'rinadi")

    def test_empty_input_is_an_error_not_a_zero(self):
        """Nol qaytarish «hammasi tez» degan yolg'on bo'lardi."""
        with self.assertRaises(ValueError):
            percentile([], 0.95)


class AccumulatorTests(SimpleTestCase):
    def setUp(self):
        self.acc = DispatcherMetrics()

    def test_an_empty_window_reports_no_samples_not_zero_latency(self):
        snap = self.acc.snapshot(window_seconds=300, monotonic=1000.0)
        self.assertEqual(snap["samples"], 0)
        self.assertNotIn("p95_ms", snap)
        self.assertNotIn("avg_ms", snap)

    def test_measurements_outside_the_window_are_dropped(self):
        """Uch soat oldingi sekinlik hozirgi tezlik bo'lib ko'rinmasligi kerak."""
        self.acc.record(duration_ms=5000.0, monotonic=0.0, wall=timezone.now())
        self.acc.record(duration_ms=10.0, monotonic=1000.0, wall=timezone.now())

        snap = self.acc.snapshot(window_seconds=60, monotonic=1000.0)

        self.assertEqual(snap["samples"], 1)
        self.assertEqual(snap["max_ms"], 10.0)

    def test_totals_survive_the_window(self):
        """Oyna tezlik uchun; umumiy hisob jarayon boshidan beri."""
        self.acc.record(duration_ms=5000.0, failed=True, monotonic=0.0, wall=timezone.now())
        self.acc.record(duration_ms=10.0, monotonic=1000.0, wall=timezone.now())

        snap = self.acc.snapshot(window_seconds=60, monotonic=1000.0)

        self.assertEqual(snap["updates_total"], 2)
        self.assertEqual(snap["errors_total"], 1)
        self.assertEqual(snap["errors"], 0, "xato oynadan tashqarida")

    def test_errors_and_unhandled_are_counted_separately(self):
        self.acc.record(duration_ms=1.0, failed=True, monotonic=10.0, wall=timezone.now())
        self.acc.record(duration_ms=1.0, unhandled=True, monotonic=10.0, wall=timezone.now())
        self.acc.record(duration_ms=1.0, monotonic=10.0, wall=timezone.now())

        snap = self.acc.snapshot(window_seconds=300, monotonic=10.0)

        self.assertEqual(snap["samples"], 3)
        self.assertEqual(snap["errors"], 1)
        self.assertEqual(snap["unhandled"], 1)

    def test_memory_is_bounded(self):
        """Cheksiz o'sish yo'q — bu siyosat emas, xotira kafolati."""
        for index in range(metrics.MAX_SAMPLES + 500):
            self.acc.record(duration_ms=1.0, monotonic=float(index), wall=timezone.now())

        snap = self.acc.snapshot(window_seconds=10**9, monotonic=float(metrics.MAX_SAMPLES + 500))

        self.assertEqual(snap["samples"], metrics.MAX_SAMPLES)
        self.assertEqual(snap["updates_total"], metrics.MAX_SAMPLES + 500)


class MeasurementCostTests(SimpleTestCase):
    """`SimpleTestCase` — DB so'rovi taqiqlangan.

    Bu faylning eng muhim testi: o'lchash yo'li **hech qanday** DB so'rovi
    qilmasligi kerak. Jonli darsda 50 o'quvchi bir vaqtda «Keldim» bosganda
    har update uchun bitta `UPDATE` — o'lchovning o'zi nosozlik manbasi
    bo'lib qolardi.
    """

    def setUp(self):
        metrics.METRICS.reset()
        # Polling rejimida flush sikli alohida ishlaydi, ya'ni middleware
        # hech narsa yozmaydi. Shu holatni aynan o'sha flag bilan qo'yamiz.
        self._saved = metrics._flusher_active
        metrics._flusher_active = True

    def tearDown(self):
        metrics._flusher_active = self._saved
        metrics.METRICS.reset()

    def _run(self, handler):
        return asyncio.run(MetricsMiddleware()(handler, object(), {}))

    def test_a_successful_update_is_measured_without_touching_the_database(self):
        async def handler(event, data):
            return "javob"

        self.assertEqual(self._run(handler), "javob")

        snap = metrics.METRICS.snapshot(window_seconds=300)
        self.assertEqual(snap["samples"], 1)
        self.assertEqual(snap["errors"], 0)
        self.assertGreaterEqual(snap["max_ms"], 0.0)

    def test_a_handler_exception_is_counted_and_re_raised(self):
        """Xato yutilmaydi: aiogram ning `ErrorsMiddleware` i tashqarida."""

        async def handler(event, data):
            raise RuntimeError("buzildi")

        with self.assertRaises(RuntimeError):
            self._run(handler)

        snap = metrics.METRICS.snapshot(window_seconds=300)
        self.assertEqual(snap["errors"], 1)
        self.assertEqual(snap["samples"], 1)

    def test_skip_handler_is_control_flow_not_an_error(self):
        """Filtr mos kelmagani nosozlik emas — aks holda chiroq doim qizil."""

        async def handler(event, data):
            raise SkipHandler()

        with self.assertRaises(SkipHandler):
            self._run(handler)

        snap = metrics.METRICS.snapshot(window_seconds=300)
        self.assertEqual(snap["errors"], 0)
        self.assertEqual(snap["samples"], 1)

    def test_an_unhandled_update_is_recorded_as_unhandled_not_as_an_error(self):
        async def handler(event, data):
            return UNHANDLED

        self._run(handler)

        snap = metrics.METRICS.snapshot(window_seconds=300)
        self.assertEqual(snap["unhandled"], 1)
        self.assertEqual(snap["errors"], 0)


class MiddlewareOrderTests(SimpleTestCase):
    """O'lchov identity'dan TASHQARIDA bo'lishi kerak.

    Identity har update'da 3 DB so'rovi qiladi. Agar o'lchov undan ichkarida
    bo'lsa p95 foydalanuvchi kutgan vaqtning bir qismini ko'rsatadi va «bot
    tez» degan yolg'on javob beradi.
    """

    def _outer_middleware_classes(self):
        from bot.aiogram_app import get_dispatcher

        return [type(item) for item in list(get_dispatcher().update.outer_middleware)]

    def test_metrics_wraps_identity(self):
        classes = self._outer_middleware_classes()
        self.assertIn(MetricsMiddleware, classes)
        self.assertIn(IdentityMiddleware, classes)
        self.assertLess(
            classes.index(MetricsMiddleware),
            classes.index(IdentityMiddleware),
            "aiogram birinchi ro'yxatdan o'tganni tashqi qatlam qiladi",
        )

    def test_polling_lifecycle_hooks_are_registered(self):
        """Flush sikli `start_polling` bilan o'z-o'zidan ko'tarilishi kerak.

        Ikkita polling kirish nuqtasi bor (`manage.py runbot` va
        `run_bot.py`); siklni ularga qo'lda ulash bittasini unutish yo'li.
        """
        from bot.aiogram_app import get_dispatcher

        dp = get_dispatcher()
        self.assertTrue(
            any("_start" in getattr(h.callback, "__name__", "") for h in dp.startup.handlers),
            "startup hooki yo'q — polling'da heartbeat yozilmaydi",
        )
        self.assertTrue(
            any("_stop" in getattr(h.callback, "__name__", "") for h in dp.shutdown.handlers),
            "shutdown hooki yo'q — rejali to'xtatish halokatdan ajralmaydi",
        )


class HeartbeatWriteTests(TestCase):
    def setUp(self):
        metrics.METRICS.reset()

    def tearDown(self):
        metrics.METRICS.reset()

    def test_flush_writes_the_window_and_the_interval_it_used(self):
        metrics.METRICS.record(duration_ms=120.0, wall=timezone.now())

        metrics.flush_metrics()

        beat = WorkerHeartbeat.objects.get(name=metrics.WORKER_NAME)
        self.assertEqual(beat.detail["samples"], 1)
        # Probe eskirish chegarasini shundan hisoblaydi — sozlamadagi joriy
        # qiymatdan emas, jarayon ishlatgan qiymatdan.
        self.assertEqual(
            beat.detail["flush_seconds"], DeliveryPolicy.defaults().metrics_flush_seconds
        )

    def test_a_quiet_process_still_writes_a_heartbeat(self):
        """Tunda hech kim yozmasa ham bot tirik — chiroq yashil qolishi kerak."""
        metrics.flush_metrics()

        beat = WorkerHeartbeat.objects.get(name=metrics.WORKER_NAME)
        self.assertEqual(beat.detail["samples"], 0)
        self.assertIsNone(beat.detail["last_update_at"])
        self.assertNotIn("stopped_at", beat.detail)

    def test_a_planned_stop_is_marked(self):
        metrics.flush_metrics(stopped=True)

        beat = WorkerHeartbeat.objects.get(name=metrics.WORKER_NAME)
        self.assertIn("stopped_at", beat.detail)

    def test_restarting_clears_the_stop_mark(self):
        """Aks holda bot qaytib ishga tushsa ham chiroq «to'xtatilgan» qolardi."""
        metrics.flush_metrics(stopped=True)

        metrics.flush_metrics()

        beat = WorkerHeartbeat.objects.get(name=metrics.WORKER_NAME)
        self.assertNotIn("stopped_at", beat.detail)

    def test_safe_flush_never_raises(self):
        """Kuzatuv vositasi kuzatilayotgan tizimni o'chira olmaydi."""
        def _explode(**kwargs):
            raise RuntimeError("DB yo'q")

        original = metrics.flush_metrics
        metrics.flush_metrics = _explode
        try:
            # Xato **logga** ketadi, yuqoriga emas: shuning uchun
            # `assertLogs` — u ham tekshiradi, ham test chiqishini tozalaydi.
            with self.assertLogs("bot.metrics", level="WARNING"):
                self.assertIsNone(metrics.safe_flush())
        finally:
            metrics.flush_metrics = original

    def test_the_owner_can_change_the_window_without_a_deploy(self):
        row = BotRuntimeSettings.load()
        row.metrics_flush_seconds = 60
        row.metrics_window_seconds = 900
        row.save()

        metrics.METRICS.record(duration_ms=7.0, wall=timezone.now())
        metrics.flush_metrics()

        beat = WorkerHeartbeat.objects.get(name=metrics.WORKER_NAME)
        self.assertEqual(beat.detail["window_seconds"], 900)
        self.assertEqual(beat.detail["flush_seconds"], 60)


class PolicyClampTests(TestCase):
    def test_a_window_shorter_than_the_interval_is_widened_on_read(self):
        """Aks holda har yozuv o'zidan oldingi siklni ko'rmay qolardi."""
        row = BotRuntimeSettings.load()
        # Formani chetlab o'tgan yozuv: `update()` `clean()` ni chaqirmaydi.
        BotRuntimeSettings.objects.filter(pk=row.pk).update(
            metrics_flush_seconds=120, metrics_window_seconds=30
        )

        policy = BotRuntimeSettings.resolved()

        self.assertEqual(policy.metrics_window_seconds, 120)

    def test_garbage_falls_back_to_the_code_default(self):
        policy = DeliveryPolicy.from_row(
            type("Row", (), {"metrics_flush_seconds": "salom"})()
        )

        self.assertEqual(
            policy.metrics_flush_seconds,
            DeliveryPolicy.defaults().metrics_flush_seconds,
        )

    def test_the_form_rejects_a_window_shorter_than_the_interval(self):
        from django.core.exceptions import ValidationError

        row = BotRuntimeSettings.load()
        row.metrics_flush_seconds = 120
        row.metrics_window_seconds = 30

        with self.assertRaises(ValidationError) as caught:
            row.full_clean()

        self.assertIn("metrics_window_seconds", caught.exception.message_dict)


class PiggybackFlushTests(TransactionTestCase):
    """Webhook rejimi: yozuv update'ga ilashadi, ammo oraliqqa bir marta.

    `TransactionTestCase` — middleware async va `sync_to_async` ORM'ga boshqa
    oqimdan tegadi; `TestCase` ning o'rab turgan tranzaksiyasi SQLite'da
    qulflanib qolardi (bu naqsh `core/test_worker_heartbeat.py` da ham).
    """

    def setUp(self):
        metrics.METRICS.reset()
        metrics.reset_flush_clock()
        self._saved = metrics._flusher_active
        metrics._flusher_active = False

    def tearDown(self):
        metrics._flusher_active = self._saved
        metrics.METRICS.reset()
        metrics.reset_flush_clock()

    def _two_updates(self):
        from asgiref.sync import sync_to_async
        from django.db import connections

        async def handler(event, data):
            return "ok"

        async def run():
            await MetricsMiddleware()(handler, object(), {})
            first = await sync_to_async(_last_seen)()
            await MetricsMiddleware()(handler, object(), {})
            second = await sync_to_async(_last_seen)()
            # Alohida oqim o'z ulanishini ochiq qoldiradi; PostgreSQL test
            # bazasini o'chira olmay yiqilardi.
            await sync_to_async(connections.close_all)()
            return first, second

        def _last_seen():
            beat = WorkerHeartbeat.objects.filter(name=metrics.WORKER_NAME).first()
            return beat.last_seen_at if beat else None

        return asyncio.run(run())

    def test_the_first_update_writes_and_the_second_does_not(self):
        first, second = self._two_updates()

        self.assertIsNotNone(first, "webhook rejimida birinchi update yozishi kerak")
        self.assertEqual(first, second, "oraliq ichida ikkinchi yozuv bo'lmasligi kerak")

    def test_both_updates_are_still_measured(self):
        self._two_updates()

        snap = metrics.METRICS.snapshot(window_seconds=300)
        self.assertEqual(snap["samples"], 2, "yozuv tejalsa ham o'lchov tejalmaydi")


class FlusherLoopTests(TransactionTestCase):
    def tearDown(self):
        metrics.METRICS.reset()

    def test_the_loop_writes_immediately_and_marks_itself_active(self):
        """Bot ishga tushganda chiroq darhol yashil bo'lishi kerak.

        Birinchi yozuvni bir oraliq kutib yuborish Control Center'da yangi
        ko'tarilgan botni «hech qachon ishga tushmagan» qilib ko'rsatardi.
        """
        from asgiref.sync import sync_to_async
        from django.db import connections

        seen = {}

        async def run():
            task = asyncio.create_task(metrics.run_metrics_flusher())
            for _ in range(200):
                await asyncio.sleep(0.01)
                exists = await sync_to_async(
                    WorkerHeartbeat.objects.filter(name=metrics.WORKER_NAME).exists
                )()
                if exists:
                    break
            seen["active"] = metrics.flusher_active()
            seen["exists"] = exists
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            seen["active_after"] = metrics.flusher_active()
            await sync_to_async(connections.close_all)()

        asyncio.run(run())

        self.assertTrue(seen["exists"], "sikl birinchi yozuvni kutmasdan qilishi kerak")
        self.assertTrue(seen["active"], "sikl ishlayotganda middleware yozmasligi kerak")
        self.assertFalse(seen["active_after"], "to'xtagach piggy-back yana yoqilishi kerak")


class StaleHeartbeatAgeTests(TestCase):
    def test_age_grows_with_the_clock(self):
        """Probe yoshni shu yo'l bilan o'qiydi — arifmetika qulflanadi."""
        metrics.flush_metrics()
        WorkerHeartbeat.objects.filter(name=metrics.WORKER_NAME).update(
            last_seen_at=timezone.now() - datetime.timedelta(seconds=400)
        )

        beat = WorkerHeartbeat.objects.get(name=metrics.WORKER_NAME)

        self.assertGreaterEqual(int(beat.age().total_seconds()), 399)
