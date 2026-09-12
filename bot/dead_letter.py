"""Terminal bo'lgan Telegram xabarlarini navbatga qaytarish (T6).

PR #101 dead-letter'ni **qurdi**: urinishlar tugagach yoki nosozlik
tuzalmaydigan turda bo'lsa qator `failed` bo'lib to'xtaydi. Ammo o'sha qator
bilan keyin nima qilish kerakligi qurilmagan edi — ya'ni xabar navbatda
abadiy o'lik yotardi va uni qaytarishning **yagona** yo'li SQL yozish edi.
`05-launch-ops.md` §2 buni ochiq qarz deb yozgan: «Outbox replay auditlanmagan,
chunki bunday amal hali mavjud emas.» Shu modul amalni beradi, auditni esa
yuza (`core/views.py`) yozadi.

**Nega ikki navbat bitta modulda.** `bot.TelegramOutbox` (DM) va
`classbook.TelegramGroupDelivery` (guruh) — ikki alohida model, ammo bu
amal uchun ular bir xil shaklda: `status`, `attempts`, `last_error`,
`failure_kind`, `next_attempt_at`, `claimed_at`, `claim_token`. Qayta urinish
siyosati allaqachon ikkisi uchun **bitta** (`bot/retry_policy.py`); replay
ham shunday bo'lishi kerak, aks holda bittasi tuzatilib ikkinchisi eskirib
qolardi.

**Nega qator lock qilinmaydi.** Idempotentlikni shartli `UPDATE` beradi:
`WHERE status = 'failed'`. Ikkita owner bir vaqtda bossa ham qator bir marta
qaytadi, ikkinchi chaqiruv nol qator o'zgartiradi va yuza hech narsa
yozmaydi. Bu naqsh outbox'ning o'z claim'ida ham shunday.
"""

from dataclasses import dataclass, field
from datetime import datetime

from django.db import transaction

from bot import retry_policy

QUEUE_DM = "dm"
QUEUE_GROUP = "group"
QUEUE_SLUGS = (QUEUE_DM, QUEUE_GROUP)

QUEUE_LABELS = {
    QUEUE_DM: "Shaxsiy xabar",
    QUEUE_GROUP: "Classbook guruh xabari",
}

#: `key` ajratuvchisi: `dm:42`. Forma qiymati sifatida ishlatiladi, ya'ni
#: brauzerdan keladi va **ishonchsiz** — `parse_keys()` uni tekshiradi.
KEY_SEPARATOR = ":"

#: Ro'yxatda va xato matnida ko'rsatiladigan xabar uzunligi.
PREVIEW_CHARS = 90


def queue_model(queue):
    """Navbat slug'idan model. Import lazy: `core` `classbook` ni bilmasin."""
    if queue == QUEUE_DM:
        from bot.models import TelegramOutbox

        return TelegramOutbox
    if queue == QUEUE_GROUP:
        from classbook.models import TelegramGroupDelivery

        return TelegramGroupDelivery
    raise ValueError(f"Noma'lum navbat: {queue!r}")


def dead_letter_queryset(queue):
    """Shu navbatdagi terminal qatorlar, yangisidan boshlab."""
    model = queue_model(queue)
    queryset = model.objects.filter(status=model.STATUS_FAILED)
    if queue == QUEUE_DM:
        queryset = queryset.select_related("notification", "notification__recipient")
    return queryset.order_by("-id")


@dataclass(frozen=True)
class DeadLetterRow:
    """Sahifa uchun o'qish-modeli — shablon modelga bevosita tegmaydi."""

    queue: str
    pk: int
    target: str
    label: str
    failure_kind: str
    attempts: int
    last_error: str
    created_at: datetime
    preview: str

    @property
    def key(self):
        return f"{self.queue}{KEY_SEPARATOR}{self.pk}"

    @property
    def queue_label(self):
        return QUEUE_LABELS.get(self.queue, self.queue)

    @property
    def is_permanent(self):
        """Qayta urinish hech qachon yordam bermaydigan tur.

        Foydalanuvchi botni bloklagan, chat o'chirilgan yoki bot guruhdan
        chiqarilgan. Bunday qatorni qaytarish faqat rate budjetini yeydi —
        shuning uchun yuza alohida tasdiq talab qiladi, ammo **taqiqlamaydi**:
        owner blokni yechgan bo'lishi mumkin va buni faqat u biladi.
        """
        return self.failure_kind == retry_policy.KIND_PERMANENT

    @property
    def short_label(self):
        return f"{self.queue_label} → {self.target}"


def _preview(text):
    value = " ".join((text or "").split())
    if len(value) <= PREVIEW_CHARS:
        return value
    return value[:PREVIEW_CHARS] + "…"


def _dm_row(item):
    notification = getattr(item, "notification", None)
    recipient = getattr(notification, "recipient", None)
    target = (
        getattr(recipient, "username", None)
        or getattr(recipient, "get_full_name", lambda: "")()
        or str(item.telegram_id)
    )
    return DeadLetterRow(
        queue=QUEUE_DM,
        pk=item.pk,
        target=str(target),
        label=getattr(notification, "category", "") or "—",
        failure_kind=item.failure_kind or "",
        attempts=item.attempts,
        last_error=item.last_error or "",
        created_at=item.created_at,
        preview=_preview(
            getattr(notification, "title", "") or getattr(notification, "message", "")
        ),
    )


def _group_row(item):
    return DeadLetterRow(
        queue=QUEUE_GROUP,
        pk=item.pk,
        target=str(item.chat_id),
        label=item.kind or "—",
        failure_kind=item.failure_kind or "",
        attempts=item.attempts,
        last_error=item.last_error or "",
        created_at=item.created_at,
        preview=_preview(item.text),
    )


ROW_BUILDERS = {QUEUE_DM: _dm_row, QUEUE_GROUP: _group_row}


def visible_rows(*, limit):
    """Ikki navbatdan eng yangi `limit` ta terminal qator.

    Chegara **owner sozlamasida** (`BotRuntimeSettings.dead_letter_replay_limit`):
    bu sahifa nechta qatorni bir vaqtda ko'rsatishi ham, bitta amal nechtasiga
    tegishi ham bitta qaror — «bir o'tirishda qanchasini qaytaraman». Ikki
    alohida knob bir xil narsani boshqarardi.
    """
    limit = max(1, int(limit))
    rows = []
    for queue in QUEUE_SLUGS:
        builder = ROW_BUILDERS[queue]
        rows.extend(builder(item) for item in dead_letter_queryset(queue)[:limit])
    rows.sort(key=lambda row: row.created_at, reverse=True)
    return rows[:limit]


def counts():
    """Chiroq va sahifa sarlavhasi uchun sonlar.

    `permanent` alohida: «hech qachon tuzalmaydi» bilan «o'zi tuzaladi»
    bir xil son ostida turmasligi kerak — Control Center outbox chirog'i ham
    shu ajratmani ishlatadi.
    """
    result = {"total": 0, "permanent": 0}
    for queue in QUEUE_SLUGS:
        queryset = dead_letter_queryset(queue)
        total = queryset.count()
        result[queue] = total
        result["total"] += total
        result["permanent"] += queryset.filter(
            failure_kind=retry_policy.KIND_PERMANENT
        ).count()
    return result


def parse_keys(values):
    """`["dm:1", "group:7", "axlat"]` → `{"dm": [1], "group": [7]}`.

    Brauzerdan kelgan qiymat — buzuq element butun amalni yiqitmasligi kerak,
    ammo jim ham o'tmasligi kerak: tanilmagan kalitlar alohida qaytariladi va
    yuza ularni «o'tkazib yuborildi» deb ko'rsatadi.
    """
    selection = {queue: [] for queue in QUEUE_SLUGS}
    unknown = []
    for value in values or ():
        text = str(value)
        queue, _, raw_pk = text.partition(KEY_SEPARATOR)
        if queue not in selection or not raw_pk.isdigit():
            unknown.append(text)
            continue
        pk = int(raw_pk)
        if pk not in selection[queue]:
            selection[queue].append(pk)
    return selection, unknown


@dataclass
class ReplayResult:
    """Amalning natijasi — yuza xabarni shundan yozadi."""

    replayed: dict = field(default_factory=dict)
    requested: dict = field(default_factory=dict)
    permanent: int = 0
    unknown: list = field(default_factory=list)

    @property
    def total_replayed(self):
        return sum(self.replayed.values())

    @property
    def total_requested(self):
        return sum(len(ids) for ids in self.requested.values())

    @property
    def skipped(self):
        """So'ralgan, ammo endi `failed` bo'lmagan qatorlar.

        Ikki holatda bo'ladi: boshqa owner allaqachon qaytargan, yoki qator
        sahifa ochilgandan keyin o'zi holat o'zgartirgan.
        """
        return max(0, self.total_requested - self.total_replayed)


def replay(*, keys, limit=None, now=None):
    """Terminal qatorlarni navbatga qaytaradi va natijani qaytaradi.

    **Auditni bu funksiya yozmaydi** — uni chaqiruvchi yuza yozadi, chunki
    aktor, sabab va request kontekstini faqat u biladi (`core/audit.py`
    yagona yozish nuqtasi). Shu sabab funksiya sof: berilgan kalitlar
    bo'yicha nimani o'zgartirganini aytadi.

    Nima tiklanadi va nega:

    * `attempts = 0` — aks holda qator birinchi transient xatoda darhol yana
      dead-letter bo'lardi, ya'ni replay amalda hech narsa bermasdi.
    * `next_attempt_at = None` — keyingi siklda darhol olinadi.
    * `failure_kind`/`last_error` tozalanadi, chunki `pending` qatorda eski
      nosozlik matni chalg'itadi. Ularning qiymati yo'qolmaydi: yuza ularni
      audit yozuvining `before` snapshotiga oladi.
    * `claimed_at`/`claim_token` tozalanadi — himoya uchun: terminal qatorda
      ular bo'sh bo'lishi kerak, lekin bo'sh emas deb ishonmaymiz.
    """
    from django.utils import timezone

    now = now or timezone.now()
    selection, unknown = parse_keys(keys)
    result = ReplayResult(requested=selection, unknown=unknown)

    if limit is not None:
        total = sum(len(ids) for ids in selection.values())
        if total > int(limit):
            raise ValueError(
                f"Bir amalda ko'pi bilan {limit} qator qaytarilishi mumkin "
                f"(so'ralgani: {total})."
            )

    with transaction.atomic():
        for queue, ids in selection.items():
            if not ids:
                result.replayed[queue] = 0
                continue
            model = queue_model(queue)
            failed = model.objects.filter(pk__in=ids, status=model.STATUS_FAILED)
            result.permanent += failed.filter(
                failure_kind=retry_policy.KIND_PERMANENT
            ).count()
            # Shartli `UPDATE` — idempotentlik va poyga himoyasi shu yerda.
            result.replayed[queue] = model.objects.filter(
                pk__in=ids, status=model.STATUS_FAILED
            ).update(
                status=model.STATUS_PENDING,
                attempts=0,
                last_error="",
                failure_kind="",
                next_attempt_at=None,
                claimed_at=None,
                claim_token="",
            )
    return result


def snapshot_for_audit(rows):
    """Audit `before` uchun — qaytarilgan qatorlarning diagnozi.

    Sabab: `last_error` va `failure_kind` replay paytida tozalanadi, ya'ni
    «nima uchun o'lgan edi» savolining javobi faqat shu yerda qoladi.
    `core/audit.py` qiymatni 300 belgida qirqadi, shuning uchun ro'yxat
    qisqa: sonlar aniq, id'lar esa eng yaxshi holatda.
    """
    kinds = {}
    for row in rows:
        name = row.failure_kind or "unknown"
        kinds[name] = kinds.get(name, 0) + 1
    return {
        "count": len(rows),
        "kinds": kinds,
        "keys": ", ".join(row.key for row in rows),
    }
