from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from core import teacher_views
from courses.models import Course, Exam, ExamSection, Lesson, Module
from messenger.models import ChatRoom, Message


@override_settings(GEMINI_API_KEY=None)
class BackofficeDashboardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff_user = User.objects.create_user(
            username="backoffice_staff",
            email="backoffice_staff@example.test",
            password="pass-12345",
            is_staff=True,
        )
        self.student_user = User.objects.create_user(
            username="backoffice_student",
            email="backoffice_student@example.test",
            password="pass-12345",
        )

    def test_staff_user_can_open_backoffice_dashboard(self):
        self.client.force_login(self.staff_user)

        response = self.client.get(reverse("backoffice_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "backoffice/dashboard.html")
        self.assertContains(response, "Backoffice")
        self.assertContains(response, "Faol o'quvchi")
        self.assertContains(response, "E'tibor talab qiladi")
        self.assertContains(response, "AI RAG index")
        self.assertIn("rag_status", response.context)

    def test_non_staff_user_is_redirected_from_backoffice_dashboard(self):
        self.client.force_login(self.student_user)

        response = self.client.get(reverse("backoffice_dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response["Location"])

    def test_staff_user_can_open_backoffice_prototype_pages(self):
        course = Course.objects.create(
            title="Backoffice Course",
            description="Course description",
            instructor=self.staff_user,
            level="beginner",
            duration=10,
            price=1000,
        )
        module = Module.objects.create(course=course, title="Intro", order=1)
        lesson = Lesson.objects.create(module=module, title="First lesson", order=1, content="<p>Body</p>")
        exam = Exam.objects.create(
            course=course,
            title="Final exam",
            exam_type="final",
            weight_percentage=60,
            passing_score=60,
            max_attempts=2,
        )
        ExamSection.objects.create(
            exam=exam,
            title="Reading",
            section_type="reading",
            instructions="Read the text.",
            max_score=20,
            time_limit_minutes=20,
            order=1,
        )
        chat_room = ChatRoom.objects.create(room_type="ai", name="Backoffice AI chat")
        chat_room.participants.add(self.student_user)
        Message.objects.create(room=chat_room, text="Monitoring uchun test xabar", is_ai_response=True)
        self.client.force_login(self.staff_user)

        # Markerlar yangi AdminShell sahifa sarlavhalariga mos
        checks = (
            (reverse("backoffice_users"), "Foydalanuvchilar"),
            (reverse("backoffice_chats"), "Suhbatlar"),
            (reverse("backoffice_course_create"), "Yangi kurs"),
            (reverse("backoffice_course_edit", kwargs={"course_id": course.pk}), course.title),
            (reverse("backoffice_lessons"), "Dars muharriri"),
            (reverse("backoffice_lesson_edit", kwargs={"lesson_id": lesson.pk}), lesson.title),
            (reverse("backoffice_exams"), "Imtihon muharriri"),
            (reverse("backoffice_exam_edit", kwargs={"exam_id": exam.pk}), exam.title),
        )

        for url, marker in checks:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, marker)

        owner_only = self.client.get(reverse("backoffice_ai_control"))
        self.assertEqual(owner_only.status_code, 302)


class TeacherPanelTests(TestCase):
    """TeacherShell — kirish huquqi, grading oqimi, davomat."""

    def setUp(self):
        import datetime

        from cohorts.models import Cohort, Enrollment
        from courses.models import Assignment, AssignmentSubmission, ExamAttempt, Question

        User = get_user_model()
        self.teacher = User.objects.create_user(
            username="tch_teacher",
            email="tch_teacher@example.test",
            password="pass-12345",
            is_staff=True,
            first_name="Dilnoza",
        )
        self.student = User.objects.create_user(
            username="tch_student",
            email="tch_student@example.test",
            password="pass-12345",
            first_name="Nigora",
        )
        self.course = Course.objects.create(
            title="Teacher Panel Course",
            description="d",
            instructor=self.teacher,
            level="beginner",
        )
        self.cohort = Cohort.objects.create(
            name="Teacher Panel Cohort",
            course=self.course,
            start_date=datetime.date(2026, 5, 1),
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student, cohort=self.cohort, status="active"
        )
        module = Module.objects.create(course=self.course, title="1-modul", order=1)
        self.lesson = Lesson.objects.create(module=module, title="Teacher Lesson", order=1)
        assignment = Assignment.objects.create(
            lesson=self.lesson, title="Teacher HW", description="<p>d</p>", max_xp=20
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=assignment, student=self.student, answer_text="Mening javobim"
        )
        self.exam = Exam.objects.create(
            course=self.course,
            title="Teacher Panel Exam",
            exam_type="final",
            weight_percentage=100,
            passing_score=50,
            max_attempts=2,
        )
        self.section = ExamSection.objects.create(
            exam=self.exam,
            title="Writing",
            section_type="writing",
            instructions="Yozing.",
            max_score=10,
            time_limit_minutes=30,
            order=1,
        )
        self.question = Question.objects.create(
            exam_section=self.section, text="Esse yozing", points=10, min_word_count=3
        )
        self.attempt = ExamAttempt.objects.create(
            student=self.student, exam=self.exam, attempt_number=1
        )
        self.attempt.answers.create(
            question=self.question, answer_text="Bir ikki uch beshta"
        )
        self.attempt.submit_for_review()

    def test_non_staff_is_redirected(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("teacher_dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/users/login/", response["Location"])

    def test_teacher_pages_render(self):
        self.client.force_login(self.teacher)
        checks = (
            (reverse("teacher_dashboard"), "Assalomu alaykum"),
            (reverse("teacher_cohorts"), "Teacher Panel Cohort"),
            (reverse("teacher_students"), "tch_student@example.test"),
            (reverse("teacher_courses"), "Teacher Panel Course"),
            (reverse("teacher_grading"), "Teacher Panel Exam"),
            (reverse("teacher_attendance"), "Davomat olish"),
        )
        for url, marker in checks:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, marker)

    def test_exam_grading_flow_saves_and_finalizes(self):
        self.client.force_login(self.teacher)

        detail_url = reverse("teacher_grade_exam", kwargs={"attempt_id": self.attempt.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bir ikki uch beshta")

        answer = self.attempt.answers.get(question=self.question)
        review = self.attempt.section_reviews.get(section=self.section)
        response = self.client.post(
            detail_url,
            {
                f"answer_score_{answer.id}": "8",
                f"answer_feedback_{answer.id}": "Yaxshi esse, grammatikaga ahamiyat.",
                f"section_score_{review.id}": "8",
                f"section_feedback_{review.id}": "Umumiy yaxshi",
                "review_notes": "Barakalla",
                "action": "finalize",
            },
        )
        self.assertEqual(response.status_code, 302)

        answer.refresh_from_db()
        review.refresh_from_db()
        self.attempt.refresh_from_db()
        self.assertEqual(float(answer.awarded_score), 8.0)
        self.assertTrue(answer.is_graded)
        self.assertIn("grammatikaga", answer.grader_feedback)
        self.assertEqual(float(review.awarded_score), 8.0)
        self.assertTrue(self.attempt.is_reviewed)
        self.assertTrue(self.attempt.passed)
        self.assertEqual(float(self.attempt.score), 80.0)
        self.assertEqual(self.attempt.reviewed_by, self.teacher)

    def test_answer_score_is_clamped_to_question_points(self):
        self.client.force_login(self.teacher)
        answer = self.attempt.answers.get(question=self.question)
        detail_url = reverse("teacher_grade_exam", kwargs={"attempt_id": self.attempt.id})
        self.client.post(detail_url, {f"answer_score_{answer.id}": "999", "action": "save"})
        answer.refresh_from_db()
        self.assertEqual(float(answer.awarded_score), 10.0)

    def test_assignment_approval_flow(self):
        from courses.models import AssignmentSubmission

        self.client.force_login(self.teacher)
        url = reverse("teacher_grade_assignment", kwargs={"submission_id": self.submission.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mening javobim")

        response = self.client.post(
            url,
            {"teacher_feedback": "Ajoyib ish", "awarded_xp": "15", "action": "approve"},
        )
        self.assertEqual(response.status_code, 302)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, AssignmentSubmission.STATUS_APPROVED)
        self.assertEqual(self.submission.awarded_xp, 15)
        self.assertEqual(self.submission.reviewed_by, self.teacher)

    def test_attendance_marking_creates_records(self):
        from cohorts.models import Attendance

        self.client.force_login(self.teacher)
        url = reverse("teacher_attendance")
        response = self.client.post(
            url,
            {
                "cohort": self.cohort.id,
                "lesson": self.lesson.id,
                f"att_{self.enrollment.id}": "present",
            },
        )
        self.assertEqual(response.status_code, 302)
        record = Attendance.objects.get(enrollment=self.enrollment, lesson=self.lesson)
        self.assertEqual(record.status, "present")
        self.assertEqual(record.marked_by, self.teacher)

        # qayta belgilash mavjud yozuvni yangilaydi, dublikat yaratmaydi
        self.client.post(
            url,
            {
                "cohort": self.cohort.id,
                "lesson": self.lesson.id,
                f"att_{self.enrollment.id}": "absent",
            },
        )
        self.assertEqual(
            Attendance.objects.filter(enrollment=self.enrollment, lesson=self.lesson).count(), 1
        )
        record.refresh_from_db()
        self.assertEqual(record.status, "absent")


class BackofficeAIControlTests(TestCase):
    """Owner-only AI boshqaruv markazi — sozlama saqlash va reset qo'llash."""

    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="aic_staff", email="aic@example.test", password="pass-12345", is_staff=True
        )
        self.owner = User.objects.create_superuser(
            username="aic_owner", email="aic-owner@example.test", password="pass-12345"
        )
        self.student = User.objects.create_user(
            username="aic_student", email="aics@example.test", password="pass-12345"
        )

    def test_non_staff_redirected(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("backoffice_ai_control"))
        self.assertEqual(response.status_code, 302)

    def test_staff_without_owner_role_is_redirected(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("backoffice_ai_control"))
        self.assertEqual(response.status_code, 302)

    def test_save_settings(self):
        from aicontrol.models import AISettings

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("backoffice_ai_control"),
            {
                "action": "save_settings",
                "enforcement_enabled": "on",
                "default_5h_token_limit": "77000",
                "default_weekly_token_limit": "888000",
            },
        )
        self.assertEqual(response.status_code, 302)
        s = AISettings.load()
        self.assertTrue(s.enforcement_enabled)
        self.assertEqual(s.default_5h_token_limit, 77000)
        self.assertFalse(s.exempt_staff)  # checkbox yuborilmadi -> False

    def test_apply_mass_reset_event(self):
        from aicontrol.models import AIUsageResetEvent

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("backoffice_ai_control"),
            {"action": "apply_event", "scope": "all", "kind": "reset", "window": "both", "reason": "Navro'z"},
        )
        self.assertEqual(response.status_code, 302)
        event = AIUsageResetEvent.objects.latest("created_at")
        self.assertEqual(event.reason, "Navro'z")
        self.assertEqual(event.created_by, self.owner)


class TeacherScopeDefaultDenyTests(TestCase):
    """A0b — teacher paneli default-deny: biriktirilmagan staff hech nima ko'rmaydi.

    Ilgari `_teacher_courses()` biriktirilgan kursi yo'q staff uchun barcha
    kurslarni qaytarardi, ya'ni istalgan yangi staff butun platformaning
    o'quvchilari, baholash navbati va davomatini ko'ra olardi. Panelning
    barcha view'lari shu bitta scope'dan oziqlanadi, shuning uchun bu yerda
    ro'yxat sahifalari ham, ID bo'yicha ochiladigan baholash sahifalari ham
    tekshiriladi.
    """

    LIST_VIEWS = (
        "teacher_dashboard",
        "teacher_cohorts",
        "teacher_students",
        "teacher_courses",
        "teacher_grading",
        "teacher_attendance",
    )

    def setUp(self):
        import datetime

        from cohorts.models import Cohort, Enrollment
        from courses.models import Assignment, AssignmentSubmission, ExamAttempt, Question

        User = get_user_model()
        self.owner_teacher = User.objects.create_user(
            username="scope_owner", email="scope_owner@example.test",
            password="pass-12345", is_staff=True,
        )
        self.other_teacher = User.objects.create_user(
            username="scope_other", email="scope_other@example.test",
            password="pass-12345", is_staff=True,
        )
        self.unassigned_teacher = User.objects.create_user(
            username="scope_unassigned", email="scope_unassigned@example.test",
            password="pass-12345", is_staff=True,
        )
        self.superuser = User.objects.create_superuser(
            username="scope_super", email="scope_super@example.test", password="pass-12345",
        )
        self.student = User.objects.create_user(
            username="scope_student", email="scope_student@example.test", password="pass-12345",
        )

        self.course = Course.objects.create(
            title="Scoped Course", description="d",
            instructor=self.owner_teacher, level="beginner",
        )
        self.cohort = Cohort.objects.create(
            name="Scoped Cohort", course=self.course, start_date=datetime.date(2026, 5, 1),
        )
        Enrollment.objects.create(student=self.student, cohort=self.cohort, status="active")
        module = Module.objects.create(course=self.course, title="1-modul", order=1)
        lesson = Lesson.objects.create(module=module, title="Scoped Lesson", order=1)
        assignment = Assignment.objects.create(
            lesson=lesson, title="Scoped HW", description="<p>d</p>", max_xp=20,
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=assignment, student=self.student, answer_text="javob",
        )
        self.exam = Exam.objects.create(
            course=self.course, title="Scoped Exam", exam_type="final",
            weight_percentage=100, passing_score=50, max_attempts=2,
        )
        section = ExamSection.objects.create(
            exam=self.exam, title="Writing", section_type="writing",
            instructions="Yozing.", max_score=10, time_limit_minutes=30, order=1,
        )
        question = Question.objects.create(
            exam_section=section, text="Esse yozing", points=10, min_word_count=3,
        )
        self.attempt = ExamAttempt.objects.create(
            student=self.student, exam=self.exam, attempt_number=1,
        )
        self.attempt.answers.create(question=question, answer_text="bir ikki uch")
        self.attempt.submit_for_review()

    def test_unassigned_staff_sees_no_courses(self):
        self.assertEqual(list(teacher_views._teacher_courses(self.unassigned_teacher)), [])

    def test_assigned_teacher_sees_only_own_courses(self):
        self.assertEqual(
            list(teacher_views._teacher_courses(self.owner_teacher)), [self.course]
        )
        self.assertEqual(list(teacher_views._teacher_courses(self.other_teacher)), [])

    def test_superuser_still_sees_every_course(self):
        self.assertEqual(list(teacher_views._teacher_courses(self.superuser)), [self.course])

    def test_unassigned_staff_pages_render_but_stay_empty(self):
        self.client.force_login(self.unassigned_teacher)
        for name in self.LIST_VIEWS:
            with self.subTest(view=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(list(response.context["teacher_courses"]), [])
                self.assertEqual(response.context["grading_pending_count"], 0)

    def test_unassigned_staff_cannot_open_grading_detail_pages(self):
        self.client.force_login(self.unassigned_teacher)
        for name, kwargs in (
            ("teacher_grade_exam", {"attempt_id": self.attempt.id}),
            ("teacher_grade_assignment", {"submission_id": self.submission.id}),
        ):
            with self.subTest(view=name):
                self.assertEqual(self.client.get(reverse(name, kwargs=kwargs)).status_code, 404)

    def test_other_teacher_cannot_grade_foreign_submission(self):
        from courses.models import AssignmentSubmission

        self.client.force_login(self.other_teacher)
        response = self.client.post(
            reverse("teacher_grade_assignment", kwargs={"submission_id": self.submission.id}),
            {"action": "approve", "teacher_feedback": "boshqa o'qituvchi"},
        )
        self.assertEqual(response.status_code, 404)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, AssignmentSubmission.STATUS_PENDING)

    def test_unassigned_staff_attendance_has_no_cohort(self):
        self.client.force_login(self.unassigned_teacher)
        response = self.client.get(reverse("teacher_attendance"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["cohorts"]), [])
        self.assertIsNone(response.context["cohort"])

    def test_inactive_staff_gets_empty_scope(self):
        self.owner_teacher.is_active = False
        self.owner_teacher.save(update_fields=["is_active"])
        self.assertEqual(list(teacher_views._teacher_courses(self.owner_teacher)), [])

    def test_telegram_adapter_shares_the_same_cohort_scope(self):
        """Parity: bot adapteri web panel bilan bir xil scope'ni ko'rsatadi.

        Ilgari bot'da teskari qoida turardi — active staff barcha guruhlarni
        ko'rardi. Endi ikkala yuza ham `core.access` canonical scope'idan
        oziqlanadi, shuning uchun bu test dublikat mantiq qaytib kelsa yiqiladi.
        """
        from bot.services import teacher_cohorts_overview

        self.assertEqual(teacher_cohorts_overview(self.unassigned_teacher), [])
        self.assertEqual(teacher_cohorts_overview(self.other_teacher), [])
        self.assertEqual(
            [item["name"] for item in teacher_cohorts_overview(self.owner_teacher)],
            [self.cohort.name],
        )

    def test_telegram_grading_queue_respects_scope(self):
        from bot.services import teacher_grading_queue

        empty = teacher_grading_queue(self.unassigned_teacher)
        self.assertEqual((empty["exam_count"], empty["assignment_count"]), (0, 0))

        owned = teacher_grading_queue(self.owner_teacher)
        self.assertEqual((owned["exam_count"], owned["assignment_count"]), (1, 1))
