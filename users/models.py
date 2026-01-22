from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedModel


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None  # username fieldni butunlay olib tashlaymiz
    email = models.EmailField(_("email address"), unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    @property
    def display_name(self):
        if hasattr(self, "profile") and self.profile.display_name:
            return self.profile.display_name
        full_name = self.get_full_name()
        return full_name or self.email

    def __str__(self):
        return self.email


class Profile(TimeStampedModel):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="profile")

    display_name = models.CharField(max_length=50, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(blank=True)

    is_onboarded = models.BooleanField(default=False)

    streak_days = models.PositiveIntegerField(default=0)
    xp_points = models.PositiveIntegerField(default=0)

    GOAL_CHOICES = [
        ("study", "Magistratura"),
        ("work", "Ish"),
        ("travel", "Sayohat"),
    ]
    LEVEL_CHOICES = [
        ("zero", "Noldan"),
        ("a1", "A1"),
        ("b1", "B1"),
    ]

    goal = models.CharField(max_length=20, choices=GOAL_CHOICES, blank=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, blank=True)
    daily_commitment = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return self.display_name or self.user.email
