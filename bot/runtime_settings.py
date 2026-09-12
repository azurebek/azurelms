"""Amaldagi yetkazish siyosati — sozlama va kod defaulti o'rtasidagi qatlam (T0).

Owner qarori (2026-09-11): operatsion qiymat kodda qotirib qo'yilmaydi. Ammo
sozlamani to'g'ridan-to'g'ri iste'mol qilish ikki yangi nosozlik turini ochadi,
va shu modul aynan ularni yopish uchun bor:

1. **Sozlama jadvali yo'q bo'lishi.** Yangi o'rnatishda, `migrate` dan oldin
   yoki `collectstatic` paytida qator ham, jadval ham bo'lmasligi mumkin.
   Worker shu sababli ko'tarilmasligi kerak: bu **ixtiyoriy moslash qatlami**,
   yetishmayotgan xizmat emas (farq uchun `core/runtime_gate.py` ga qarang —
   u aynan teskari holatda, Redis yo'q bo'lganda, ataylab to'xtatadi).
2. **Chegaradan chiqqan qiymat.** Maydonda validator bor, ammo u faqat forma
   orqali yozishda ishlaydi; `update()`, fixture yoki qo'lda SQL uni chetlab
   o'tadi. Owner jonli dars kunida sozlamani o'zgartiradi — bitta noto'g'ri
   raqam butun navbatni to'xtatib qo'ymasligi kerak. Shu sabab qiymat o'qishda
   ham qisiladi (clamp).

Natija — o'zgarmas (frozen) obyekt: bir sikl boshida bir marta o'qiladi va
pastga argument sifatida uzatiladi. Aks holda `send_interval_ms` har xabar
uchun bitta DB so'roviga aylanardi — ya'ni tezlikni boshqaradigan sozlamaning
o'zi sekinlashtirish manbasi bo'lib qolardi.
"""

from dataclasses import dataclass

#: Kod defaultlari — sozlama bo'lmaganda ham tizim ishlashi kerak.
DEFAULTS = {
    "dm_batch_size": 25,
    "group_batch_size": 10,
    "poll_interval_seconds": 15,
    "lease_seconds": 120,
    "send_interval_ms": 50,
    "max_attempts": 5,
    "base_backoff_seconds": 30,
    "max_backoff_seconds": 900,
    # Kuzatuv (T4) — bot jarayonining o'z o'lchov kadensi. Yetkazish bilan
    # bir qatorda turishining sababi: ikkisi ham **bot jarayonining**
    # sozlamasi va bir sikl boshida bitta DB o'qishi bilan olinadi.
    "metrics_flush_seconds": 30,
    "metrics_window_seconds": 300,
    # Dead-letter replay (T6) — bitta amalda nechta terminal qator navbatga
    # qaytariladi. Sahifa ham shu qadar qator ko'rsatadi: «bir o'tirishda
    # qanchasini qaytaraman» bitta qaror, ikki knob emas.
    "dead_letter_replay_limit": 200,
}

#: Xavfsiz oraliqlar — modeldagi validatorlar bilan bir xil. Ikki joyda
#: turishining sababi: validator formani, bu esa **o'qishni** qo'riqlaydi.
BOUNDS = {
    "dm_batch_size": (1, 200),
    "group_batch_size": (1, 200),
    "poll_interval_seconds": (1, 600),
    "lease_seconds": (10, 3600),
    "send_interval_ms": (0, 5000),
    "max_attempts": (1, 20),
    "base_backoff_seconds": (1, 3600),
    "max_backoff_seconds": (5, 86400),
    "metrics_flush_seconds": (5, 3600),
    "metrics_window_seconds": (30, 86400),
    "dead_letter_replay_limit": (1, 5000),
}


def clamp(name, value):
    """Qiymatni xavfsiz oraliqqa qisadi; o'qib bo'lmasa defaultni qaytaradi."""
    low, high = BOUNDS[name]
    try:
        number = int(value)
    except (TypeError, ValueError):
        return DEFAULTS[name]
    return max(low, min(number, high))


@dataclass(frozen=True)
class DeliveryPolicy:
    """Bir sikl uchun amaldagi qiymatlar."""

    dm_batch_size: int
    group_batch_size: int
    poll_interval_seconds: int
    lease_seconds: int
    send_interval_ms: int
    max_attempts: int
    base_backoff_seconds: int
    max_backoff_seconds: int
    metrics_flush_seconds: int
    metrics_window_seconds: int
    dead_letter_replay_limit: int

    @classmethod
    def defaults(cls):
        return cls(**DEFAULTS)

    @classmethod
    def from_row(cls, row):
        """Sozlama qatoridan (yoki `None` dan) amaldagi siyosatni quradi."""
        if row is None:
            return cls.defaults()
        values = {}
        for name in DEFAULTS:
            values[name] = clamp(name, getattr(row, name, None))
        # Maksimal kutish bazadan kichik bo'lib qolsa backoff o'sishdan
        # to'xtaydi. `clean()` buni formada ushlaydi, bu yerda esa formani
        # chetlab o'tgan yozuv uchun to'r.
        if values["max_backoff_seconds"] < values["base_backoff_seconds"]:
            values["max_backoff_seconds"] = values["base_backoff_seconds"]
        # O'lchov oynasi flush oralig'idan qisqa bo'lsa har yozuv o'zidan
        # oldingi siklni ko'rmaydi, ya'ni o'lchovlarning bir qismi hech
        # qachon hisobga olinmaydi. `clean()` buni formada ushlaydi; bu
        # yerda formani chetlab o'tgan yozuv uchun to'r.
        if values["metrics_window_seconds"] < values["metrics_flush_seconds"]:
            values["metrics_window_seconds"] = values["metrics_flush_seconds"]
        return cls(**values)

    @property
    def send_interval_seconds(self):
        """Millisekund admin uchun qulay, `asyncio.sleep` uchun soniya kerak."""
        return self.send_interval_ms / 1000.0


def current_policy():
    """Amaldagi siyosat — iste'molchilar uchun yagona kirish nuqtasi."""
    from bot.models import BotRuntimeSettings

    return BotRuntimeSettings.resolved()
