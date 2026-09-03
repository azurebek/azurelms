"""Mehmon demo chegarasi — tekshirish va band qilish bitta amalda (K11).

Ilgari oqim shunday edi: oddiy `if used >= LIMIT` tekshiruvi, keyin provider
chaqiruvi, keyin hisoblagichni oshirish. Ikki savol bir vaqtda kelsa
**ikkalasi ham** tekshiruvdan o'tardi — chegara 5 bo'lsa ham mehmon 6 ta
bepul javob olishi mumkin edi.

Endi slot chaqiruvdan **oldin** shartli `UPDATE` bilan band qilinadi:
`demo_questions_used < LIMIT` filtri faqat bitta so'rovda mos keladi,
ikkinchisi `0` qator yangilaydi va rad javobini oladi.

Ikkinchi shart ham saqlanadi: provider javob bermasa band qilingan slot
qaytariladi — yiqilgan chaqiruv mehmonning bepul savolini yemaydi.
"""

from types import SimpleNamespace

from django.test import TestCase, TransactionTestCase

from aicontrol.models import AISettings
from bot.models import BotGuest
from bot.services import GUEST_DEMO_QUESTION_LIMIT, guest_demo_answer
from core.qa_support import skip_unless_file_backed_db

TELEGRAM_ID = 550001


def _provider(text="Javob"):
    return SimpleNamespace(generate=lambda prompt: SimpleNamespace(text=text))


def _enable_guest_demo():
    settings_row = AISettings.load()
    settings_row.guest_demo_enabled = True
    settings_row.save(update_fields=["guest_demo_enabled"])


class GuestDemoLimitTests(TestCase):
    def setUp(self):
        _enable_guest_demo()

    def _ask(self, provider=None):
        return guest_demo_answer(
            telegram_id=TELEGRAM_ID,
            telegram_username="mehmon",
            question="Salom qanday aytiladi?",
            provider=provider or _provider(),
        )

    def test_the_limit_is_enforced_exactly(self):
        for index in range(GUEST_DEMO_QUESTION_LIMIT):
            result = self._ask()
            self.assertTrue(result.ok, f"{index + 1}-savol rad etildi: {result.message}")

        extra = self._ask()

        self.assertFalse(extra.ok)
        self.assertEqual(extra.code, "limit_reached")
        self.assertEqual(
            BotGuest.objects.get(telegram_id=TELEGRAM_ID).demo_questions_used,
            GUEST_DEMO_QUESTION_LIMIT,
        )

    def test_remaining_counts_down(self):
        first = self._ask()

        self.assertEqual(first.remaining, GUEST_DEMO_QUESTION_LIMIT - 1)

    def test_a_failed_call_gives_the_slot_back(self):
        """Yiqilgan chaqiruv mehmonning bepul savolini yemasligi kerak."""
        broken = SimpleNamespace(
            generate=lambda prompt: (_ for _ in ()).throw(RuntimeError("provider yiqildi"))
        )

        result = self._ask(provider=broken)

        self.assertFalse(result.ok)
        self.assertEqual(result.code, "provider_error")
        self.assertEqual(
            BotGuest.objects.get(telegram_id=TELEGRAM_ID).demo_questions_used, 0
        )

    def test_the_counter_never_goes_negative(self):
        broken = SimpleNamespace(
            generate=lambda prompt: (_ for _ in ()).throw(RuntimeError("yiqildi"))
        )

        for _ in range(3):
            self._ask(provider=broken)

        self.assertEqual(
            BotGuest.objects.get(telegram_id=TELEGRAM_ID).demo_questions_used, 0
        )


class GuestDemoConcurrencyTests(TransactionTestCase):
    """Asosiy da'vo — parallel savollar chegaradan o'tib ketmaydi.

    **Fayl bazasini talab qiladi** va defaultda skip bo'ladi:

        AZURELMS_TEST_FILE_DB=1 python manage.py test bot.test_guest_demo_limit

    Buni tekshirmasdan qoldirib bo'lmasdi. Nazorat yugurishida eski
    `check-then-act` kod qaytarilganda test **xotira bazasida o'tib ketdi**
    (ya'ni hech nimani isbotlamasdi), fayl bazasida esa yiqildi:
    `2 != 1 : [False, False, True, True]` — bitta slotdan ikkita savol
    o'tgan. Shared-cache in-memory baza oqimlar orasidagi haqiqiy qulflash
    semantikasini ko'rsatmaydi.

    `TransactionTestCase` ham ataylab: oddiy `TestCase` har testni bitta
    tranzaksiyada ushlaydi va boshqa oqimlar yozuvni umuman ko'rmaydi.
    """

    def setUp(self):
        skip_unless_file_backed_db(self)
        _enable_guest_demo()

    def test_parallel_questions_cannot_exceed_the_limit(self):
        import threading

        from django.db import connection

        BotGuest.objects.create(
            telegram_id=TELEGRAM_ID,
            telegram_username="mehmon",
            demo_questions_used=GUEST_DEMO_QUESTION_LIMIT - 1,
        )
        results = []
        lock = threading.Lock()

        def ask():
            try:
                outcome = guest_demo_answer(
                    telegram_id=TELEGRAM_ID,
                    telegram_username="mehmon",
                    question="Parallel savol",
                    provider=_provider(),
                )
                with lock:
                    results.append(outcome.ok)
            finally:
                connection.close()

        threads = [threading.Thread(target=ask) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Bitta slot qolgan edi — faqat bitta savol o'tishi kerak.
        self.assertEqual(sum(1 for ok in results if ok), 1, results)
        self.assertEqual(
            BotGuest.objects.get(telegram_id=TELEGRAM_ID).demo_questions_used,
            GUEST_DEMO_QUESTION_LIMIT,
        )

    def tearDown(self):
        BotGuest.objects.all().delete()
