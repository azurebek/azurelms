"""Demo seed imtihonni ham yaratishi kerak (A5).

2026-08-20 da imtihonni 568x320 landscape'da sinamoqchi bo'lganda ma'lum
bo'ldiki, `seed_demo` kurs, dars, vazifa va guruh yaratadi — ammo **imtihon
yaratmaydi**. Ya'ni imtihon yuzasi na avtomatik probe bilan, na owner tomonidan
qurilmada sinalishi mumkin emas edi: sinaydigan narsaning o'zi yo'q.

Speaking bo'limi alohida muhim: mikrofon oqimini faqat shu yerda tekshirish
mumkin va u qurilma sign-off'ining majburiy bandi.
"""

from django.test import TestCase, override_settings

from core.demo_seed import DEMO_MARK, seed_demo_data
from courses.models import Choice, Exam, ExamSection, Question


@override_settings(IS_LOCAL=True)
class DemoSeedExamTests(TestCase):
    def setUp(self):
        self.data = seed_demo_data()

    def test_seed_creates_a_demo_exam_on_the_demo_course(self):
        exam = Exam.objects.filter(course=self.data["course"]).first()
        self.assertIsNotNone(exam, "imtihonsiz A5 ning imtihon bandini sinab bo'lmaydi")
        self.assertIn(DEMO_MARK, exam.title, "demo yozuvlari `--wipe` uchun belgilanishi shart")

    def test_every_section_type_the_exam_ui_renders_is_present(self):
        """Har bo'lim turi boshqacha render qilinadi — bittasi yetmaydi."""
        exam = Exam.objects.filter(course=self.data["course"]).first()
        present = set(exam.sections.values_list("section_type", flat=True))

        for required in ("grammar_quiz", "reading", "writing", "listening", "speaking"):
            self.assertIn(required, present, f"`{required}` bo'limi yo'q — u yuza sinalmay qoladi")

    def test_choice_based_sections_have_answerable_questions(self):
        exam = Exam.objects.filter(course=self.data["course"]).first()
        quiz_section = exam.sections.filter(section_type="grammar_quiz").first()
        question = Question.objects.filter(exam_section=quiz_section).first()

        self.assertIsNotNone(question, "savolsiz bo'limda javob berish oqimi sinalmaydi")
        choices = Choice.objects.filter(question=question)
        self.assertGreaterEqual(choices.count(), 2, "kamida ikki variant bo'lmasa tanlov yo'q")
        self.assertEqual(choices.filter(is_correct=True).count(), 1, "aynan bitta to'g'ri javob")

    def test_written_sections_carry_the_word_limits_the_ui_shows(self):
        exam = Exam.objects.filter(course=self.data["course"]).first()
        writing = exam.sections.filter(section_type="writing").first()
        question = Question.objects.filter(exam_section=writing).first()

        self.assertIsNotNone(question)
        self.assertTrue(question.min_word_count, "so'z hisoblagichi UIda ko'rsatiladi — chegara kerak")
        self.assertGreater(question.max_word_count, question.min_word_count)

    def test_seeding_twice_does_not_duplicate_the_exam(self):
        seed_demo_data()
        self.assertEqual(Exam.objects.filter(course=self.data["course"]).count(), 1)
        self.assertEqual(
            ExamSection.objects.filter(exam__course=self.data["course"]).count(),
            5,
            "seed idempotent bo'lishi shart — runbook uni qayta-qayta chaqiradi",
        )


@override_settings(IS_LOCAL=True)
class DemoSeedTeacherLoginTests(TestCase):
    """Owner o'qituvchi oqimini qurilmada sinay olishi kerak (A5).

    Seed o'qituvchi yaratardi, ammo unga parol bermasdi — ya'ni davomat,
    baholash va dars ochish yuzalarini telefonda ochib ko'rishning iloji
    yo'q edi. O'quvchi hisobiga parol berilgan, o'qituvchiga esa yo'q:
    e'tibordan chetda qolgan.
    """

    def setUp(self):
        self.data = seed_demo_data()

    def test_demo_teacher_can_actually_log_in(self):
        from django.contrib.auth import authenticate

        teacher = self.data["teacher"]
        self.assertTrue(teacher.is_staff, "davomat sahifasi staff talab qiladi")
        self.assertIsNotNone(
            authenticate(username=teacher.username, password="demo12345"),
            "o'qituvchi paroli yo'q — teacher oqimi qurilmada sinalmay qoladi",
        )

    def test_seeding_twice_keeps_the_teacher_password_working(self):
        from django.contrib.auth import authenticate

        seed_demo_data()
        self.assertIsNotNone(authenticate(username="demo-teacher", password="demo12345"))


@override_settings(IS_LOCAL=True)
class DemoSeedCohortSizeTests(TestCase):
    """Bitta o'quvchi bilan davomat ro'yxati sinalmaydi (A5).

    Davomat sahifasi har o'quvchi uchun uch tugmali qator chizadi. Bitta
    qator bilan uzun ism, ko'p qatorli ro'yxat va scroll xulqi umuman
    ko'rinmaydi — 320px da ular aynan muammo chiqaradigan joylar.
    """

    def setUp(self):
        self.data = seed_demo_data()

    def test_cohort_has_enough_students_to_exercise_the_list(self):
        from cohorts.models import Enrollment

        active = Enrollment.objects.filter(
            cohort=self.data["cohort"], status=Enrollment.STATUS_ACTIVE
        ).count()
        self.assertGreaterEqual(active, 5, "qisqa ro'yxat mobil layoutni sinamaydi")

    def test_at_least_one_long_name_stresses_the_row_layout(self):
        from cohorts.models import Enrollment

        names = [
            e.student.get_full_name()
            for e in Enrollment.objects.filter(cohort=self.data["cohort"]).select_related("student")
        ]
        self.assertTrue(
            any(len(name) >= 28 for name in names),
            "uzun ism bo'lmasa, ism ustunining siqilishi topilmaydi: %s" % names,
        )

    def test_extra_students_are_marked_as_demo_data(self):
        """`--wipe` ularni ham tozalay olishi kerak."""
        from cohorts.models import Enrollment

        for enrollment in Enrollment.objects.filter(cohort=self.data["cohort"]):
            self.assertTrue(
                enrollment.student.username.startswith("demo-"),
                f"{enrollment.student.username} demo prefiksisiz — wipe uni qoldirib ketadi",
            )
