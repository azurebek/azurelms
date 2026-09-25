"""V1 is a renderer over the existing auth/enrollment policy, never a demo API."""

from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model, SESSION_KEY
from django.db import OperationalError
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.shortcuts import resolve_url
from django.utils import timezone

from cohorts.models import Cohort, Enrollment, enrollment_grace_limit
from core.flags import flag_by_slug, flag_enabled, set_flag
from courses.models import Course, Lesson, LessonProgress, Module


class FrontendV1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model()
        cls.student = user.objects.create_user("v1-student", "v1@example.test", "V1-test-password-49", first_name="O‘quvchi")
        cls.teacher = user.objects.create_user("v1-teacher", "teacher@example.test", "V1-test-password-49", is_staff=True)
        cls.other = user.objects.create_user("v1-other", "other@example.test", "V1-test-password-49")
        cls.course = Course.objects.create(title="Haqiqiy Turk tili", instructor=cls.teacher, level="beginner")
        module = Module.objects.create(course=cls.course, title="Birinchi modul", order=1)
        cls.lesson = Lesson.objects.create(module=module, title="Haqiqiy dars", order=1)
        Lesson.objects.create(module=module, title="Ikkinchi dars", order=2)
        cls.cohort = Cohort.objects.create(course=cls.course, name="Ertalabgi guruh", start_date=timezone.localdate())
        cls.enrollment = Enrollment.objects.create(student=cls.student, cohort=cls.cohort, status="active")
        LessonProgress.objects.create(enrollment=cls.enrollment, lesson=cls.lesson, is_completed=True)

    def enable(self):
        set_flag("frontend_v1_learning", enabled=True, reason="V1 automated regression")

    def sign_in(self):
        self.enable()
        self.client.force_login(self.student)

    def study_url(self, cohort=None):
        cohort = cohort or self.cohort
        return f'{reverse("course_study", kwargs={"course_id": cohort.course_id})}?cohort={cohort.pk}'

    def test_flag_defaults_off_and_preserves_all_three_legacy_templates(self):
        self.assertFalse(flag_by_slug("frontend_v1_learning").default)
        self.assertTemplateUsed(self.client.get(reverse("login")), "registration/login.html")
        self.client.force_login(self.student)
        for name, template in [("dashboard", "users/dashboard.html"), ("my_courses", "users/my_courses.html")]:
            response = self.client.get(reverse(name))
            self.assertTemplateUsed(response, template)
            self.assertNotContains(response, 'data-frontend="v1"')

    def test_flag_database_failure_falls_back_to_off(self):
        with patch("aicontrol.models.FeatureFlag.objects.filter", side_effect=OperationalError):
            self.assertFalse(flag_enabled("frontend_v1_learning"))

    def test_rollback_restores_legacy_without_changing_domain_records(self):
        self.sign_in()
        self.assertTemplateUsed(self.client.get(reverse("dashboard")), "frontend_v1/dashboard.html")
        set_flag("frontend_v1_learning", enabled=False, reason="Rollback test")
        self.assertTemplateUsed(self.client.get(reverse("dashboard")), "users/dashboard.html")
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, "active")
        self.assertEqual(LessonProgress.objects.filter(enrollment=self.enrollment).count(), 1)

    def test_unauthenticated_requests_still_require_login_with_next(self):
        self.enable()
        for name in ("dashboard", "my_courses"):
            response = self.client.get(reverse(name))
            self.assertRedirects(response, f'{reverse("login")}?next={reverse(name)}', fetch_redirect_response=False)

    def test_real_progress_context_and_cohort_urls_are_preserved(self):
        self.sign_in()
        for name in ("dashboard", "my_courses"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Haqiqiy Turk tili")
            self.assertContains(response, "Ertalabgi guruh")
            self.assertContains(response, "50%")
            self.assertContains(response, f'href="{self.study_url()}"')
            self.assertContains(response, '<progress class="c-progress" max="100" value="50"')
            self.assertIn("private", response.headers["Cache-Control"])
            self.assertIn("no-store", response.headers["Cache-Control"])

    def test_real_context_matches_legacy_context(self):
        self.client.force_login(self.student)
        before = self.client.get(reverse("dashboard")).context
        self.enable()
        after = self.client.get(reverse("dashboard")).context
        for key in ("active_courses_count", "completed_lessons_count", "xp_points", "streak", "current_plan", "resume_enrollment"):
            self.assertEqual(before[key], after[key], key)
        self.assertEqual(before["primary_enrollment"].dashboard_progress, after["primary_enrollment"].dashboard_progress)

    def test_multiple_courses_keep_exact_cohort_destination(self):
        second_course = Course.objects.create(title="Ikkinchi haqiqiy kurs", instructor=self.teacher)
        other_cohort = Cohort.objects.create(course=second_course, name="Kechki guruh", start_date=timezone.localdate())
        Enrollment.objects.create(student=self.student, cohort=other_cohort, status="active")
        self.sign_in()
        for name in ("dashboard", "my_courses"):
            response = self.client.get(reverse(name))
            for cohort in (self.cohort, other_cohort):
                self.assertContains(response, cohort.name)
                self.assertContains(response, f'href="{self.study_url(cohort)}"')
        self.assertEqual(response.context["count_active"], 2)

    def test_other_users_enrollments_are_not_selected_by_query(self):
        private_course = Course.objects.create(title="Private other course", instructor=self.teacher)
        private_cohort = Cohort.objects.create(course=private_course, name="Private cohort", start_date=timezone.localdate())
        Enrollment.objects.create(student=self.other, cohort=private_cohort, status="active")
        self.sign_in()
        for name in ("dashboard", "my_courses"):
            response = self.client.get(reverse(name), {"user": self.other.pk, "cohort": private_cohort.pk})
            self.assertNotContains(response, "Private other course")
            self.assertNotContains(response, "Private cohort")
            self.assertNotContains(response, f'href="{self.study_url(private_cohort)}"')

    def test_empty_account_has_no_fake_course_or_resume_action(self):
        self.enable()
        self.client.force_login(self.other)
        for name in ("dashboard", "my_courses"):
            response = self.client.get(reverse(name))
            self.assertContains(response, "Hali kursga yozilmagansiz")
            self.assertNotContains(response, "Haqiqiy Turk tili")
            self.assertNotContains(response, '/study/?cohort=')
            self.assertContains(response, f'href="{reverse("courses")}"')

    def test_non_active_enrollment_never_gets_resume_even_if_progress_is_complete(self):
        self.sign_in()
        LessonProgress.objects.create(enrollment=self.enrollment, lesson=self.course.modules.first().lessons.get(order=2), is_completed=True)
        for status in ("pending", "frozen", "expired"):
            with self.subTest(status=status):
                Enrollment.objects.filter(pk=self.enrollment.pk).update(status=status)
                for name in ("dashboard", "my_courses"):
                    response = self.client.get(reverse(name))
                    self.assertNotContains(response, f'href="{self.study_url()}"')
                    self.assertContains(response, "Obuna holatini ko‘rish")

    def test_elapsed_deadline_uses_effective_status_not_stored_active_label(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).update(next_payment_deadline=enrollment_grace_limit() - timedelta(days=1))
        self.sign_in()
        response = self.client.get(reverse("dashboard"))
        self.assertIsNone(response.context["resume_enrollment"])
        self.assertNotContains(response, f'href="{self.study_url()}"')

    def test_user_and_course_text_is_escaped(self):
        Course.objects.filter(pk=self.course.pk).update(title='<script>alert("course")</script>')
        self.sign_in()
        response = self.client.get(reverse("my_courses"))
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, '<script>alert("course")</script>')

    def test_student_has_no_staff_links_and_staff_has_both_role_links(self):
        self.sign_in()
        response = self.client.get(reverse("dashboard"))
        for name in ("teacher_dashboard", "backoffice_dashboard"):
            self.assertNotContains(response, f'href="{reverse(name)}"')
        self.client.force_login(self.teacher)
        response = self.client.get(reverse("dashboard"))
        for name in ("teacher_dashboard", "backoffice_dashboard"):
            self.assertContains(response, f'href="{reverse(name)}"')

    def test_legacy_navigation_is_explicit_and_not_removed(self):
        self.sign_in()
        response = self.client.get(reverse("dashboard"))
        for name in ("profile", "settings", "blog:list", "sit:home", "classbook:live_home", "messenger:ai", "exam_center", "notifications", "subscriptions"):
            self.assertContains(response, f'href="{reverse(name)}"')
        self.assertContains(response, "AVVALGI KO‘RINISHDA")
        self.assertContains(response, '<dialog id="nav-dialog"')
        self.assertContains(response, '<noscript>')

    def test_only_v1_assets_and_no_demo_runtime_are_rendered(self):
        self.sign_in()
        for name in ("dashboard", "my_courses"):
            response = self.client.get(reverse(name))
            for forbidden in ("/_preview/", "preview-bootstrap", "Sinov paneli", "/static/js/app.js", "/static/css/tokens.css", "Eleventh Trial"):
                self.assertNotContains(response, forbidden)
            self.assertContains(response, "/static/frontend_v1/js/theme.js")

    def test_login_invalid_preserves_username_and_next_not_password(self):
        self.enable()
        response = self.client.post(reverse("login"), {"username": "v1-student", "password": "wrong-secret-value", "next": reverse("my_courses")})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "frontend_v1/login.html")
        self.assertContains(response, 'value="v1-student"')
        self.assertContains(response, 'data-form-errors')
        self.assertContains(response, "Email yoki username va parol mos kelmadi.")
        self.assertContains(response, f'name="next" value="{reverse("my_courses")}"')
        self.assertNotContains(response, "wrong-secret-value")
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_login_valid_email_and_next_reaches_real_session(self):
        self.enable()
        response = self.client.post(reverse("login"), {"username": self.student.email, "password": "V1-test-password-49", "next": reverse("my_courses")})
        self.assertRedirects(response, reverse("my_courses"))
        self.assertEqual(int(self.client.session[SESSION_KEY]), self.student.pk)

    def test_login_external_next_cannot_redirect_offsite(self):
        self.enable()
        response = self.client.post(reverse("login"), {"username": self.student.username, "password": "V1-test-password-49", "next": "https://untrusted.example/"})
        self.assertRedirects(response, resolve_url(settings.LOGIN_REDIRECT_URL), fetch_redirect_response=False)

    def test_login_requires_csrf(self):
        self.enable()
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("login"), {"username": self.student.username, "password": "V1-test-password-49"})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(SESSION_KEY, client.session)

    def test_logout_is_post_and_requires_csrf(self):
        self.enable()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.student)
        response = client.get(reverse("dashboard"))
        self.assertContains(response, f'method="post" action="{reverse("logout")}"')
        self.assertEqual(client.get(reverse("logout")).status_code, 405)
        self.assertEqual(client.post(reverse("logout")).status_code, 403)
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        self.assertEqual(client.post(reverse("logout"), {"csrfmiddlewaretoken": token}).status_code, 302)
        self.assertNotIn(SESSION_KEY, client.session)

    def test_authenticated_login_redirects_to_safe_destination(self):
        self.sign_in()
        self.assertRedirects(self.client.get(reverse("login"), {"next": reverse("my_courses")}), reverse("my_courses"))

    def test_login_telegram_uses_existing_endpoints_not_preview(self):
        self.enable()
        response = self.client.get(reverse("login"))
        self.assertContains(response, f'data-init-url="{reverse("telegram_auth_init")}"')
        self.assertContains(response, f'data-status-url="{reverse("telegram_auth_status", kwargs={"token": "TOKEN"})}"')
        self.assertNotContains(response, 'href="#"')

    def test_production_assets_have_no_fixture_controller_or_credential_storage(self):
        asset_root = Path(settings.BASE_DIR) / "static" / "frontend_v1"
        for path in asset_root.rglob("*.js"):
            source = path.read_text(encoding="utf-8")
            for forbidden in ("/_preview/", "preview-bootstrap", "boot.snapshot", "sessionStorage", "fixture"):
                self.assertNotIn(forbidden, source, str(path))
        self.assertNotIn("localStorage", (asset_root / "js" / "login.js").read_text(encoding="utf-8"))


class FrontendV1StaticTests(SimpleTestCase):
    def test_slice_collects_with_hashed_production_static_storage(self):
        from django.core.management import call_command
        from django.contrib.staticfiles.storage import staticfiles_storage

        source = Path(settings.BASE_DIR) / "static" / "frontend_v1"
        with TemporaryDirectory(prefix="azurelms-v1-static-") as target:
            with override_settings(
                DEBUG=False,
                STATIC_ROOT=target,
                STATICFILES_DIRS=[("frontend_v1", source)],
                STATICFILES_FINDERS=["django.contrib.staticfiles.finders.FileSystemFinder"],
                STORAGES={"staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}},
            ):
                call_command("collectstatic", interactive=False, verbosity=0, stdout=StringIO())
                for asset in ("css/tokens.css", "css/learning.css", "js/theme.js", "js/shell.js", "js/login.js", "icons.svg"):
                    url = staticfiles_storage.url("frontend_v1/" + asset)
                    self.assertNotEqual(url, "/static/frontend_v1/" + asset)
                    self.assertTrue(staticfiles_storage.exists(staticfiles_storage.stored_name("frontend_v1/" + asset)))
