from django.apps import AppConfig


class FrontendConfig(AppConfig):
    name = 'frontend'

    def ready(self):
        # Route registri system check'i (PUB1.1a).
        from frontend import checks  # noqa: F401

        # Yangi to'lov cheki voronkaning oxirgi qadami (PUB1.8a) — tranzaksiyadan keyin sanaladi.
        from django.db.models.signals import post_save

        from frontend import public_telemetry

        post_save.connect(public_telemetry.on_receipt_saved, sender="cohorts.PaymentReceipt",
                          dispatch_uid="public_telemetry_receipt_created")
