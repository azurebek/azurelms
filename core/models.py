"""Core domen modellari.

Hozircha bitta model bor: namuna kontent seederining proveniyensiyasi.

**Nega kerak bo'ldi.** `core/content_seed.py` avval yozuvni sarlavha yoki
slug bo'yicha tanirdi. Ko'rsatiladigan identifikator esa egalik dalili emas:
agar bazada aynan shu nomli **haqiqiy** kurs bo'lsa, `get_or_create` uni
namuna deb qabul qilardi va `--wipe` uni modul, dars, imtihon va topshiriqlari
bilan birga o'chirib yuborardi. Bu PR #53 dagi Codex reviewining topilmasi.

**Nega fayl emas, jadval.** Iz aynan o'zi tavsiflayotgan baza bilan birga
yashashi kerak. Baza nusxalansa yoki boshqa mashinaga ko'chirilsa, iz ham
u bilan ketadi; yonidagi JSON fayl esa qolib ketardi va `--wipe` boshqa
bazadagi yozuvlarni o'chirishga urinardi.
"""

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.operational_settings import ORDERED_PAIRS


class SeededRecord(models.Model):
    """Namuna kontent seeder **o'zi yaratgan** yozuvning izi.

    Faqat ildiz obyektlar belgilanadi (kurs, guruh, maqola, teg). Modul,
    dars, test va vazifa kursga cascade bilan bog'langan, ya'ni ular alohida
    iz talab qilmaydi.
    """

    #: `"courses.Course"` ko'rinishidagi model yorlig'i. `ContentType` emas,
    #: chunki bu yerda generic relation kerak emas va yorliq migratsiyalar
    #: orasida barqarorroq o'qiladi.
    model_label = models.CharField(max_length=100)
    object_id = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Seeder yaratgan yozuv"
        verbose_name_plural = "Seeder yaratgan yozuvlar"
        constraints = [
            models.UniqueConstraint(
                fields=["model_label", "object_id"],
                name="core_seededrecord_unique_target",
            ),
        ]
        indexes = [models.Index(fields=["model_label"])]

    def __str__(self):
        return f"{self.model_label}#{self.object_id}"


class OperationalSettings(models.Model):
    """Control Center chegaralari — owner sozlamasi (T0).

    Owner qarori (2026-09-11): operatsion qiymat kodda qotirib qo'yilmaydi.
    Bu uchta chegara ilgari `core/control_center/snapshot.py` da Python
    konstantasi edi, ya'ni "zaxira qachon eskirgan hisoblanadi" yoki "navbat
    qancha kutganda qizil bo'ladi" degan **operatsion** qarorni o'zgartirish
    uchun deploy kerak bo'lardi.

    Bu qiymatlar nosozlikni **o'lchamaydi**, faqat uni qachon ko'rsatishni
    belgilaydi. Shu sabab ular xavfsiz sozlama: noto'g'ri qiymat chiroq rangini
    o'zgartiradi, tizim xatti-harakatini emas.
    """

    singleton = models.BooleanField(default=True, unique=True, editable=False)

    backup_stale_after_days = models.PositiveIntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        verbose_name="Zaxira necha kundan keyin eskirgan hisoblanadi",
        help_text="Shundan oshsa Control Center zaxira chirog'ini AMBER qiladi.",
    )
    queue_age_amber_minutes = models.PositiveIntegerField(
        default=15,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
        verbose_name="Navbat yoshi: AMBER chegarasi (daqiqa)",
        help_text="Eng qadimgi kutayotgan xabar shundan oshsa e'tibor talab qiladi.",
    )
    queue_age_red_minutes = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(2), MaxValueValidator(10080)],
        verbose_name="Navbat yoshi: RED chegarasi (daqiqa)",
        help_text="Eng qadimgi kutayotgan xabar shundan oshsa nosozlik deb qaraladi.",
    )

    # --- Bot dispatcher chiroqlari (T4) ---------------------------------- #
    # Bu oltita chegara `telegram_dispatcher` chirog'ini boshqaradi. Ular
    # `queue_age_*` bilan bir modelda, chunki ikkisi ham **ko'rsatish**
    # qarori: nosozlikni o'lchamaydi, faqat uni qachon ko'rsatishni belgilaydi.
    dispatcher_stale_after_seconds = models.PositiveIntegerField(
        default=120,
        validators=[MinValueValidator(30), MaxValueValidator(86400)],
        verbose_name="Bot belgisi: AMBER chegarasi (soniya)",
        help_text=(
            "Bot shuncha vaqt o'zini belgilamasa e'tibor talab qiladi. "
            "Qiymat yozuv oralig'idan ikki baravar past bo'lsa, probe "
            "avtomatik oshiradi — aks holda chiroq doim sariq bo'lib turardi."
        ),
    )
    dispatcher_dead_after_seconds = models.PositiveIntegerField(
        default=600,
        validators=[MinValueValidator(60), MaxValueValidator(604800)],
        verbose_name="Bot belgisi: RED chegarasi (soniya)",
        help_text="Shundan oshsa bot sekin emas, to'xtagan deb qaraladi.",
    )
    handler_latency_amber_ms = models.PositiveIntegerField(
        default=1500,
        validators=[MinValueValidator(50), MaxValueValidator(60000)],
        verbose_name="Javob vaqti: AMBER chegarasi (ms)",
        help_text="Oynadagi p95 shundan oshsa bot sekinlashgan hisoblanadi.",
    )
    handler_latency_red_ms = models.PositiveIntegerField(
        default=4000,
        validators=[MinValueValidator(100), MaxValueValidator(120000)],
        verbose_name="Javob vaqti: RED chegarasi (ms)",
        help_text="Telegram tugma bosilganda bu qadar kutish uzilish bilan teng.",
    )
    handler_error_amber_percent = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name="Xato foizi: AMBER chegarasi (%)",
        help_text=(
            "Oynadagi xato ulushi. Kamida 20 ta update bo'lmaguncha rang "
            "o'zgarmaydi — bittadan bitta xato 100% bo'lib ko'rinmasligi uchun."
        ),
    )
    handler_error_red_percent = models.PositiveIntegerField(
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name="Xato foizi: RED chegarasi (%)",
        help_text="Oynadagi xato ulushi shundan oshsa nosozlik deb qaraladi.",
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Kim o'zgartirdi",
    )

    class Meta:
        verbose_name = "Operatsion chegaralar"
        verbose_name_plural = "Operatsion chegaralar"

    def __str__(self):
        return "Operatsion chegaralar"

    def clean(self):
        """Har AMBER/RED juftligi to'g'ri tartibda bo'lishi kerak.

        Teskari bo'lsa chiroq AMBER bosqichini butunlay o'tkazib yuboradi va
        owner ogohlantirishni ko'rmasdan to'g'ridan-to'g'ri qizilni oladi.
        Juftliklar ro'yxati `core/operational_settings.py::ORDERED_PAIRS` da —
        **bitta joyda**. U yerdan `Thresholds.from_row()` ham o'qiydi, ya'ni
        forma qo'riqlaydigan shart va o'qishda qo'llanadigan to'r bir xil
        ro'yxatdan keladi. Ikki nusxa bo'lsa yangi juftlik qo'shilganda
        bittasiga yozib, ikkinchisini unutish oson bo'lardi.
        """
        super().clean()
        errors = {}
        for red_name, amber_name in ORDERED_PAIRS:
            red = getattr(self, red_name, None)
            amber = getattr(self, amber_name, None)
            if red is None or amber is None:
                continue
            if red <= amber:
                errors[red_name] = (
                    "RED chegarasi AMBER chegarasidan katta bo'lishi kerak."
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def resolved(cls):
        """Amaldagi chegaralar — hech qachon xato tashlamaydi.

        Probe'lar readiness yo'lida ham chaqiriladi; sozlama jadvali sababli
        `/readyz` yiqilishi mumkin emas.
        """
        from core.operational_settings import Thresholds

        try:
            row = cls.objects.filter(pk=1).first()
        except Exception:  # noqa: BLE001 — jadval hali yo'q yoki DB yetib bormadi
            row = None
        return Thresholds.from_row(row)
