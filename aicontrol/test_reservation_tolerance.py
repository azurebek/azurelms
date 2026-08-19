"""Zaxira taxminidan biroz oshib ketish circuit'ni ochmasligi kerak.

2026-08-19 da owner AI'dan tinmay "budjet mavjud emas" javobini oldi. Sabab
budjet ham, Google ham emas edi: chat qo'ng'irog'i qat'iy `4000` token zaxira
qiladi, bitta javob esa `4071` token sarfladi — va reconciliation buni
buzilish deb hisoblab circuit'ni 15 daqiqaga ochib qo'ydi.

Zaxira — bu **taxmin**. Reconciliation aynan uni haqiqiy sarf bilan almashtirish
uchun bor; har qanday musbat farqda circuit ochilsa, reconciliation o'z
ma'nosini yo'qotadi va suhbat uzaygan sari AI muntazam o'chib turadi.

Haqiqiy himoyalar joyida qoladi: kunlik project cap (`project_cap_overrun`),
provayder kvotasi (`quota`) va so'rovlar soni — so'rov **aniq sanaladi**,
taxmin emas, shuning uchun unga bag'rikenglik berilmaydi.
"""

from django.test import TestCase
from django.utils import timezone

from aicontrol.models import AISettings, AISupplyEvent, AISupplyState
from aicontrol.supply import RESERVATION_TOKEN_TOLERANCE, reconcile_supply, reserve_supply


class ReservationToleranceTests(TestCase):
    def setUp(self):
        policy = AISettings.load()
        policy.supply_enforcement_enabled = True
        policy.ai_remote_calls_enabled = True
        policy.supply_daily_request_limit = 100
        policy.supply_daily_token_limit = 250_000
        policy.save()

        state = AISupplyState.load()
        state.circuit_open_until = None
        state.circuit_reason = ""
        state.save()

    def _reserve(self, *, key, tokens=4_000, requests=2):
        return reserve_supply(
            request_key=key,
            call_type=AISupplyEvent.CALL_CHAT,
            provider="gemini",
            model_name="gemini-3.1-flash-lite",
            reserved_requests=requests,
            reserved_tokens=tokens,
        )

    def _circuit_open(self):
        state = AISupplyState.load()
        return bool(state.circuit_open_until and state.circuit_open_until > timezone.now())

    def test_small_overshoot_does_not_open_the_circuit(self):
        """Owner ko'rgan aynan holat: 4000 zaxira, 4071 sarf."""
        reservation = self._reserve(key="tolerance-small")
        reconcile_supply(reservation, succeeded=True, actual_requests=1, usage={"total_tokens": 4_071})

        self.assertFalse(
            self._circuit_open(),
            "taxmindan 71 token oshgani buzilish emas — reconciliation aynan shuning uchun bor",
        )
        self.assertEqual(AISupplyState.load().circuit_reason, "")

    def test_overshoot_within_tolerance_does_not_open_the_circuit(self):
        reservation = self._reserve(key="tolerance-edge")
        just_inside = int(4_000 * RESERVATION_TOKEN_TOLERANCE) - 1
        reconcile_supply(reservation, succeeded=True, actual_requests=1, usage={"total_tokens": just_inside})

        self.assertFalse(self._circuit_open())

    def test_wild_overshoot_still_opens_the_circuit(self):
        """Bag'rikenglik hisob-kitob buzilishini yashirmasligi kerak."""
        reservation = self._reserve(key="tolerance-wild")
        far_outside = int(4_000 * RESERVATION_TOKEN_TOLERANCE) + 1_000
        reconcile_supply(reservation, succeeded=True, actual_requests=1, usage={"total_tokens": far_outside})

        self.assertTrue(self._circuit_open())
        self.assertEqual(AISupplyState.load().circuit_reason, "reservation_overrun")

    def test_extra_requests_still_open_the_circuit(self):
        """So'rov soni aniq sanaladi — unga bag'rikenglik berilmaydi."""
        reservation = self._reserve(key="tolerance-requests", requests=2)
        reconcile_supply(reservation, succeeded=True, actual_requests=5, usage={"total_tokens": 100})

        self.assertTrue(self._circuit_open())
        self.assertEqual(AISupplyState.load().circuit_reason, "reservation_overrun")

    def test_daily_cap_overrun_still_opens_the_circuit(self):
        """Haqiqiy budjet himoyasi o'z joyida qoladi."""
        policy = AISettings.load()
        policy.supply_daily_token_limit = 5_000
        policy.save()

        # Zaxira limit ichida (aks holda rezervatsiya bosqichidayoq rad etiladi);
        # kunlik cap faqat haqiqiy sarf ma'lum bo'lgach oshib ketadi.
        reservation = self._reserve(key="tolerance-daily", tokens=4_000)
        reconcile_supply(reservation, succeeded=True, actual_requests=1, usage={"total_tokens": 6_000})

        self.assertTrue(self._circuit_open())
        self.assertEqual(AISupplyState.load().circuit_reason, "project_cap_overrun")
