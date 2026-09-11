"""Eslatma sozlamalari — amaldagi qiymatlar qatlami (T2).

`bot/runtime_settings.py` va `core/operational_settings.py` bilan bir xil
shakl va bir xil sabab (owner qarori: operatsion qiymat kodda qotirib
qo'yilmaydi): sozlama jadvali bo'lmasligi yoki chegaradan chiqqan qiymat
kunlik beat ishini yiqitmasligi kerak.

**Nega bu yerda alohida modul.** Eslatma vaqtlari ikki joyda o'qiladi —
bildirishnoma yaratuvchi servis va Telegram outbox (jim soatlar). Ikkalasi
bitta manbadan o'qishi kerak, aks holda "kechasi yubormaymiz" qoidasi bir
joyda bor, ikkinchisida yo'q bo'lib qolardi.
"""

from dataclasses import dataclass

#: `days_before` — to'lov muddatidan necha kun oldin eslatiladi. Ilgari bu
#: `users/notification_service.py` da `days_left in {3, 1, 0}` bo'lib qotib
#: turardi.
DEFAULT_PAYMENT_DAYS_BEFORE = "3,1,0"

DEFAULTS = {
    "payment_days_before": DEFAULT_PAYMENT_DAYS_BEFORE,
    "teacher_review_after_days": 2,
    "quiet_hours_start": 22,
    "quiet_hours_end": 8,
}

BOUNDS = {
    "teacher_review_after_days": (1, 60),
    "quiet_hours_start": (0, 23),
    "quiet_hours_end": (0, 23),
}

#: Bitta ro'yxatdagi eng katta kun. 90 kundan oldin eslatish ma'nosiz va
#: tasodifiy katta raqam har kuni ortiqcha so'rov yasardi.
MAX_DAYS_BEFORE = 90
#: Ro'yxat uzunligi chegarasi — har qiymat bitta xabar degani.
MAX_DAYS_BEFORE_COUNT = 6


def clamp(name, value):
    low, high = BOUNDS[name]
    try:
        number = int(value)
    except (TypeError, ValueError):
        return DEFAULTS[name]
    return max(low, min(number, high))


def parse_days_before(raw):
    """`"3,1,0"` → `[3, 1, 0]`. Buzuq kirishda kod defaultiga tushadi.

    Owner buni admin panelidan yozadi, ya'ni `"3, 1, 0"`, `"3;1"` yoki bo'sh
    satr kelishi mumkin. Bitta noto'g'ri belgi butun kunlik eslatma ishini
    to'xtatib qo'ymasligi kerak.
    """
    text = (raw or "").strip()
    if not text:
        return _parse_clean(DEFAULT_PAYMENT_DAYS_BEFORE)
    values = _parse_clean(text)
    return values or _parse_clean(DEFAULT_PAYMENT_DAYS_BEFORE)


def _parse_clean(text):
    seen = []
    for chunk in str(text).replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            number = int(chunk)
        except ValueError:
            continue
        if 0 <= number <= MAX_DAYS_BEFORE and number not in seen:
            seen.append(number)
    return sorted(seen, reverse=True)[:MAX_DAYS_BEFORE_COUNT]


@dataclass(frozen=True)
class ReminderPolicy:
    payment_days_before: tuple
    teacher_review_after_days: int
    quiet_hours_start: int
    quiet_hours_end: int

    @classmethod
    def defaults(cls):
        return cls(
            payment_days_before=tuple(_parse_clean(DEFAULT_PAYMENT_DAYS_BEFORE)),
            teacher_review_after_days=DEFAULTS["teacher_review_after_days"],
            quiet_hours_start=DEFAULTS["quiet_hours_start"],
            quiet_hours_end=DEFAULTS["quiet_hours_end"],
        )

    @classmethod
    def from_row(cls, row):
        if row is None:
            return cls.defaults()
        return cls(
            payment_days_before=tuple(
                parse_days_before(getattr(row, "payment_days_before", None))
            ),
            teacher_review_after_days=clamp(
                "teacher_review_after_days",
                getattr(row, "teacher_review_after_days", None),
            ),
            quiet_hours_start=clamp(
                "quiet_hours_start", getattr(row, "quiet_hours_start", None)
            ),
            quiet_hours_end=clamp(
                "quiet_hours_end", getattr(row, "quiet_hours_end", None)
            ),
        )

    @property
    def quiet_hours_enabled(self):
        """Boshlanish va tugash bir xil bo'lsa jim soatlar yo'q.

        `22 == 22` ni "butun sutka jim" deb talqin qilish xavfli bo'lardi:
        bitta tasodifiy qiymat butun eslatma kanalini abadiy to'xtatib
        qo'yardi. Shuning uchun teng qiymat "o'chirilgan" degani.
        """
        return self.quiet_hours_start != self.quiet_hours_end

    def is_quiet_at(self, moment):
        """`moment` (aware datetime, lokal zona) jim soatlar ichidami."""
        if not self.quiet_hours_enabled:
            return False
        hour = moment.hour
        start, end = self.quiet_hours_start, self.quiet_hours_end
        if start < end:
            return start <= hour < end
        # Yarim tundan o'tadigan oyna: 22:00 → 08:00.
        return hour >= start or hour < end


def current_policy():
    from users.models import ReminderSettings

    return ReminderSettings.resolved()
