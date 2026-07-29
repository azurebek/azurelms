import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

from core.utils import validate_file_size, validate_image_extension


def build_unique_slug(instance, source_value):
    base_slug = slugify(source_value or "")[:180] or uuid.uuid4().hex[:8]
    slug = base_slug
    suffix = 2
    model_class = type(instance)
    while model_class.objects.exclude(pk=instance.pk).filter(slug=slug).exists():
        suffix_text = f"-{suffix}"
        slug = f"{base_slug[: max(1, 180 - len(suffix_text))]}{suffix_text}"
        suffix += 1
    return slug


def format_money(value, currency):
    if value is None:
        return "Narx aniqlanmoqda"
    amount = f"{value:,.0f}".replace(",", " ")
    if currency == University.Currency.USD:
        return f"${amount}"
    if currency == University.Currency.EUR:
        return f"€{amount}"
    if currency == University.Currency.TRY:
        return f"₺{amount}"
    return f"{amount} so'm"


class UniversityQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class University(models.Model):
    class UniversityType(models.TextChoices):
        PUBLIC = "public", "Davlat"
        PRIVATE = "private", "Xususiy"

    class AdmissionStatus(models.TextChoices):
        OPEN = "open", "Qabul ochiq"
        SOON = "soon", "Tez orada"
        CLOSED = "closed", "Qabul yopiq"

    class Currency(models.TextChoices):
        USD = "USD", "AQSH dollari"
        EUR = "EUR", "Yevro"
        TRY = "TRY", "Turk lirasi"
        UZS = "UZS", "O'zbek so'mi"

    class CoverTheme(models.TextChoices):
        AZURE = "azure", "Azure"
        VIOLET = "violet", "Binafsha"
        EMERALD = "emerald", "Yashil"
        RUBY = "ruby", "Qizil"
        GRAPHITE = "graphite", "Grafit"

    name = models.CharField(max_length=220, verbose_name="Universitet nomi")
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    short_name = models.CharField(max_length=24, verbose_name="Qisqa nomi", help_text="Masalan: İTÜ")
    city = models.CharField(max_length=100, db_index=True, verbose_name="Shahar")
    location_detail = models.CharField(
        max_length=160,
        blank=True,
        verbose_name="Joylashuv tafsiloti",
        help_text="Masalan: İstanbul (Avrupa)",
    )
    university_type = models.CharField(
        max_length=12,
        choices=UniversityType.choices,
        default=UniversityType.PUBLIC,
        db_index=True,
        verbose_name="Universitet turi",
    )
    admission_status = models.CharField(
        max_length=12,
        choices=AdmissionStatus.choices,
        default=AdmissionStatus.CLOSED,
        db_index=True,
        verbose_name="Qabul holati",
    )
    admission_deadline = models.DateField(blank=True, null=True, verbose_name="Qabul muddati")
    academic_year = models.CharField(max_length=20, blank=True, verbose_name="O'quv yili")
    founded_year = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Tashkil topgan yil")
    student_count = models.PositiveIntegerField(blank=True, null=True, verbose_name="Talabalar soni")
    description = models.TextField(blank=True, verbose_name="Umumiy ma'lumot")
    tuition_from = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Eng arzon kontrakt",
    )
    tuition_currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
        verbose_name="Kontrakt valyutasi",
    )
    application_help_enabled = models.BooleanField(default=True, verbose_name="Hujjat topshirish yordami faol")
    application_help_fee = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=5000,
        verbose_name="Yordam boshlang'ich to'lovi (so'm)",
    )
    official_website = models.URLField(blank=True, verbose_name="Rasmiy sayt")
    source_url = models.URLField(
        blank=True,
        verbose_name="Ma'lumot manbasi",
        help_text="Qabul, kontrakt va dasturlar tekshirilgan rasmiy sahifa.",
    )
    last_verified_on = models.DateField(
        blank=True,
        null=True,
        verbose_name="Oxirgi tekshirilgan sana",
    )
    cover_theme = models.CharField(
        max_length=16,
        choices=CoverTheme.choices,
        default=CoverTheme.AZURE,
        verbose_name="Muqova rangi",
    )
    cover_image = models.ImageField(
        upload_to="sit/universities/covers/",
        blank=True,
        null=True,
        validators=[validate_file_size, validate_image_extension],
        verbose_name="Muqova rasmi",
    )
    logo_image = models.ImageField(
        upload_to="sit/universities/logos/",
        blank=True,
        null=True,
        validators=[validate_file_size, validate_image_extension],
        verbose_name="Universitet logosi",
    )
    is_featured = models.BooleanField(default=False, db_index=True, verbose_name="Bosh sahifada ko'rsatilsin")
    is_published = models.BooleanField(default=False, db_index=True, verbose_name="Nashr etilgan")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UniversityQuerySet.as_manager()

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Universitet"
        verbose_name_plural = "Universitetlar"
        indexes = [
            models.Index(fields=["is_published", "admission_status", "order"]),
            models.Index(fields=["city", "university_type"]),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        errors = {}
        if self.is_published and not self.source_url:
            errors["source_url"] = "Universitetni nashr qilish uchun rasmiy manba majburiy."
        if self.is_published and not self.last_verified_on:
            errors["last_verified_on"] = (
                "Universitetni nashr qilishdan oldin tekshirilgan sanani kiriting."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = build_unique_slug(self, self.name)
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("sit:university_detail", kwargs={"slug": self.slug})

    @property
    def admission_badge_class(self):
        return {
            self.AdmissionStatus.OPEN: "badge-open",
            self.AdmissionStatus.SOON: "badge-soon",
            self.AdmissionStatus.CLOSED: "badge-closed",
        }[self.admission_status]

    @property
    def display_tuition_from(self):
        if self.tuition_from is None:
            return "Narx aniqlanmoqda"
        return f"{format_money(self.tuition_from, self.tuition_currency)}+"

    @property
    def display_help_fee(self):
        return format_money(self.application_help_fee, self.Currency.UZS)

    def _visible_programs(self):
        faculties = getattr(self, "visible_faculties", None)
        if faculties is None:
            faculties = self.faculties.filter(is_active=True).prefetch_related("programs")
        for faculty in faculties:
            programs = getattr(faculty, "visible_programs", None)
            if programs is None:
                programs = faculty.programs.filter(is_active=True)
            yield from programs

    @property
    def language_summary(self):
        order = [UniversityProgram.Language.TURKISH, UniversityProgram.Language.ENGLISH, UniversityProgram.Language.OTHER]
        values = {program.language for program in self._visible_programs()}
        labels = {
            UniversityProgram.Language.TURKISH: "TR",
            UniversityProgram.Language.ENGLISH: "EN",
            UniversityProgram.Language.OTHER: "Boshqa",
        }
        return " / ".join(labels[value] for value in order if value in values) or "Til aniqlanmoqda"

    @property
    def degree_summary(self):
        order = [
            UniversityProgram.DegreeLevel.ASSOCIATE,
            UniversityProgram.DegreeLevel.BACHELOR,
            UniversityProgram.DegreeLevel.MASTER,
            UniversityProgram.DegreeLevel.PHD,
        ]
        values = {program.degree_level for program in self._visible_programs()}
        labels = {
            UniversityProgram.DegreeLevel.ASSOCIATE: "Texnikum",
            UniversityProgram.DegreeLevel.BACHELOR: "Bakalavr",
            UniversityProgram.DegreeLevel.MASTER: "Magistr",
            UniversityProgram.DegreeLevel.PHD: "PhD",
        }
        return " · ".join(labels[value] for value in order if value in values) or "Dasturlar kutilmoqda"


class UniversityFaculty(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="faculties")
    name = models.CharField(max_length=180, verbose_name="Fakultet yoki institut")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Fakultet"
        verbose_name_plural = "Fakultetlar"
        constraints = [
            models.UniqueConstraint(fields=["university", "name"], name="sit_unique_university_faculty"),
        ]

    def __str__(self):
        return f"{self.university.short_name} — {self.name}"


class UniversityProgram(models.Model):
    class DegreeLevel(models.TextChoices):
        ASSOCIATE = "associate", "Texnikum"
        BACHELOR = "bachelor", "Bakalavr"
        MASTER = "master", "Magistr"
        PHD = "phd", "PhD"

    class Language(models.TextChoices):
        TURKISH = "tr", "Turk tili"
        ENGLISH = "en", "Ingliz tili"
        OTHER = "other", "Boshqa"

    faculty = models.ForeignKey(UniversityFaculty, on_delete=models.CASCADE, related_name="programs")
    name = models.CharField(max_length=180, verbose_name="Yo'nalish")
    degree_level = models.CharField(max_length=16, choices=DegreeLevel.choices, db_index=True, verbose_name="Daraja")
    language = models.CharField(max_length=8, choices=Language.choices, db_index=True, verbose_name="Ta'lim tili")
    duration = models.CharField(max_length=40, verbose_name="Davomiylik", help_text="Masalan: 4 yil")
    tuition_fee = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        blank=True,
        null=True,
        verbose_name="Yillik kontrakt",
    )
    tuition_currency = models.CharField(
        max_length=3,
        choices=University.Currency.choices,
        default=University.Currency.USD,
        verbose_name="Valyuta",
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="Faol")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")

    class Meta:
        ordering = ["degree_level", "faculty__order", "order", "name"]
        verbose_name = "Universitet dasturi"
        verbose_name_plural = "Universitet dasturlari"
        constraints = [
            models.UniqueConstraint(
                fields=["faculty", "name", "degree_level", "language"],
                name="sit_unique_program_variant",
            ),
        ]
        indexes = [
            models.Index(fields=["degree_level", "language", "is_active"]),
        ]

    def __str__(self):
        return f"{self.faculty.university.short_name} — {self.name} ({self.get_language_display()})"

    @property
    def display_tuition(self):
        return format_money(self.tuition_fee, self.tuition_currency)


class UniversityPreparationCourse(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="preparation_courses")
    language = models.CharField(max_length=80, verbose_name="Til")
    duration = models.CharField(max_length=40, default="1 yil", verbose_name="Davomiylik")
    tuition_fee = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Kontrakt")
    tuition_currency = models.CharField(
        max_length=3,
        choices=University.Currency.choices,
        default=University.Currency.USD,
        verbose_name="Valyuta",
    )
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")

    class Meta:
        ordering = ["order", "language"]
        verbose_name = "Til tayyorlov kursi"
        verbose_name_plural = "Til tayyorlov kurslari"
        constraints = [
            models.UniqueConstraint(fields=["university", "language"], name="sit_unique_preparation_language"),
        ]

    def __str__(self):
        return f"{self.university.short_name} — {self.language}"

    @property
    def display_tuition(self):
        return format_money(self.tuition_fee, self.tuition_currency)


class UniversityRequirement(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="requirements")
    text = models.CharField(max_length=320, verbose_name="Qabul talabi")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Qabul talabi"
        verbose_name_plural = "Qabul talablari"

    def __str__(self):
        return self.text


class UniversityDocument(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="required_documents")
    text = models.CharField(max_length=320, verbose_name="Kerakli hujjat")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Kerakli hujjat"
        verbose_name_plural = "Kerakli hujjatlar"

    def __str__(self):
        return self.text


class UniversityServiceItem(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="service_items")
    text = models.CharField(max_length=320, verbose_name="Yordam xizmati bandi")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Yordam xizmati bandi"
        verbose_name_plural = "Yordam xizmati bandlari"

    def __str__(self):
        return self.text


class UniversityMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = "image", "Rasm"
        VIDEO = "video", "Video"

    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="media_items")
    media_type = models.CharField(max_length=8, choices=MediaType.choices, default=MediaType.IMAGE)
    image = models.ImageField(
        upload_to="sit/universities/gallery/",
        blank=True,
        null=True,
        validators=[validate_file_size, validate_image_extension],
        verbose_name="Rasm",
    )
    video_url = models.URLField(blank=True, verbose_name="Video havolasi")
    caption = models.CharField(max_length=180, blank=True, verbose_name="Izoh")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Universitet media fayli"
        verbose_name_plural = "Universitet media fayllari"

    def __str__(self):
        return f"{self.university.short_name} — {self.get_media_type_display()}"

    def clean(self):
        super().clean()
        if self.media_type == self.MediaType.IMAGE and not self.image:
            raise ValidationError({"image": "Rasm turida rasm fayli majburiy."})
        if self.media_type == self.MediaType.VIDEO and not self.video_url:
            raise ValidationError({"video_url": "Video turida video havolasi majburiy."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Announcement(models.Model):
    class Category(models.TextChoices):
        ADMISSION = "admission", "Qabul"
        DISCOUNT = "discount", "Chegirma"
        DEADLINE = "deadline", "Muddat"
        NEWS = "news", "Yangilik"

    title = models.CharField(max_length=220, verbose_name="Sarlavha")
    university = models.ForeignKey(
        University,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="announcements",
    )
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.NEWS)
    published_on = models.DateField(db_index=True, verbose_name="E'lon sanasi")
    external_url = models.URLField(blank=True, verbose_name="Tashqi havola")
    show_on_home = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Bosh sahifada ko'rsatilsin",
    )
    is_published = models.BooleanField(default=False, db_index=True, verbose_name="Nashr etilgan")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-published_on", "-id"]
        verbose_name = "SIT e'loni"
        verbose_name_plural = "SIT e'lonlari"
        indexes = [models.Index(fields=["is_published", "published_on"])]

    def __str__(self):
        return self.title

    @property
    def badge_class(self):
        return {
            self.Category.ADMISSION: "badge-open",
            self.Category.DISCOUNT: "badge-soon",
            self.Category.DEADLINE: "badge-closed",
            self.Category.NEWS: "badge-soon",
        }[self.category]

    @property
    def target_url(self):
        if self.external_url:
            return self.external_url
        if self.university_id and self.university.is_published:
            return self.university.get_absolute_url()
        return reverse("sit:home")


class KnowledgeArticleQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)


class KnowledgeArticle(models.Model):
    title = models.CharField(max_length=220, verbose_name="Sarlavha")
    slug = models.SlugField(max_length=190, unique=True, blank=True)
    category = models.CharField(max_length=80, verbose_name="Kategoriya")
    excerpt = models.CharField(max_length=320, blank=True, verbose_name="Qisqa tavsif")
    body = CKEditor5Field(config_name="default", verbose_name="Maqola matni")
    cover_image = models.ImageField(
        upload_to="sit/knowledge/",
        blank=True,
        null=True,
        validators=[validate_file_size, validate_image_extension],
        verbose_name="Muqova rasmi",
    )
    is_featured = models.BooleanField(default=False, db_index=True, verbose_name="Bosh sahifada ko'rsatilsin")
    is_published = models.BooleanField(default=False, db_index=True, verbose_name="Nashr etilgan")
    published_on = models.DateField(blank=True, null=True, verbose_name="Nashr sanasi")
    source_url = models.URLField(
        blank=True,
        verbose_name="Asosiy manba",
        help_text="Viza, qabul va rasmiy talablar tekshirilgan sahifa.",
    )
    last_verified_on = models.DateField(blank=True, null=True, verbose_name="Oxirgi tekshirilgan sana")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartibi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = KnowledgeArticleQuerySet.as_manager()

    class Meta:
        ordering = ["order", "-published_on", "-created_at"]
        verbose_name = "SIT bilim bazasi maqolasi"
        verbose_name_plural = "SIT bilim bazasi maqolalari"

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        errors = {}
        if self.is_published and not self.source_url:
            errors["source_url"] = "Qo'llanmani nashr qilish uchun manba majburiy."
        if self.is_published and not self.last_verified_on:
            errors["last_verified_on"] = (
                "Qo'llanmani nashr qilishdan oldin tekshirilgan sanani kiriting."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = build_unique_slug(self, self.title)
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("sit:knowledge_detail", kwargs={"slug": self.slug})
