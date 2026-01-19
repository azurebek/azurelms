from django.apps import AppConfig


class CommunicationConfig(AppConfig):
    name = 'communication'

    def ready(self):
        from . import signals  # noqa: F401
