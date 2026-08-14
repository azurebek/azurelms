from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from aicontrol.models import AISupplyEvent, AISupplyState
from aicontrol.supply import SupplyDenied, SupplyDuplicate
from ai.memory.semantic import SemanticMemoryScorer
from messenger.management.commands.reindex_ai_memory import Command as ReindexMemoryCommand
from messenger.models import AIMemoryFact
from messenger.rag import (
    _embedding_cache_key,
    _embedding_supply_request_key,
    embed_texts,
)


User = get_user_model()


@override_settings(GEMINI_API_KEY="test-key")
class EmbeddingSupplyGuardTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="embedding-supply-user",
            email="embedding-supply@example.com",
            password="testpass123",
        )

    def tearDown(self):
        cache.clear()

    @patch("messenger.rag.reconcile_supply")
    @patch("messenger.rag.reserve_supply")
    @patch("messenger.rag.genai.Client")
    def test_cache_hit_uses_no_supply_reservation_or_network(
        self,
        client_class,
        reserve_supply,
        reconcile_supply,
    ):
        cache.set(
            _embedding_cache_key("cached text", embedding_model="gemini-embedding-001"),
            [0.25, 0.75],
            timeout=60,
        )

        vectors = embed_texts(
            ["cached text"],
            call_type="rag_embedding",
            user=self.user,
            request_key="cached-query",
        )

        self.assertEqual(vectors, [[0.25, 0.75]])
        reserve_supply.assert_not_called()
        reconcile_supply.assert_not_called()
        client_class.assert_not_called()

    @patch("messenger.rag.genai.Client")
    def test_cache_miss_is_reserved_once_and_charges_conservative_tokens(self, client_class):
        client_class.return_value.models.embed_content.return_value = SimpleNamespace(
            embeddings=[
                SimpleNamespace(values=[1.0, 0.0]),
                SimpleNamespace(values=[0.0, 1.0]),
            ]
        )

        vectors = embed_texts(
            ["birinchi", "ikkinchi"],
            call_type="memory_embedding",
            user=self.user,
            request_key="memory-query",
        )

        self.assertEqual(vectors, [[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(client_class.return_value.models.embed_content.call_count, 1)
        event = AISupplyEvent.objects.get()
        self.assertEqual(event.call_type, AISupplyEvent.CALL_MEMORY_EMBEDDING)
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.status, AISupplyEvent.STATUS_SUCCEEDED)
        self.assertEqual(event.actual_requests, 1)
        self.assertEqual(event.accounted_requests, 1)
        self.assertGreater(event.reserved_tokens, 0)
        self.assertEqual(event.accounted_tokens, event.reserved_tokens)
        self.assertEqual(event.total_tokens, 0)

        # Cache yo'qolsa ham shu kun/model/dimension/input fingerprinti remote
        # requestni takrorlamaydi.
        cache.clear()
        with self.assertRaises(SupplyDuplicate):
            embed_texts(
                ["birinchi", "ikkinchi"],
                call_type="memory_embedding",
                user=self.user,
                request_key="memory-query",
            )
        self.assertEqual(client_class.return_value.models.embed_content.call_count, 1)

    @patch("messenger.rag.genai.Client")
    def test_quota_error_makes_exactly_one_sdk_call_and_reconciles_failure(self, client_class):
        client_class.return_value.models.embed_content.side_effect = RuntimeError(
            "429 RESOURCE_EXHAUSTED: quota exceeded"
        )

        with self.assertRaisesRegex(RuntimeError, "RESOURCE_EXHAUSTED"):
            embed_texts(
                ["quota text"],
                call_type="rag_embedding",
                user=self.user,
                request_key="quota-query",
            )

        self.assertEqual(client_class.return_value.models.embed_content.call_count, 1)
        self.assertEqual(client_class.call_args.kwargs["http_options"].retry_options.attempts, 1)
        event = AISupplyEvent.objects.get()
        self.assertEqual(event.status, AISupplyEvent.STATUS_FAILED)
        self.assertEqual(event.error_kind, "quota")
        self.assertEqual(event.actual_requests, 1)
        self.assertEqual(event.accounted_tokens, event.reserved_tokens)
        self.assertIsNotNone(AISupplyState.load().circuit_open_until)

    @patch("messenger.rag.reserve_supply", side_effect=SupplyDenied("budget tugadi"))
    @patch("messenger.rag.genai.Client")
    def test_supply_denied_stops_before_client_or_network(self, client_class, _reserve_supply):
        with self.assertRaises(SupplyDenied):
            embed_texts(
                ["denied text"],
                call_type="rag_embedding",
                user=self.user,
                request_key="denied-query",
            )

        client_class.assert_not_called()

    @override_settings(GEMINI_EMBEDDING_MAX_INPUTS=1)
    @patch("messenger.rag.reserve_supply")
    @patch("messenger.rag.genai.Client")
    def test_oversized_batch_is_rejected_before_reservation_or_network(
        self,
        client_class,
        reserve_supply,
    ):
        with self.assertRaisesRegex(ValueError, "input cap"):
            embed_texts(["bir", "ikki"], request_key="oversized-batch")

        reserve_supply.assert_not_called()
        client_class.assert_not_called()

    @override_settings(GEMINI_API_KEY=None)
    @patch("messenger.rag.genai.Client")
    def test_local_client_setup_failure_reconciles_zero_network_attempts(self, client_class):
        with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
            embed_texts(
                ["no key"],
                call_type="memory_embedding",
                user=self.user,
                request_key="no-key",
            )

        client_class.assert_not_called()
        event = AISupplyEvent.objects.get()
        self.assertEqual(event.status, AISupplyEvent.STATUS_FAILED)
        self.assertEqual(event.actual_requests, 0)
        self.assertEqual(event.accounted_requests, 0)
        self.assertEqual(event.accounted_tokens, 0)

    def test_daily_fingerprint_changes_with_model_dimension_or_input(self):
        base = _embedding_supply_request_key(
            request_key="query",
            call_type="rag_embedding",
            embedding_model="model-a",
            embedding_dim=768,
            input_hash="hash-a",
        )

        self.assertEqual(
            base,
            _embedding_supply_request_key(
                request_key="query",
                call_type="rag_embedding",
                embedding_model="model-a",
                embedding_dim=768,
                input_hash="hash-a",
            ),
        )
        for model, dimension, input_hash in (
            ("model-b", 768, "hash-a"),
            ("model-a", 3072, "hash-a"),
            ("model-a", 768, "hash-b"),
        ):
            with self.subTest(model=model, dimension=dimension, input_hash=input_hash):
                self.assertNotEqual(
                    base,
                    _embedding_supply_request_key(
                        request_key="query",
                        call_type="rag_embedding",
                        embedding_model=model,
                        embedding_dim=dimension,
                        input_hash=input_hash,
                    ),
                )


class EmbeddingCallerDegradationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="embedding-degrade-user",
            email="embedding-degrade@example.com",
            password="testpass123",
        )
        self.fact = AIMemoryFact.objects.create(
            user=self.user,
            category=AIMemoryFact.CATEGORY_WEAK_TOPIC,
            key="weak:python",
            value="Python funksiyalarida qiynaladi",
            fingerprint="embedding-degrade-fact",
            embedding=[1.0, 0.0],
            embedding_model="gemini-embedding-001",
            embedding_dim=2,
        )

    @patch("ai.memory.semantic.embed_texts", side_effect=SupplyDenied("budget tugadi"))
    def test_memory_query_supply_denial_keeps_lexical_scoring(self, _embed_texts):
        scored = SemanticMemoryScorer().score(
            facts=[self.fact],
            question="Python funksiyalarida yordam kerak",
        )

        self.assertEqual(scored[0].fact, self.fact)
        self.assertGreater(scored[0].lexical_overlap, 0)
        self.assertIsNone(scored[0].vector_score)

    @patch(
        "messenger.management.commands.reindex_ai_memory.embed_texts",
        side_effect=SupplyDenied("budget tugadi"),
    )
    def test_memory_reindex_supply_denial_leaves_vector_unchanged(self, _embed_texts):
        self.fact.embedding = []
        self.fact.embedding_model = ""
        self.fact.embedding_dim = 0
        self.fact.save(update_fields=["embedding", "embedding_model", "embedding_dim"])

        updated = ReindexMemoryCommand()._embed_batch(
            [self.fact],
            embedding_model="gemini-embedding-001",
        )

        self.assertEqual(updated, 0)
        self.fact.refresh_from_db()
        self.assertEqual(self.fact.embedding, [])

    @patch(
        "messenger.management.commands.reindex_ai_memory.embed_texts",
        return_value=[[0.5, 0.25]],
    )
    def test_memory_reindex_uses_reindex_call_type(self, embed_texts_mock):
        updated = ReindexMemoryCommand()._embed_batch(
            [self.fact],
            embedding_model="gemini-embedding-001",
        )

        self.assertEqual(updated, 1)
        self.assertEqual(embed_texts_mock.call_args.kwargs["call_type"], "reindex")
        self.assertIsNone(embed_texts_mock.call_args.kwargs["user"])
