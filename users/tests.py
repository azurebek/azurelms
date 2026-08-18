import datetime

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from users.context_processors import notification_context
from users.models import Notification
from users.views import NotificationCenterView
from cohorts.models import Attendance, Cohort, Enrollment
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

    def test_context_does_not_create_subscription_notifications_on_render(self):
        teacher = User.objects.create_user(
            username="notif-render-teacher",
            email="notif-render-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        course = Course.objects.create(
            title="Notif Render Course",
            description="Render should stay read-only",
            instructor=teacher,
            level="beginner",
        )
        cohort = Cohort.objects.create(
            name="Notif Render Cohort",
            course=course,
            start_date="2026-03-01",
        )
        Enrollment.objects.create(
            student=self.user,
            cohort=cohort,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=timezone.localdate(),
        )

        request = self.factory.get("/")
        request.user = self.user
        notification_context(request)

        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 0)

    def test_notification_center_context_does_not_create_notifications(self):
        teacher = User.objects.create_user(
            username="notif-page-teacher",
            email="notif-page-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        course = Course.objects.create(
            title="Notif Page Course",
            description="Notification center should stay read-only",
            instructor=teacher,
            level="beginner",
        )
        cohort = Cohort.objects.create(
            name="Notif Page Cohort",
            course=course,
            start_date="2026-03-01",
        )
        Enrollment.objects.create(
            student=self.user,
            cohort=cohort,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=timezone.localdate(),
        )

        request = self.factory.get("/users/notifications/")
        request.user = self.user
        view = NotificationCenterView()
        view.setup(request)
        context = view.get_context_data()

        self.assertEqual(list(context["unread_notifications"]), [])
        self.assertEqual(Notification.objects.filter(recipient=self.user).count(), 0)


class AIToneUpdateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tone-user",
            email="tone-user@example.com",
            password="testpass123",
        )
        self.client.force_login(self.user)

    def test_ajax_update_saves_ai_tone(self):
        response = self.client.post(
            reverse("update_ai_tone"),
            {"ai_tone": User.AI_TONE_BRIEF},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["ai_tone"], User.AI_TONE_BRIEF)
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_tone, User.AI_TONE_BRIEF)

    def test_ajax_update_rejects_invalid_ai_tone(self):
        response = self.client.post(
            reverse("update_ai_tone"),
            {"ai_tone": "robot-poet"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_tone, User.AI_TONE_FRIENDLY)


@override_settings(
    AI_FREE_TIER_MODE=True,
    GEMINI_FREE_MODEL_ALLOWLIST=(
        User.AI_MODEL_25_FLASH,
        User.AI_MODEL_35_FLASH_LITE,
    ),
)
class AIModelUpdateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="model-user",
            email="model-user@example.com",
            password="testpass123",
        )
        self.client.force_login(self.user)

    def test_ajax_update_saves_ai_model(self):
        response = self.client.post(
            reverse("update_ai_model"),
            {"ai_model": User.AI_MODEL_35_FLASH_LITE},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["ai_model"], User.AI_MODEL_35_FLASH_LITE)
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_model, User.AI_MODEL_35_FLASH_LITE)

    def test_ajax_update_rejects_pro_preview_model_in_free_tier(self):
        response = self.client.post(
            reverse("update_ai_model"),
            {"ai_model": User.AI_MODEL_31_PRO},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_model, User.AI_MODEL_31_FLASH_LITE)

    def test_ajax_update_rejects_invalid_ai_model(self):
        response = self.client.post(
            reverse("update_ai_model"),
            {"ai_model": "gemini-mystery"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_model, User.AI_MODEL_31_FLASH_LITE)

    def test_regular_post_rejects_disallowed_model_with_400(self):
        response = self.client.post(
            reverse("update_ai_model"),
            {"ai_model": User.AI_MODEL_35_FLASH},
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_model, User.AI_MODEL_31_FLASH_LITE)


@override_settings(AI_FREE_TIER_MODE=True)
class AIWebSearchEffortUpdateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="effort-user",
            email="effort-user@example.com",
            password="testpass123",
        )
        self.client.force_login(self.user)

    def test_medium_effort_remains_available_in_free_tier(self):
        response = self.client.post(
            reverse("update_ai_web_search_effort"),
            {"ai_web_search_effort": User.AI_WEB_SEARCH_MEDIUM},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_web_search_effort, User.AI_WEB_SEARCH_MEDIUM)

    def test_heavy_effort_is_rejected_in_free_tier(self):
        response = self.client.post(
            reverse("update_ai_web_search_effort"),
            {"ai_web_search_effort": User.AI_WEB_SEARCH_HEAVY},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_web_search_effort, User.AI_WEB_SEARCH_LIGHT)

    def test_regular_heavy_post_is_rejected_with_400(self):
        response = self.client.post(
            reverse("update_ai_web_search_effort"),
            {"ai_web_search_effort": User.AI_WEB_SEARCH_HEAVY},
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.ai_web_search_effort, User.AI_WEB_SEARCH_LIGHT)


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

    def test_profile_shows_telegram_connect_button_for_unlinked_user(self):
        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["telegram_linked"])
        self.assertContains(response, response.context["telegram_bot_link"])

    def test_profile_shows_linked_username_for_linked_user(self):
        self.user.telegram_id = 6211651081
        self.user.telegram_username = "lmsazurebot_tester"
        self.user.save(update_fields=["telegram_id", "telegram_username"])

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["telegram_linked"])
        self.assertContains(response, "@lmsazurebot_tester")
        self.assertNotIn("telegram_bot_link", response.context)

    def test_dashboard_does_not_render_inline_telegram_or_notification_blocks(self):
        Notification.objects.create(
            recipient=self.user,
            title="Telegram hisobi ulandi",
            message="Profilingiz Telegram botiga muvaffaqiyatli bog'landi.",
            icon="telegram",
            category=Notification.CATEGORY_SYSTEM,
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Telegram botimizga ulanib")
        self.assertNotContains(response, "info-box--blue")

    def test_dashboard_lists_all_active_cohorts_for_multi_cohort_student(self):
        second_course = Course.objects.create(
            title="Dashboard Progress Course 2",
            description="Second dashboard course",
            instructor=self.teacher,
            level="beginner",
        )
        second_cohort = Cohort.objects.create(
            name="Second Dashboard Cohort",
            course=second_course,
            start_date="2026-03-15",
        )
        Enrollment.objects.create(
            student=self.user,
            cohort=second_cohort,
            status="active",
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["active_dashboard_enrollments"]), 2)
        self.assertContains(response, "Dashboard Cohort")
        self.assertContains(response, "Second Dashboard Cohort")
        self.assertNotContains(response, "Davom etayotgan kurs")
        self.assertContains(response, "Barcha guruhlaringiz")

    def test_dashboard_keeps_primary_focus_card_for_single_active_cohort(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Davom etayotgan kurs")

    def test_attendance_calendar_allows_switching_between_active_cohorts(self):
        second_course = Course.objects.create(
            title="Attendance Course 2",
            description="Second attendance course",
            instructor=self.teacher,
            level="beginner",
        )
        second_module = Module.objects.create(course=second_course, title="2-modul", order=1)
        second_lesson = Lesson.objects.create(module=second_module, title="2-dars", order=1)
        second_cohort = Cohort.objects.create(
            name="Attendance Switch Cohort",
            course=second_course,
            start_date="2026-03-15",
        )
        second_enrollment = Enrollment.objects.create(
            student=self.user,
            cohort=second_cohort,
            status="active",
        )
        Attendance.objects.create(
            enrollment=second_enrollment,
            lesson=second_lesson,
            date=timezone.localdate().replace(day=5),
            status=Attendance.STATUS_PRESENT,
        )

        response = self.client.get(
            reverse("attendance_calendar"),
            {"year": timezone.localdate().year, "month": timezone.localdate().month, "cohort": second_cohort.id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["attendance_cohort"], second_cohort)
        self.assertEqual(response.context["attendance_summary"]["present"], 1)
        self.assertContains(response, "Dashboard Cohort")
        self.assertContains(response, "Attendance Switch Cohort")

    def test_leaderboard_allows_switching_between_active_cohorts(self):
        second_course = Course.objects.create(
            title="Leaderboard Course 2",
            description="Second leaderboard course",
            instructor=self.teacher,
            level="beginner",
        )
        second_cohort = Cohort.objects.create(
            name="Leaderboard Cohort 2",
            course=second_course,
            start_date="2026-03-15",
        )
        Enrollment.objects.create(
            student=self.user,
            cohort=second_cohort,
            status="active",
        )
        second_student = User.objects.create_user(
            username="leaderboard-peer",
            email="leaderboard-peer@example.com",
            password="testpass123",
            total_xp=120,
        )
        Enrollment.objects.create(
            student=second_student,
            cohort=second_cohort,
            status="active",
        )

        response = self.client.get(reverse("leaderboard"), {"cohort": second_cohort.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["leaderboard_cohort"], second_cohort)
        self.assertEqual(response.context["selected_leaderboard_cohort_id"], second_cohort.id)
        self.assertContains(response, "Dashboard Cohort")
        self.assertContains(response, "Leaderboard Cohort 2")
        self.assertContains(response, "leaderboard-peer")

    def test_leaderboard_uses_cohort_specific_score_not_global_total_xp(self):
        second_course = Course.objects.create(
            title="Leaderboard Score Course 2",
            description="Second score course",
            instructor=self.teacher,
            level="beginner",
        )
        second_module = Module.objects.create(course=second_course, title="2-modul", order=1)
        second_lesson = Lesson.objects.create(module=second_module, title="2-dars", order=1)
        second_cohort = Cohort.objects.create(
            name="Leaderboard Cohort Score 2",
            course=second_course,
            start_date="2026-03-20",
        )
        second_enrollment = Enrollment.objects.create(
            student=self.user,
            cohort=second_cohort,
            status="active",
        )
        self.user.total_xp = 999
        self.user.save(update_fields=["total_xp"])

        LessonProgress.objects.create(
            enrollment=self.enrollment,
            lesson=self.lesson_1,
            is_completed=True,
        )
        LessonProgress.objects.create(
            enrollment=self.enrollment,
            lesson=self.lesson_2,
            is_completed=True,
        )
        LessonProgress.objects.create(
            enrollment=second_enrollment,
            lesson=second_lesson,
            is_completed=True,
        )

        cohort_one_response = self.client.get(reverse("leaderboard"), {"cohort": self.enrollment.cohort_id})
        cohort_two_response = self.client.get(reverse("leaderboard"), {"cohort": second_cohort.id})

        self.assertEqual(cohort_one_response.status_code, 200)
        self.assertEqual(cohort_two_response.status_code, 200)
        self.assertEqual(cohort_one_response.context["leaderboard_my_row"]["cohort_score"], self.lesson_1.xp_reward + self.lesson_2.xp_reward)
        self.assertEqual(cohort_two_response.context["leaderboard_my_row"]["cohort_score"], second_lesson.xp_reward)
        self.assertNotEqual(
            cohort_one_response.context["leaderboard_my_row"]["cohort_score"],
            self.user.total_xp,
        )


class SubscriptionLifecycleCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="expired-user",
            email="expired-user@example.com",
            password="testpass123",
        )
        self.teacher = User.objects.create_user(
            username="expired-teacher",
            email="expired-teacher@example.com",
            password="testpass123",
            is_staff=True,
        )
        course = Course.objects.create(
            title="Expired Course",
            description="Expired lifecycle test",
            instructor=self.teacher,
            level="beginner",
        )
        cohort = Cohort.objects.create(
            name="Expired Cohort",
            course=course,
            start_date="2026-03-01",
        )
        self.enrollment = Enrollment.objects.create(
            student=self.user,
            cohort=cohort,
            status=Enrollment.STATUS_ACTIVE,
            next_payment_deadline=timezone.localdate() - datetime.timedelta(days=3),
        )

    def test_notification_command_expires_overdue_enrollment_before_notifying(self):
        call_command("generate_subscription_notifications")

        self.enrollment.refresh_from_db()

        self.assertEqual(self.enrollment.status, Enrollment.STATUS_EXPIRED)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.user,
                external_key__startswith=f"sub-expired-{self.enrollment.id}-",
            ).exists()
        )
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.user,
                external_key__startswith=f"sub-due-{self.enrollment.id}-",
            ).exists()
        )


class MyCoursesViewTests(TestCase):
    """App-shell ichidagi "Mening kurslarim" sahifasi."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="mc-user", email="mc-user@example.com", password="testpass123"
        )
        self.teacher = User.objects.create_user(
            username="mc-teacher", email="mc-teacher@example.com", password="testpass123", is_staff=True
        )
        self.course = Course.objects.create(
            title="My Courses Turk tili",
            description="Test course",
            instructor=self.teacher,
            level="beginner",
        )
        module = Module.objects.create(course=self.course, title="1-modul", order=1)
        self.lesson_1 = Lesson.objects.create(module=module, title="1-dars", order=1)
        self.lesson_2 = Lesson.objects.create(module=module, title="2-dars", order=2)
        self.cohort = Cohort.objects.create(
            name="My Courses Cohort", course=self.course, start_date="2026-03-01"
        )
        self.enrollment = Enrollment.objects.create(
            student=self.user, cohort=self.cohort, status="active"
        )
        self.url = reverse("my_courses")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, (302, 403))

    def test_lists_enrolled_course_with_progress(self):
        LessonProgress.objects.create(
            enrollment=self.enrollment, lesson=self.lesson_1, is_completed=True
        )
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_nav"], "my_courses")
        self.assertEqual(response.context["count_all"], 1)
        self.assertEqual(response.context["count_active"], 1)
        self.assertContains(response, "My Courses Turk tili")
        self.assertContains(response, "My Courses Cohort")
        # 1/2 dars = 50%
        self.assertContains(response, "50%")
        self.assertContains(response, "Davom etish")

    def test_empty_state_for_user_without_enrollment(self):
        other = User.objects.create_user(
            username="mc-empty", email="mc-empty@example.com", password="testpass123"
        )
        self.client.force_login(other)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["count_all"], 0)
        self.assertContains(response, "Hali kursga yozilmagansiz")
        self.assertContains(response, "Kurslarni ko'rish")

    def test_does_not_show_other_users_courses(self):
        other_course = Course.objects.create(
            title="Begona kurs", description="x", instructor=self.teacher, level="beginner"
        )
        other_cohort = Cohort.objects.create(
            name="Begona Cohort", course=other_course, start_date="2026-03-01"
        )
        other_user = User.objects.create_user(
            username="mc-other", email="mc-other@example.com", password="testpass123"
        )
        Enrollment.objects.create(student=other_user, cohort=other_cohort, status="active")
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertContains(response, "My Courses Turk tili")
        self.assertNotContains(response, "Begona kurs")

    def test_pending_enrollment_shows_awaiting_state(self):
        self.enrollment.status = "pending"
        self.enrollment.save(update_fields=["status"])
        self.client.force_login(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.context["count_active"], 0)
        self.assertContains(response, "Tasdiq kutilmoqda")


from users.models import TelegramAuthSession
from bot.services import handle_telegram_auth_token

class TelegramCustomAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="auth-test-user",
            email="auth-test-user@example.com",
            password="testpass123",
            telegram_id=987654321,
        )

    def test_telegram_auth_init_creates_session(self):
        response = self.client.get(reverse('telegram_auth_init'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertIn('token', data)
        self.assertIn('bot_link', data)
        
        session = TelegramAuthSession.objects.filter(token=data['token']).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.status, TelegramAuthSession.STATUS_PENDING)

    def _start_flow(self):
        """Haqiqiy oqim: init token va client_key'ni brauzer sessiyasiga bog'laydi."""
        response = self.client.get(reverse('telegram_auth_init'))
        return response.json()['token']

    def test_telegram_auth_status_pending(self):
        token = self._start_flow()
        response = self.client.get(reverse('telegram_auth_status', args=[token]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['status'], 'pending')

    def test_telegram_auth_success_logs_in_existing_user(self):
        token = self._start_flow()

        result = handle_telegram_auth_token(f"auth_{token}", 987654321)
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "login_success")

        session = TelegramAuthSession.objects.get(token=token)
        self.assertEqual(session.status, TelegramAuthSession.STATUS_AUTHENTICATED)
        self.assertEqual(session.user, self.user)

        response = self.client.get(reverse('telegram_auth_status', args=[token]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['status'], 'authenticated')
        self.assertEqual(data['redirect_url'], '/users/dashboard/')

        self.assertIn('_auth_user_id', self.client.session)

    def test_telegram_auth_creates_new_user_if_not_exists(self):
        session = TelegramAuthSession.objects.create(token="test_register_token")
        
        result = handle_telegram_auth_token(
            "auth_test_register_token",
            88887777,
            first_name="TG_User",
            last_name="TG_Last",
            telegram_username="tg_new_user"
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.code, "register_success")
        
        session.refresh_from_db()
        self.assertEqual(session.status, TelegramAuthSession.STATUS_AUTHENTICATED)
        self.assertIsNotNone(session.user)
        self.assertEqual(session.user.telegram_id, 88887777)
        self.assertEqual(session.user.first_name, "TG_User")
        self.assertEqual(session.user.last_name, "TG_Last")
        self.assertEqual(session.user.telegram_username, "tg_new_user")
        self.assertEqual(session.user.email, "tg_88887777@telegram.local")

