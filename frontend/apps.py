from django.apps import AppConfig


class FrontendConfig(AppConfig):
    name = 'frontend'

    def ready(self):
        # Route registri system check'i (PUB1.1a).
        from frontend import checks  # noqa: F401
