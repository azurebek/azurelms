from django.apps import AppConfig


class CohortsConfig(AppConfig):
    name = "cohorts"

    def ready(self):
        import cohorts.signals  # noqa: F401
