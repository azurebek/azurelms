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

class LandingPage(SingletonModel):
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
    footer_background_image = models.ImageField(
        upload_to='landing/footer/',
        blank=True,
        null=True,
        verbose_name='Footer fon rasmi',
        help_text='Footer orqasida transparency overlay bilan ko\'rinadigan rasm.',
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

    class Meta:
        verbose_name = "Bosh sahifa sozlamasi"
        verbose_name_plural = "1. Bosh sahifa sozlamalari"

    def __str__(self):
        return "Bosh sahifa dizayn matnlari"


class Statistic(models.Model):
    value = models.CharField(max_length=50, help_text="Masalan: 5,000+", verbose_name="Qiymati")
    label = models.CharField(max_length=100, help_text="Masalan: Faol o'quvchilar", verbose_name="Nomi")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib raqami")
    
    class Meta:
        ordering = ['order']
        verbose_name = "Bosh sahifa statistikasi"
        verbose_name_plural = "2. Bosh sahifa statistikalari"

    def __str__(self):
        return f"{self.value} - {self.label}"


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

    class Meta:
        verbose_name = "Platforma sozlamasi"
        verbose_name_plural = "7. Platforma sozlamalari"

    def __str__(self):
        return "Platforma sozlamalari"


class LandingNavItem(models.Model):
    class LinkKey(models.TextChoices):
        HOME = "home", "Bosh sahifa"
        COURSES = "courses", "Kurslar"
        PRICING = "pricing", "Narxlar"
        ABOUT = "about", "Biz haqimizda"
        BLOG = "blog", "Blog"

    ROUTE_MAP = {
        LinkKey.HOME: "home",
        LinkKey.COURSES: "courses",
        LinkKey.PRICING: "subscriptions:pricing",
        LinkKey.ABOUT: "about",
        LinkKey.BLOG: "blog:list",
    }

    key = models.CharField(max_length=20, choices=LinkKey.choices, unique=True, verbose_name="Link turi")
    label = models.CharField(max_length=80, verbose_name="Navbar matni")
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
        return self.get_url_for_key(self.key)

    def is_active_for(self, request):
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
