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
}

BOUNDS = {
    "backup_stale_after_days": (1, 365),
    "queue_age_amber_minutes": (1, 1440),
    "queue_age_red_minutes": (2, 10080),
}


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

    @classmethod
    def defaults(cls):
        return cls(**DEFAULTS)

    @classmethod
    def from_row(cls, row):
        if row is None:
            return cls.defaults()
        values = {name: clamp(name, getattr(row, name, None)) for name in DEFAULTS}
        # RED chegarasi AMBER dan keyin bo'lishi kerak, aks holda navbat
        # ogohlantirish bosqichini butunlay o'tkazib yuboradi va owner
        # to'g'ridan-to'g'ri qizilni ko'radi. `clean()` buni formada ushlaydi;
        # bu yerda formani chetlab o'tgan yozuv uchun to'r.
        if values["queue_age_red_minutes"] <= values["queue_age_amber_minutes"]:
            values["queue_age_red_minutes"] = values["queue_age_amber_minutes"] + 1
        return cls(**values)


def current_thresholds():
    from core.models import OperationalSettings

    return OperationalSettings.resolved()
