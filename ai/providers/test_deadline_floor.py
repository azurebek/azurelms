"""Google minimal deadline talabi (A8).

2026-08-19: AI javob bermay qoldi va ledger `timeout` deb yozdi. Aslida
timeout emas edi — Google so'rovni **ishlashdan oldin** rad etardi:

    400 INVALID_ARGUMENT: Manually set deadline 8s is too short.
                          Minimum allowed deadline is 10s.

Ilova `GEMINI_REQUEST_TIMEOUT_MS=8000` yuborardi. Xato matnida "deadline"
so'zi borligi uchun provider uni `timeout` deb tasniflagan va sabab
yashiringan — o'lchangan haqiqiy javob vaqti esa 2-3 soniya edi.

Ikkita da'vo shu yerda qo'riqlanadi: sozlangan qiymat Google minimumidan
past bo'lmaydi, va deadline tugayotganda provider aniq rad etilaman
deydigan so'rov yubormaydi.
"""

from django.test import SimpleTestCase, override_settings

from ai.providers.gemini import (
    DEFAULT_DEADLINE_MS,
    DEFAULT_REQUEST_TIMEOUT_MS,
    MIN_PROVIDER_DEADLINE_MS,
)


class DeadlineFloorTests(SimpleTestCase):
    def test_google_minimum_is_recorded(self):
        self.assertEqual(MIN_PROVIDER_DEADLINE_MS, 10_000)

    def test_the_default_request_timeout_clears_the_minimum(self):
        self.assertGreaterEqual(DEFAULT_REQUEST_TIMEOUT_MS, MIN_PROVIDER_DEADLINE_MS)

    def test_the_deadline_leaves_room_for_two_attempts(self):
        """Provider ikkita urinishga ruxsat beradi; deadline shunga yetishi kerak.

        Aks holda ikkinchi urinishda qolgan vaqt 10s dan tushib, so'rov
        yana `400` bilan rad etilardi.
        """
        self.assertGreaterEqual(DEFAULT_DEADLINE_MS, 2 * DEFAULT_REQUEST_TIMEOUT_MS)

    @override_settings(GEMINI_REQUEST_TIMEOUT_MS=3_000)
    def test_a_too_small_setting_is_raised_to_the_minimum(self):
        """Sozlama xato bo'lsa ham Google rad etadigan qiymat yuborilmaydi."""
        from ai.providers.gemini import GeminiProvider

        provider = GeminiProvider()
        self.assertGreaterEqual(provider.effective_request_timeout_ms(), MIN_PROVIDER_DEADLINE_MS)
