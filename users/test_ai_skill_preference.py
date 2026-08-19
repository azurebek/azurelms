"""AI skill tanlovi saqlanishi uchun testlar.

Ilgari skill faqat brauzer xotirasida turardi: `initSkillPicker` JS
o'zgaruvchisini o'zgartirar, shablon esa `data-current-ai-skill="auto"` ni
qattiq yozardi. Sahifa yangilanishi bilan tanlov yo'qolardi. Tanlagich chat
sarlavhasida yashiringanida buni hech kim sezmasdi; kompozitorga ko'tarilgach,
saqlanishi kutiladi.
"""

from django.test import TestCase
from django.urls import reverse

from ai.skills.registry import SkillRegistry
from users.models import CustomUser as User


def _a_real_skill_slug():
    return SkillRegistry().all()[0].slug


class AISkillChoicesTests(TestCase):
    def test_choices_track_the_skill_registry(self):
        """Qo'lda yozilgan ro'yxat yangi skill qo'shilganda eskiradi."""
        choices = dict(User.effective_ai_skill_choices())
        registry_slugs = {skill.slug for skill in SkillRegistry().all()}

        self.assertIn("auto", choices, "avtomatik routing har doim variant bo'lib qolishi kerak")
        self.assertEqual(
            set(choices) - {"auto"}, registry_slugs,
            "skill variantlari registrdan olinishi shart, aks holda yangi skill UIda ko'rinmaydi",
        )


class AISkillUpdateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="skill-user",
            email="skill-user@example.com",
            password="testpass123",
        )
        self.client.force_login(self.user)

    def test_ajax_update_saves_ai_skill(self):
        slug = _a_real_skill_slug()
        response = self.client.post(
            reverse("update_ai_skill"),
            {"ai_skill": slug},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["ai_skill"], slug)
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_skill, slug)

    def test_auto_returns_to_automatic_routing(self):
        self.user.ai_skill = _a_real_skill_slug()
        self.user.save(update_fields=["ai_skill"])

        response = self.client.post(
            reverse("update_ai_skill"),
            {"ai_skill": "auto"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_skill, "auto")

    def test_rejects_unknown_skill_without_writing(self):
        response = self.client.post(
            reverse("update_ai_skill"),
            {"ai_skill": "sehrli_skill"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_skill, "auto")

    def test_anonymous_cannot_change_the_skill(self):
        self.client.logout()
        response = self.client.post(reverse("update_ai_skill"), {"ai_skill": "auto"})

        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response.url)


class MessengerRendersSavedSkillTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="skill-render",
            email="skill-render@example.com",
            password="testpass123",
        )
        self.client.force_login(self.user)

    def test_panel_reflects_the_saved_skill_not_a_hardcoded_auto(self):
        slug = _a_real_skill_slug()
        self.user.ai_skill = slug
        self.user.save(update_fields=["ai_skill"])

        response = self.client.get(reverse("messenger:ai"))
        self.assertEqual(response.status_code, 200)

        html = response.content.decode()
        self.assertIn(f'data-current-ai-skill="{slug}"', html)
        self.assertNotIn(
            'data-current-ai-skill="auto"', html,
            "qattiq yozilgan 'auto' saqlangan tanlovni bosib ketadi",
        )
