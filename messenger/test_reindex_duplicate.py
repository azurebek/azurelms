"""Takroriy reindex — nosozlik emas, himoyaning ishlagani (K11 auditi).

`02-yol-xarita.md` dagi `K11` riski "lesson reindex batch'i uchun lease/claim
yo'q, duplicate work oynasi qolishi mumkin" deydi. Kodni o'lchab ko'rilganda
holat **teskari** chiqdi.

`embed_texts` supply kalitini `request_key + call_type + model + dimension +
input_hash` dan **kunlik** fingerprint sifatida quradi, `reserve_supply` esa
o'sha kalit ledgerda bo'lsa `SupplyDuplicate` bilan rad etadi — tarmoqqa
umuman chiqmasdan. Ya'ni ikkita parallel reindex bir xil darsni ikki marta
embed **qilmaydi**; kvota ikki marta sarflanmaydi.

Haqiqiy nuqson boshqa joyda edi: `reindex_lessons` bu rad etishni umumiy
`except Exception` bilan ushlab, darsni `failed_lessons` deb sanardi va
traceback yozardi. Operator uchun bu "dars indekslanmadi" degani; u qayta
uraveradi, qayta urinish esa kun oxirigacha **hech qachon** o'tmaydi.

Takrorlash sharti oddiy: `--force` bilan ikkinchi marta yugurtirish va
oradagi kesh yo'qolishi. Lokal profil `LocMem` keshdan foydalanadi, ya'ni
kesh **server har qayta ishga tushganda** tozalanadi.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from courses.models import Course, Lesson, Module
from messenger.models import LessonRAGChunk
from messenger.rag import reindex_lessons


@override_settings(GEMINI_API_KEY="test-key")
class ReindexDuplicateTests(TestCase):
    def setUp(self):
        cache.clear()
        course = Course.objects.create(title="Kurs", description="d", level="beginner")
        module = Module.objects.create(course=course, title="M1", order=1)
        self.lesson = Lesson.objects.create(
            module=module,
            title="Dars 1",
            content="<p>" + " ".join(["so'z"] * 60) + "</p>",
            order=1,
        )

    def _run(self, client_class):
        client_class.return_value.models.embed_content.return_value = SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.1] * 768)]
        )
        return reindex_lessons(force=True)

    @patch("messenger.rag.genai.Client")
    def test_the_first_run_indexes(self, client_class):
        stats = self._run(client_class)

        self.assertEqual(stats["indexed_lessons"], 1)
        self.assertEqual(stats["failed_lessons"], 0)
        self.assertEqual(stats["skipped_duplicate"], 0)

    @patch("messenger.rag.genai.Client")
    def test_a_repeat_run_is_counted_as_duplicate_not_failure(self, client_class):
        """Asosiy da'vo: ilgari bu yerda `failed_lessons=1` chiqardi."""
        self._run(client_class)
        cache.clear()  # server qayta ishga tushdi

        stats = self._run(client_class)

        self.assertEqual(stats["skipped_duplicate"], 1)
        self.assertEqual(stats["failed_lessons"], 0)
        self.assertEqual(stats["indexed_lessons"], 0)

    @patch("messenger.rag.genai.Client")
    def test_the_repeat_run_makes_no_second_network_call(self, client_class):
        """Dublikat himoyasi tarmoqdan **oldin** ishlaydi."""
        self._run(client_class)
        cache.clear()

        self._run(client_class)

        self.assertEqual(client_class.return_value.models.embed_content.call_count, 1)

    @patch("messenger.rag.genai.Client")
    def test_the_indexed_chunks_survive_the_repeat_run(self, client_class):
        """O'tkazib yuborish mavjud indeksni buzmasligi kerak."""
        self._run(client_class)
        chunk_ids = set(
            LessonRAGChunk.objects.filter(lesson=self.lesson).values_list("id", flat=True)
        )
        self.assertTrue(chunk_ids)
        cache.clear()

        self._run(client_class)

        self.assertEqual(
            set(
                LessonRAGChunk.objects.filter(lesson=self.lesson).values_list(
                    "id", flat=True
                )
            ),
            chunk_ids,
        )

    @patch("messenger.rag.genai.Client")
    def test_a_real_failure_is_still_reported_as_a_failure(self, client_class):
        """Dublikatni ajratish haqiqiy nosozlikni yashirmasligi kerak."""
        client_class.return_value.models.embed_content.side_effect = RuntimeError(
            "provider yiqildi"
        )

        stats = reindex_lessons(force=True)

        self.assertEqual(stats["failed_lessons"], 1)
        self.assertEqual(stats["skipped_duplicate"], 0)
