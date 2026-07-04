"""Smart Form Engine uchun users app formalari.

MUHIM: bu modul `users/forms.py` YONIDA yashaydi (users/forms/ package emas!) —
avvalgi `users/forms/smart_onboarding.py` namespace-package bo'lib, `users/forms.py`
moduli soyasida import qilib bo'lmasdi va @register_form hech qachon ishlamasdi.
Registratsiya `users/apps.py` ready() da import qilinishi bilan sodir bo'ladi.
"""
from pydantic import Field, field_validator

from ai.smart_form.base import BaseSmartForm
from ai.smart_form.registry import register_form

GOAL_ALIASES = {
    "work": "work", "ish": "work", "karyera": "work", "career": "work",
    "travel": "travel", "sayohat": "travel", "sayohat qilish": "travel",
    "exam": "exam", "imtihon": "exam", "study": "exam", "o'qish": "exam", "test": "exam",
    "personal": "personal", "shaxsiy": "personal", "qiziqish": "personal", "hobby": "personal",
    "other": "other", "boshqa": "other",
}

LEVEL_ALIASES = {
    "a1": "a1", "a2": "a2", "b1": "b1", "b2": "b2", "c1": "c1", "c2": "c2",
    "unknown": "unknown", "bilmayman": "unknown", "boshlang'ich": "a1", "beginner": "a1",
    "nol": "unknown", "0": "unknown",
}


@register_form("user_onboarding")
class UserOnboardingSmartForm(BaseSmartForm):
    goal: str = Field(
        description=(
            "O'quvchining turk tilini o'rganishdan maqsadi. Faqat shu qiymatlardan biri: "
            "work (ish/karyera), travel (sayohat), exam (imtihon/o'qish), "
            "personal (shaxsiy qiziqish), other (boshqa)."
        ),
        json_schema_extra={"priority": 100},
    )
    level: str = Field(
        description=(
            "O'quvchining hozirgi turk tili darajasi. Faqat shu qiymatlardan biri: "
            "a1, a2, b1, b2, c1, c2, unknown (bilmasa)."
        ),
        json_schema_extra={"priority": 90},
    )

    @field_validator("goal", mode="before")
    @classmethod
    def normalize_goal(cls, value):
        key = str(value or "").strip().lower()
        return GOAL_ALIASES.get(key, "other")

    @field_validator("level", mode="before")
    @classmethod
    def normalize_level(cls, value):
        key = str(value or "").strip().lower()
        return LEVEL_ALIASES.get(key, "unknown")

    def submit(self, user):
        from django.urls import reverse

        from users.models import UserOnboarding

        UserOnboarding.objects.update_or_create(
            user=user,
            defaults={"goal": self.goal, "current_level": self.level},
        )
        # SKILL.md kontrakti: SUBMIT_SUCCESS|<redirect_url> — AI foydalanuvchiga link beradi
        return reverse("dashboard")
