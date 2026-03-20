from django.contrib.auth import get_user_model
from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Attendance, Cohort, Enrollment
from blog.models import BlogComment, BlogCommentLike, BlogHomeSettings, BlogPost, BlogPostClap, BlogPostRead, BlogTag
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
from frontend.models import (
    AboutPage,
    AboutStatistic,
    LandingNavItem,
    LandingPage,
    LegalPage,
    SiteSettings,
    Statistic,
    TeamMember,
    Testimonial,
)
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
        self.blog_tag = BlogTag.objects.create(name="Initial Tag")
        self.blog_post.tags.add(self.blog_tag)
        self.blog_read = BlogPostRead.objects.create(
            post=self.blog_post,
            viewer_key="viewer-1",
            user=self.student,
        )
        self.blog_clap = BlogPostClap.objects.create(
            post=self.blog_post,
            viewer_key="viewer-1",
            user=self.student,
            clap_count=3,
        )
        self.blog_comment_like = BlogCommentLike.objects.create(
            comment=self.blog_comment,
            user=self.staff,
        )
        self.landing_page = LandingPage.load()
        self.about_page = AboutPage.load()
        self.statistic = Statistic.objects.create(value="1000+", label="Talaba", order=1)
        self.testimonial = Testimonial.objects.create(
            name="Ali Test",
            role="Talaba",
            text="Platforma yaxshi.",
            rating=5,
            is_active=True,
        )
        self.about_stat = AboutStatistic.objects.create(value="20+", label="Mentor", order=1)
        self.team_member = TeamMember.objects.create(
            name="Team User",
            role_1="Mentor",
            role_2="Lead",
            bio="Short bio",
            order=1,
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
            "backoffice:content_landing_page",
            "backoffice:content_landing_blocks",
            "backoffice:content_about_page",
            "backoffice:content_about_blocks",
            "backoffice:content_landing_nav",
            "backoffice:content_blog_home",
            "backoffice:content_blog_tags",
            "backoffice:content_blog_signals",
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
        testimonial_detail = self.client.get(reverse("backoffice:content_testimonial_detail", args=[self.testimonial.id]))
        self.assertEqual(testimonial_detail.status_code, 200)
        member_detail = self.client.get(reverse("backoffice:content_team_member_detail", args=[self.team_member.id]))
        self.assertEqual(member_detail.status_code, 200)

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

    def test_staff_can_manage_landing_content_from_backoffice(self):
        self.client.force_login(self.staff)

        landing_url = reverse("backoffice:content_landing_page")
        landing_response = self.client.post(
            landing_url,
            {
                "hero_badge": "Yangi badge",
                "hero_title_start": "Turk tilini",
                "hero_title_highlight": "tez",
                "hero_title_end": "orgating",
                "hero_subtitle": "Hero subtitle text",
                "cta_title": "CTA title",
                "cta_description": "CTA description text",
            },
        )
        self.assertEqual(landing_response.status_code, 302)
        self.landing_page.refresh_from_db()
        self.assertEqual(self.landing_page.hero_badge, "Yangi badge")

        blocks_url = reverse("backoffice:content_landing_blocks")
        create_stat_response = self.client.post(
            blocks_url,
            {
                "action": "create_statistic",
                "value": "3000+",
                "label": "Yangi stat",
                "order": 10,
            },
        )
        self.assertEqual(create_stat_response.status_code, 302)
        created_stat = Statistic.objects.get(label="Yangi stat")
        self.assertEqual(created_stat.value, "3000+")

        update_stat_response = self.client.post(
            blocks_url,
            {
                "action": "update_statistic",
                "statistic_id": created_stat.id,
                "value": "3500+",
                "label": "Yangi stat",
                "order": 11,
            },
        )
        self.assertEqual(update_stat_response.status_code, 302)
        created_stat.refresh_from_db()
        self.assertEqual(created_stat.value, "3500+")

        create_testimonial_response = self.client.post(
            blocks_url,
            {
                "action": "create_testimonial",
                "name": "Sara",
                "role": "Talaba",
                "text": "Yangi testimonial",
                "rating": 4,
                "is_active": "on",
            },
        )
        self.assertEqual(create_testimonial_response.status_code, 302)
        self.assertTrue(Testimonial.objects.filter(name="Sara").exists())

        delete_testimonial_response = self.client.post(
            blocks_url,
            {
                "action": "delete_testimonial",
                "testimonial_id": self.testimonial.id,
            },
        )
        self.assertEqual(delete_testimonial_response.status_code, 302)
        self.assertFalse(Testimonial.objects.filter(id=self.testimonial.id).exists())

    def test_staff_can_manage_about_content_from_backoffice(self):
        self.client.force_login(self.staff)

        about_url = reverse("backoffice:content_about_page")
        about_response = self.client.post(
            about_url,
            {
                "hero_title_start": "Sifatli ta'lim",
                "hero_title_highlight": "hammasi",
                "hero_subtitle": "About subtitle",
                "mission_title": "Mission update",
                "mission_text": "Mission text update",
                "vision_title": "Vision update",
                "vision_text": "Vision text update",
            },
        )
        self.assertEqual(about_response.status_code, 302)
        self.about_page.refresh_from_db()
        self.assertEqual(self.about_page.mission_title, "Mission update")

        blocks_url = reverse("backoffice:content_about_blocks")
        create_stat_response = self.client.post(
            blocks_url,
            {
                "action": "create_about_statistic",
                "value": "40+",
                "label": "Mentorlar",
                "order": 3,
            },
        )
        self.assertEqual(create_stat_response.status_code, 302)
        created_about_stat = AboutStatistic.objects.get(value="40+")

        delete_stat_response = self.client.post(
            blocks_url,
            {
                "action": "delete_about_statistic",
                "about_statistic_id": created_about_stat.id,
            },
        )
        self.assertEqual(delete_stat_response.status_code, 302)
        self.assertFalse(AboutStatistic.objects.filter(id=created_about_stat.id).exists())

        create_member_response = self.client.post(
            blocks_url,
            {
                "action": "create_team_member",
                "name": "Team 2",
                "role_1": "Teacher",
                "role_2": "Advisor",
                "bio": "Bio text",
                "order": 2,
            },
        )
        self.assertEqual(create_member_response.status_code, 302)
        created_member = TeamMember.objects.get(name="Team 2")

        member_detail_url = reverse("backoffice:content_team_member_detail", args=[created_member.id])
        update_member_response = self.client.post(
            member_detail_url,
            {
                "action": "update",
                "name": "Team 2 updated",
                "role_1": "Teacher",
                "role_2": "Advisor",
                "bio": "Updated bio",
                "order": 5,
            },
        )
        self.assertEqual(update_member_response.status_code, 302)
        created_member.refresh_from_db()
        self.assertEqual(created_member.name, "Team 2 updated")

    def test_staff_can_manage_landing_nav_items_from_backoffice(self):
        self.client.force_login(self.staff)
        nav_url = reverse("backoffice:content_landing_nav")

        get_response = self.client.get(nav_url)
        self.assertEqual(get_response.status_code, 200)
        nav_item = LandingNavItem.objects.order_by("order", "id").first()
        self.assertIsNotNone(nav_item)

        update_response = self.client.post(
            nav_url,
            {
                "action": "update_nav_item",
                "nav_item_id": nav_item.id,
                "label": "Bosh sahifa update",
                "is_visible": "on",
                "order": 9,
            },
        )
        self.assertEqual(update_response.status_code, 302)
        nav_item.refresh_from_db()
        self.assertEqual(nav_item.label, "Bosh sahifa update")
        self.assertEqual(nav_item.order, 9)

        normalize_response = self.client.post(
            nav_url,
            {
                "action": "normalize_order",
            },
        )
        self.assertEqual(normalize_response.status_code, 302)

    def test_staff_can_manage_blog_home_tags_and_signals_from_backoffice(self):
        self.client.force_login(self.staff)

        blog_home_url = reverse("backoffice:content_blog_home")
        home_response = self.client.post(
            blog_home_url,
            {
                "hero_kicker": "Journal",
                "hero_title": "Yangi blog sarlavha",
                "hero_description": "Desc",
                "search_label": "Search",
                "search_placeholder": "Find",
                "carousel_kicker": "Kicker",
                "carousel_title": "Carousel title",
                "stories_kicker": "Stories",
                "stories_title": "Stories title",
                "stories_description": "Stories desc",
            },
        )
        self.assertEqual(home_response.status_code, 302)
        self.assertEqual(BlogHomeSettings.load().hero_title, "Yangi blog sarlavha")

        tags_url = reverse("backoffice:content_blog_tags")
        create_tag_response = self.client.post(
            tags_url,
            {
                "action": "create_tag",
                "name": "Grammar",
                "slug": "",
            },
        )
        self.assertEqual(create_tag_response.status_code, 302)
        created_tag = BlogTag.objects.get(name="Grammar")

        update_tag_response = self.client.post(
            tags_url,
            {
                "action": "update_tag",
                "tag_id": created_tag.id,
                "name": "Grammar Plus",
                "slug": "grammar-plus",
            },
        )
        self.assertEqual(update_tag_response.status_code, 302)
        created_tag.refresh_from_db()
        self.assertEqual(created_tag.slug, "grammar-plus")

        signals_url = reverse("backoffice:content_blog_signals")
        signals_response = self.client.get(signals_url + f"?kind=reads&post_id={self.blog_post.id}")
        self.assertEqual(signals_response.status_code, 200)
        self.assertContains(signals_response, self.blog_post.title)

        delete_tag_response = self.client.post(
            tags_url,
            {
                "action": "delete_tag",
                "tag_id": created_tag.id,
            },
        )
        self.assertEqual(delete_tag_response.status_code, 302)
        self.assertFalse(BlogTag.objects.filter(id=created_tag.id).exists())
