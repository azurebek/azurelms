from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from django.core.exceptions import ImproperlyConfigured

from ai.providers import get_chat_provider
from ai.providers.digitalocean import DigitalOceanProvider
from ai.providers.gemini import GeminiProvider


class GeminiProviderTests(SimpleTestCase):
    settings = {
        "GEMINI_API_KEY": "test-key",
        "AI_FREE_TIER_MODE": True,
        "GEMINI_GROUNDING_ENABLED": False,
        "GEMINI_FREE_MODEL_ALLOWLIST": (
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
        ),
        "GEMINI_PRIMARY_MODEL": "gemini-3.1-flash-lite",
        "GEMINI_FALLBACK_MODEL": "gemini-3.5-flash-lite",
        "GEMINI_MAX_OUTPUT_TOKENS": 640,
        # Google 10s dan past deadline'ni `400` bilan rad etadi, shuning uchun
        # fixture ham haqiqiy qiymatlarni ishlatadi (ilgari 7s edi).
        "GEMINI_REQUEST_TIMEOUT_MS": 12_000,
        "GEMINI_DEADLINE_MS": 30_000,
    }

    @override_settings(**settings)
    def test_model_candidates_normalize_non_allowlisted_model(self):
        provider = GeminiProvider()

        for selected_model in ("gemini-3.1-pro-preview", "gemini-unknown-default"):
            with self.subTest(selected_model=selected_model):
                self.assertEqual(
                    provider._model_candidates(selected_model),
                    ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"],
                )

    @override_settings(GEMINI_API_KEY="")
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "ambient-google-key"}, clear=False)
    @patch("ai.providers.gemini.genai.Client")
    def test_missing_project_key_does_not_use_ambient_google_key(self, client_class):
        provider = GeminiProvider()

        with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
            provider.generate(prompt="Salom")

        client_class.assert_not_called()
        self.assertEqual(provider.last_attempt_count, 0)
        self.assertEqual(provider.last_error_kind, "missing_credential")

    @override_settings(**settings)
    @patch("ai.providers.gemini.genai_types.GoogleSearch")
    @patch("ai.providers.gemini.genai.Client")
    def test_free_tier_strips_grounding_tool_before_single_network_call(
        self,
        client_class,
        google_search,
    ):
        client_class.return_value.models.generate_content.return_value = SimpleNamespace(
            text="Jonli qidiruvsiz javob.",
            candidates=[],
            usage_metadata=None,
        )
        provider = GeminiProvider()

        result = provider.generate(prompt="Bugungi kursni qidir", enable_web_search=True)

        call = client_class.return_value.models.generate_content.call_args
        self.assertEqual(client_class.return_value.models.generate_content.call_count, 1)
        google_search.assert_not_called()
        self.assertFalse(getattr(call.kwargs["config"], "tools", None))
        self.assertEqual(result.model_name, "gemini-3.1-flash-lite")
        self.assertIsNone(result.web_search)
        self.assertTrue(provider.last_grounding_requested)
        self.assertTrue(provider.last_grounding_blocked)

    @override_settings(
        **(settings | {"AI_FREE_TIER_MODE": False, "GEMINI_GROUNDING_ENABLED": True})
    )
    @patch("ai.providers.gemini.genai.Client")
    def test_admitted_paid_mode_can_attach_grounding_tool(self, client_class):
        client_class.return_value.models.generate_content.return_value = SimpleNamespace(
            text="Grounded javob.",
            candidates=[],
            usage_metadata=None,
        )
        provider = GeminiProvider()

        provider.generate(prompt="Bugungi kursni qidir", enable_web_search=True)

        config = client_class.return_value.models.generate_content.call_args.kwargs["config"]
        self.assertTrue(getattr(config, "tools", None))
        self.assertTrue(provider.last_grounding_requested)
        self.assertFalse(provider.last_grounding_blocked)

    @override_settings(**settings)
    @patch("ai.providers.gemini.genai.Client")
    def test_429_fails_fast_after_one_network_attempt(self, client_class):
        client = client_class.return_value
        client.models.generate_content.side_effect = RuntimeError(
            "429 RESOURCE_EXHAUSTED: project quota exceeded"
        )
        provider = GeminiProvider()

        with self.assertRaisesRegex(RuntimeError, "quota/billing"):
            provider.generate(prompt="Salom")

        self.assertEqual(client.models.generate_content.call_count, 1)
        self.assertEqual(provider.last_attempt_count, 1)
        self.assertEqual(provider.last_error_kind, "quota")

    @override_settings(**settings)
    @patch("ai.providers.gemini.genai.Client")
    def test_quota_and_billing_errors_also_fail_fast(self, client_class):
        client = client_class.return_value
        for error_text in (
            "quota exceeded for requests per day",
            "billing account is disabled",
        ):
            with self.subTest(error_text=error_text):
                client.models.generate_content.reset_mock()
                client.models.generate_content.side_effect = RuntimeError(error_text)
                provider = GeminiProvider()

                with self.assertRaisesRegex(RuntimeError, "quota/billing"):
                    provider.generate(prompt="Salom")

                self.assertEqual(client.models.generate_content.call_count, 1)
                self.assertEqual(provider.last_attempt_count, 1)
                self.assertEqual(provider.last_error_kind, "quota")

    @override_settings(**settings)
    @patch("ai.providers.gemini.genai.Client")
    def test_non_quota_error_uses_only_one_fallback(self, client_class):
        response = SimpleNamespace(text="Javob tayyor.", usage_metadata=None)
        client = client_class.return_value
        client.models.generate_content.side_effect = [
            RuntimeError("temporary upstream 500"),
            response,
        ]
        provider = GeminiProvider()

        result = provider.generate(
            prompt="Salom",
            selected_model="gemini-3.1-pro-preview",
        )

        self.assertEqual(result.text, "Javob tayyor.")
        self.assertEqual(result.model_name, "gemini-3.5-flash-lite")
        self.assertEqual(client.models.generate_content.call_count, 2)
        self.assertEqual(
            [call.kwargs["model"] for call in client.models.generate_content.call_args_list],
            ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite"],
        )
        self.assertEqual(provider.last_attempt_count, 2)
        self.assertEqual(provider.last_error_kind, "provider_error")

    @override_settings(**settings)
    @patch("ai.providers.gemini.genai.Client")
    def test_not_found_message_containing_migrate_is_not_misclassified_as_rate_limit(
        self,
        client_class,
    ):
        response = SimpleNamespace(text="Fallback javob.", usage_metadata=None)
        client = client_class.return_value
        client.models.generate_content.side_effect = [
            RuntimeError("404 NOT_FOUND: migrate to a supported model"),
            response,
        ]
        provider = GeminiProvider()

        result = provider.generate(prompt="Salom")

        self.assertEqual(result.model_name, "gemini-3.5-flash-lite")
        self.assertEqual(client.models.generate_content.call_count, 2)
        self.assertEqual(provider.last_attempt_count, 2)
        self.assertEqual(provider.last_error_kind, "provider_error")

    @override_settings(**settings)
    @patch("ai.providers.gemini.genai.Client")
    def test_two_non_quota_failures_do_not_fan_out_further(self, client_class):
        client = client_class.return_value
        client.models.generate_content.side_effect = RuntimeError("temporary upstream 500")
        provider = GeminiProvider()

        with self.assertRaisesRegex(RuntimeError, "Barcha modellar"):
            provider.generate(prompt="Salom")

        self.assertEqual(client.models.generate_content.call_count, 2)
        self.assertEqual(provider.last_attempt_count, 2)
        self.assertEqual(provider.last_error_kind, "provider_error")

    @override_settings(**settings)
    @patch("ai.providers.gemini.genai.Client")
    def test_request_config_caps_output_timeout_and_sdk_retries(self, client_class):
        response = SimpleNamespace(text="Javob tayyor.", usage_metadata=None)
        client_class.return_value.models.generate_content.return_value = response
        provider = GeminiProvider()

        result = provider.generate(prompt="Salom")

        self.assertEqual(result.model_name, "gemini-3.1-flash-lite")
        client_http = client_class.call_args.kwargs["http_options"]
        self.assertEqual(client_http.timeout, 12_000)
        self.assertEqual(client_http.retry_options.attempts, 1)
        config = client_class.return_value.models.generate_content.call_args.kwargs["config"]
        self.assertEqual(config.max_output_tokens, 640)
        self.assertLessEqual(config.http_options.timeout, 12_000)
        self.assertEqual(config.http_options.retry_options.attempts, 1)
        self.assertEqual(provider.last_attempt_count, 1)
        self.assertIsNone(provider.last_error_kind)

    @override_settings(**settings)
    @override_settings(GEMINI_MAX_PROMPT_CHARS=90)
    @patch("ai.providers.gemini.genai.Client")
    def test_oversized_prompt_is_bounded_before_network(self, client_class):
        client_class.return_value.models.generate_content.return_value = SimpleNamespace(
            text="Javob tayyor.",
            usage_metadata=None,
        )
        provider = GeminiProvider()
        provider.generate(prompt="S" * 120 + "U" * 120)

        sent = client_class.return_value.models.generate_content.call_args.kwargs["contents"]
        self.assertLessEqual(len(sent), 90)
        self.assertIn("CONTEXT TRUNCATED", sent)
        self.assertTrue(sent.startswith("S"))
        self.assertTrue(sent.endswith("U" * 30))


class DigitalOceanProviderTests(SimpleTestCase):
    @override_settings(
        DIGITALOCEAN_INFERENCE_API_KEY="test-key",
        DIGITALOCEAN_INFERENCE_BASE_URL="https://inference.example/v1",
        DIGITALOCEAN_INFERENCE_MODEL="router:general",
    )
    def test_generate_uses_chat_completions_endpoint_and_configured_model(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": "Javob tayyor."}}],
        }
        session = SimpleNamespace(post=Mock(return_value=response))

        provider = DigitalOceanProvider(session=session)
        result = provider.generate(prompt="Salom", selected_model="gemini-2.5-flash")

        self.assertEqual(result.text, "Javob tayyor.")
        self.assertEqual(result.model_name, "router:general")
        call = session.post.call_args
        self.assertEqual(call.args[0], "https://inference.example/v1/chat/completions")
        self.assertEqual(call.kwargs["json"]["model"], "router:general")
        self.assertEqual(call.kwargs["json"]["messages"], [{"role": "user", "content": "Salom"}])
        self.assertEqual(call.kwargs["headers"]["Authorization"], "Bearer test-key")

    @override_settings(
        AI_CHAT_PROVIDER="digitalocean",
        AI_ALLOW_DIGITALOCEAN=False,
        DIGITALOCEAN_INFERENCE_API_KEY="test-key",
    )
    @patch("ai.providers.DigitalOceanProvider")
    def test_factory_blocks_digitalocean_without_explicit_admission(self, provider_class):
        with self.assertRaisesRegex(
            ImproperlyConfigured,
            "blocked by owner policy",
        ):
            get_chat_provider()

        provider_class.assert_not_called()

    @override_settings(
        AI_CHAT_PROVIDER="digitalocean",
        AI_ALLOW_DIGITALOCEAN=True,
        DIGITALOCEAN_INFERENCE_API_KEY="test-key",
        DIGITALOCEAN_INFERENCE_BASE_URL="https://inference.example/v1",
        DIGITALOCEAN_INFERENCE_MODEL="router:general",
    )
    def test_factory_selects_digitalocean_provider(self):
        self.assertIsInstance(get_chat_provider(), DigitalOceanProvider)

    @override_settings(AI_CHAT_PROVIDER="off")
    @patch("ai.providers.GeminiProvider")
    @patch("ai.providers.DigitalOceanProvider")
    def test_factory_rejects_unknown_provider_without_constructing_adapter(
        self,
        digitalocean_provider,
        gemini_provider,
    ):
        with self.assertRaisesRegex(ImproperlyConfigured, "Unknown AI_CHAT_PROVIDER"):
            get_chat_provider()

        gemini_provider.assert_not_called()
        digitalocean_provider.assert_not_called()
