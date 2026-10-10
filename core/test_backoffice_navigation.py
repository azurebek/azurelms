"""Navigation rollout, scope and writer entry parity at the real HTTP boundary."""
from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from blog.models import BlogPost
from cohorts.models import Cohort
from core.flags import set_flag
from courses.models import Course
from frontend.models import AuthPageSettings, LandingPage, SiteSettings


class BackofficeNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user('nav-owner', 'nav-owner@example.test', is_superuser=True, is_staff=True)
        cls.teacher = User.objects.create_user('nav-teacher', 'nav-teacher@example.test', is_staff=True)
        cls.other = User.objects.create_user('nav-other', 'nav-other@example.test', is_staff=True)
        cls.student = User.objects.create_user('nav-student', 'nav-student@example.test')
        cls.course = Course.objects.create(title='Own course', instructor=cls.teacher)
        cls.foreign = Course.objects.create(title='PRIVATE foreign course', instructor=cls.other)
        cls.cohort = Cohort.objects.create(name='Own group', course=cls.course, start_date=date(2026, 10, 1))
        cls.foreign_group = Cohort.objects.create(name='PRIVATE foreign group', course=cls.foreign, start_date=date(2026, 10, 1))
        cls.own_post = BlogPost.objects.create(title='Own article', slug='own-article', author=cls.teacher, body='Body')
        cls.other_post = BlogPost.objects.create(title='PRIVATE other draft', slug='other-draft', author=cls.other, body='Body')
        SiteSettings.load()
        AuthPageSettings.load()
        LandingPage.load()

    hubs = ('backoffice_workspace_payments', 'backoffice_workspace_site', 'backoffice_workspace_settings',
            'backoffice_workspace_groups', 'backoffice_workspace_plans')

    def setUp(self):
        self.client.force_login(self.owner)
        set_flag('backoffice_unified_navigation', enabled=True, reason='Navigation HTTP test')

    def get(self, name, **params):
        return self.client.get(reverse(name), params)

    def test_hubs_are_private_read_only_and_create_no_state(self):
        for name in self.hubs:
            with self.subTest(name=name), CaptureQueriesContext(connection) as queries:
                response = self.get(name)
                self.assertEqual(response.status_code, 200)
                self.assertIn('private', response['Cache-Control'])
                self.assertIn('no-store', response['Cache-Control'])
                self.assertContains(response, 'ws-shell')
            writes = [q['sql'] for q in queries if q['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))]
            self.assertEqual(writes, [])
            self.assertEqual(self.client.post(reverse(name), {'enabled': 'on'}).status_code, 405)

    def test_unified_shell_uses_saved_brand_mark_and_name(self):
        brand = SiteSettings.load()
        brand.brand_name = 'Saved navigation brand'
        brand.logo_mark_image = 'brand/synthetic-navigation-mark.svg'
        brand.save(update_fields=['brand_name', 'logo_mark_image'])
        response = self.get('backoffice_workspace_site')
        self.assertContains(response, 'Saved navigation brand')
        self.assertContains(response, 'brand/synthetic-navigation-mark.svg')
        self.assertContains(response, 'brand-logo-mark--image')

    def test_flag_off_closes_new_hubs_but_preserves_old_shells(self):
        set_flag('backoffice_unified_navigation', enabled=False, reason='Renderer rollback')
        for name in self.hubs:
            self.assertEqual(self.get(name).status_code, 404)
        response = self.get('backoffice_receipts')
        self.assertTemplateUsed(response, 'backoffice/legacy_base.html')
        self.assertNotContains(response, 'ws-shell')
        response = self.get('blog:studio')
        self.assertTemplateUsed(response, 'base_teacher.html')

    def test_new_flag_is_independent_of_three_workspace_flags(self):
        for flag in ('backoffice_course_workspace', 'backoffice_student_support', 'backoffice_design_workspace'):
            set_flag(flag, enabled=False, reason='Independent navigation gate')
        response = self.get('backoffice_workspace_site')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('backoffice_design'))
        self.assertContains(response, reverse('backoffice_brand'))
        self.assertContains(response, 'href="' + reverse('backoffice_courses') + '"')

    def test_anonymous_student_inactive_and_staff_gates(self):
        self.client.logout()
        for name in self.hubs:
            self.assertEqual(self.get(name).status_code, 302)
        self.client.force_login(self.student)
        for name in self.hubs:
            self.assertEqual(self.get(name).status_code, 403)
        self.client.force_login(self.teacher)
        for name in ('backoffice_workspace_settings', 'backoffice_workspace_plans'):
            self.assertEqual(self.get(name).status_code, 403)
        for name in ('backoffice_workspace_site', 'backoffice_workspace_payments', 'backoffice_workspace_groups'):
            self.assertEqual(self.get(name).status_code, 200)
        self.teacher.is_active = False
        self.teacher.save(update_fields=['is_active'])
        self.assertEqual(self.get('backoffice_workspace_groups').status_code, 302)

    def test_staff_menu_keeps_receipts_and_own_blog_but_not_owner_entries(self):
        self.client.force_login(self.teacher)
        response = self.get('backoffice_workspace_site')
        for name in ('blog:studio', 'backoffice_workspace_payments'):
            self.assertContains(response, reverse(name))
        for name in ('backoffice_workspace_settings', 'backoffice_brand', 'backoffice_landing', 'sit_backoffice:dashboard', 'backoffice_workspace_plans'):
            self.assertNotContains(response, 'href="' + reverse(name) + '"')
        self.assertContains(self.get('backoffice_workspace_payments'), reverse('backoffice_receipts'))
        response = self.get('blog:studio')
        self.assertContains(response, 'Own article')
        self.assertNotContains(response, 'PRIVATE other draft')
        self.assertEqual(self.client.get(reverse('blog:studio_edit', args=[self.other_post.slug])).status_code, 404)

    def test_groups_scope_search_status_pagination_and_named_actions(self):
        self.client.force_login(self.teacher)
        response = self.get('backoffice_workspace_groups')
        self.assertContains(response, 'Own group')
        self.assertNotContains(response, 'PRIVATE foreign')
        self.assertNotContains(response, reverse('backoffice_cohort_edit', args=[self.cohort.pk]))
        self.assertContains(response, reverse('teacher_release') + '?cohort=' + str(self.cohort.pk))
        self.assertNotContains(self.get('backoffice_workspace_groups', q='PRIVATE'), 'PRIVATE foreign')
        for number in range(13):
            Cohort.objects.create(name=f'Own search {number}', course=self.course, start_date=date(2026, 10, 2))
        response = self.get('backoffice_workspace_groups', q='Own search', status='active', page=2)
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertContains(response, 'q=Own%20search&amp;status=active&amp;page=1')
        self.assertEqual(self.get('backoffice_workspace_groups', status='unknown').status_code, 400)
        self.assertEqual(self.client.get(reverse('backoffice_workspace_groups') + '?q=a&q=b').status_code, 400)

    def test_all_legacy_destinations_render_in_correct_section(self):
        sections = {
            'payments': ('backoffice_receipts', 'backoffice_catalog'),
            'design': ('backoffice_brand', 'backoffice_landing', 'blog:studio', 'blog:studio_create',
                       'sit_backoffice:dashboard', 'sit_backoffice:universities', 'sit_backoffice:announcements',
                       'sit_backoffice:guides', 'sit_backoffice:university_create', 'sit_backoffice:announcement_create', 'sit_backoffice:guide_create'),
            'settings': ('backoffice_control', 'backoffice_feature_flags', 'backoffice_runtime_settings',
                         'backoffice_ai_control', 'backoffice_ai_cost', 'backoffice_dead_letter'),
            'courses': ('backoffice_exams', 'backoffice_cohort_create', 'library_backoffice:resources'),
            'students': ('backoffice_users', 'backoffice_chats'),
        }
        for section, names in sections.items():
            for name in names:
                with self.subTest(name=name):
                    response = self.get(name)
                    self.assertEqual(response.status_code, 200)
                    self.assertTemplateUsed(response, 'backoffice/workspace/base.html')
                    self.assertEqual([item['key'] for item in response.context['workspace_nav'] if item['active']], [section])
                    self.assertContains(response, 'data-legacy-page=')

    def test_closed_group_has_management_but_no_ineligible_teaching_links(self):
        self.cohort.is_active = False
        self.cohort.save(update_fields=['is_active'])
        response = self.get('backoffice_workspace_groups', status='closed')
        self.assertContains(response, reverse('backoffice_cohort_edit', args=[self.cohort.pk]))
        self.assertNotContains(response, reverse('teacher_release') + '?cohort=' + str(self.cohort.pk))
        self.assertNotContains(response, reverse('teacher_attendance') + '?cohort=' + str(self.cohort.pk))
        self.assertContains(response, 'Darslar ruxsati va davomat faol guruhda ochiladi.')

    def test_team_filter_has_settings_context_and_public_blog_does_not(self):
        response = self.get('backoffice_users', role='teachers')
        self.assertEqual([item['key'] for item in response.context['workspace_nav'] if item['active']], ['settings'])
        response = self.get('blog:list')
        self.assertNotContains(response, 'data-workspace-legacy')

    def test_teacher_handoff_has_safe_return_and_existing_v1_guards_survive(self):
        response = self.get('teacher_cohorts')
        self.assertContains(response, 'Boshqaruvga qaytish')
        self.assertContains(response, reverse('backoffice_workspace_groups'))
        set_flag('frontend_v1_library', enabled=True, reason='Existing V1 adapter')
        response = self.get('library_backoffice:resources')
        self.assertContains(response, 'Boshqaruvga qaytish')
        self.assertContains(response, 'data-library-root')
        self.assertTemplateUsed(response, 'frontend_v1/library/base.html')

    def test_home_has_all_sections_and_group_link_has_a_new_destination(self):
        set_flag('backoffice_course_workspace', enabled=True, reason='Existing course adapter')
        response = self.get('backoffice_workspace_home')
        for name in ('backoffice_workspace_site', 'backoffice_workspace_payments', 'backoffice_workspace_settings'):
            self.assertContains(response, reverse(name))
        response = self.get('backoffice_workspace_courses')
        self.assertContains(response, reverse('backoffice_workspace_groups'))
