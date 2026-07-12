from django.apps import AppConfig


class BotConfig(AppConfig):
    name = 'bot'

    def ready(self):
        from bot import signals  # noqa: F401 — Notification→outbox signal
