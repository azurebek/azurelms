from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone


class CustomUser(AbstractUser):
    # Django'ning standart User modelini kengaytiramiz
    email = models.EmailField('email address', unique=True)

    # Telegram bilan bog'lash uchun eng muhim maydonlar
    telegram_id = models.BigIntegerField(unique=True, blank=True, null=True,
                                         help_text="O'quvchining Telegramdagi o'zgarmas ID raqami")
    telegram_username = models.CharField(max_length=100, blank=True, null=True)

    # Profil uchun
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    from core.utils import validate_file_size, validate_image_extension
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        validators=[validate_file_size, validate_image_extension]
    )
    bio = models.TextField(blank=True, null=True, help_text="O'zingiz haqida qisqacha ma'lumot")

    # O'quvchining umumiy XP (Tajriba) ballari
    total_xp = models.IntegerField(default=0, help_text="O'quvchining jami to'plagan XP ballari")

    # AzureAI suhbatining uslubi (messenger input menyusidan tanlanadi)
    AI_TONE_FRIENDLY = 'friendly'
    AI_TONE_FORMAL = 'formal'
    AI_TONE_BRIEF = 'brief'
    AI_TONE_DETAILED = 'detailed'
    AI_TONE_CHOICES = [
        (AI_TONE_FRIENDLY, "Samimiy va do'stona"),
        (AI_TONE_FORMAL, "Rasmiy va professional"),
        (AI_TONE_BRIEF, "Qisqa va aniq"),
        (AI_TONE_DETAILED, "Kengaytirilgan va tushuntiruvchi"),
    ]
    ai_tone = models.CharField(
        max_length=16,
        choices=AI_TONE_CHOICES,
        default=AI_TONE_FRIENDLY,
        help_text="AzureAI yordamchisi javob beradigan uslub",
    )
    AI_MODEL_25_FLASH = 'gemini-2.5-flash'
    AI_MODEL_35_FLASH_LITE = 'gemini-3.5-flash-lite'
    AI_MODEL_31_PRO = 'gemini-3.1-pro-preview'
    AI_MODEL_35_FLASH = 'gemini-3.5-flash'
    AI_MODEL_31_FLASH_LITE = 'gemini-3.1-flash-lite'
    AI_MODEL_CHOICES = [
        (AI_MODEL_25_FLASH, "Gemini 2.5 Flash"),
        (AI_MODEL_35_FLASH_LITE, "Gemini 3.5 Flash Lite"),
        (AI_MODEL_31_PRO, "Gemini 3.1 Pro"),
        (AI_MODEL_35_FLASH, "Gemini 3.5 Flash"),
        (AI_MODEL_31_FLASH_LITE, "Gemini 3.1 Flash Lite"),
    ]
    ai_model = models.CharField(
        max_length=80,
        choices=AI_MODEL_CHOICES,
        default=AI_MODEL_31_FLASH_LITE,
        help_text="AzureAI javob yaratishda birinchi ishlatadigan Gemini modeli",
    )
    ai_memory_enabled = models.BooleanField(
        default=True,
        help_text="AzureAI uzoq muddatli xotirasi yoqilganmi (o'quvchi shaxsiy faktlarni eslab qolish/foydalanishga ruxsat berishi)",
    )
    AI_WEB_SEARCH_LIGHT = "light"
    AI_WEB_SEARCH_MEDIUM = "medium"
    AI_WEB_SEARCH_HEAVY = "heavy"
    AI_WEB_SEARCH_EFFORT_CHOICES = [
        (AI_WEB_SEARCH_LIGHT, "Yengil — faqat aniq so'rov bo'lsa"),
        (AI_WEB_SEARCH_MEDIUM, "O'rta — vaqtga oid savollarda avtomatik"),
        (AI_WEB_SEARCH_HEAVY, "Og'ir — har savolda AI o'zi qaror qiladi"),
    ]
    ai_web_search_effort = models.CharField(
        max_length=16,
        choices=AI_WEB_SEARCH_EFFORT_CHOICES,
        default=AI_WEB_SEARCH_LIGHT,
        help_text="AzureAI internet qidiruvini qanchalik faol ishlatishi",
    )

    @classmethod
    def effective_ai_model_choices(cls):
        """Return only models admitted by the current Gemini allowlist.

        Database field choices remain backwards-compatible so old rows can be
        read, while every current UI and mutation endpoint shares this narrower
        runtime policy.
        """
        raw_models = getattr(settings, "GEMINI_FREE_MODEL_ALLOWLIST", ())
        if isinstance(raw_models, str):
            raw_models = raw_models.split(",")
        try:
            allowed = [str(value).strip() for value in raw_models if str(value).strip()]
        except TypeError:
            allowed = []
        allowed = list(dict.fromkeys(allowed)) or [
            cls.AI_MODEL_31_FLASH_LITE,
            cls.AI_MODEL_35_FLASH_LITE,
        ]
        labels = dict(cls.AI_MODEL_CHOICES)
        return [(value, labels.get(value, value)) for value in allowed]

    @classmethod
    def effective_ai_web_search_effort_choices(cls):
        """Hide the costly heavy search mode while free-tier mode is active."""
        choices = list(cls.AI_WEB_SEARCH_EFFORT_CHOICES)
        if bool(getattr(settings, "AI_FREE_TIER_MODE", False)):
            choices = [
                (value, label)
                for value, label in choices
                if value != cls.AI_WEB_SEARCH_HEAVY
            ]
        return choices

    # To'qnashuvni (clash) oldini olish uchun
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        # Admin panelda o'quvchining ismi va username'i chiroyli chiqib turishi uchun
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.username})"
        return self.username

    @property
    def streak_days(self):
        """Shablonlar uchun jonli seriya qiymati (buzilgan bo'lsa 0).

        Templatelar `request.user.streak_days` ni ishlatadi. Haqiqiy manba —
        `LearnerStreak` modeli va `users.streak` servisi. Real qiymat uchun
        `streak` obyektini `select_related`/`prefetch_related('streak')` bilan
        oldindan yuklang, aks holda har chaqiruv qo'shimcha so'rov qiladi.
        """
        try:
            streak = self.streak
        except LearnerStreak.DoesNotExist:
            return 0
        return streak.effective_current()

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"


class LearnerStreak(models.Model):
    """O'quvchining kunlik faollik seriyasi (Duolingo uslubidagi streak).

    Seriya DAVOMATDAN emas, o'quvchining o'z tashabbusi bilan qilgan
    kunlik MALAKALI O'QUV HARAKATIDAN oshadi (dars tugatish, quiz/vazifa
    topshirish, imtihon urinishi, jonli darsga qatnashish). Bitta canonical
    yozuv nuqtasi — `users.streak.record_activity`; boshqa hech joy bu
    maydonlarni to'g'ridan-to'g'ri o'zgartirmaydi.

    "Muzlatish" (freeze) o'tkazib yuborilgan bir kunni himoya qiladi: seriya
    uzilmaydi, o'rniga bitta freeze sarflanadi.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='streak',
    )
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    total_active_days = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    freezes_available = models.PositiveIntegerField(default=0)
    freezes_used_total = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "O'quv seriyasi"
        verbose_name_plural = "O'quv seriyalari"

    def __str__(self):
        return f"{self.user.username}: {self.current_streak} kun"

    def effective_current(self, today=None):
        """Bugungi jonli seriya qiymati — o'qish paytida hisoblanadi, yozmaydi.

        Saqlangan `current_streak` faqat keyingi faollik yoki kunlik
        maintenance job'da yangilanadi. Ko'rsatish uchun esa "bugun holati"
        muhim: seriya bugun yoki kecha (yoki freeze qamrovida) faol bo'lsa
        saqlangan qiymat, aks holda uzilgan — 0.
        """
        if self.last_activity_date is None or self.current_streak == 0:
            return 0
        today = today or timezone.localdate()
        gap = (today - self.last_activity_date).days
        if gap <= 0:
            return self.current_streak  # bugun faol
        # kechagacha bo'lgan bo'shliq freeze bilan qoplanadimi (bugun hali
        # hisobga olinmaydi — bugun uchun bir kun beriladi)
        missed = gap - 1
        if missed <= self.freezes_available:
            return self.current_streak
        return 0

    def is_active_today(self, today=None):
        today = today or timezone.localdate()
        return self.last_activity_date == today

    def at_risk(self, today=None):
        """Seriya bor, lekin bugun hali faollik yo'q — xavf ostida."""
        today = today or timezone.localdate()
        return self.effective_current(today) > 0 and not self.is_active_today(today)


class UserOnboarding(models.Model):
    """Ro'yxatdan o'tish wizard'i orqali olingan onboarding javoblari."""

    GOAL_WORK = "work"
    GOAL_TRAVEL = "travel"
    GOAL_EXAM = "exam"
    GOAL_PERSONAL = "personal"
    GOAL_OTHER = "other"
    GOAL_CHOICES = (
        (GOAL_WORK, "Ish / karyera"),
        (GOAL_TRAVEL, "Sayohat"),
        (GOAL_EXAM, "Imtihon"),
        (GOAL_PERSONAL, "Shaxsiy qiziqish"),
        (GOAL_OTHER, "Boshqa"),
    )

    LEVEL_UNKNOWN = "unknown"
    LEVEL_A1 = "a1"
    LEVEL_A2 = "a2"
    LEVEL_B1 = "b1"
    LEVEL_B2 = "b2"
    LEVEL_C1 = "c1"
    LEVEL_C2 = "c2"
    LEVEL_CHOICES = (
        (LEVEL_UNKNOWN, "Bilmayman"),
        (LEVEL_A1, "A1 — Boshlang'ich"),
        (LEVEL_A2, "A2 — Asosiy"),
        (LEVEL_B1, "B1 — O'rta"),
        (LEVEL_B2, "B2 — O'rta yuqori"),
        (LEVEL_C1, "C1 — Yuqori"),
        (LEVEL_C2, "C2 — Mukammal"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="onboarding",
    )
    goal = models.CharField(max_length=20, choices=GOAL_CHOICES, blank=True, default="")
    current_level = models.CharField(max_length=10, choices=LEVEL_CHOICES, blank=True, default="")
    extra = models.JSONField(blank=True, null=True, help_text="Kelajakda qo'shimcha savollar uchun")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Onboarding javobi"
        verbose_name_plural = "Onboarding javoblari"

    def __str__(self):
        return f"Onboarding: {self.user}"


class Notification(models.Model):
    CATEGORY_MANUAL = "manual"
    CATEGORY_SUBSCRIPTION = "subscription"
    CATEGORY_SYSTEM = "system"
    CATEGORY_STREAK = "streak"
    CATEGORY_CHOICES = (
        (CATEGORY_MANUAL, "Manual"),
        (CATEGORY_SUBSCRIPTION, "Subscription"),
        (CATEGORY_SYSTEM, "System"),
        (CATEGORY_STREAK, "Streak"),
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=180, blank=True, default="")
    message = models.TextField()
    icon = models.CharField(max_length=40, default="bell")
    url = models.CharField(max_length=255, blank=True, default="")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_SYSTEM)
    external_key = models.CharField(max_length=120, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A deterministic secondary key matters when two notifications are
        # created inside the same database timestamp tick.
        ordering = ["-created_at", "-id"]
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
        unique_together = ("recipient", "external_key")

    def __str__(self):
        return f"{self.recipient} | {self.message[:40]}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])


class NotificationBroadcast(models.Model):
    TARGET_ALL = "all"
    TARGET_USERS = "users"
    TARGET_COHORTS = "cohorts"
    TARGET_CHOICES = (
        (TARGET_ALL, "Barchaga"),
        (TARGET_USERS, "Tanlangan foydalanuvchilarga"),
        (TARGET_COHORTS, "Tanlangan cohort a'zolariga"),
    )

    title = models.CharField(max_length=180, blank=True, default="")
    message = models.TextField()
    icon = models.CharField(max_length=40, default="megaphone")
    url = models.CharField(max_length=255, blank=True, default="")
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES, default=TARGET_ALL)
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="manual_notification_broadcasts")
    cohorts = models.ManyToManyField("cohorts.Cohort", blank=True, related_name="notification_broadcasts")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_notification_broadcasts",
    )
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bildirishnoma jo'natish"
        verbose_name_plural = "Bildirishnoma jo'natishlar"

    def __str__(self):
        return f"{self.get_target_type_display()} | {self.message[:50]}"


class TelegramAuthSession(models.Model):
    """Telegram deep-link orqali kirish uchun bir martalik token.

    Xavfsizlik shartlari:
    - token faqat BIR MARTA ishlatiladi (`consumed_at` bilan qulflanadi);
    - `authenticated` holat ham muddatga bo'ysunadi, abadiy yashamaydi;
    - tokenni boshlagan brauzergagina beriladi (`client_key`) — tokenni
      bilgan uchinchi shaxs o'z brauzerida login bo'lolmaydi.
    """

    STATUS_PENDING = 'pending'
    STATUS_AUTHENTICATED = 'authenticated'
    STATUS_EXPIRED = 'expired'
    STATUS_USED = 'used'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Kutilmoqda'),
        (STATUS_AUTHENTICATED, 'Tizimga kirdi'),
        (STATUS_EXPIRED, 'Muddati o\'tgan'),
        (STATUS_USED, 'Ishlatilgan'),
    ]

    TOKEN_TTL = timezone.timedelta(minutes=5)

    token = models.CharField(max_length=64, unique=True)
    client_key = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text="Tokenni boshlagan brauzer sessiyasiga bog'lanish kaliti.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='telegram_auth_sessions'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Telegram Auth Sessiyasi"
        verbose_name_plural = "Telegram Auth Sessiyalari"

    def __str__(self):
        return f"AuthSession: {self.token[:8]}... | Status: {self.status}"

    def is_expired(self):
        return timezone.now() - self.created_at > self.TOKEN_TTL

    def is_valid(self):
        """Bot tomonida tasdiqlash uchun: hali kutilmoqda va muddati o'tmagan."""
        return self.status == self.STATUS_PENDING and not self.is_expired()

    def is_claimable(self):
        """Brauzer login qilib olishi mumkinmi.

        Bir marta olingach (`consumed_at`) yoki muddati o'tgach yopiladi.
        """
        return (
            self.status == self.STATUS_AUTHENTICATED
            and self.consumed_at is None
            and self.user_id is not None
            and not self.is_expired()
        )



class TelegramLinkToken(models.Model):
    """Mavjud hisobga Telegram akkauntini ulash uchun bir martalik havola (A4).

    Ilgari havola `Signer().sign(user.id)` ning base64'i edi. Bu ikki jihatdan
    noto'g'ri chiqdi:

    1. **Muddat yo'q edi.** `Signer` vaqt qo'shmaydi va har safar bir xil
       token beradi, ya'ni havola abadiy yaroqli bearer credential edi. U bir
       marta sizib chiqsa (skrinshot, forward, brauzer tarixi), topgan odam
       o'z Telegramini o'quvchining hisobiga ulab, botda o'sha o'quvchi
       sifatida ishlayverardi. Yonidagi login oqimi (`TelegramAuthSession`)
       esa 5 daqiqalik va bir martalik — ulash yo'li tasodifan zaifroq edi.

    2. **`user.id >= 10000` da havola umuman ishlamasdi.** Telegram `start`
       payloadiga 64 belgi chegara qo'yadi; imzolangan IDning base64'i
       4 xonali IDda aynan 64 ga yetib, 5 xonalisida 66 bo'lardi.

    Qisqa, tasodifiy va bazada saqlanadigan token ikkala muammoni ham yopadi:
    22 belgi (prefikssiz) va muddat/ishlatilganlik holati yozib boriladi.
    """

    TOKEN_TTL = timezone.timedelta(minutes=30)

    token = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_link_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Telegram ulash tokeni"
        verbose_name_plural = "Telegram ulash tokenlari"
        ordering = ["-created_at"]

    def __str__(self):
        return f"LinkToken: {self.token[:8]}... | user={self.user_id}"

    def is_expired(self, *, now=None):
        return (now or timezone.now()) - self.created_at > self.TOKEN_TTL

    def is_valid(self, *, now=None):
        return self.consumed_at is None and not self.is_expired(now=now)

    def consume(self, *, now=None):
        self.consumed_at = now or timezone.now()
        self.save(update_fields=["consumed_at"])

    @classmethod
    def issue(cls, user, *, now=None):
        """Foydalanuvchi uchun yaroqli token beradi.

        Hali yaroqli token bo'lsa o'sha qaytariladi: profil sahifasini qayta
        ochish endigina nusxalangan havolani bekor qilmasligi kerak.
        """
        import secrets

        now = now or timezone.now()
        existing = (
            cls.objects.filter(user=user, consumed_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if existing and existing.is_valid(now=now):
            return existing
        return cls.objects.create(user=user, token=secrets.token_urlsafe(16))
