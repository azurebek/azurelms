from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import NoReverseMatch, reverse
from django_ckeditor_5.fields import CKEditor5Field

class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super(SingletonModel, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


def resolve_public_link(route_name="", custom_url="", fallback="#"):
    if custom_url:
        return custom_url
    if route_name:
        try:
            return reverse(route_name)
        except NoReverseMatch:
            return fallback
    return fallback

class LandingPage(SingletonModel):
    class BackgroundPreset(models.TextChoices):
        MIDNIGHT = "midnight", "Midnight blue"
        OCEAN = "ocean", "Ocean teal"
        GRAPHITE = "graphite", "Graphite blue"
        AURORA = "aurora", "Aurora violet"
        EMERALD = "emerald", "Emerald gold"
        RUBY = "ruby", "Ruby night"
        INDIGO = "indigo", "Indigo sky"

    # Hero Section
    hero_badge = models.CharField(max_length=100, default="2026 yilning eng yaxshi platformasi", verbose_name="Bosh sahifa nishonchasi (Badge)")
    hero_title_start = models.CharField(max_length=100, default="Turk tilini", verbose_name="Sarlavha boshi")
    hero_title_highlight = models.CharField(max_length=100, default="professional", verbose_name="Sarlavha ajratilgan qismi")
    hero_title_end = models.CharField(max_length=100, default="darajada o'rganing", verbose_name="Sarlavha oxiri")
    hero_subtitle = CKEditor5Field(default="Tajribali o'qituvchilar, interaktiv darslar va sertifikatlar bilan turk tilini A1 dan C1 gacha o'rganing.", verbose_name="Kichik matn (Subtitle)", config_name='default')
    hero_background_image = models.ImageField(
        upload_to='landing/hero/backgrounds/',
        blank=True,
        null=True,
        verbose_name="Hero fon rasmi",
        help_text="Butun hero bo'limi orqasida ko'rinadigan rasm. Bo'sh qoldirilsa default nozik gradient ishlaydi.",
    )
    hero_background_video = models.FileField(
        upload_to='landing/hero/backgrounds/videos/',
        blank=True,
        null=True,
        verbose_name="Hero fon videosi",
        help_text="MP4, WebM, OGV yoki MOV yuklang. Video bo'lsa fon rasmidan ustun turadi, bo'sh bo'lsa default gradient ishlaydi.",
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'webm', 'ogv', 'mov'])],
    )

    hero_image = models.ImageField(upload_to='landing/', blank=True, null=True, verbose_name="Asosiy rasm (Hero Image)")
    hero_video = models.FileField(
        upload_to='landing/videos/',
        blank=True,
        null=True,
        verbose_name="Asosiy video (Hero Video)",
        help_text="MP4, WebM, OGV yoki MOV fayl yuklang. Video bo'lsa, hero qismida rasm o'rniga video ko'rsatiladi.",
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'webm', 'ogv', 'mov'])],
    )
    how_it_works_background_image = models.ImageField(
        upload_to='landing/sections/',
        blank=True,
        null=True,
        verbose_name='"Qanday ishlaydi?" bo\'limi foni',
        help_text='Ushbu rasm shaffof overlay bilan "Qanday ishlaydi?" bo\'limi orqasida chiqadi.',
    )
    how_it_works_background_video = models.FileField(
        upload_to='landing/sections/videos/',
        blank=True,
        null=True,
        verbose_name='"Qanday ishlaydi?" bo\'limi fon videosi',
        help_text='MP4, WebM, OGV yoki MOV yuklang. Video bo\'lsa, shu bo\'limda rasm o\'rniga video ishlatiladi.',
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'webm', 'ogv', 'mov'])],
    )
    how_it_works_title = models.CharField(
        max_length=120,
        default="Qanday ishlaydi?",
        verbose_name='"Qanday ishlaydi?" sarlavhasi',
    )
    how_it_works_subtitle = models.CharField(
        max_length=220,
        default="4 ta oddiy qadamda o'rganishni boshlang",
        verbose_name='"Qanday ishlaydi?" ostsarlavhasi',
    )
    how_it_works_step_one_title = models.CharField(
        max_length=120,
        default="Ro'yxatdan o'ting",
        verbose_name="1-qadam sarlavhasi",
    )
    how_it_works_step_one_description = models.CharField(
        max_length=220,
        default="Bepul hisob yarating va platformaga kiring",
        verbose_name="1-qadam tavsifi",
    )
    how_it_works_step_two_title = models.CharField(
        max_length=120,
        default="Kurs tanlang",
        verbose_name="2-qadam sarlavhasi",
    )
    how_it_works_step_two_description = models.CharField(
        max_length=220,
        default="Darajangizga mos kursni tanlang",
        verbose_name="2-qadam tavsifi",
    )
    how_it_works_step_three_title = models.CharField(
        max_length=120,
        default="O'rganishni boshlang",
        verbose_name="3-qadam sarlavhasi",
    )
    how_it_works_step_three_description = models.CharField(
        max_length=220,
        default="Video darslar va mashqlar bilan o'rganing",
        verbose_name="3-qadam tavsifi",
    )
    how_it_works_step_four_title = models.CharField(
        max_length=120,
        default="Sertifikat oling",
        verbose_name="4-qadam sarlavhasi",
    )
    how_it_works_step_four_description = models.CharField(
        max_length=220,
        default="Kursni tugatib, sertifikat oling",
        verbose_name="4-qadam tavsifi",
    )
    footer_background_image = models.ImageField(
        upload_to='landing/footer/',
        blank=True,
        null=True,
        verbose_name='Footer fon rasmi',
        help_text='Footer orqasida transparency overlay bilan ko\'rinadigan rasm.',
    )
    footer_background_preset = models.CharField(
        max_length=20,
        choices=BackgroundPreset.choices,
        default=BackgroundPreset.MIDNIGHT,
        verbose_name="Footer fon preseti",
    )
    footer_background_video = models.FileField(
        upload_to='landing/footer/videos/',
        blank=True,
        null=True,
        verbose_name='Footer fon videosi',
        help_text='MP4, WebM, OGV yoki MOV yuklang. Video bo\'lsa, footerda rasm o\'rniga video ishlatiladi.',
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'webm', 'ogv', 'mov'])],
    )

    # CTA Section
    cta_title = models.CharField(max_length=100, default="Bugun o'rganishni boshlang!", verbose_name="Bottom CTA Sarlavhasi")
    cta_description = CKEditor5Field(default="Minglab o'quvchilar safiga qo'shiling va turk tilini professional darajada o'rganing.", verbose_name="Bottom CTA matni", config_name='default')
    cta_kicker = models.CharField(max_length=80, default="Boshlash", verbose_name="Bottom CTA kicker")
    cta_primary_label = models.CharField(max_length=80, default="Bepul boshlash", verbose_name="CTA asosiy tugma")
    cta_secondary_label = models.CharField(max_length=80, default="Kurslarni ko'rish", verbose_name="CTA ikkinchi tugma")
    cta_background_preset = models.CharField(
        max_length=20,
        choices=BackgroundPreset.choices,
        default=BackgroundPreset.MIDNIGHT,
        verbose_name="CTA fon preseti",
    )
    cta_background_image = models.ImageField(
        upload_to='landing/cta/',
        blank=True,
        null=True,
        verbose_name="CTA fon rasmi",
        help_text="Bottom CTA orqasida ko'rinadigan rasm. Video bo'lsa, rasm o'rniga video ishlaydi.",
    )
    cta_background_video = models.FileField(
        upload_to='landing/cta/videos/',
        blank=True,
        null=True,
        verbose_name="CTA fon videosi",
        help_text="MP4, WebM, OGV yoki MOV yuklang. Video bo'lsa, CTA fonida rasm o'rniga ishlatiladi.",
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'webm', 'ogv', 'mov'])],
    )

    # Public homepage section labels
    portal_media_label = models.CharField(max_length=100, default="Platforma preview", verbose_name="Portal media label")
    portal_cover_label = models.CharField(max_length=100, default="AzureLMS model", verbose_name="Portal cover label")
    portal_cover_title = models.CharField(max_length=80, default="TR A1-C1", verbose_name="Portal cover title")
    portal_program_title = models.CharField(
        max_length=180,
        default="Kurslar, lesson workspace va sertifikat oqimi bitta tizimda",
        verbose_name="Portal blok sarlavhasi",
    )
    search_placeholder = models.CharField(
        max_length=180,
        default="Turk tili, B2, sertifikat yoki blog qidiring",
        verbose_name="Qidiruv placeholder",
    )
    courses_section_kicker = models.CharField(max_length=80, default="Katalog", verbose_name="Kurslar blok kicker")
    courses_section_title = models.CharField(max_length=120, default="Mashhur kurslar", verbose_name="Kurslar blok sarlavhasi")
    courses_section_link_label = models.CharField(max_length=100, default="Barcha kurslarni ko'rish", verbose_name="Kurslar blok linki")
    process_section_kicker = models.CharField(max_length=80, default="Jarayon", verbose_name="Jarayon blok kicker")
    testimonials_section_kicker = models.CharField(max_length=80, default="Fikrlar", verbose_name="Fikrlar blok kicker")
    testimonials_section_title = models.CharField(max_length=120, default="O'quvchilar fikri", verbose_name="Fikrlar blok sarlavhasi")

    # --- Yon panel (rail) ---
    rail_tagline = models.CharField(max_length=80, default="Turk tili · A1—C1", verbose_name="Rail tagline")
    rail_footer_line_one = models.CharField(max_length=60, default="© 2026 AZURELMS", verbose_name="Rail footer 1-qator")
    rail_footer_line_two = models.CharField(max_length=60, default="TOSHKENT · UZ", verbose_name="Rail footer 2-qator")

    # --- Hero qo'shimcha matnlari ---
    hero_kicker_left = models.CharField(max_length=140, default="Turk tili · A1—C1 · Onlayn platforma", verbose_name="Hero kicker (chap)")
    hero_kicker_right = models.CharField(max_length=60, default="EST. 2024", verbose_name="Hero kicker (o'ng)")
    hero_primary_label = models.CharField(max_length=60, default="Bepul boshlash", verbose_name="Hero asosiy tugma matni")
    hero_secondary_label = models.CharField(max_length=60, default="Daraja yo'lini ko'rish", verbose_name="Hero ikkinchi tugma matni")

    # --- Demo dashboard (hero ostidagi mock brauzer) ---
    demo_url = models.CharField(max_length=120, default="app.azurelms.uz/dashboard", verbose_name="Demo URL matni")
    demo_course_kicker = models.CharField(max_length=60, default="Joriy kurs", verbose_name="Demo kurs kicker")
    demo_course_name = models.CharField(max_length=90, default="Turk tili — B2 Intensiv", verbose_name="Demo kurs nomi")
    demo_progress = models.PositiveSmallIntegerField(default=68, verbose_name="Demo progress (%)")
    demo_next_title = models.CharField(max_length=90, default="Listening — Dialog 14", verbose_name="Demo keyingi dars nomi")
    demo_next_time = models.CharField(max_length=60, default="Bugun · 18:00", verbose_name="Demo keyingi dars vaqti")
    demo_next_badge = models.CharField(max_length=30, default="KEYINGI", verbose_name="Demo keyingi dars nishoni")
    demo_stat_one_value = models.CharField(max_length=20, default="18", verbose_name="Demo stat 1 qiymati")
    demo_stat_one_label = models.CharField(max_length=40, default="Dars o'tildi", verbose_name="Demo stat 1 nomi")
    demo_stat_two_value = models.CharField(max_length=20, default="94%", verbose_name="Demo stat 2 qiymati")
    demo_stat_two_label = models.CharField(max_length=40, default="Exam natija", verbose_name="Demo stat 2 nomi")
    demo_stat_three_value = models.CharField(max_length=20, default="11", verbose_name="Demo stat 3 qiymati")
    demo_stat_three_label = models.CharField(max_length=40, default="Streak", verbose_name="Demo stat 3 nomi")

    # --- Daraja yo'li (PATH) bo'lim sarlavhasi ---
    path_kicker = models.CharField(max_length=60, default="Daraja yo'li", verbose_name="Daraja yo'li kicker")
    path_title = models.CharField(max_length=140, default="Uch bosqich. Har biri oldingisiga ulanadi.", verbose_name="Daraja yo'li sarlavhasi")
    path_subtitle = models.CharField(max_length=200, default="Bo'sh joy yo'q, qaytariq yo'q — faqat keyingi aniq qadam.", verbose_name="Daraja yo'li ostsarlavhasi")

    # --- AI repetitor bo'limi ---
    ai_kicker = models.CharField(max_length=60, default="AI repetitor", verbose_name="AI bo'lim kicker")
    ai_title = models.CharField(max_length=140, default="Darslaringizni biladigan shaxsiy repetitor.", verbose_name="AI bo'lim sarlavhasi")
    ai_subtitle = models.CharField(max_length=240, default="Azure AI sizning bosqichingizni, xatolaringizni va maqsadingizni eslab qoladi — javoblar tasodifiy emas, sizga moslangan.", verbose_name="AI bo'lim matni")
    ai_demo_session_label = models.CharField(max_length=60, default="azure-ai · session", verbose_name="AI demo sessiya yorlig'i")
    ai_demo_question = models.CharField(max_length=200, default="\"gitmek\" o'tgan zamonda qanday bo'ladi?", verbose_name="AI demo savol")
    ai_demo_answer = models.CharField(max_length=240, default="gittim · gittin · gitti. Keling, uchta misol bilan mustahkamlaymiz va so'ng siz yozib ko'rasiz.", verbose_name="AI demo javob")
    ai_demo_input_placeholder = models.CharField(max_length=80, default="Savol yozing…", verbose_name="AI demo input placeholder")

    # --- Imtihon muhiti bo'limi ---
    exam_kicker = models.CharField(max_length=60, default="Imtihon muhiti", verbose_name="Imtihon bo'lim kicker")
    exam_title = models.CharField(max_length=140, default="Haqiqiy imtihon. To'rt ko'nikma, xalqaro format.", verbose_name="Imtihon bo'lim sarlavhasi")
    exam_subtitle = models.CharField(max_length=240, default="Timer, bo'limlar va baholash — rasmiy imtihonga to'liq mos muhitda mashq qiling.", verbose_name="Imtihon bo'lim matni")

    # --- Sertifikat bo'limi ---
    cert_kicker = models.CharField(max_length=60, default="Sertifikat", verbose_name="Sertifikat bo'lim kicker")
    cert_title = models.CharField(max_length=140, default="Tugatdingizmi — tasdiqlangan sertifikat.", verbose_name="Sertifikat bo'lim sarlavhasi")
    cert_text = models.CharField(max_length=280, default="Har bir sertifikat QR kod orqali tekshiriladi. Ish beruvchi yoki universitet bir soniyada haqiqiyligiga ishonch hosil qiladi.", verbose_name="Sertifikat bo'lim matni")
    cert_cta_label = models.CharField(max_length=80, default="Namuna sertifikatni ko'rish", verbose_name="Sertifikat CTA matni")
    cert_sample_number = models.CharField(max_length=40, default="№ AZ-2026-0481", verbose_name="Namuna sertifikat raqami")
    cert_sample_label = models.CharField(max_length=40, default="Sertifikat", verbose_name="Namuna sertifikat yorlig'i")
    cert_sample_course = models.CharField(max_length=80, default="Turk tili — C1", verbose_name="Namuna sertifikat kursi")
    cert_sample_name = models.CharField(max_length=80, default="Nigora Soliyeva", verbose_name="Namuna sertifikat egasi")
    cert_sample_score = models.CharField(max_length=30, default="96 / 100", verbose_name="Namuna sertifikat bahosi")
    cert_sample_date = models.CharField(max_length=30, default="12.06.2026", verbose_name="Namuna sertifikat sanasi")
    cert_sample_location = models.CharField(max_length=40, default="Toshkent", verbose_name="Namuna sertifikat joyi")

    # --- Pastki CTA + footer ---
    final_cta_title = models.CharField(max_length=120, default="Bugun birinchi darsdan boshlang.", verbose_name="Pastki CTA sarlavhasi")
    final_cta_secondary_label = models.CharField(max_length=80, default="Narxlar bilan tanishish", verbose_name="Pastki CTA ikkinchi havola")
    footer_tagline = models.CharField(max_length=160, default="O'zbek tilida turk tilini tartibli o'rgatadigan onlayn platforma.", verbose_name="Footer tavsifi")
    footer_col_platform_title = models.CharField(max_length=40, default="Platforma", verbose_name="Footer: Platforma ustuni nomi")
    footer_col_company_title = models.CharField(max_length=40, default="Kompaniya", verbose_name="Footer: Kompaniya ustuni nomi")
    footer_col_legal_title = models.CharField(max_length=40, default="Huquqiy", verbose_name="Footer: Huquqiy ustuni nomi")
    footer_col_contact_title = models.CharField(max_length=40, default="Aloqa", verbose_name="Footer: Aloqa ustuni nomi")
    footer_copyright = models.CharField(max_length=140, default="© 2026 AZURELMS — BARCHA HUQUQLAR HIMOYALANGAN", verbose_name="Footer copyright matni")

    class Meta:
        verbose_name = "Bosh sahifa sozlamasi"
        verbose_name_plural = "1. Bosh sahifa sozlamalari"

    def __str__(self):
        return "Bosh sahifa dizayn matnlari"

    @property
    def cta_background_class(self):
        return f"cta-strip--{self.cta_background_preset}"

    @property
    def footer_background_class(self):
        return f"public-footer--{self.footer_background_preset}"


class Statistic(models.Model):
    value = models.CharField(max_length=50, blank=True, help_text="Raqamli qiymat bo'sh bo'lsa shu matn statik ko'rsatiladi. Masalan: 5,000+", verbose_name="Matnli qiymat")
    numeric_value = models.DecimalField(
        max_digits=10,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="To'ldirilsa sahifada 0 dan shu songacha animatsiya bo'ladi. Masalan: 2400 yoki 4.9",
        verbose_name="Raqamli qiymat (animatsiya)",
    )
    suffix = models.CharField(max_length=8, blank=True, help_text="Masalan: + yoki %", verbose_name="Qiymat qo'shimchasi")
    decimals = models.PositiveSmallIntegerField(default=0, verbose_name="Kasr xonalar soni")
    label = models.CharField(max_length=100, help_text="Masalan: Faol o'quvchilar", verbose_name="Nomi")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")

    class Meta:
        ordering = ['order']
        verbose_name = "Bosh sahifa statistikasi"
        verbose_name_plural = "2. Bosh sahifa statistikalari"

    def __str__(self):
        return f"{self.value or self.numeric_value} - {self.label}"

    @property
    def display_value(self):
        """Animatsiya ishlamagan holatda ko'rsatiladigan matn."""
        if self.value:
            return self.value
        if self.numeric_value is None:
            return ""
        number = self.numeric_value
        if self.decimals:
            formatted = f"{number:.{self.decimals}f}"
        else:
            formatted = f"{int(number)}"
        return f"{formatted}{self.suffix}"


class LandingHeroSlide(models.Model):
    class Layout(models.TextChoices):
        STAGE_LEFT = "stage_left", "Vizual chapda, matn o'ngda"
        STAGE_RIGHT = "stage_right", "Matn chapda, vizual o'ngda"

    class GradientPreset(models.TextChoices):
        OCEAN = "ocean", "Ocean teal"
        GRAPHITE = "graphite", "Graphite blue"
        AURORA = "aurora", "Aurora violet"
        EMERALD = "emerald", "Emerald gold"
        RUBY = "ruby", "Ruby night"
        INDIGO = "indigo", "Indigo sky"

    class ChartPreset(models.TextChoices):
        ACADEMIC = "academic", "Academic"
        CATALOG = "catalog", "Catalog"
        CERTIFICATION = "certification", "Certification"
        GROWTH = "growth", "Growth"

    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")
    layout = models.CharField(max_length=20, choices=Layout.choices, default=Layout.STAGE_LEFT, verbose_name="Joylashuv")
    gradient_preset = models.CharField(
        max_length=20,
        choices=GradientPreset.choices,
        default=GradientPreset.OCEAN,
        verbose_name="Background gradient",
    )
    chart_preset = models.CharField(max_length=20, choices=ChartPreset.choices, default=ChartPreset.ACADEMIC, verbose_name="Chart turi")

    kicker = models.CharField(max_length=100, default="Turk tili platformasi", verbose_name="Kicker")
    title = models.CharField(max_length=180, verbose_name="Asosiy sarlavha")
    subtitle = models.TextField(verbose_name="Subtitle")
    primary_label = models.CharField(max_length=80, default="Kurslarni ko'rish", verbose_name="Asosiy tugma matni")
    primary_url = models.CharField(max_length=200, default="/courses/", verbose_name="Asosiy tugma URL")
    secondary_label = models.CharField(max_length=80, blank=True, verbose_name="Ikkinchi tugma matni")
    secondary_url = models.CharField(max_length=200, blank=True, verbose_name="Ikkinchi tugma URL")

    poster_kicker = models.CharField(max_length=80, default="Academic bulletin", verbose_name="Asosiy karta yuqori matni")
    poster_year_label = models.CharField(max_length=30, default="2026", verbose_name="Asosiy karta yil/label")
    poster_title = models.CharField(max_length=80, default="A1-C1", verbose_name="Asosiy karta title")
    poster_text = models.CharField(max_length=180, default="Tartibli track, lesson workspace va dashboard bitta oqimda.", verbose_name="Asosiy karta matni")
    poster_chip_one = models.CharField(max_length=80, default="A1-C1 flow", verbose_name="Chip 1")
    poster_chip_two = models.CharField(max_length=80, default="Sertifikat track", verbose_name="Chip 2")
    poster_chip_three = models.CharField(max_length=80, default="Live support", verbose_name="Chip 3")

    side_label = models.CharField(max_length=40, default="TR", verbose_name="Yon karta label")
    side_title = models.CharField(max_length=80, default="A1-C1", verbose_name="Yon karta title")
    side_text = models.CharField(max_length=180, default="Turk tili, dashboard va exam flow yagona tizimda.", verbose_name="Yon karta matni")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Carousel slide"
        verbose_name_plural = "1.1 Carousel slide'lari"

    def __str__(self):
        return self.title

    @property
    def layout_class(self):
        return "public-billboard-slide--reverse" if self.layout == self.Layout.STAGE_RIGHT else "public-billboard-slide--default"

    @property
    def gradient_class(self):
        return f"public-billboard-slide--{self.gradient_preset}"

    @property
    def chart_class(self):
        return f"poster-chart--{self.chart_preset}"

    @property
    def metric_items(self):
        return self.metrics.all()


class LandingHeroSlideMetric(models.Model):
    slide = models.ForeignKey(LandingHeroSlide, related_name="metrics", on_delete=models.CASCADE, verbose_name="Slide")
    value = models.CharField(max_length=70, verbose_name="Qiymat")
    label = models.CharField(max_length=120, verbose_name="Izoh")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Carousel slide statistikasi"
        verbose_name_plural = "1.2 Carousel slide statistikalari"

    def __str__(self):
        return f"{self.value} - {self.label}"


class LandingPortalTab(models.Model):
    label = models.CharField(max_length=80, verbose_name="Tab nomi")
    url = models.CharField(max_length=200, default="/courses/", verbose_name="URL")
    is_active = models.BooleanField(default=False, verbose_name="Aktiv ko'rinsinmi?")
    is_visible = models.BooleanField(default=True, verbose_name="Ko'rinsinmi?")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Portal tab"
        verbose_name_plural = "1.3 Portal tablari"

    def __str__(self):
        return self.label


class LandingPortalListItem(models.Model):
    text = models.CharField(max_length=140, verbose_name="Matn")
    is_visible = models.BooleanField(default=True, verbose_name="Ko'rinsinmi?")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Portal ro'yxat elementi"
        verbose_name_plural = "1.4 Portal ro'yxat elementlari"

    def __str__(self):
        return self.text


class LandingProcessStep(models.Model):
    title = models.CharField(max_length=120, verbose_name="Sarlavha")
    description = models.CharField(max_length=240, verbose_name="Tavsif")
    icon_class = models.CharField(
        max_length=60,
        default="bi bi-person-plus",
        verbose_name="Bootstrap icon class",
        help_text="Masalan: bi bi-person-plus, bi bi-signpost-split, bi bi-play-circle",
    )
    color_class = models.CharField(max_length=60, blank=True, verbose_name="Qo'shimcha rang class")
    is_visible = models.BooleanField(default=True, verbose_name="Ko'rinsinmi?")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Jarayon qadami"
        verbose_name_plural = "1.5 Jarayon qadamlari"

    def __str__(self):
        return self.title


class LandingLevelStage(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Ochiq"
        CURRENT = "current", "Joriy"
        LOCKED = "locked", "Yopiq"

    title = models.CharField(max_length=80, verbose_name="Bosqich nomi")
    description = models.CharField(max_length=140, verbose_name="Tavsif")
    level_range = models.CharField(max_length=30, default="A1—A2", verbose_name="Daraja oralig'i")
    lessons_count = models.CharField(max_length=20, default="36", verbose_name="Darslar soni")
    duration = models.CharField(max_length=40, default="14 hafta", verbose_name="Davomiyligi")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, verbose_name="Holati")
    status_label = models.CharField(max_length=40, blank=True, verbose_name="Holat matni", help_text="Bo'sh bo'lsa holat turi nomi ishlatiladi.")
    is_visible = models.BooleanField(default=True, verbose_name="Ko'rinsinmi?")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Daraja bosqichi"
        verbose_name_plural = "2.1 Daraja yo'li bosqichlari"

    def __str__(self):
        return f"{self.title} ({self.level_range})"

    @property
    def status_text(self):
        return self.status_label or self.get_status_display()


class LandingAIFeature(models.Model):
    text = models.CharField(max_length=140, verbose_name="Xususiyat matni")
    is_visible = models.BooleanField(default=True, verbose_name="Ko'rinsinmi?")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "AI xususiyati"
        verbose_name_plural = "2.2 AI repetitor xususiyatlari"

    def __str__(self):
        return self.text


class LandingExamSkill(models.Model):
    name = models.CharField(max_length=60, verbose_name="Ko'nikma nomi")
    meta = models.CharField(max_length=60, default="30 MIN · 40 Q", verbose_name="Meta matn")
    icon_class = models.CharField(
        max_length=60,
        default="bi bi-headphones",
        verbose_name="Bootstrap icon class",
        help_text="Masalan: bi bi-headphones, bi bi-book, bi bi-pencil, bi bi-mic",
    )
    is_visible = models.BooleanField(default=True, verbose_name="Ko'rinsinmi?")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Imtihon ko'nikmasi"
        verbose_name_plural = "2.3 Imtihon ko'nikmalari"

    def __str__(self):
        return self.name


class Testimonial(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ism-familiya")
    role = models.CharField(max_length=100, verbose_name="Kasbi/Darajasi", default="Talaba")
    text = models.TextField(verbose_name="Fikr matni")
    rating = models.PositiveSmallIntegerField(default=5, verbose_name="Baho (1-5)")
    avatar = models.ImageField(upload_to='testimonials/', blank=True, null=True, verbose_name="Rasm")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi?")

    class Meta:
        verbose_name = "Fikr"
        verbose_name_plural = "3. O'quvchilar fikrlari"

    def __str__(self):
        return self.name


class AboutPage(SingletonModel):
    hero_title_start = models.CharField(max_length=100, default="Sifatli ta'lim orqali", verbose_name="Sarlavha boshi")
    hero_title_highlight = models.CharField(max_length=100, default="maqsad sari", verbose_name="Sarlavha ajratilgan qismi")
    hero_subtitle = CKEditor5Field(default="AzureLMS — turk tilini zamonaviy, interaktiv va qulay usulda o'rganishni xohlovchilar uchun...", verbose_name="Kichik matn (Subtitle)", config_name='default')

    mission_title = models.CharField(max_length=200, default="Bizning maqsadimiz (Missiya)", verbose_name="Missiya Sarlavhasi")
    mission_text = CKEditor5Field(verbose_name="Missiya matni", blank=True, config_name='default')

    vision_title = models.CharField(max_length=200, default="Bizning qarashimiz (Vision)", verbose_name="Vision Sarlavhasi")
    vision_text = CKEditor5Field(verbose_name="Vision matni", blank=True, config_name='default')

    class Meta:
        verbose_name = "Biz haqimizda sozlamasi"
        verbose_name_plural = "4. Biz haqimizda sozlamalari"

    def __str__(self):
        return "Biz haqimizda matnlari"


class AboutStatistic(models.Model):
    value = models.CharField(max_length=50, verbose_name="Qiymati")
    label = models.CharField(max_length=100, verbose_name="Nomi")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")

    class Meta:
        ordering = ['order']
        verbose_name = "Biz haqimizda statistikasi"
        verbose_name_plural = "5. Biz haqimizda statistikalari"

    def __str__(self):
        return f"{self.value} - {self.label}"


class TeamMember(models.Model):
    name = models.CharField(max_length=100, verbose_name="Ism-familiya")
    role_1 = models.CharField(max_length=100, verbose_name="Asosiy rol (Masalan: O'qituvchi)")
    role_2 = models.CharField(max_length=100, verbose_name="Qo'shimcha rol (Masalan: CEO)")
    bio = CKEditor5Field(verbose_name="Qisqa ma'lumot", config_name='default')
    avatar = models.ImageField(upload_to='team/', blank=True, null=True, verbose_name="Rasm")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")

    class Meta:
        ordering = ['order']
        verbose_name = "Jamoa a'zosi"
        verbose_name_plural = "6. Jamoa a'zolari"

    def __str__(self):
        return self.name


class SiteSettings(SingletonModel):
    brand_name = models.CharField(max_length=80, default="AzureLMS", verbose_name="Brend nomi")
    brand_tagline = models.CharField(
        max_length=140,
        default="Turk tili va sertifikat platformasi",
        verbose_name="Brend ostsarlavhasi",
    )
    logo_mark_text = models.CharField(
        max_length=8,
        default="AL",
        verbose_name="Logo mark matni",
        help_text="Logo rasmi yuklanmasa shu qisqa matn ko'rinadi.",
    )
    logo_image = models.ImageField(
        upload_to="site/logo/primary/",
        blank=True,
        null=True,
        verbose_name="Asosiy logo",
        help_text="Oq yoki yorug' fonlarda ishlatiladigan gorizontal wordmark.",
    )
    logo_dark_image = models.ImageField(
        upload_to="site/logo/dark/",
        blank=True,
        null=True,
        verbose_name="Qorong'i fon uchun logo",
        help_text="Login kabi qorong'i fonlarda ishlatiladi. Bo'sh bo'lsa matnli fallback chiqadi.",
    )
    logo_mark_image = models.ImageField(
        upload_to="site/logo/mark/",
        blank=True,
        null=True,
        verbose_name="Ixcham logo belgisi",
        help_text="Sidebar, messenger, Mini App va sertifikatlar uchun kvadrat belgi.",
    )
    favicon_image = models.ImageField(
        upload_to="site/logo/favicon/",
        blank=True,
        null=True,
        verbose_name="Brauzer ikonkasi",
        help_text="PNG, JPG yoki WebP. Tavsiya: kvadrat 64x64 yoki 128x128.",
    )
    company_description = models.TextField(
        default="Professional o'qituvchilar bilan turk tilini samarali o'rganing. A1 dan C1 gacha barcha darajalar.",
        verbose_name="Kompaniya qisqacha matni",
    )
    contact_phone = models.CharField(max_length=50, default="+998 90 123 45 67", verbose_name="Telefon")
    contact_email = models.EmailField(default="info@azurelms.uz", verbose_name="Email")
    contact_address = models.CharField(max_length=255, blank=True, verbose_name="Manzil")
    support_url = models.URLField(blank=True, verbose_name="Qo'llab-quvvatlash havolasi")
    payment_card_number = models.CharField(
        max_length=32,
        default="8600 1234 5678 9012",
        verbose_name="To'lov karta raqami",
    )
    payment_card_holder = models.CharField(
        max_length=120,
        default="Azizbek Sirojiddinov",
        verbose_name="Karta egasi",
    )
    payment_provider_label = models.CharField(
        max_length=120,
        default="Uzcard / Humo",
        verbose_name="To'lov turi yoki bank",
    )
    payment_instruction = models.CharField(
        max_length=255,
        default="To'lovni ushbu kartaga o'tkazing va chekni aniq ko'rinadigan formatda yuklang.",
        verbose_name="To'lov bo'yicha izoh",
    )

    telegram_url = models.URLField(blank=True, verbose_name="Telegram URL")
    instagram_url = models.URLField(blank=True, verbose_name="Instagram URL")
    youtube_url = models.URLField(blank=True, verbose_name="YouTube URL")
    facebook_url = models.URLField(blank=True, verbose_name="Facebook URL")

    @property
    def contact_phone_href(self):
        phone = self.contact_phone or "+998 90 123 45 67"
        normalized = "".join(
            character for character in phone if character.isdigit() or character == "+"
        )
        return normalized or phone

    class Meta:
        verbose_name = "Platforma sozlamasi"
        verbose_name_plural = "7. Platforma sozlamalari"

    def __str__(self):
        return "Platforma sozlamalari"


class LandingNavItem(models.Model):
    class Placement(models.TextChoices):
        MAIN = "main", "Asosiy navbar"
        UTILITY = "utility", "Yuqori utility navbar"
        FOOTER_PLATFORM = "footer_platform", "Footer: Platforma"
        FOOTER_COMPANY = "footer_company", "Footer: Kompaniya"
        FOOTER_LEGAL = "footer_legal", "Footer: Huquqiy"

    class LinkKey(models.TextChoices):
        CUSTOM = "custom", "Custom URL"
        HOME = "home", "Bosh sahifa"
        COURSES = "courses", "Kurslar"
        PRICING = "pricing", "Narxlar"
        ABOUT = "about", "Biz haqimizda"
        BLOG = "blog", "Blog"
        FAQ = "faq", "Yordam / FAQ"
        LOGIN = "login", "Kirish"
        REGISTER = "register", "Ro'yxatdan o'tish"
        DASHBOARD = "dashboard", "Dashboard"

    ROUTE_MAP = {
        LinkKey.HOME: "home",
        LinkKey.COURSES: "courses",
        LinkKey.PRICING: "subscriptions:pricing",
        LinkKey.ABOUT: "about",
        LinkKey.BLOG: "blog:list",
        LinkKey.FAQ: "faq_page",
        LinkKey.LOGIN: "login",
        LinkKey.REGISTER: "register",
        LinkKey.DASHBOARD: "dashboard",
    }

    placement = models.CharField(max_length=30, choices=Placement.choices, default=Placement.MAIN, verbose_name="Qayerda ko'rinsin?")
    key = models.CharField(max_length=20, choices=LinkKey.choices, default=LinkKey.CUSTOM, verbose_name="Link turi")
    label = models.CharField(max_length=80, verbose_name="Navbar matni")
    custom_url = models.CharField(
        max_length=220,
        blank=True,
        verbose_name="Custom URL",
        help_text="Custom URL tanlansa yoki route bo'sh bo'lsa shu ishlaydi. Masalan: /courses/ yoki https://...",
    )
    open_in_new_tab = models.BooleanField(default=False, verbose_name="Yangi tabda ochilsinmi?")
    is_visible = models.BooleanField(default=True, verbose_name="Ko'rinsinmi?")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Landing navbar linki"
        verbose_name_plural = "9. Landing navbar linklari"

    def __str__(self):
        return self.label

    def save(self, *args, **kwargs):
        if not self.label:
            default_labels = {item["key"]: item["label"] for item in self.default_items()}
            self.label = default_labels.get(self.key, self.get_key_display())
        super().save(*args, **kwargs)

    @classmethod
    def default_items(cls):
        return [
            {"key": cls.LinkKey.HOME, "label": "Bosh sahifa", "is_visible": True, "order": 1},
            {"key": cls.LinkKey.COURSES, "label": "Kurslar", "is_visible": True, "order": 2},
            {"key": cls.LinkKey.PRICING, "label": "Narxlar", "is_visible": True, "order": 3},
            {"key": cls.LinkKey.ABOUT, "label": "Biz haqimizda", "is_visible": True, "order": 4},
            {"key": cls.LinkKey.BLOG, "label": "Blog", "is_visible": True, "order": 5},
        ]

    @classmethod
    def default_utility_items(cls):
        return [
            {"key": cls.LinkKey.HOME, "label": "Bosh sahifa", "is_visible": True, "order": 1},
            {"key": cls.LinkKey.COURSES, "label": "Kurslar", "is_visible": True, "order": 2},
            {"key": cls.LinkKey.PRICING, "label": "Narxlar", "is_visible": True, "order": 3},
            {"key": cls.LinkKey.BLOG, "label": "Blog", "is_visible": True, "order": 4},
            {"key": cls.LinkKey.FAQ, "label": "Yordam", "is_visible": True, "order": 5},
        ]

    @classmethod
    def default_footer_items(cls, placement):
        defaults = {
            cls.Placement.FOOTER_PLATFORM: [
                {"key": cls.LinkKey.COURSES, "label": "Kurslar", "is_visible": True, "order": 1},
                {"key": cls.LinkKey.PRICING, "label": "Narxlar", "is_visible": True, "order": 2},
                {"key": cls.LinkKey.ABOUT, "label": "Sertifikatlar", "is_visible": True, "order": 3},
                {"key": cls.LinkKey.REGISTER, "label": "Qabul yo'li", "is_visible": True, "order": 4},
            ],
            cls.Placement.FOOTER_COMPANY: [
                {"key": cls.LinkKey.ABOUT, "label": "Biz haqimizda", "is_visible": True, "order": 1},
                {"key": cls.LinkKey.BLOG, "label": "Blog", "is_visible": True, "order": 2},
                {"key": cls.LinkKey.FAQ, "label": "Yordam markazi", "is_visible": True, "order": 3},
            ],
            cls.Placement.FOOTER_LEGAL: [
                {"key": cls.LinkKey.CUSTOM, "label": "Foydalanish shartlari", "custom_url": "/terms-of-service/", "is_visible": True, "order": 1},
                {"key": cls.LinkKey.CUSTOM, "label": "Maxfiylik siyosati", "custom_url": "/privacy-policy/", "is_visible": True, "order": 2},
                {"key": cls.LinkKey.FAQ, "label": "FAQ", "is_visible": True, "order": 3},
            ],
        }
        return defaults.get(placement, [])

    @classmethod
    def get_url_for_key(cls, key):
        route_name = cls.ROUTE_MAP.get(key)
        if not route_name:
            return "#"
        try:
            return reverse(route_name)
        except NoReverseMatch:
            return "#"

    @classmethod
    def is_key_active(cls, key, request):
        match = getattr(request, "resolver_match", None)
        if not match:
            return False

        view_name = match.view_name or ""
        url_name = match.url_name or ""
        namespace = match.namespace or ""

        if key == cls.LinkKey.HOME:
            return view_name == "home"
        if key == cls.LinkKey.COURSES:
            return url_name in {
                "courses",
                "course_detail",
                "course_study",
                "lesson_detail",
                "exam_detail",
                "exam_result",
                "certificate_detail",
                "certificate_appendix",
            }
        if key == cls.LinkKey.PRICING:
            return namespace == "subscriptions" or view_name == "subscriptions:pricing"
        if key == cls.LinkKey.ABOUT:
            return view_name == "about"
        if key == cls.LinkKey.BLOG:
            return namespace == "blog"
        return False

    def get_url(self):
        if self.key == self.LinkKey.CUSTOM:
            return self.custom_url or "#"
        return self.custom_url or self.get_url_for_key(self.key)

    def is_active_for(self, request):
        if self.custom_url:
            return request.path == self.custom_url
        return self.is_key_active(self.key, request)


class AuthPageSettings(SingletonModel):
    meta_description = models.CharField(
        max_length=180,
        default="AzureLMS hisobga kirish va xavfsiz autentifikatsiya sahifalari.",
        verbose_name="Auth meta description",
    )
    topbar_back_label = models.CharField(
        max_length=90,
        default="Bosh sahifaga qaytish",
        verbose_name="Yuqoridagi qaytish tugmasi",
    )
    visual_point_one = models.CharField(
        max_length=180,
        default="Yengil, fokuslangan va keraksiz chalg'ituvchisiz auth tajribasi.",
        verbose_name="Chap panel 1-matn",
    )
    visual_point_two = models.CharField(
        max_length=180,
        default="Xavfsiz parol oqimlari va tiklash scenariylari.",
        verbose_name="Chap panel 2-matn",
    )
    visual_point_three = models.CharField(
        max_length=180,
        default="Tez kirish va mobilga mos professional layout.",
        verbose_name="Chap panel 3-matn",
    )
    stat_one_value = models.CharField(max_length=30, default="24/7", verbose_name="Stat 1 qiymati")
    stat_one_label = models.CharField(max_length=60, default="Platform access", verbose_name="Stat 1 yorlig'i")
    stat_two_value = models.CharField(max_length=30, default="A1-C1", verbose_name="Stat 2 qiymati")
    stat_two_label = models.CharField(max_length=60, default="Structured learning", verbose_name="Stat 2 yorlig'i")
    stat_three_value = models.CharField(max_length=30, default="Pro", verbose_name="Stat 3 qiymati")
    stat_three_label = models.CharField(max_length=60, default="Guided journey", verbose_name="Stat 3 yorlig'i")
    help_prompt = models.CharField(max_length=60, default="Need help?", verbose_name="Pastki yordam matni")
    help_link_label = models.CharField(
        max_length=60,
        default="Qo'llab-quvvatlash",
        verbose_name="Pastki yordam link nomi",
    )
    login_visual_kicker = models.CharField(max_length=80, default="Welcome Back", verbose_name="Login kicker")
    login_visual_title = models.CharField(
        max_length=220,
        default="Kurslaringiz, progress va bildirishnomalaringiz bir joyda kutib turibdi.",
        verbose_name="Login chap panel sarlavhasi",
    )
    login_visual_description = models.TextField(
        default="Tez va fokuslangan login oqimi bilan platformaga qayting. Keraksiz menyular yo'q, faqat kirish va davom etish.",
        verbose_name="Login chap panel matni",
    )
    login_panel_badge = models.CharField(max_length=60, default="Login", verbose_name="Login form badge")
    login_panel_heading = models.CharField(max_length=120, default="Hisobga kirish", verbose_name="Login form sarlavhasi")
    login_panel_intro = models.CharField(
        max_length=180,
        default="Email yoki username va parolingizni kiriting.",
        verbose_name="Login form izohi",
    )
    login_footer_prompt = models.CharField(
        max_length=120,
        default="Hali hisobingiz yo'qmi?",
        verbose_name="Login pastki matni",
    )
    login_footer_link_label = models.CharField(
        max_length=60,
        default="Ro'yxatdan o'ting",
        verbose_name="Login pastki link nomi",
    )

    register_visual_kicker = models.CharField(max_length=80, default="Create Account", verbose_name="Register kicker")
    register_visual_title = models.CharField(
        max_length=220,
        default="Yangi o'quvchi safarini chiroyli, tushunarli va ishonchli onboarding bilan boshlang.",
        verbose_name="Register chap panel sarlavhasi",
    )
    register_visual_description = models.TextField(
        default="Hisob yaratish bir necha maydondan iborat, lekin layout tez to'ldirishga moslangan. Mobil va desktopda bir xil silliq ishlaydi.",
        verbose_name="Register chap panel matni",
    )
    register_panel_badge = models.CharField(max_length=60, default="Sign Up", verbose_name="Register form badge")
    register_panel_heading = models.CharField(
        max_length=120,
        default="Hisob yaratish",
        verbose_name="Register form sarlavhasi",
    )
    register_panel_intro = models.CharField(
        max_length=180,
        default="Asosiy ma'lumotlarni to'ldiring va platformaga qo'shiling.",
        verbose_name="Register form izohi",
    )
    register_footer_prompt = models.CharField(
        max_length=120,
        default="Allaqachon hisobingiz bormi?",
        verbose_name="Register pastki matni",
    )
    register_footer_link_label = models.CharField(
        max_length=60,
        default="Kirish",
        verbose_name="Register pastki link nomi",
    )

    class Meta:
        verbose_name = "Auth sahifa sozlamasi"
        verbose_name_plural = "10. Auth sahifa sozlamalari"

    def __str__(self):
        return "Auth sahifa sozlamalari"


class LegalPage(models.Model):
    PAGE_PRIVACY = "privacy"
    PAGE_TERMS = "terms"
    PAGE_FAQ = "faq"
    PAGE_CHOICES = [
        (PAGE_PRIVACY, "Privacy Policy"),
        (PAGE_TERMS, "Terms of Service"),
        (PAGE_FAQ, "FAQ"),
    ]

    page_type = models.CharField(max_length=20, choices=PAGE_CHOICES, unique=True, verbose_name="Sahifa turi")
    title = models.CharField(max_length=150, verbose_name="Sarlavha")
    content = CKEditor5Field(config_name="default", verbose_name="Kontent")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Huquqiy sahifa"
        verbose_name_plural = "8. Huquqiy sahifalar"

    def __str__(self):
        return self.get_page_type_display()

    @classmethod
    def defaults_for(cls, page_type):
        defaults = {
            cls.PAGE_PRIVACY: {
                "title": "Privacy Policy",
                "content": (
                    "<h3>Ma'lumotlarni yig'ish</h3><p>Platforma foydalanuvchi hisobini yuritish uchun zarur "
                    "ma'lumotlarni yig'adi.</p><h3>Ma'lumotlardan foydalanish</h3><p>Ma'lumotlar xizmat sifatini "
                    "oshirish va tizimni ishlatish uchun foydalaniladi.</p>"
                ),
            },
            cls.PAGE_TERMS: {
                "title": "Terms of Service",
                "content": (
                    "<h3>Umumiy qoidalar</h3><p>Platformadan foydalanish orqali siz xizmat shartlariga rozilik "
                    "bildirasiz.</p><h3>Foydalanuvchi majburiyatlari</h3><p>Hisob ma'lumotlarini xavfsiz saqlash "
                    "foydalanuvchi zimmasida.</p>"
                ),
            },
            cls.PAGE_FAQ: {
                "title": "FAQ",
                "content": (
                    "<h3>Qanday ro'yxatdan o'taman?</h3><p>Bosh sahifadagi ro'yxatdan o'tish tugmasini bosing va "
                    "formani to'ldiring.</p><h3>To'lov qanday ishlaydi?</h3><p>Obuna tarifini tanlab, mavjud to'lov "
                    "usuli orqali to'lovni amalga oshirasiz.</p>"
                ),
            },
        }
        return defaults[page_type]
