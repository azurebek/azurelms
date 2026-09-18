"""Material kutubxonasi — ichki kontent ombori va uning darsga biriktirilishi.

Modul **o'quvchi uchun kutubxona emas**. U kurs mualliflari (staff) uchun ichki
ombor: material bir marta yuklanadi, tasniflanadi, keyin qidirib topiladi va
kerakli darslarga biriktiriladi. O'quvchi faqat darsga ochiq biriktirilgan
materialni ko'radi.

Ikki tushuncha ataylab ajratilgan:

* **`LibraryResource`** — asl fayl va uning metadatasi. Yagona nusxa.
* **`LessonMaterial`** — o'sha manbaning **bitta darsdagi** ko'rinishi: tartib,
  ko'rinuvchanlik, yuklab olish huquqi, auditoriya va ochilish vaqti.

Bitta manba o'nta darsga biriktirilsa ham fayl bitta bo'lib qoladi; darsga xos
sozlama esa biriktirma qatorida turadi.

**Nega `resource_type` va `file_kind` alohida.** Talab ro'yxati ikki xil narsani
aralashtirardi: maqsad (taqdimot, daftar, uy vazifasi) va fayl turi (PDF, audio,
rasm). Maqsadni odam tanlaydi; fayl turini esa qo'lda yozdirish xato manbasi —
u `core/upload_validation.py` dagi **baytlarni** o'qiydigan sniffer natijasidan
avtomatik to'ldiriladi. Ikkalasi bo'yicha ham filtr bor.

**Nega daraja alohida `level`.** `Course.LEVEL_CHOICES` uch bosqichli
(boshlang'ich/o'rta/mukammal) va kurs kartasi uchun yetarli; kutubxonada esa
"A1 + speaking + tanishuv" kabi qidiruv kerak, ya'ni CEFR darajasi.

**Nega fayl doim private.** Manbaning ochiqligi biriktirma sozlamasiga bog'liq
va u istalgan payt o'zgaradi. Fayl `MEDIA_ROOT` ichida tursa, biriktirmani
yopish faylni yopmasdi — public havola qolaverardi. Shuning uchun hamma narsa
`PRIVATE_MEDIA_ROOT` da va yagona kirish nuqtasi ruxsat tekshiradigan view
(`library/views.py`, `library/backoffice_views.py`).
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.private_storage import private_media_storage

#: Fayl hajmi chegarasining kod defaulti (MB). Sozlama jadvali bo'lmasa ham
#: yuklash ishlashi kerak, shuning uchun default kodda turadi.
DEFAULT_MAX_UPLOAD_MB = 50


class ResourceType(models.TextChoices):
    """Materialning **maqsadi** — uni odam tanlaydi."""

    LIVE_DECK = "live_deck", "Jonli dars taqdimoti"
    WORKBOOK = "workbook", "O'quvchi daftari"
    CHEAT_SHEET = "cheat_sheet", "Qisqa eslatma"
    SUMMARY = "summary", "Dars xulosasi"
    HOMEWORK = "homework", "Uyga vazifa"
    QUIZ = "quiz", "Test materiali"
    EXAM = "exam", "Imtihon materiali"
    TEACHER_NOTE = "teacher_note", "Ustoz uchun qo'llanma"
    MEDIA = "media", "Audio/video material"
    HANDOUT = "handout", "Tarqatma"
    OTHER = "other", "Boshqa"


class ResourceLanguage(models.TextChoices):
    UZ = "uz", "O'zbekcha"
    TR = "tr", "Turkcha"
    EN = "en", "Inglizcha"
    MIXED = "mixed", "Aralash"


class ResourceLevel(models.TextChoices):
    """CEFR darajasi. `ANY` — darajaga bog'liq bo'lmagan material."""

    ANY = "any", "Umumiy"
    A1 = "a1", "A1"
    A2 = "a2", "A2"
    B1 = "b1", "B1"
    B2 = "b2", "B2"
    C1 = "c1", "C1"
    C2 = "c2", "C2"


#: Sniffer qaytaradigan tur -> odam o'qiydigan yorliq. Kalitlar
#: `core/upload_validation.py` dagi turlar bilan bir xil bo'lishi kerak; u yerga
#: yangi tur qo'shilsa shu jadval ham to'ldiriladi.
FILE_KIND_LABELS = {
    "pdf": "PDF",
    "zip": "Office/ZIP",
    "text": "Matn",
    "png": "PNG rasm",
    "jpeg": "JPEG rasm",
    "webp": "WebP rasm",
    "gif": "GIF",
    "mp3": "MP3 audio",
    "wav": "WAV audio",
    "ogg": "OGG audio",
    "webm": "WebM",
    "mp4": "MP4",
}


class LibrarySettings(models.Model):
    """Kutubxonaning owner sozlamasi — hozircha bitta qiymat.

    Owner qoidasi (2026-09-11): operatsion chegara kodda qotirib qo'yilmaydi.
    Fayl hajmi aynan shunday qiymat — jonli dars kunida 60 MB lik taqdimotni
    yuklash uchun deploy kutib bo'lmaydi. Yozish yo'li auditlangan:
    `/backoffice/control/runtime-settings/` (sabab + tasdiq + `SystemAuditEvent`).

    Ruxsat etilgan **fayl turlari** bu yerda emas: u xavfsizlik allowlisti va
    `core/upload_validation.py` da qoladi.
    """

    singleton = models.BooleanField(default=True, unique=True, editable=False)

    max_upload_mb = models.PositiveIntegerField(
        default=DEFAULT_MAX_UPLOAD_MB,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        verbose_name="Material fayli uchun hajm chegarasi (MB)",
        help_text=(
            "Kutubxonaga yuklanadigan bitta faylning eng katta hajmi. "
            "Katta qiymat diskni tezroq to'ldiradi — zaxira hajmi ham oshadi."
        ),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_settings_updates",
        editable=False,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kutubxona sozlamasi"
        verbose_name_plural = "Kutubxona sozlamasi"

    def __str__(self):
        return "Kutubxona sozlamasi"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def max_upload_bytes(cls):
        """Amaldagi chegara baytda — jadval bo'lmasa kod defaultiga tushadi.

        Yuklash yo'li sozlama o'qishdagi xato sababli yiqilmasligi kerak:
        `OperationalSettings.resolved()` bilan bir xil sabab.
        """
        from django.db import DatabaseError

        try:
            value = cls.load().max_upload_mb
        except DatabaseError:
            value = DEFAULT_MAX_UPLOAD_MB
        return max(1, int(value or DEFAULT_MAX_UPLOAD_MB)) * 1024 * 1024


class LibraryTag(models.Model):
    """Erkin teg — qidiruv uchun normallashtirilgan.

    Teglar matn maydonida vergul bilan turmaydi: mingta material bo'lganda
    `icontains` bilan teg qidirish "a1" ni "a10" ichidan ham topib yuboradi va
    mavjud teglar ro'yxatini ko'rsatib bo'lmaydi.
    """

    name = models.CharField(max_length=60, unique=True, verbose_name="Teg")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Kutubxona tegi"
        verbose_name_plural = "Kutubxona teglari"

    def __str__(self):
        return self.name

    @staticmethod
    def normalize(raw):
        """`"A1, Speaking , a1"` -> `["a1", "speaking"]` (tartib saqlanadi)."""
        seen = []
        for chunk in (raw or "").replace(";", ",").split(","):
            name = " ".join(chunk.split()).lower()[:60]
            if name and name not in seen:
                seen.append(name)
        return seen


class LibraryResourceQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_archived=False)

    def archived(self):
        return self.filter(is_archived=True)

    def with_usage(self):
        return self.annotate(usage_count=models.Count("lesson_links", distinct=True))


class LibraryResource(models.Model):
    """Kutubxonadagi asl manba: bitta fayl + metadata."""

    title = models.CharField(max_length=200, db_index=True, verbose_name="Nomi")
    description = models.TextField(blank=True, verbose_name="Tavsif")

    resource_type = models.CharField(
        max_length=24,
        choices=ResourceType.choices,
        default=ResourceType.HANDOUT,
        db_index=True,
        verbose_name="Material turi",
    )
    language = models.CharField(
        max_length=8,
        choices=ResourceLanguage.choices,
        default=ResourceLanguage.UZ,
        db_index=True,
        verbose_name="Til",
    )
    level = models.CharField(
        max_length=4,
        choices=ResourceLevel.choices,
        default=ResourceLevel.ANY,
        db_index=True,
        verbose_name="Daraja",
    )
    topic = models.CharField(
        max_length=120,
        blank=True,
        db_index=True,
        verbose_name="Mavzu",
        help_text="Masalan: tanishuv, kelasi zamon, restoranda.",
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_resources",
        verbose_name="Asosiy kurs",
        help_text="Ixtiyoriy. Material boshqa kurslarga ham biriktilaveradi.",
    )
    tags = models.ManyToManyField(
        LibraryTag,
        blank=True,
        related_name="resources",
        verbose_name="Teglar",
    )

    file = models.FileField(
        upload_to="library/%Y/%m/",
        storage=private_media_storage,
        verbose_name="Fayl",
    )
    #: Yuklovchi bergan nom — `upload_to` uni o'zgartirishi mumkin, yuklab
    #: olishda esa aynan shu nom ko'rinadi.
    original_filename = models.CharField(max_length=200, blank=True, editable=False)
    #: Sniffer aniqlagan tur (`pdf`, `mp3`, ...) — filtr uchun.
    file_kind = models.CharField(max_length=16, blank=True, db_index=True, editable=False)
    file_size = models.PositiveBigIntegerField(default=0, editable=False)
    #: SHA-256. Ikki maqsad: bir xil fayl ikkinchi marta yuklanayotganini aytish
    #: va kelajakdagi versiya tarixi uchun barqaror identifikator.
    checksum = models.CharField(max_length=64, blank=True, db_index=True, editable=False)
    #: Fayl har almashtirilganda bittaga oshadi. Tarix hali saqlanmaydi — maydon
    #: versiyalash qo'shilganda mavjud yozuvlarga asos bo'ladi.
    version = models.PositiveIntegerField(default=1, editable=False, verbose_name="Versiya")

    is_teacher_only = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Faqat ustoz uchun",
        help_text=(
            "Belgilansa, bu manbani darsga o'quvchiga ko'rinadigan qilib "
            "biriktirib bo'lmaydi (javoblar kaliti kabi materiallar uchun)."
        ),
    )
    is_archived = models.BooleanField(default=False, db_index=True, verbose_name="Arxivlangan")
    archived_at = models.DateTimeField(null=True, blank=True, editable=False)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_resources_created",
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="library_resources_updated",
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = LibraryResourceQuerySet.as_manager()

    class Meta:
        ordering = ["-updated_at", "-pk"]
        verbose_name = "Kutubxona materiali"
        verbose_name_plural = "Kutubxona materiallari"
        indexes = [
            models.Index(fields=["is_archived", "resource_type"]),
            models.Index(fields=["is_archived", "level"]),
            models.Index(fields=["is_archived", "-updated_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def file_kind_label(self):
        return FILE_KIND_LABELS.get(self.file_kind, (self.file_kind or "fayl").upper())

    @property
    def size_display(self):
        size = self.file_size or 0
        if size >= 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        if size >= 1024:
            return f"{size / 1024:.0f} KB"
        return f"{size} B"

    @property
    def usage_total(self):
        """Nechta darsga biriktirilgan (annotatsiya bo'lsa o'shani oladi)."""
        if hasattr(self, "usage_count"):
            return self.usage_count
        return self.lesson_links.count()

    @property
    def is_in_use(self):
        return self.usage_total > 0

    def archive(self, *, actor=None):
        self.is_archived = True
        self.archived_at = timezone.now()
        self.updated_by = actor if getattr(actor, "pk", None) else None
        self.save(update_fields=["is_archived", "archived_at", "updated_by", "updated_at"])

    def restore(self, *, actor=None):
        self.is_archived = False
        self.archived_at = None
        self.updated_by = actor if getattr(actor, "pk", None) else None
        self.save(update_fields=["is_archived", "archived_at", "updated_by", "updated_at"])


class MaterialAudience(models.TextChoices):
    STUDENT = "student", "O'quvchiga ko'rinadi"
    TEACHER = "teacher", "Faqat ustozga"


class LessonMaterial(models.Model):
    """Manbaning darsdagi ko'rinishi — fayl nusxalanmaydi, havola qilinadi.

    `resource` uchun `PROTECT`: ishlatilayotgan manbani o'chirish urinishi
    darsdagi materialni jim yo'qotib yuborardi. O'chirish o'rniga arxivlash bor
    (`LibraryResource.archive()`), arxiv esa mavjud biriktirmalarni buzmaydi —
    faqat yangi biriktirish uchun taklif qilinmaydi.
    """

    lesson = models.ForeignKey(
        "courses.Lesson",
        on_delete=models.CASCADE,
        related_name="materials",
        verbose_name="Dars",
    )
    resource = models.ForeignKey(
        LibraryResource,
        on_delete=models.PROTECT,
        related_name="lesson_links",
        verbose_name="Material",
    )

    display_title = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Ko'rsatiladigan nom",
        help_text="Bo'sh bo'lsa material nomi ishlatiladi.",
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")
    audience = models.CharField(
        max_length=8,
        choices=MaterialAudience.choices,
        default=MaterialAudience.STUDENT,
        verbose_name="Kimga ko'rinadi",
    )
    is_visible = models.BooleanField(
        default=True,
        verbose_name="Ko'rinsin",
        help_text="O'chirilsa material darsda umuman ko'rinmaydi (qoralama biriktirma).",
    )
    is_downloadable = models.BooleanField(
        default=True,
        verbose_name="Yuklab olsa bo'ladi",
        help_text="O'chirilsa fayl faqat brauzerda ochiladi, yuklab olish tugmasi bo'lmaydi.",
    )
    is_required = models.BooleanField(default=False, verbose_name="Majburiy material")
    available_from = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Shu vaqtdan ochiladi",
        help_text="Bo'sh bo'lsa dars ochilishi bilan ko'rinadi.",
    )

    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lesson_materials_added",
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "Darsdagi material"
        verbose_name_plural = "Darsdagi materiallar"
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "resource"],
                name="library_lessonmaterial_unique_pair",
            ),
        ]
        indexes = [models.Index(fields=["lesson", "order"])]

    def __str__(self):
        return f"{self.lesson} -> {self.title}"

    @property
    def title(self):
        return self.display_title or self.resource.title

    def clean(self):
        """Ustoz uchun belgilangan manba o'quvchiga ochilib qolmasin.

        Tekshiruv modelda, chunki biriktirma formadan ham, servisdan ham
        yoziladi; faqat formada bo'lsa ikkinchi yo'l uni chetlab o'tardi.
        """
        super().clean()
        if self.audience == MaterialAudience.STUDENT and self.resource_id:
            if self.resource.is_teacher_only:
                raise ValidationError(
                    {
                        "audience": (
                            "Bu material «faqat ustoz uchun» deb belgilangan — "
                            "o'quvchiga ko'rinadigan qilib biriktirib bo'lmaydi."
                        )
                    }
                )

    def is_open_for_student(self, *, now=None):
        """O'quvchi shu biriktirmani ko'ra oladimi (darsga ruxsatdan tashqari).

        Dars darajasidagi qulf bu yerda tekshirilmaydi — u
        `courses/access_service.py` ning ishi va `library/services.py` da
        ikkalasi birga chaqiriladi.
        """
        if not self.is_visible or self.audience != MaterialAudience.STUDENT:
            return False
        if self.resource.is_teacher_only:
            return False
        if self.available_from and self.available_from > (now or timezone.now()):
            return False
        return True
