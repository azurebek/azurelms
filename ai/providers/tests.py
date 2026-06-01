from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase, override_settings

from ai.providers import get_chat_provider
from ai.providers.digitalocean import DigitalOceanProvider


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
        DIGITALOCEAN_INFERENCE_API_KEY="test-key",
        DIGITALOCEAN_INFERENCE_BASE_URL="https://inference.example/v1",
        DIGITALOCEAN_INFERENCE_MODEL="router:general",
    )
    def test_factory_selects_digitalocean_provider(self):
        self.assertIsInstance(get_chat_provider(), DigitalOceanProvider)
