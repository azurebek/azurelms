"""Release oldidan tekshiruv: parol tiklash xati yetib bora oladimi (PUB1.0f).

    python manage.py check --deploy

Faqat `--deploy` bilan ishlaydi: lokal `check` va testlar console backend
bilan davom etadi. Non-local profilda jim backend — release xatosi, chunki
parolni tiklash yopiq turadi (sahifa buni ochiq aytadi) va console tokenli
havolani logga yozardi.
"""

from django.conf import settings
from django.core.checks import Error, Tags, register

RESET_DELIVERY_CHECK_ID = "azurelms.E101"


@register(Tags.security, deploy=True)
def check_reset_delivery(app_configs, **kwargs):
    from core.email_delivery import backend_kind, reset_delivery_available

    if reset_delivery_available():
        return []
    return [
        Error(
            f"Email backend `{backend_kind()}` xatni hech kimga yubormaydi: parolni email orqali tiklash ishlamaydi.",
            hint="deploy/.env da EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD va DEFAULT_FROM_EMAIL ni to'ldiring.",
            id=RESET_DELIVERY_CHECK_ID,
        )
    ]
