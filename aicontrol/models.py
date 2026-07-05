"""AI boshqaruv markazi modellari.

Admin uchun AI token-iqtisodiyotini bir joydan boshqarish: global default limitlar,
tarif (Plan) bo'yicha limitlar, foydalanuvchi override/reset holati, va bayram/event
munosabati bilan ommaviy/guruh/tarif reset-bonuslari (audit bilan).

Limit birligi — TOKEN (prompt+javob). Oyna: rolling 5 soat + haftalik.
Xom usage messenger.AIResponseRun.total_tokens da yotadi; bu app faqat siyosat
va reset markerlarini boshqaradi.
"""
from django.conf import settings
from django.db import models


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
