"""Amaldagi Control Center chegaralari — sozlama va kod defaulti qatlami (T0).

`bot/runtime_settings.py` bilan bir xil sabab va bir xil shakl: sozlama jadvali
bo'lmasligi yoki chegaradan chiqqan qiymat probe'ni yiqitmasligi kerak. Bu
yerda talab yana ham qat'iyroq — probe'lar `/readyz` yo'lida chaqiriladi, ya'ni
sozlama o'qishdagi xato butun instance'ni trafikdan chiqarib yuborardi.
"""

from dataclasses import dataclass

DEFAULTS = {
    "backup_stale_after_days": 7,
    "queue_age_amber_minutes": 15,
    "queue_age_red_minutes": 60,
    # Bot dispatcher chiroqlari (T4).
    "dispatcher_stale_after_seconds": 120,
    "dispatcher_dead_after_seconds": 600,
    "handler_latency_amber_ms": 1500,
    "handler_latency_red_ms": 4000,
    "handler_error_amber_percent": 5,
    "handler_error_red_percent": 20,
}

BOUNDS = {
    "backup_stale_after_days": (1, 365),
    "queue_age_amber_minutes": (1, 1440),
    "queue_age_red_minutes": (2, 10080),
    "dispatcher_stale_after_seconds": (30, 86400),
    "dispatcher_dead_after_seconds": (60, 604800),
    "handler_latency_amber_ms": (50, 60000),
    "handler_latency_red_ms": (100, 120000),
    "handler_error_amber_percent": (1, 100),
    "handler_error_red_percent": (1, 100),
}

#: AMBER/RED juftliklari — RED har doim kattaroq bo'lishi kerak.
#:
#: Ro'yxat **bitta joyda** turadi va ikki iste'molchisi bor:
#: `core/models.py::OperationalSettings.clean()` (forma orqali yozishni
#: rad etadi) va pastdagi `from_row()` (formani chetlab o'tgan yozuvni
#: o'qishda tuzatadi). Nusxalansa yangi juftlik bittasiga yozilib,
#: ikkinchisida unutilishi oson bo'lardi.
ORDERED_PAIRS = (
    ("queue_age_red_minutes", "queue_age_amber_minutes"),
    ("dispatcher_dead_after_seconds", "dispatcher_stale_after_seconds"),
    ("handler_latency_red_ms", "handler_latency_amber_ms"),
    ("handler_error_red_percent", "handler_error_amber_percent"),
)


def clamp(name, value):
    low, high = BOUNDS[name]
    try:
        number = int(value)
    except (TypeError, ValueError):
        return DEFAULTS[name]
    return max(low, min(number, high))


@dataclass(frozen=True)
class Thresholds:
    backup_stale_after_days: int
    queue_age_amber_minutes: int
    queue_age_red_minutes: int
    dispatcher_stale_after_seconds: int
    dispatcher_dead_after_seconds: int
    handler_latency_amber_ms: int
    handler_latency_red_ms: int
    handler_error_amber_percent: int
    handler_error_red_percent: int

    @classmethod
    def defaults(cls):
        return cls(**DEFAULTS)

    @classmethod
    def from_row(cls, row):
        if row is None:
            return cls.defaults()
        values = {name: clamp(name, getattr(row, name, None)) for name in DEFAULTS}
        # RED chegarasi AMBER dan keyin bo'lishi kerak, aks holda chiroq
        # ogohlantirish bosqichini butunlay o'tkazib yuboradi va owner
        # to'g'ridan-to'g'ri qizilni ko'radi. `clean()` buni formada ushlaydi;
        # bu yerda formani chetlab o'tgan yozuv uchun to'r.
        for red_name, amber_name in ORDERED_PAIRS:
            if values[red_name] <= values[amber_name]:
                values[red_name] = values[amber_name] + 1
        return cls(**values)


def current_thresholds():
    from core.models import OperationalSettings

    return OperationalSettings.resolved()
