from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from users.context_processors import notification_context
from users.models import Notification
from cohorts.models import Cohort, Enrollment
from courses.models import Course, Lesson, LessonProgress, Module
from subscriptions.models import Plan


User = get_user_model()


class NotificationContextTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="notif-user",
            email="notif-user@example.com",
            password="testpass123",
        )

    def test_context_returns_full_unread_count_while_limiting_preview_list(self):
        for index in range(10):
            Notification.objects.create(
                recipient=self.user,
                title=f"Notif {index}",
                message=f"Message {index}",
            )

        request = self.factory.get("/")
        request.user = self.user

        context = notification_context(request)

        self.assertEqual(context["unread_notifications_count"], 10)
        self.assertEqual(len(context["notifications"]), 8)

    def test_context_exposes_sidebar_current_plan(self):
        teacher = User.objects.create_user(
            username="notif-teacher",
            email="notif-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        course = Course.objects.create(
            title="Notif Plan Course",
            description="Plan context test",
            instructor=teacher,
            level="beginner",
        )
        cohort = Cohort.objects.create(
            name="Notif Plan Cohort",
            course=course,
            start_date="2026-03-01",
        )
        plan = Plan.objects.create(
            name="Standard",
            price=99000,
            description="Standart tarif",
            order=1,
        )
        Enrollment.objects.create(
            student=self.user,
            cohort=cohort,
            status="active",
            plan=plan,
        )

        request = self.factory.get("/")
        request.user = self.user

        context = notification_context(request)

        self.assertEqual(context["sidebar_current_plan"], plan)


class DashboardProgressTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="dashboard-user",
            email="dashboard-user@example.com",
            password="testpass123",
        )
        self.teacher = User.objects.create_user(
            username="dashboard-teacher",
            email="dashboard-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.course = Course.objects.create(
            title="Dashboard Progress Course",
            description="Dashboard progress test",
            instructor=self.teacher,
            level="beginner",
        )
        module = Module.objects.create(course=self.course, title="1-modul", order=1)
        self.lesson_1 = Lesson.objects.create(module=module, title="1-dars", order=1)
        self.lesson_2 = Lesson.objects.create(module=module, title="2-dars", order=2)
        cohort = Cohort.objects.create(
            name="Dashboard Cohort",
            course=self.course,
            start_date="2026-03-01",
        )
        self.enrollment = Enrollment.objects.create(
            student=self.user,
            cohort=cohort,
            status="active",
        )
        self.client.force_login(self.user)

    def test_dashboard_uses_lesson_progress_for_course_progress(self):
        LessonProgress.objects.create(
            enrollment=self.enrollment,
            lesson=self.lesson_1,
            is_completed=True,
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["primary_enrollment"].dashboard_progress, 50)
        self.assertContains(response, "50%")

    def test_dashboard_shows_telegram_connect_prompt_for_unlinked_user(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["telegram_linked"])
        self.assertContains(response, "Telegram botimizga ulanib")
        self.assertContains(response, response.context["telegram_bot_link"])

    def test_dashboard_hides_telegram_prompt_and_shows_link_notification_for_linked_user(self):
        self.user.telegram_id = 6211651081
        self.user.telegram_username = "lmsazurebot_tester"
        self.user.save(update_fields=["telegram_id", "telegram_username"])
        Notification.objects.create(
            recipient=self.user,
            title="Telegram hisobi ulandi",
            message="Profilingiz Telegram botiga muvaffaqiyatli bog'landi.",
            icon="telegram",
            category=Notification.CATEGORY_SYSTEM,
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["telegram_linked"])
        self.assertNotContains(response, "Telegram botimizga ulanib")
        self.assertContains(response, "Telegram hisobi ulandi")
