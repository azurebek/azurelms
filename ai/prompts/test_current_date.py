"""AI bugungi sanani bilishi kerak — uni taxmin qilmasligi kerak.

2026-08-19/20 da owner "bugun sana nechi?" deb so'raganda AI uch xil xato
javob berdi: `Bugun [current_date: 2025-05-18]` (shablon o'rniga o'xshash
matnni o'zi to'qigan), `2025-yil 18-may` va `2026-yil 30-mart`.

Sabab oddiy: promptda sana **umuman yo'q** edi. `current_date` degan o'rin
kodda hech qachon mavjud bo'lmagan — model uni o'zi o'ylab topib, "tizim
ma'lumotiga ko'ra" deb taqdim etgan.

Bu web-qidiruv muammosi emas. Sana jonli ma'lumot emas: serverning o'zi
biladi. Free-tier'da grounding ataylab o'chiq (`AI_FREE_TIER_MODE`), lekin
sanani aytish uchun tashqi manba kerak emas.
"""

from datetime import date

from django.test import TestCase
from django.utils import timezone

from ai.prompts.builder import PromptBuilder
from ai.skills.registry import SkillRegistry
from users.models import CustomUser as User


class PromptCurrentDateTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="date-user", email="date-user@example.com", password="testpass123",
        )
        self.skill = SkillRegistry().get("general_chat")

    def _build(self):
        return PromptBuilder().build(
            student=self.student,
            skill=self.skill,
            long_term_memory="",
            dialogue="",
            conversation_summary="",
            lesson_context="",
            rag_context="",
            rag_access_note="",
            tool_context="",
            user_question="bugun sana nechi?",
        )

    def test_prompt_states_todays_date(self):
        prompt = self._build()
        today = timezone.localdate()

        self.assertIn(today.isoformat(), prompt,
                      "promptda bugungi sana bo'lmasa, model uni to'qiydi")

    def test_prompt_forbids_guessing_the_date(self):
        prompt = self._build()
        self.assertIn("TO'QIMA", prompt.upper().replace("TO‘QIMA", "TO'QIMA"),
                      "sanani taxmin qilish taqiqi promptda yozilgan bo'lishi kerak")

    def test_date_is_local_not_utc_day(self):
        """Toshkent UTC+5: yarim tundan keyin UTC hali kechagi kunda bo'ladi."""
        prompt = self._build()
        self.assertIn(timezone.localdate().isoformat(), prompt)
        self.assertNotIn("current_date:", prompt,
                         "shablon o'rniga o'xshash matn promptga tushmasligi kerak")

    def test_date_is_not_hardcoded(self):
        """Sana har build'da qayta o'qilishi kerak, modulga yozib qo'yilmasligi."""
        prompt = self._build()
        self.assertNotIn(date(2025, 5, 18).isoformat(), prompt)
        self.assertIn(timezone.localdate().isoformat(), prompt)
