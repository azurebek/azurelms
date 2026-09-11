"""Operatsion sozlamalar formalari — auditlangan mutation yuzasi (T0).

Brend, landing va kill-switch muharrirlaridagi bir xil patterni: majburiy
sabab, majburiy tasdiqlash va o'zgarish bo'lmasa hech narsa yozmaydigan no-op
yo'l.

**Nega Django admin yetarli emas.** `AISettingsAdmin` faqat `updated_by` ni
yozadi — sabab, tasdiq va `SystemAuditEvent` yo'q (PR #103 dagi Codex review
aynan shuni ko'rsatdi). Ya'ni admin orqali tahrirlash operatsion o'zgarishni
**izsiz** qoldiradi. Shu sabab bu ikki sozlama admin'da faqat **o'qish uchun**
ko'rinadi, yozish esa shu yerdan — sabab va audit bilan — boradi.

**Nega label va birlik alohida.** Modeldagi `verbose_name` da birlik qavs ichida
turadi (`"Lease muddati (soniya)"`) — admin ro'yxati uchun to'g'ri, chunki u
yerda ustun sarlavhasidan boshqa joy yo'q. Formada esa birlik maydonning
**ichida** suffiks bo'lib chiqadi: shunda label qisqa qoladi va qiymat qaysi
o'lchovda ekani aynan yozayotgan joyda ko'rinadi. Shu sabab formalar o'z
labellarini va `UNITS` ini beradi.
"""

from django import forms

from bot.models import BotRuntimeSettings
from core.models import OperationalSettings
from users.models import ReminderSettings

REASON_HELP = (
    "Audit tarixida saqlanadi. Masalan: jonli darsda 429 ko'rindi, oraliq oshirildi."
)

#: Raqam maydonlari uchun umumiy widget sinflari. `brand-input` — backoffice'ning
#: mavjud input uslubi (ramka, radius, fokus halqasi); `--num` esa raqamga xos
#: qism: brauzerning o'z strelkalari o'chiriladi va kenglik cheklanadi, chunki
#: to'rt xonali son to'liq kenglikdagi maydonda tasodifiy ko'rinadi.
NUMBER_WIDGET_CLASS = "brand-input brand-input--num"


class _AuditedSettingsForm(forms.ModelForm):
    """Sabab + tasdiq majburiy bo'lgan umumiy asos."""

    #: `{maydon: birlik}` — maydon ichidagi suffiks uchun.
    UNITS: dict = {}

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

    #: Raqam bo'lmagan maydonlar — ularga `--num` uslubi (strelkasiz, tor,
    #: monospace) qo'yilmaydi, chunki ichida vergulli ro'yxat turadi.
    TEXT_FIELDS: tuple = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.Meta.fields:
            css = "brand-input" if name in self.TEXT_FIELDS else NUMBER_WIDGET_CLASS
            attrs = {"class": css}
            if name not in self.TEXT_FIELDS:
                attrs["inputmode"] = "numeric"
            self.fields[name].widget.attrs.update(attrs)

    def numeric_fields(self):
        """`(bound_field, birlik)` juftliklari — shablon shu ustidan yuradi.

        Django shablonida `{{ UNITS|get:field.name }}` qilib bo'lmaydi (dictdan
        o'zgaruvchi kalit bilan olish uchun filtr kerak), shuning uchun juftlik
        shu yerda tayyorlanadi.
        """
        for name in self.Meta.fields:
            yield self[name], self.UNITS.get(name, "")

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

    UNITS = {
        "dm_batch_size": "xabar",
        "group_batch_size": "xabar",
        "poll_interval_seconds": "soniya",
        "lease_seconds": "soniya",
        "send_interval_ms": "ms",
        "max_attempts": "urinish",
        "base_backoff_seconds": "soniya",
        "max_backoff_seconds": "soniya",
    }

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
        labels = {
            "dm_batch_size": "DM navbati: bir siklda",
            "group_batch_size": "Guruh navbati: bir siklda",
            "poll_interval_seconds": "Sikllar orasidagi kutish",
            "lease_seconds": "Lease muddati",
            "send_interval_ms": "Yuborishlar orasidagi oraliq",
            "max_attempts": "Maksimal urinish soni",
            "base_backoff_seconds": "Birinchi kutish",
            "max_backoff_seconds": "Maksimal kutish",
        }


class ReminderSettingsForm(_AuditedSettingsForm):
    """Eslatma vaqtlari va jim soatlar (T2)."""

    TEXT_FIELDS = ("payment_days_before",)

    UNITS = {
        "payment_days_before": "kun",
        "teacher_review_after_days": "kundan keyin",
        "teacher_review_hour": "soat",
        "quiet_hours_start": "soat",
        "quiet_hours_end": "soat",
    }

    class Meta:
        model = ReminderSettings
        fields = (
            "payment_days_before",
            "teacher_review_after_days",
            "teacher_review_hour",
            "quiet_hours_start",
            "quiet_hours_end",
        )
        labels = {
            "payment_days_before": "To'lov eslatmasi: necha kun oldin",
            "teacher_review_after_days": "O'qituvchi eslatmasi",
            "teacher_review_hour": "O'qituvchi eslatmasi: yuborish soati",
            "quiet_hours_start": "Jim soatlar: boshlanishi",
            "quiet_hours_end": "Jim soatlar: tugashi",
        }


class OperationalThresholdsForm(_AuditedSettingsForm):
    """Control Center chiroqlarining chegaralari."""

    UNITS = {
        "backup_stale_after_days": "kundan keyin",
        "queue_age_amber_minutes": "daqiqa",
        "queue_age_red_minutes": "daqiqa",
    }

    class Meta:
        model = OperationalSettings
        fields = (
            "backup_stale_after_days",
            "queue_age_amber_minutes",
            "queue_age_red_minutes",
        )
        labels = {
            "backup_stale_after_days": "Zaxira eskirgan hisoblanadi",
            "queue_age_amber_minutes": "Navbat yoshi: AMBER chegarasi",
            "queue_age_red_minutes": "Navbat yoshi: RED chegarasi",
        }
