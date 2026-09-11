"""Operatsion sozlamalar formalari — auditlangan mutation yuzasi (T0).

Brend, landing va kill-switch muharrirlaridagi bir xil patterni: majburiy
sabab, majburiy tasdiqlash va o'zgarish bo'lmasa hech narsa yozmaydigan no-op
yo'l.

**Nega Django admin yetarli emas.** `AISettingsAdmin` faqat `updated_by` ni
yozadi — sabab, tasdiq va `SystemAuditEvent` yo'q (PR #103 dagi Codex review
aynan shuni ko'rsatdi). Ya'ni admin orqali tahrirlash operatsion o'zgarishni
**izsiz** qoldiradi. Shu sabab bu ikki sozlama admin'da faqat **o'qish uchun**
ko'rinadi, yozish esa shu yerdan — sabab va audit bilan — boradi.
"""

from django import forms

from bot.models import BotRuntimeSettings
from core.models import OperationalSettings

REASON_HELP = (
    "Audit tarixida saqlanadi. Masalan: jonli darsda 429 ko'rindi, oraliq oshirildi."
)


class _AuditedSettingsForm(forms.ModelForm):
    """Sabab + tasdiq majburiy bo'lgan umumiy asos."""

    change_reason = forms.CharField(
        label="O'zgartirish sababi",
        max_length=240,
        help_text=REASON_HELP,
        widget=forms.Textarea(attrs={"rows": 3, "class": "brand-input"}),
    )
    confirm_change = forms.BooleanField(
        label="O'zgartirishni tasdiqlayman",
        required=True,
    )

    @property
    def settings_changed(self):
        """Sozlama maydonlaridan birortasi o'zgardimi.

        `change_reason` va `confirm_change` hisobga olinmaydi: ular har POST'da
        "o'zgargan" bo'lib ko'rinadi, ya'ni ularni qo'shib hisoblash no-op
        yo'lini butunlay ishlamas qilardi.
        """
        tracked = set(self.Meta.fields)
        return bool(tracked.intersection(self.changed_data))

    def changed_values(self):
        """`(before, after)` — audit yozuvi uchun, faqat o'zgargan maydonlar."""
        before, after = {}, {}
        for name in self.Meta.fields:
            if name not in self.changed_data:
                continue
            before[name] = self.initial.get(name)
            after[name] = self.cleaned_data.get(name)
        return before, after


class BotDeliverySettingsForm(_AuditedSettingsForm):
    """Telegram yetkazish tezligi va qayta urinish siyosati."""

    class Meta:
        model = BotRuntimeSettings
        fields = (
            "dm_batch_size",
            "group_batch_size",
            "poll_interval_seconds",
            "lease_seconds",
            "send_interval_ms",
            "max_attempts",
            "base_backoff_seconds",
            "max_backoff_seconds",
        )


class OperationalThresholdsForm(_AuditedSettingsForm):
    """Control Center chiroqlarining chegaralari."""

    class Meta:
        model = OperationalSettings
        fields = (
            "backup_stale_after_days",
            "queue_age_amber_minutes",
            "queue_age_red_minutes",
        )
