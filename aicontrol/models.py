"""AI boshqaruv markazi modellari.

Admin uchun AI token-iqtisodiyotini bir joydan boshqarish: global default limitlar,
tarif (Plan) bo'yicha limitlar, foydalanuvchi override/reset holati, va bayram/event
munosabati bilan ommaviy/guruh/tarif reset-bonuslari (audit bilan).

Limit birligi — TOKEN (prompt+javob). Oyna: rolling 5 soat + haftalik.
Xom usage messenger.AIResponseRun.total_tokens da yotadi; bu app faqat siyosat
va reset markerlarini boshqaradi.
"""
import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AISettings(models.Model):
    """Global AI sozlamalari (singleton) — default limitlar va bosh rubilnik."""

    singleton = models.BooleanField(default=True, unique=True, editable=False)

    enforcement_enabled = models.BooleanField(
        default=True,
        verbose_name="Limitlar yoqilganmi",
        help_text="O'chirilsa hech kim bloklanmaydi (chiqarish/sinov rejimi).",
    )
    exempt_staff = models.BooleanField(
        default=True,
        verbose_name="Xodimlar limitdan ozod",
        help_text="Staff/superuser AI limitiga tushmasin.",
    )
    default_5h_token_limit = models.PositiveIntegerField(
        default=100_000, verbose_name="Default 5 soatlik token limiti"
    )
    default_weekly_token_limit = models.PositiveIntegerField(
        default=1_000_000, verbose_name="Default haftalik token limiti"
    )
    default_model = models.CharField(
        max_length=80, blank=True, default="", verbose_name="Default AI modeli",
        help_text="Bo'sh bo'lsa settings.py qiymati ishlatiladi.",
    )
    default_effort = models.CharField(
        max_length=20, blank=True, default="", verbose_name="Default web-search effort"
    )
    ai_remote_calls_enabled = models.BooleanField(
        default=True,
        verbose_name="AI remote chaqiruvlari yoqilganmi (kill switch)",
        help_text=(
            "O'chirilsa hech qanday remote AI chaqirig'i ketmaydi — chat, "
            "grounding, SmartForm, bot demo va embedding ham. Budjet "
            "sozlamalaridan mustaqil: bu shoshilinch to'xtatish tugmasi."
        ),
    )
    supply_enforcement_enabled = models.BooleanField(
        default=True,
        verbose_name="Global AI supply budget yoqilganmi",
        help_text="Provider chaqirig'idan oldin project-wide request/token budgetni tekshiradi.",
    )
    supply_daily_request_limit = models.PositiveIntegerField(
        default=100,
        verbose_name="Kunlik global provider request limiti",
        help_text="Google quota raqami emas; owner belgilaydigan ichki hard budget.",
    )
    supply_minute_request_limit = models.PositiveIntegerField(
        default=10,
        verbose_name="Bir daqiqalik global provider request limiti",
        help_text="Burst/fan-outni cheklaydigan owner ichki hard budgeti.",
    )
    supply_daily_token_limit = models.PositiveIntegerField(
        default=250_000,
        verbose_name="Kunlik global token limiti",
        help_text="Usage kelmasa konservativ reservation estimate hisoblanadi.",
    )
    supply_default_reservation_tokens = models.PositiveIntegerField(
        default=4_000,
        verbose_name="Usage noma'lum call uchun token reservi",
    )
    supply_cooldown_seconds = models.PositiveIntegerField(
        default=3_600,
        verbose_name="429/quota circuit cooldown (soniya)",
    )
    guest_demo_enabled = models.BooleanField(
        default=False,
        verbose_name="Telegram guest AI demo yoqilganmi",
        help_text="Default o'chiq: guest call ham global Gemini supply budgetini sarflaydi.",
    )
    heavy_search_enabled = models.BooleanField(
        default=False,
        verbose_name="Heavy web-search rejimi yoqilganmi",
        help_text="Free-tier rejimida default o'chiq.",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name="Kim yangiladi",
    )

    class Meta:
        verbose_name = "AI sozlamasi"
        verbose_name_plural = "AI sozlamalari"

    def __str__(self):
        return "AI global sozlamalari"

    def save(self, *args, **kwargs):
        self.singleton = True  # doim bitta qator
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(singleton=True)
        return obj


class AISupplyState(models.Model):
    """Global provider circuit holati (singleton)."""

    singleton = models.BooleanField(default=True, unique=True, editable=False)
    circuit_open_until = models.DateTimeField(null=True, blank=True)
    circuit_reason = models.CharField(max_length=120, blank=True, default="")
    opened_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI supply holati"
        verbose_name_plural = "AI supply holati"

    def save(self, *args, **kwargs):
        self.singleton = True
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(singleton=True)
        return obj

    def __str__(self):
        return "AI global supply circuit"


class AISupplyEvent(models.Model):
    """Har logical remote AI call uchun reservation va reconciliation ledgeri."""

    CALL_CHAT = "chat"
    CALL_SEARCH = "web_search"
    CALL_SMART_FORM = "smart_form"
    CALL_BOT_GUEST = "bot_guest"
    CALL_RAG_EMBEDDING = "rag_embedding"
    CALL_MEMORY_EMBEDDING = "memory_embedding"
    CALL_REINDEX = "reindex"
    CALL_OTHER = "other"
    CALL_TYPE_CHOICES = (
        (CALL_CHAT, "Chat"),
        (CALL_SEARCH, "Web grounding/search"),
        (CALL_SMART_FORM, "Smart Form extractor"),
        (CALL_BOT_GUEST, "Telegram guest demo"),
        (CALL_RAG_EMBEDDING, "RAG embedding"),
        (CALL_MEMORY_EMBEDDING, "Memory embedding"),
        (CALL_REINDEX, "Reindex embedding"),
        (CALL_OTHER, "Boshqa"),
    )

    STATUS_RESERVED = "reserved"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_RESERVED, "Reserved"),
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REJECTED, "Rejected"),
    )

    request_key = models.CharField(max_length=180, unique=True)
    bucket_date = models.DateField(db_index=True)
    call_type = models.CharField(max_length=24, choices=CALL_TYPE_CHOICES, default=CALL_OTHER)
    provider = models.CharField(max_length=32, default="gemini")
    model_name = models.CharField(max_length=120, blank=True, default="")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_supply_events",
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_RESERVED)
    reserved_requests = models.PositiveIntegerField(default=1)
    reserved_tokens = models.PositiveIntegerField(default=0)
    actual_requests = models.PositiveIntegerField(default=0)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    accounted_requests = models.PositiveIntegerField(default=0)
    accounted_tokens = models.PositiveIntegerField(default=0)
    error_kind = models.CharField(max_length=40, blank=True, default="")
    error_message = models.CharField(max_length=500, blank=True, default="")
    metadata = models.JSONField(blank=True, default=dict)
    reserved_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI supply hodisasi"
        verbose_name_plural = "AI supply hodisalari"
        indexes = [
            models.Index(fields=["bucket_date", "status"]),
            models.Index(fields=["call_type", "bucket_date"]),
            models.Index(fields=["provider", "bucket_date"]),
        ]

    def __str__(self):
        return f"{self.call_type} · {self.status} · {self.request_key}"


class AIPlanPolicy(models.Model):
    """Tarif (Plan) bo'yicha token limiti — global defaultni almashtiradi."""

    plan = models.OneToOneField(
        "subscriptions.Plan", on_delete=models.CASCADE, related_name="ai_policy",
        verbose_name="Tarif",
    )
    token_limit_5h = models.PositiveIntegerField(verbose_name="5 soatlik token limiti")
    token_limit_weekly = models.PositiveIntegerField(verbose_name="Haftalik token limiti")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI tarif siyosati"
        verbose_name_plural = "AI tarif siyosatlari"
        ordering = ["plan__order", "plan__price"]

    def __str__(self):
        return f"{self.plan.name}: 5h={self.token_limit_5h}, hafta={self.token_limit_weekly}"


class AIUserAllowance(models.Model):
    """Foydalanuvchi usage holati: shaxsiy override, reset markerlari, bonus, blok."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_allowance"
    )
    override_5h_token_limit = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Shaxsiy 5 soatlik limit",
        help_text="Bo'sh bo'lsa tarif/global default ishlatiladi.",
    )
    override_weekly_token_limit = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Shaxsiy haftalik limit"
    )
    # reset markeridan OLDINGI usage hisoblanmaydi — admin reset shu markerni now qiladi
    reset_5h_at = models.DateTimeField(null=True, blank=True, verbose_name="5 soatlik reset vaqti")
    reset_weekly_at = models.DateTimeField(null=True, blank=True, verbose_name="Haftalik reset vaqti")
    # bonus — joriy oynaga qo'shimcha token allowance (bayram sovg'asi)
    bonus_5h_tokens = models.PositiveIntegerField(default=0, verbose_name="5 soatlik bonus token")
    bonus_weekly_tokens = models.PositiveIntegerField(default=0, verbose_name="Haftalik bonus token")
    is_blocked = models.BooleanField(default=False, verbose_name="AI bloklangan")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "AI foydalanuvchi ruxsati"
        verbose_name_plural = "AI foydalanuvchi ruxsatlari"

    def __str__(self):
        return f"AI allowance: {self.user}"


class AIUsageResetEvent(models.Model):
    """Admin reset/bonus amali — audit va qo'llash yozuvi (bayram/event)."""

    SCOPE_ALL = "all"
    SCOPE_COHORT = "cohort"
    SCOPE_PLAN = "plan"
    SCOPE_CHOICES = (
        (SCOPE_ALL, "Hammaga (ommaviy)"),
        (SCOPE_COHORT, "Guruh (kohort)"),
        (SCOPE_PLAN, "Tarif"),
    )

    KIND_RESET = "reset"
    KIND_BONUS = "bonus"
    KIND_CHOICES = (
        (KIND_RESET, "Reset (usage'ni nolga)"),
        (KIND_BONUS, "Bonus (qo'shimcha token)"),
    )

    WINDOW_5H = "5h"
    WINDOW_WEEKLY = "weekly"
    WINDOW_BOTH = "both"
    WINDOW_CHOICES = (
        (WINDOW_5H, "5 soatlik"),
        (WINDOW_WEEKLY, "Haftalik"),
        (WINDOW_BOTH, "Ikkalasi"),
    )

    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, verbose_name="Ko'lam")
    cohort = models.ForeignKey(
        "cohorts.Cohort", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ai_reset_events", verbose_name="Guruh (scope=cohort)",
    )
    plan = models.ForeignKey(
        "subscriptions.Plan", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ai_reset_events", verbose_name="Tarif (scope=plan)",
    )
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=KIND_RESET, verbose_name="Turi")
    window = models.CharField(max_length=10, choices=WINDOW_CHOICES, default=WINDOW_BOTH, verbose_name="Oyna")
    bonus_tokens = models.PositiveIntegerField(default=0, verbose_name="Bonus token (kind=bonus)")
    reason = models.CharField(max_length=200, blank=True, default="", verbose_name="Sabab (bayram/event)")
    affected_count = models.PositiveIntegerField(default=0, verbose_name="Ta'sirlangan foydalanuvchilar")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ai_reset_events", verbose_name="Kim berdi",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "AI reset/bonus amali"
        verbose_name_plural = "AI reset/bonus amallari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.get_scope_display()} · {self.created_at:%d.%m.%Y}"


class SystemAuditEvent(models.Model):
    """Append-only operatsion audit ledgeri (A2).

    Nega Django'ning `LogEntry` si yetarli emas: u admin uchun mo'ljallangan,
    o'chirilishi va tahrirlanishi mumkin, `source`/`outcome`/`before-after`
    kabi operatsion maydonlari yo'q va u faqat admin obyektlariga bog'lanadi.
    Control plane uchun `05-launch-ops.md` §3 aniq talab qo'ygan: kim, qayerdan,
    nima qildi, qanday sabab bilan, natija nima va qaysi release'da.

    **Append-only** — yozuv yaratilgandan keyin o'zgartirib yoki o'chirib
    bo'lmaydi. Bu model darajasida majburlanadi (`save`/`delete` bloklaydi),
    admin darajasida emas: admin faqat oxirgi to'siq.
    """

    SOURCE_WEB = "web"
    SOURCE_BOT = "bot"
    SOURCE_WORKER = "worker"
    SOURCE_CLI = "cli"
    SOURCE_RELEASE = "release"
    SOURCE_CHOICES = (
        (SOURCE_WEB, "Web"),
        (SOURCE_BOT, "Telegram bot"),
        (SOURCE_WORKER, "Worker"),
        (SOURCE_CLI, "CLI"),
        (SOURCE_RELEASE, "Release"),
    )

    OUTCOME_SUCCESS = "success"
    OUTCOME_FAILURE = "failure"
    OUTCOME_DENIED = "denied"
    OUTCOME_CHOICES = (
        (OUTCOME_SUCCESS, "Muvaffaqiyatli"),
        (OUTCOME_FAILURE, "Xato"),
        (OUTCOME_DENIED, "Rad etildi"),
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(
        max_length=80, db_index=True,
        help_text="Nuqta bilan ajratilgan kod, masalan `ai.kill_switch.disable`.",
    )
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_WEB)
    outcome = models.CharField(
        max_length=10, choices=OUTCOME_CHOICES, default=OUTCOME_SUCCESS, db_index=True
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="audit_events", verbose_name="Kim",
    )
    # Actor o'chirilsa ham kim qilgani ma'lum qolishi kerak — audit yozuvi
    # foydalanuvchi hayotidan uzoqroq yashaydi.
    actor_label = models.CharField(max_length=150, blank=True, default="")

    target_type = models.CharField(max_length=80, blank=True, default="")
    target_id = models.CharField(max_length=80, blank=True, default="")
    target_label = models.CharField(max_length=200, blank=True, default="")

    reason = models.CharField(max_length=240, blank=True, default="")
    before = models.JSONField(blank=True, default=dict)
    after = models.JSONField(blank=True, default=dict)
    error = models.CharField(max_length=300, blank=True, default="")

    request_id = models.CharField(max_length=64, blank=True, default="")
    idempotency_key = models.CharField(max_length=120, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True, default="")
    release_sha = models.CharField(max_length=40, blank=True, default="")

    class Meta:
        verbose_name = "Tizim audit yozuvi"
        verbose_name_plural = "Tizim audit yozuvlari"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self):
        who = self.actor_label or "tizim"
        return f"{self.created_at:%d.%m.%Y %H:%M} · {self.action} · {who}"

    @property
    def display_message(self):
        """Sahifadagi tarix uchun bitta o'qiladigan qator."""
        parts = [self.action]
        if self.outcome != self.OUTCOME_SUCCESS:
            parts.append(f"[{self.get_outcome_display()}]")
        if self.target_label:
            parts.append(f"→ {self.target_label}")
        if self.reason:
            parts.append(f"Sabab: {self.reason}")
        return " ".join(parts)

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError(
                "Audit yozuvi append-only: mavjud yozuvni o'zgartirib bo'lmaydi."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit yozuvi append-only: o'chirib bo'lmaydi.")


class AIModelPrice(models.Model):
    """Provider narxining sanali snapshot'i (A2).

    Narx **qattiq yozilmaydi**: u hisobga, mintaqaga va vaqtga bog'liq. Kodga
    yozilgan raqam aynan o'lik model va noto'g'ri deadline kabi jim eskirardi —
    shuning uchun uni owner manba ko'rsatib kiritadi.

    Yozuvlar **append-only**: narx o'zgarsa yangi `effective_from` bilan yangi
    qator qo'shiladi, eskisi tahrirlanmaydi. Shu sabab tarixiy xarajat keyingi
    narx bilan qayta yozilmaydi.
    """

    provider = models.CharField(max_length=32, default="gemini")
    model_name = models.CharField(max_length=80)
    #: Million token uchun narx — provayderlar odatda shu birlikda e'lon qiladi.
    input_per_million = models.DecimalField(max_digits=12, decimal_places=6)
    output_per_million = models.DecimalField(max_digits=12, decimal_places=6)
    currency = models.CharField(max_length=8, default="USD")
    effective_from = models.DateField()
    #: Qaysi manbadan olingani — raqamni keyin tekshirish mumkin bo'lsin.
    note = models.CharField(max_length=200, blank=True, default="")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-effective_from", "model_name")
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "model_name", "effective_from"],
                name="unique_price_per_model_and_date",
            )
        ]
        verbose_name = "AI model narxi"
        verbose_name_plural = "AI model narxlari"

    def __str__(self):
        return f"{self.model_name} @ {self.effective_from}"


class FeatureFlag(models.Model):
    """Registrda e'lon qilingan flagning o'zgartirilgan qiymati.

    Bu yerda faqat **override** saqlanadi: qatori yo'q flag `core/flags.py` da
    e'lon qilingan default bilan ishlaydi. Shuning uchun `slug` ga `choices`
    berilmagan — variantlar registrdan olinadi va yangi flag migratsiya talab
    qilmaydi.
    """

    slug = models.CharField(max_length=64, unique=True)
    enabled = models.BooleanField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("slug",)
        verbose_name = "Feature flag"
        verbose_name_plural = "Feature flaglar"

    def __str__(self):
        return f"{self.slug}={'on' if self.enabled else 'off'}"


class WorkerHeartbeat(models.Model):
    """Fon jarayonining "men tirikman" yozuvi (A2).

    Nega kerak: Control Center Telegram outbox'ning sog'lig'ini navbat
    yoshidan taxmin qilardi — navbatda eskirgan xabar bo'lsa AMBER/RED. Bu
    ko'r nuqta qoldiradi: **navbat bo'sh bo'lsa o'lik worker ham yashil
    ko'rinadi**. Worker tunda o'lib qolsa, ertalab birinchi bildirishnoma
    15 daqiqa turmaguncha hech kim bilmaydi.

    Jarayon har siklda o'zini shu yerda belgilaydi; holat esa navbatdan emas,
    shu yozuvdan o'qiladi.
    """

    #: Tirik deb hisoblash oynasi. Outbox sikli 15 soniyada bir yuguradi,
    #: shuning uchun bir necha o'tkazib yuborilgan sikl hali xavotir emas.
    ALIVE_WINDOW = datetime.timedelta(minutes=2)
    #: Bundan oshsa shunchaki sekin emas — jarayon o'lgan.
    DEAD_WINDOW = datetime.timedelta(minutes=15)

    name = models.CharField(max_length=64, unique=True, verbose_name="Worker nomi")
    last_seen_at = models.DateTimeField(verbose_name="Oxirgi belgi")
    detail = models.JSONField(default=dict, blank=True, verbose_name="Qo'shimcha")

    class Meta:
        verbose_name = "Worker heartbeat"
        verbose_name_plural = "Worker heartbeatlar"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} @ {self.last_seen_at:%Y-%m-%d %H:%M:%S}"

    @classmethod
    def record(cls, name, *, detail=None, now=None):
        """Workerni tirik deb belgilaydi."""
        beat, _created = cls.objects.update_or_create(
            name=name,
            defaults={"last_seen_at": now or timezone.now(), "detail": detail or {}},
        )
        return beat

    def age(self, *, now=None):
        return (now or timezone.now()) - self.last_seen_at

    def is_alive(self, *, now=None):
        return self.age(now=now) <= self.ALIVE_WINDOW

    def is_dead(self, *, now=None):
        return self.age(now=now) > self.DEAD_WINDOW


class ReleaseRecord(models.Model):
    """Ishlab turgan release va uning bazaga mosligi (A2).

    `05-launch-ops.md` §4: har release uchun commit SHA, migratsiyalar, gate
    natijalari, deploy/rollback holati va owner qarori saqlanadi.

    Bugungi haqiqat ochiq yozilsin: **deploy quvuri yo'q** (A1b `HOLD`), ya'ni
    `gate_results` ni to'ldiradigan avtomatik yo'l ham hozircha yo'q — maydon
    bor va buyruq uni qabul qiladi, lekin uni yozadigan CI bosqichi yaratilishi
    kelajak ishi. Bugun haqiqiy qiymat beradigan qism — **migratsiya holati**.

    Nega aynan u: shu sessiyaning o'zida kill switch sahifasi
    `OperationalError` bilan yiqildi, chunki beshta migratsiya haqiqiy bazaga
    qo'llanmagan edi. Kod yangi, baza eski — va Control Center o'nta
    capability'ni yashil deb turardi.
    """

    DECISION_PENDING = "pending"
    DECISION_GO = "go"
    DECISION_HOLD = "hold"
    DECISION_ROLLED_BACK = "rolled_back"
    DECISION_CHOICES = (
        (DECISION_PENDING, "Qaror kutilmoqda"),
        (DECISION_GO, "Ochildi"),
        (DECISION_HOLD, "To'xtatildi"),
        (DECISION_ROLLED_BACK, "Qaytarildi"),
    )

    commit_sha = models.CharField(max_length=40, unique=True, verbose_name="Commit SHA")
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(verbose_name="Oxirgi ko'rilgan")
    migrations_applied = models.PositiveIntegerField(default=0, verbose_name="Qo'llangan migratsiya")
    unapplied_migrations = models.JSONField(default=list, blank=True, verbose_name="Qo'llanmagan migratsiya")
    gate_results = models.JSONField(default=dict, blank=True, verbose_name="Gate natijalari")
    decision = models.CharField(
        max_length=16,
        choices=DECISION_CHOICES,
        default=DECISION_PENDING,
        verbose_name="Owner qarori",
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_decisions",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True, default="", verbose_name="Izoh")

    class Meta:
        verbose_name = "Release yozuvi"
        verbose_name_plural = "Release yozuvlari"
        ordering = ["-last_seen_at"]

    def __str__(self):
        return f"{self.commit_sha[:12]} ({self.get_decision_display()})"

    @property
    def is_consistent(self):
        """Kod va baza bir-biriga mosmi."""
        return not self.unapplied_migrations
