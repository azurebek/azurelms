from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

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
