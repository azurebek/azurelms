from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.agent.types import AIRequest
from ai.skills.registry import SkillRegistry
from ai.tools.context import ToolContextService

from .models import (
    KnowledgeArticle,
    University,
    UniversityFaculty,
    UniversityPreparationCourse,
    UniversityProgram,
)


class SITAdvisorRoutingTests(TestCase):
    """Skill tanlash: SIT savollari sit_advisor'ga, core LMS savollari unga TUSHMASLIGI kerak."""

    def setUp(self):
        User = get_user_model()
        self.student = User.objects.create_user(
            username="sit_student",
            email="sit-student@example.test",
            password="pass-12345",
        )
        self.registry = SkillRegistry()

    def _slug_for(self, question):
        return self.registry.select_for_request(
            AIRequest(room=None, student=self.student, user_question=question)
        ).slug

    def test_sit_questions_route_to_advisor(self):
        cases = [
            "Turkiyada o'qishni xohlayman, qayerdan boshlay?",
            "Byudjetim 1500 dollar, qaysi universitet mos keladi?",
            "Kontrakt narxi eng arzon universitet qaysi?",
            "TOMER kerakmi yoki ingliz tilida o'qisam bo'ladimi?",
            "Talaba vizasi uchun nima qilishim kerak?",
            "Denklik hujjati qanday olinadi?",
            "Bakalavr uchun qabul ochiqmi?",
            "Stipendiya imkoniyatlari bormi?",
        ]
        for question in cases:
            self.assertEqual(self._slug_for(question), "sit_advisor", question)

    def test_core_lms_questions_do_not_route_to_advisor(self):
        """Regressiya himoyasi: til kursi auditoriyasi SIT'ga adashib tushmaydi."""
        cases = {
            "Shu darsdan quiz tuz": "quiz_generator",
            "Vazifamni tekshirib ber": "homework_checker",
            "Bu gapimni grammatika bo'yicha tuzat": "grammar_corrector",
            "Keyingi dars qaysi?": "course_navigator",
        }
        for question, expected in cases.items():
            self.assertEqual(self._slug_for(question), expected, question)

    def test_magistratura_certificate_question_stays_out_of_sit(self):
        """`magistratura` ataylab trigger emas — u sertifikat (core LMS) auditoriyasining so'zi."""
        slug = self._slug_for("Magistratura uchun sertifikat kerak, qanday tayyorlanaman?")
        self.assertNotEqual(slug, "sit_advisor")

    def test_time_sensitive_sit_question_prefers_catalog_over_web_search(self):
        """Medium effort'da ham SIT savoli webga emas, tekshirilgan katalogga boradi."""
        self.student.ai_web_search_effort = "medium"
        self.assertEqual(self._slug_for("Yangi qabul qachon boshlanadi universitetda"), "sit_advisor")

    def test_non_sit_time_sensitive_question_still_uses_web_search(self):
        """Web search pair-detection'i buzilmaganini tasdiqlaydi."""
        self.student.ai_web_search_effort = "medium"
        self.assertEqual(self._slug_for("Hozir kim chempion bo'lib turibdi"), "web_search")

    def test_advisor_skill_declares_catalog_tool(self):
        skill = self.registry.get("sit_advisor")
        self.assertIn("sit_catalog", skill.tool_slugs)
        self.assertTrue(skill.instructions.strip(), "SKILL.md yuklanmadi")


class SITCatalogToolTests(TestCase):
    """`sit_catalog` tool faqat nashr etilgan tekshirilgan ma'lumotni beradi."""

    def setUp(self):
        self.service = ToolContextService()
        self.skill = SkillRegistry().get("sit_advisor")

    def _render(self):
        context = self.service.build(
            request=AIRequest(room=None, student=None, user_question="Universitet tavsiya qil"),
            skill=self.skill,
        )
        return context

    def _create_university(self, *, name, short_name, is_published=True, **kwargs):
        defaults = {
            "city": "İstanbul",
            "admission_status": University.AdmissionStatus.OPEN,
            "tuition_from": 1200,
            "source_url": "https://example.edu.tr/international",
            "last_verified_on": date(2026, 7, 28),
        }
        defaults.update(kwargs)
        return University.objects.create(
            name=name,
            short_name=short_name,
            is_published=is_published,
            **defaults,
        )

    def test_empty_catalog_returns_honest_no_data_instruction(self):
        context = self._render()
        self.assertIn("sit_catalog", context.used_tools)
        self.assertIn("TO'QIMA", context.rendered)
        self.assertIn("katalog hali to'ldirilmoqda", context.rendered)

    def test_unpublished_university_is_never_exposed(self):
        self._create_university(name="Nashr etilgan", short_name="NE")
        # Nashr etilmagan yozuv uchun source/verified majburiy emas.
        University.objects.create(
            name="Yashirin universitet",
            short_name="YU",
            city="Ankara",
            is_published=False,
        )
        rendered = self._render().rendered
        self.assertIn("Nashr etilgan", rendered)
        self.assertNotIn("Yashirin universitet", rendered)

    def test_programs_and_preparation_courses_are_rendered(self):
        university = self._create_university(name="Texnik universitet", short_name="TU")
        faculty = UniversityFaculty.objects.create(university=university, name="Muhandislik")
        UniversityProgram.objects.create(
            faculty=faculty,
            name="Kompyuter muhandisligi",
            degree_level=UniversityProgram.DegreeLevel.BACHELOR,
            language=UniversityProgram.Language.ENGLISH,
            duration="4 yil",
            tuition_fee=1600,
        )
        UniversityPreparationCourse.objects.create(
            university=university,
            language="Turk tili",
            tuition_fee=1200,
        )

        rendered = self._render().rendered
        self.assertIn("Kompyuter muhandisligi", rendered)
        self.assertIn("Turk tili", rendered)
        self.assertIn("til tayyorlov", rendered)

    def test_inactive_program_is_not_rendered(self):
        university = self._create_university(name="Universitet A", short_name="UA")
        faculty = UniversityFaculty.objects.create(university=university, name="Muhandislik")
        UniversityProgram.objects.create(
            faculty=faculty,
            name="Yopilgan yo'nalish",
            degree_level=UniversityProgram.DegreeLevel.BACHELOR,
            language=UniversityProgram.Language.TURKISH,
            duration="4 yil",
            tuition_fee=1000,
            is_active=False,
        )
        self.assertNotIn("Yopilgan yo'nalish", self._render().rendered)

    def test_published_guides_are_listed(self):
        self._create_university(name="Universitet B", short_name="UB")
        KnowledgeArticle.objects.create(
            title="Talaba vizasi qo'llanmasi",
            category="Viza",
            body="<p>Matn</p>",
            is_published=True,
            source_url="https://example.gov.tr/visa",
            last_verified_on=date(2026, 7, 28),
        )
        KnowledgeArticle.objects.create(
            title="Qoralama qo'llanma",
            category="Viza",
            body="<p>Matn</p>",
            is_published=False,
        )
        rendered = self._render().rendered
        self.assertIn("Talaba vizasi qo'llanmasi", rendered)
        self.assertNotIn("Qoralama qo'llanma", rendered)

    def test_hard_rules_are_always_included(self):
        self._create_university(name="Universitet C", short_name="UC")
        rendered = self._render().rendered
        self.assertIn("QAT'IY QOIDALAR", rendered)
        self.assertIn("TO'QIMA", rendered)
        self.assertIn("huquqiy maslahat", rendered)

    def test_open_admission_universities_come_first(self):
        self._create_university(
            name="Yopiq universitet",
            short_name="YOP",
            admission_status=University.AdmissionStatus.CLOSED,
            order=1,
        )
        self._create_university(
            name="Ochiq universitet",
            short_name="OCH",
            admission_status=University.AdmissionStatus.OPEN,
            order=2,
        )
        rendered = self._render().rendered
        self.assertLess(
            rendered.index("Ochiq universitet"),
            rendered.index("Yopiq universitet"),
        )
