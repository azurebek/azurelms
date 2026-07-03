from ai.smart_form.base import BaseSmartForm
from ai.smart_form.registry import register_form
from pydantic import Field
from users.models import UserOnboarding

@register_form("user_onboarding")
class UserOnboardingSmartForm(BaseSmartForm):
    goal: str = Field(
        description="The user's main goal for learning Turkish (e.g., work, travel, study, exam, personal)",
        json_schema_extra={"priority": 100}
    )
    level: str = Field(
        description="The user's current Turkish proficiency level (A1, A2, B1, B2, C1, C2, or unknown)",
        json_schema_extra={"priority": 90}
    )

    def submit(self, user):
        onboarding, created = UserOnboarding.objects.update_or_create(
            user=user,
            defaults={
                "goal": self.goal[:100],  # safety truncation
                "current_level": self.level[:20]
            }
        )
        return "ONBOARDING_COMPLETED"
