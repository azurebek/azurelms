"""Iste'moldan chiqarilgan Gemini modellari sozlamada qolib ketmasin (A8).

2026-08-19 da jonli xato: `gemini-2.5-flash-lite` ga chaqiruv
`404 NOT_FOUND — no longer available to new users` qaytardi va AI javob
bermay qoldi. U allowlistdagi yagona fallback edi.

Diqqatga sazovor tafsilot: Google'ning `models.list` endpointi bu modelni
hamon ro'yxatda ko'rsatadi — ya'ni ro'yxat hisobga xos ruxsatni bildirmaydi.
Faqat haqiqiy `generateContent` chaqiruvi 404 beradi. Shuning uchun
"ro'yxatda bor" degan tekshiruv yetarli emas; iste'moldan chiqqan modellar
qo'lda yozib boriladi.

Bu test ularning sozlamaga qaytib kirishini to'xtatadi. Google yana bir
modelni yopganda: nomni `RETIRED_MODELS` ga qo'shing — test qayerda hali
ishlatilayotganini ko'rsatib beradi.
"""

from django.conf import settings
from django.test import SimpleTestCase

from ai.providers.gemini import (
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_FREE_MODEL_ALLOWLIST,
    DEFAULT_PRIMARY_MODEL,
    RETIRED_MODELS,
)


class RetiredModelTests(SimpleTestCase):
    def test_the_retired_list_is_not_empty(self):
        """Bo'sh ro'yxat testni ma'nosiz qilib qo'yadi."""
        self.assertTrue(RETIRED_MODELS)

    def test_defaults_do_not_reference_a_retired_model(self):
        self.assertNotIn(DEFAULT_PRIMARY_MODEL, RETIRED_MODELS)
        self.assertNotIn(DEFAULT_FALLBACK_MODEL, RETIRED_MODELS)
        for model in DEFAULT_FREE_MODEL_ALLOWLIST:
            self.assertNotIn(model, RETIRED_MODELS, f"Allowlistda o'lik model: {model}")

    def test_runtime_settings_do_not_reference_a_retired_model(self):
        """Muhit fayli ham tekshiriladi — xato ko'pincha o'sha yerda qoladi."""
        self.assertNotIn(settings.GEMINI_PRIMARY_MODEL, RETIRED_MODELS)
        self.assertNotIn(settings.GEMINI_FALLBACK_MODEL, RETIRED_MODELS)
        for model in settings.GEMINI_FREE_MODEL_ALLOWLIST:
            self.assertNotIn(model, RETIRED_MODELS, f"Sozlamada o'lik model: {model}")

    def test_the_fallback_is_a_different_model_from_the_primary(self):
        """Fallback primary bilan bir xil bo'lsa, u umuman fallback emas."""
        self.assertNotEqual(DEFAULT_PRIMARY_MODEL, DEFAULT_FALLBACK_MODEL)

    def test_the_fallback_is_inside_the_allowlist(self):
        self.assertIn(DEFAULT_FALLBACK_MODEL, DEFAULT_FREE_MODEL_ALLOWLIST)
