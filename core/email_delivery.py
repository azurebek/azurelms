"""Email yetkazish qobiliyati — parol tiklash shunga tayanadi (PUB1.0f).

Bitta qaror uch joyda ishlatiladi: Control Center email chirog'i, release
oldidan `manage.py check --deploy` va parol tiklash sahifasi. Ular alohida
hisoblasa biri "yuborilyapti" deb, ikkinchisi "yo'q" deb turishi mumkin edi.

Non-local profilda "jim" backend (console va boshqalar) avariya hisoblanadi:
xat yuborilgandek ko'rinadi, hech kimga bormaydi, console esa tiklash
havolasini — ya'ni tokenni — konteyner logiga yozadi.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

# Xatni egasiga yetkazmaydigan backend modullari.
SILENT_BACKENDS = frozenset({"console", "dummy", "locmem", "filebased"})

RESET_DELIVERY_FAILED_ACTION = "auth.password_reset.delivery_failed"
# Control Center shu oynadagi yetkazilmagan xatlarni ko'rsatadi.
FAILURE_WINDOW = timedelta(hours=24)

RESET_UNAVAILABLE_MESSAGE = (
    "Parolni email orqali tiklash hozircha ishlamayapti. Telegram orqali kirgan "
    "bo‘lsangiz, “Telegram orqali kirish” tugmasidan foydalaning yoki "
    "administrator bilan bog‘laning."
)


def backend_kind(path=None):
    """`django.core.mail.backends.console.EmailBackend` → `console`."""
    path = str(path if path is not None else getattr(settings, "EMAIL_BACKEND", ""))
    # Klass nomi hamma backendda `EmailBackend` — farq modul qismida.
    parts = path.split(".")
    return parts[-2] if len(parts) >= 2 else path


def is_silent_backend(path=None):
    return backend_kind(path) in SILENT_BACKENDS


def reset_delivery_available():
    """Parol tiklash xati haqiqatan yuborila oladimi.

    Lokal profilda console ataylab ruxsat etilgan: xat terminalga chiqadi.
    """
    return bool(settings.IS_LOCAL) or not is_silent_backend()


def record_reset_delivery_failure(user, exc):
    """Operator uchun dalil: kim (id), qaysi xato turi. Email va token yozilmaydi."""
    from aicontrol.models import SystemAuditEvent
    from core.audit import record_audit_event

    # `request` ataylab berilmaydi: so'rovchi anonim, uning IP va user-agent'i
    # bu dalilga kerak emas.
    record_audit_event(
        action=RESET_DELIVERY_FAILED_ACTION,
        outcome=SystemAuditEvent.OUTCOME_FAILURE,
        target=user,
        target_label=f"Foydalanuvchi #{user.pk}",
        error=exc.__class__.__name__,
    )


def recent_reset_delivery_failures(now=None):
    from aicontrol.models import SystemAuditEvent

    since = (now or timezone.now()) - FAILURE_WINDOW
    return SystemAuditEvent.objects.filter(action=RESET_DELIVERY_FAILED_ACTION, created_at__gte=since).count()
