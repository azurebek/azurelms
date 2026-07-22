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
    AI_MODEL_25_FLASH_LITE = 'gemini-2.5-flash-lite'
    AI_MODEL_31_PRO = 'gemini-3.1-pro-preview'
    AI_MODEL_35_FLASH = 'gemini-3.5-flash'
    AI_MODEL_31_FLASH_LITE = 'gemini-3.1-flash-lite'
    AI_MODEL_CHOICES = [
        (AI_MODEL_25_FLASH, "Gemini 2.5 Flash"),
        (AI_MODEL_25_FLASH_LITE, "Gemini 2.5 Flash-Lite"),
        (AI_MODEL_31_PRO, "Gemini 3.1 Pro"),
        (AI_MODEL_35_FLASH, "Gemini 3.5 Flash"),
        (AI_MODEL_31_FLASH_LITE, "Gemini 3.1 Flash Lite"),
    ]
    ai_model = models.CharField(
        max_length=80,
        choices=AI_MODEL_CHOICES,
        default=AI_MODEL_25_FLASH,
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

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"


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
    CATEGORY_CHOICES = (
        (CATEGORY_MANUAL, "Manual"),
        (CATEGORY_SUBSCRIPTION, "Subscription"),
        (CATEGORY_SYSTEM, "System"),
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
        ordering = ["-created_at"]
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

