from django.contrib.auth import get_user_model
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Attendance, Cohort, Enrollment
from blog.models import BlogComment, BlogPost
from courses.models import (
    Assignment,
    AssignmentSubmission,
    CohortLessonRelease,
    Course,
    Exam,
    ExamAttempt,
    ExamSection,
    ExamSectionReview,
    Lesson,
    Module,
)
from frontend.models import LegalPage, SiteSettings
from subscriptions.models import Plan, PlanFeature
from users.models import Notification, NotificationBroadcast


User = get_user_model()


class BackofficeAccessTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="regular-user",
            email="regular@example.com",
            password="testpass123",
        )
        self.staff = User.objects.create_user(
            username="staff-user",
            email="staff@example.com",
            password="testpass123",
            is_staff=True,
        )
        self.teacher = User.objects.create_user(
            username="teacher-user",
            email="teacher@example.com",
            password="testpass123",
            is_staff=True,
        )

        self.course = Course.objects.create(
            title="Backoffice Cohort Course",
            description="Backoffice test",
            instructor=self.teacher,
            level="beginner",
        )
        self.module = Module.objects.create(course=self.course, title="1-modul", order=1)
        self.lesson = Lesson.objects.create(module=self.module, title="1-dars", order=1)
        self.cohort = Cohort.objects.create(
            name="Backoffice Cohort",
            course=self.course,
            start_date="2026-03-01",
            is_active=True,
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            cohort=self.cohort,
            status="active",
        )
        self.assignment = Assignment.objects.create(
            lesson=self.lesson,
            title="1-vazifa",
            description="Vazifa matni",
            max_xp=50,
        )
        self.submission = AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            answer_text="Javob",
            status=AssignmentSubmission.STATUS_PENDING,
        )
        self.release = CohortLessonRelease.objects.create(
            cohort=self.cohort,
            lesson=self.lesson,
            is_released=True,
            released_by=self.staff,
        )
        self.exam = Exam.objects.create(
            course=self.course,
            title="Backoffice Exam",
            exam_type="final",
            weight_percentage=60,
            passing_score=60,
        )
        self.exam_section = ExamSection.objects.create(
            exam=self.exam,
            title="Reading",
            section_type="reading",
            instructions="Ko'rsatma",
            max_score=20,
            order=1,
        )
        self.exam_attempt = ExamAttempt.objects.create(
            student=self.student,
            exam=self.exam,
            is_completed=True,
            completed_time=timezone.now(),
        )
        self.blog_post = BlogPost.objects.create(
            title="Test Blog Post",
            author=self.staff,
            body="Blog body text",
            status=BlogPost.STATUS_DRAFT,
        )
        self.blog_comment = BlogComment.objects.create(
            post=self.blog_post,
            user=self.student,
            content="Comment text",
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("backoffice:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_dashboard_denies_non_staff_user(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("backoffice:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard"), response.url)

    def test_staff_can_open_backoffice_pages(self):
        self.client.force_login(self.staff)
        for route_name in (
            "backoffice:dashboard",
            "backoffice:students",
            "backoffice:users",
            "backoffice:payments",
            "backoffice:subscriptions",
            "backoffice:cohorts",
            "backoffice:attendance",
            "backoffice:notifications",
            "backoffice:learning_assignments",
            "backoffice:learning_releases",
            "backoffice:learning_exams",
            "backoffice:content_settings",
            "backoffice:legal_pages",
            "backoffice:blog_posts",
            "backoffice:blog_comments",
        ):
            response = self.client.get(reverse(route_name))
            self.assertEqual(response.status_code, 200, route_name)
        detail_response = self.client.get(reverse("backoffice:user_detail", args=[self.student.id]))
        self.assertEqual(detail_response.status_code, 200)
        legal_page = LegalPage.objects.first()
        legal_detail = self.client.get(reverse("backoffice:legal_page_detail", args=[legal_page.id]))
        self.assertEqual(legal_detail.status_code, 200)

    def test_staff_can_save_attendance_from_backoffice(self):
        self.client.force_login(self.staff)
        target_date = date(2026, 3, 20)
        query = f"?cohort_id={self.cohort.id}&lesson_id={self.lesson.id}&date={target_date.isoformat()}"
        url = reverse("backoffice:attendance") + query

        response = self.client.post(
            url,
            {
                f"status_{self.enrollment.id}": Attendance.STATUS_PRESENT,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("backoffice:attendance"), response.url)

        attendance = Attendance.objects.get(
            enrollment=self.enrollment,
            lesson=self.lesson,
            date=target_date,
        )
        self.assertEqual(attendance.status, Attendance.STATUS_PRESENT)

    def test_staff_can_update_user_from_backoffice(self):
        self.client.force_login(self.staff)
        url = reverse("backoffice:user_detail", args=[self.student.id])
        response = self.client.post(
            url,
            {
                "username": self.student.username,
                "email": self.student.email,
                "first_name": "Aziz",
                "last_name": "Siroj",
                "phone_number": "+998901112233",
                "telegram_id": "",
                "telegram_username": "azizdev",
                "total_xp": 777,
                "is_active": "on",
                "is_staff": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Aziz")
        self.assertEqual(self.student.total_xp, 777)
        self.assertEqual(self.student.telegram_username, "azizdev")

    def test_staff_can_send_broadcast_from_backoffice(self):
        self.client.force_login(self.staff)
        url = reverse("backoffice:notifications")
        response = self.client.post(
            url,
            {
                "title": "Platform update",
                "message": "Yangi funksiya ishga tushdi.",
                "icon": "megaphone",
                "url": "/users/dashboard/",
                "target_type": NotificationBroadcast.TARGET_ALL,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(NotificationBroadcast.objects.count(), 1)
        broadcast = NotificationBroadcast.objects.first()
        self.assertTrue(broadcast.is_sent)
        self.assertGreater(Notification.objects.count(), 0)

    def test_staff_can_manage_subscription_plan_from_backoffice(self):
        self.client.force_login(self.staff)
        create_url = reverse("backoffice:subscriptions")
        response = self.client.post(
            create_url,
            {
                "name": "Standard",
                "price": 99000,
                "description": "Standart obuna",
                "is_popular": "on",
                "button_text": "Boshlash",
                "order": 1,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Plan.objects.count(), 1)
        plan = Plan.objects.first()

        detail_url = reverse("backoffice:subscription_plan_detail", args=[plan.id])
        response_feature = self.client.post(
            detail_url,
            {
                "action": "add_feature",
                "name": "Barcha darslar",
                "is_included": "on",
                "order": 1,
            },
        )
        self.assertEqual(response_feature.status_code, 302)
        self.assertEqual(PlanFeature.objects.filter(plan=plan).count(), 1)

    def test_staff_can_moderate_assignments_from_backoffice(self):
        self.client.force_login(self.staff)
        url = reverse("backoffice:learning_assignments")
        response = self.client.post(
            url,
            {
                "action": "mark_approved",
                "submission_ids": [str(self.submission.id)],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, AssignmentSubmission.STATUS_APPROVED)
        self.assertEqual(self.submission.reviewed_by, self.staff)

    def test_staff_can_toggle_lesson_releases_from_backoffice(self):
        self.client.force_login(self.staff)
        url = reverse("backoffice:learning_releases")
        response = self.client.post(
            url,
            {
                "action": "mark_locked",
                "release_ids": [str(self.release.id)],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.release.refresh_from_db()
        self.assertFalse(self.release.is_released)

    def test_staff_can_process_exam_reviews_from_backoffice(self):
        self.client.force_login(self.staff)
        url = reverse("backoffice:learning_exams")

        prepare_response = self.client.post(
            url,
            {
                "action": "prepare_reviews",
                "attempt_ids": [str(self.exam_attempt.id)],
            },
        )
        self.assertEqual(prepare_response.status_code, 302)
        self.assertEqual(ExamSectionReview.objects.filter(attempt=self.exam_attempt).count(), 1)

        approve_response = self.client.post(
            url,
            {
                "action": "approve_selected_attempts",
                "attempt_ids": [str(self.exam_attempt.id)],
            },
        )
        self.assertEqual(approve_response.status_code, 302)
        self.exam_attempt.refresh_from_db()
        self.assertTrue(self.exam_attempt.is_reviewed)

    def test_staff_can_update_site_settings_from_backoffice(self):
        self.client.force_login(self.staff)
        url = reverse("backoffice:content_settings")
        response = self.client.post(
            url,
            {
                "action": "update_site",
                "site-company_description": "Yangi company copy",
                "site-contact_phone": "+998900000000",
                "site-contact_email": "info@example.com",
                "site-contact_address": "Tashkent",
                "site-support_url": "https://example.com/support",
                "site-payment_card_number": "8600 0000 0000 0000",
                "site-payment_card_holder": "Azure Admin",
                "site-payment_provider_label": "Uzcard",
                "site-payment_instruction": "To'lov qilib chek yuboring",
                "site-telegram_url": "https://t.me/example",
                "site-instagram_url": "https://instagram.com/example",
                "site-youtube_url": "https://youtube.com/example",
                "site-facebook_url": "https://facebook.com/example",
            },
        )
        self.assertEqual(response.status_code, 302)
        settings_obj = SiteSettings.load()
        self.assertEqual(settings_obj.company_description, "Yangi company copy")

    def test_staff_can_publish_blog_posts_from_backoffice(self):
        self.client.force_login(self.staff)
        url = reverse("backoffice:blog_posts")
        response = self.client.post(
            url,
            {
                "action": "mark_published",
                "post_ids": [str(self.blog_post.id)],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.blog_post.refresh_from_db()
        self.assertEqual(self.blog_post.status, BlogPost.STATUS_PUBLISHED)
        self.assertIsNotNone(self.blog_post.published_at)

    def test_staff_can_soft_delete_blog_comments_from_backoffice(self):
        self.client.force_login(self.staff)
        url = reverse("backoffice:blog_comments")
        response = self.client.post(
            url,
            {
                "action": "mark_deleted",
                "comment_ids": [str(self.blog_comment.id)],
            },
        )
        self.assertEqual(response.status_code, 302)
        self.blog_comment.refresh_from_db()
        self.assertTrue(self.blog_comment.is_deleted)
