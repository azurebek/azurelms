"""A8 closeout — global supply ledgerining haqiqiy parallel contention isboti.

Mavjud `GlobalSupplyBudgetTests` ketma-ket ishlaydi va `TestCase` bo'lgani uchun
har bir test bitta ochiq transaction ichida bajariladi — tuzilishi bo'yicha
parallel rezervatsiyani sinay olmaydi. Bu modul `TransactionTestCase` ustida
real threadlar (har biri o'z DB connection'i bilan) ishlatib, ledgerning asosiy
invariantlarini tekshiradi:

    sum(accounted_requests) <= supply_daily_request_limit
    sum(accounted_tokens)   <= supply_daily_token_limit

**Nima uchun bu kerak edi.** `reserve_supply()` singleton qatorlarni
`select_for_update()` bilan qulflaydi. PostgreSQL'da bu rezervatsiyalarni
ketma-ketlashtiradi, ammo SQLite'da `BaseDatabaseFeatures.has_select_for_update
= False` va sqlite3 backend uni override qilmaydi — Django `FOR UPDATE` bandini
jimgina tushirib qoldiradi (`django/db/models/sql/compiler.py`). `BEGIN
DEFERRED` bilan o'qigan tranzaksiya keyin yozishga ko'tarilganda SQLite
busy_timeout'ni kutmasdan darhol `database is locked` qaytaradi, chunki kutish
deadlockka olib kelishi mumkin. Natijada tuzatishdan oldin 8 parallel
rezervatsiyadan 7 tasi `SupplyUnavailable` bilan yiqilardi.

Yechim `core/settings.py`da: SQLite uchun `transaction_mode='IMMEDIATE'`
(write lock tranzaksiya boshida olinadi, raqiblar xato o'rniga kutadi),
`timeout` va WAL.

**Ishga tushirish.** Default test bazasi tez, ammo shared-cache in-memory
SQLite — uning qulflash semantikasi real `db.sqlite3` bilan bir xil emas.
Shuning uchun contention testlari faqat fayl bazasida bajariladi:

    AZURELMS_TEST_FILE_DB=1 python manage.py test aicontrol.test_supply_concurrency

Fayl bazasisiz ular skip bo'ladi, ammo `SQLiteConcurrencyConfigTests` har
yugurishda ishlaydi va konfiguratsiya regressiyasini darhol ushlaydi.
"""

import threading
import unittest

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase

from aicontrol.models import AISettings, AISupplyEvent, AISupplyState
from core.qa_support import is_file_backed_sqlite, skip_unless_file_backed_db
from aicontrol.supply import (
    SupplyDenied,
    SupplyDuplicate,
    reconcile_supply,
    reserve_supply,
)

User = get_user_model()

WORKERS = 8
BARRIER_TIMEOUT = 15



class SupplyReservationContentionTests(TransactionTestCase):
    """Parallel workerlar bitta global budjetga urilganda invariant buzilmaydi."""

    reset_sequences = True

    def setUp(self):
        skip_unless_file_backed_db(self)
        AISupplyEvent.objects.all().delete()
        AISupplyState.objects.all().delete()
        AISettings.objects.all().delete()
        self.policy = AISettings.load()
        self.policy.supply_enforcement_enabled = True
        self.policy.supply_daily_request_limit = 1
        self.policy.supply_minute_request_limit = 100
        self.policy.supply_daily_token_limit = 1_000_000
        self.policy.supply_default_reservation_tokens = 100
        self.policy.supply_cooldown_seconds = 60
        self.policy.save()
        AISupplyState.load()

    # --- yordamchi ---------------------------------------------------------

    def _run_parallel(self, worker_count, call):
        """`call(index)` ni bir vaqtda `worker_count` ta threadda bajaradi.

        Har bir thread barrier'da kutib turadi, shuning uchun ular imkon qadar
        bir vaqtda `reserve_supply()` ichiga kiradi. Natija: (kind, value)
        juftliklari — `kind` "ok" yoki xato sinfi nomi.
        """
        barrier = threading.Barrier(worker_count)
        results = [None] * worker_count

        def worker(index):
            try:
                barrier.wait(timeout=BARRIER_TIMEOUT)
                results[index] = ("ok", call(index))
            except BaseException as exc:  # noqa: BLE001 — natijani testga qaytaramiz
                results[index] = (type(exc).__name__, exc)
            finally:
                connection.close()

        threads = [
            threading.Thread(target=worker, args=(index,), name=f"supply-{index}")
            for index in range(worker_count)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=BARRIER_TIMEOUT * 2)
        for thread in threads:
            self.assertFalse(thread.is_alive(), "contention threadi muzlab qoldi")
        return results

    def _accounted(self):
        events = AISupplyEvent.objects.all()
        return (
            sum(event.accounted_requests for event in events),
            sum(event.accounted_tokens for event in events),
        )

    def _unexpected(self, results, *allowed):
        allowed_names = {"ok", *(cls.__name__ for cls in allowed)}
        return [
            (kind, f"{value} <- {value.__cause__!r}")
            for kind, value in results
            if kind not in allowed_names
        ]

    def _outcome_counts(self, results):
        counts = {}
        for kind, _ in results:
            counts[kind] = counts.get(kind, 0) + 1
        return counts

    # --- testlar -----------------------------------------------------------

    def test_parallel_reservations_never_exceed_daily_request_budget(self):
        """Oxirgi bitta kunlik request uchun kurash: faqat bittasi o'tishi kerak."""
        results = self._run_parallel(
            WORKERS,
            lambda index: reserve_supply(
                request_key=f"contention:daily:{index}",
                call_type=AISupplyEvent.CALL_CHAT,
                reserved_requests=1,
            ),
        )

        self.assertEqual(self._unexpected(results, SupplyDenied), [])
        granted = [kind for kind, _ in results].count("ok")
        accounted_requests, _ = self._accounted()

        self.assertLessEqual(
            accounted_requests,
            self.policy.supply_daily_request_limit,
            "global kunlik request budjeti parallel rezervatsiyada oshib ketdi",
        )
        self.assertEqual(granted, self.policy.supply_daily_request_limit)

    def test_parallel_reservations_never_exceed_minute_request_budget(self):
        """Bir daqiqalik burst capi ham parallel oqimda ushlab turilishi kerak."""
        self.policy.supply_daily_request_limit = 1_000
        self.policy.supply_minute_request_limit = 2
        self.policy.save(
            update_fields=[
                "supply_daily_request_limit",
                "supply_minute_request_limit",
                "updated_at",
            ]
        )

        results = self._run_parallel(
            WORKERS,
            lambda index: reserve_supply(
                request_key=f"contention:minute:{index}",
                call_type=AISupplyEvent.CALL_CHAT,
                reserved_requests=1,
            ),
        )

        self.assertEqual(self._unexpected(results, SupplyDenied), [])
        accounted_requests, _ = self._accounted()
        self.assertLessEqual(
            accounted_requests,
            self.policy.supply_minute_request_limit,
            "bir daqiqalik request budjeti parallel rezervatsiyada oshib ketdi",
        )

    def test_parallel_reservations_never_exceed_daily_token_budget(self):
        """Token budjeti ham request soni kabi hard cap bo'lib qolishi kerak."""
        self.policy.supply_daily_request_limit = 1_000
        self.policy.supply_minute_request_limit = 1_000
        self.policy.supply_daily_token_limit = 300
        self.policy.supply_default_reservation_tokens = 100
        self.policy.save(
            update_fields=[
                "supply_daily_request_limit",
                "supply_minute_request_limit",
                "supply_daily_token_limit",
                "supply_default_reservation_tokens",
                "updated_at",
            ]
        )

        results = self._run_parallel(
            WORKERS,
            lambda index: reserve_supply(
                request_key=f"contention:token:{index}",
                call_type=AISupplyEvent.CALL_CHAT,
                reserved_requests=1,
                reserved_tokens=100,
            ),
        )

        self.assertEqual(self._unexpected(results, SupplyDenied), [])
        _, accounted_tokens = self._accounted()
        self.assertLessEqual(
            accounted_tokens,
            self.policy.supply_daily_token_limit,
            "global kunlik token budjeti parallel rezervatsiyada oshib ketdi",
        )

    def test_reserve_and_reconcile_lifecycle_survives_contention(self):
        """To'liq reserve → reconcile sikli parallel oqimda ham buzilmasligi kerak.

        `reconcile_supply()` ham `select_for_update()` ga tayanadi va o'zi ham
        kunlik totallarni qayta hisoblab, overrun sezsa circuit'ni ochadi. Agar
        parallel yozuvlar buzilsa, bu yerda yo yozuv yo'qoladi, yo hech qanday
        haqiqiy overrun bo'lmagan holda circuit ochilib qoladi.
        """
        self.policy.supply_daily_request_limit = 1_000
        self.policy.supply_minute_request_limit = 1_000
        self.policy.save(
            update_fields=[
                "supply_daily_request_limit",
                "supply_minute_request_limit",
                "updated_at",
            ]
        )

        def reserve_then_reconcile(index):
            reservation = reserve_supply(
                request_key=f"contention:lifecycle:{index}",
                call_type=AISupplyEvent.CALL_CHAT,
                reserved_requests=1,
                reserved_tokens=100,
            )
            return reconcile_supply(
                reservation,
                succeeded=True,
                actual_requests=1,
                usage={"prompt_tokens": 6, "completion_tokens": 4, "total_tokens": 10},
                model_name="gemini-3.1-flash-lite",
            )

        results = self._run_parallel(WORKERS, reserve_then_reconcile)

        self.assertEqual(self._unexpected(results), [])
        self.assertEqual(self._outcome_counts(results), {"ok": WORKERS})

        events = AISupplyEvent.objects.all()
        self.assertEqual(events.count(), WORKERS, "parallel oqimda ledger yozuvi yo'qoldi")
        self.assertTrue(
            all(event.status == AISupplyEvent.STATUS_SUCCEEDED for event in events)
        )

        accounted_requests, accounted_tokens = self._accounted()
        self.assertEqual(accounted_requests, WORKERS)
        self.assertEqual(accounted_tokens, WORKERS * 10)

        state = AISupplyState.objects.get(singleton=True)
        self.assertIsNone(
            state.circuit_open_until,
            f"haqiqiy overrun yo'q, ammo circuit ochildi: {state.circuit_reason}",
        )

    def test_same_idempotency_key_reserves_exactly_once_under_contention(self):
        """Bir xil request_key bilan kelgan parallel workerlar bitta yozuv qoldiradi."""
        self.policy.supply_daily_request_limit = 1_000
        self.policy.supply_minute_request_limit = 1_000
        self.policy.save(
            update_fields=[
                "supply_daily_request_limit",
                "supply_minute_request_limit",
                "updated_at",
            ]
        )

        results = self._run_parallel(
            WORKERS,
            lambda index: reserve_supply(
                request_key="contention:duplicate",
                call_type=AISupplyEvent.CALL_CHAT,
                reserved_requests=1,
            ),
        )

        self.assertEqual(self._unexpected(results, SupplyDuplicate), [])
        granted = [kind for kind, _ in results].count("ok")
        self.assertEqual(granted, 1, "bir xil idempotency key bir necha marta rezerv qilindi")
        self.assertEqual(
            AISupplyEvent.objects.filter(request_key="contention:duplicate").count(),
            1,
        )


@unittest.skipUnless(connection.vendor == "sqlite", "faqat SQLite backendiga tegishli")
class SQLiteConcurrencyConfigTests(TestCase):
    """Konfiguratsiya kontrakti — har yugurishda ishlaydigan arzon regressiya qo'riqchisi.

    Contention testlari fayl bazasini talab qiladi va default suite'da skip
    bo'ladi. Bu testlar esa doim ishlaydi: kimdir `transaction_mode`ni olib
    tashlasa, sabab darhol va aniq ko'rinadi.

    Bu sozlama faqat AI supply ledgeriga tegishli emas — `aicontrol/supply.py`dan
    tashqarida `select_for_update()` ga tayanadigan yana 13 ta chaqiruv joyi bor
    (8 faylda: enrollment transition, promo redemption, exam attempt/answer/reading
    response, davomat, streak, XP va Telegram auth tokenini bir martalik consume
    qilish). SQLite'da ularning hammasi shu serializatsiyaga bog'liq.
    """

    def test_sqlite_uses_immediate_transactions(self):
        options = connection.settings_dict.get("OPTIONS", {})
        self.assertEqual(
            options.get("transaction_mode"),
            "IMMEDIATE",
            "SQLite `BEGIN DEFERRED` bilan ishlasa, read-modify-write raqiblari "
            "busy_timeout'ni kutmasdan 'database is locked' oladi",
        )

    def test_sqlite_has_busy_timeout(self):
        options = connection.settings_dict.get("OPTIONS", {})
        self.assertGreaterEqual(
            options.get("timeout") or 0,
            5,
            "write lock navbatini kutish uchun busy timeout kerak",
        )

    def test_sqlite_init_command_enables_wal(self):
        options = connection.settings_dict.get("OPTIONS", {})
        self.assertIn(
            "journal_mode=WAL",
            (options.get("init_command") or "").replace(" ", ""),
            "WAL bo'lmasa o'quvchilar yozuvchini bloklaydi",
        )

    def test_sqlite_runtime_journal_mode_is_wal(self):
        if not is_file_backed_sqlite():
            self.skipTest("in-memory test bazasi WAL rejimini qo'llab-quvvatlamaydi")
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode;")
            mode = cursor.fetchone()[0]
        self.assertEqual(str(mode).lower(), "wal")
