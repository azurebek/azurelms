from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    # Django'ning standart User modelini kengaytiramiz (Ism, familiya, email o'zida bor)

    # Telegram bilan bog'lash uchun eng muhim maydonlar
    telegram_id = models.BigIntegerField(unique=True, blank=True, null=True,
                                         help_text="O'quvchining Telegramdagi o'zgarmas ID raqami")
    telegram_username = models.CharField(max_length=100, blank=True, null=True)

    # Profil uchun
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    # O'quvchining umumiy XP (Tajriba) ballari
    total_xp = models.IntegerField(default=0, help_text="O'quvchining jami to'plagan XP ballari")

    def __str__(self):
        # Admin panelda o'quvchining ismi va username'i chiroyli chiqib turishi uchun
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name} ({self.username})"
        return self.username

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"