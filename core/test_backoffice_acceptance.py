"""Cross-stage release checks: rendered entrances, scope and reversible rollout.

These are automated regression checks, not evidence of human usability or a
production release. Individual domain writer contracts live in their own suites.
"""
import json
from datetime import date
from html.parser import HTMLParser
from itertools import product
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from cohorts.models import Cohort, Enrollment
from core.design_models import DesignDraft, DesignOperation, DesignState, DesignVersion
from core.design_schema import defaults
from core.flags import set_flag
from courses.models import Course, Lesson, Module
from frontend.models import AuthPageSettings, LandingPage, SiteSettings


class NavigationLinks(HTMLParser):
    """Read the links the operator actually receives, including section cards."""

    def __init__(self, response):
        super().__init__()
        self.links = set()
        self.section_nav = False
        self.feed(response.content.decode())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        if tag == 'nav' and 'ws-section-nav' in classes:
            self.section_nav = True
        if tag == 'a' and (self.section_nav or {'ws-nav-link', 'ws-section-card'} & set(classes)):
            self.links.add(attrs['href'])

    def handle_endtag(self, tag):
        if tag == 'nav':
            self.section_nav = False


@override_settings(GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='')
class BackofficeAcceptanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(
            'acceptance-owner', 'acceptance-owner@example.test', is_staff=True, is_superuser=True,
        )
        cls.teacher = users.objects.create_user('acceptance-teacher', 'acceptance-teacher@example.test', is_staff=True)
        cls.other = users.objects.create_user('acceptance-other', 'acceptance-other@example.test', is_staff=True)
        cls.learner = users.objects.create_user('acceptance-learner', 'acceptance-learner@example.test')
        cls.foreign_learner = users.objects.create_user('foreign-learner', 'foreign-learner@example.test')
        cls.course = Course.objects.create(title='Acceptance course', instructor=cls.teacher)
        cls.module = Module.objects.create(course=cls.course, title='Acceptance module')
        cls.lesson = Lesson.objects.create(module=cls.module, title='Acceptance lesson', content='Saved content')
        cls.group = Cohort.objects.create(course=cls.course, name='Acceptance group', start_date=date(2026, 10, 1))
        cls.foreign_course = Course.objects.create(title='PRIVATE other course', instructor=cls.other)
        cls.foreign_group = Cohort.objects.create(
            course=cls.foreign_course, name='PRIVATE other group', start_date=date(2026, 10, 1),
        )
        Enrollment.objects.create(student=cls.learner, cohort=cls.group, status=Enrollment.STATUS_ACTIVE)
        Enrollment.objects.create(student=cls.foreign_learner, cohort=cls.foreign_group, status=Enrollment.STATUS_ACTIVE)
        SiteSettings.load()
        AuthPageSettings.load()
        LandingPage.load()

    def rollout(self, *, course=True, support=True, design=True, navigation=True):
        for flag, enabled in (
            ('backoffice_course_workspace', course), ('backoffice_student_support', support),
            ('backoffice_design_workspace', design), ('backoffice_unified_navigation', navigation),
        ):
            set_flag(flag, enabled=enabled, reason='Synthetic stage-six release check')

    def assert_links_open(self, response):
        self.assertEqual(response.status_code, 200)
        for url in sorted(NavigationLinks(response).links):
            with self.subTest(destination=url):
                opened = self.client.get(url, follow=True)
                self.assertEqual(opened.status_code, 200)
                self.assertTrue(all(status == 302 for _, status in opened.redirect_chain))

    def test_all_sixteen_rollout_combinations_offer_working_owner_and_staff_entrances(self):
        for navigation, course, support, design in product((False, True), repeat=4):
            self.rollout(course=course, support=support, design=design, navigation=navigation)
            for actor in (self.owner, self.teacher):
                with self.subTest(navigation=navigation, course=course, support=support,
                                  design=design, actor=actor.username):
                    self.client.force_login(actor)
                    if navigation:
                        entrance = 'backoffice_workspace_site'
                    elif course:
                        entrance = 'backoffice_workspace_home'
                    elif support:
                        entrance = 'backoffice_workspace_students'
                    elif design and actor.is_superuser:
                        entrance = 'backoffice_design'
                    else:
                        entrance = 'backoffice_receipts'
                    response = self.client.get(reverse(entrance))
                    self.assert_links_open(response)
                    links = NavigationLinks(response).links
                    if not course:
                        self.assertNotIn(reverse('backoffice_workspace_home'), links)
                        self.assertNotIn(reverse('backoffice_workspace_courses'), links)
                    if not support:
                        self.assertNotIn(reverse('backoffice_workspace_students'), links)
                    if not design or not actor.is_superuser:
                        self.assertNotIn(reverse('backoffice_design'), links)
                    if not actor.is_superuser:
                        for route in ('backoffice_workspace_settings', 'backoffice_workspace_plans',
                                      'backoffice_brand', 'backoffice_control'):
                            self.assertNotIn(reverse(route), links)
                    if navigation:
                        self.assertTemplateUsed(response, 'backoffice/workspace/base.html')
                    elif entrance == 'backoffice_receipts':
                        self.assertTemplateUsed(response, 'backoffice/legacy_base.html')
                        self.assertEqual(links, set())

    def test_owner_hub_cards_and_section_links_open_existing_destinations(self):
        self.rollout()
        self.client.force_login(self.owner)
        for route in ('backoffice_workspace_courses', 'backoffice_workspace_students',
                      'backoffice_workspace_groups', 'backoffice_workspace_payments',
                      'backoffice_workspace_plans', 'backoffice_workspace_settings'):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assert_links_open(response)

    def test_teacher_scope_and_handoff_return_survive_new_and_old_teacher_renderers(self):
        self.rollout()
        self.client.force_login(self.teacher)
        for v1_teacher in (False, True):
            set_flag('frontend_v1_teacher', enabled=v1_teacher, reason='Verify retained teacher handoff')
            listing = self.client.get(reverse('backoffice_workspace_groups'))
            self.assertContains(listing, self.group.name)
            self.assertNotContains(listing, self.foreign_group.name)
            for route in ('teacher_release', 'teacher_attendance'):
                url = reverse(route) + '?cohort=' + str(self.group.pk)
                with self.subTest(v1_teacher=v1_teacher, route=route):
                    self.assertContains(listing, 'href="' + url + '"')
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'Boshqaruvga qaytish')
                    self.assertEqual(response.context['backoffice_return_url'], reverse('backoffice_workspace_groups'))
                    self.assertEqual(self.client.get(reverse(route), {'cohort': self.foreign_group.pk}).status_code, 404)
            student = self.client.get(reverse('backoffice_workspace_student', args=[self.learner.pk]),
                                      {'course': self.course.pk, 'lesson': self.lesson.pk})
            self.assertEqual(student.status_code, 200)
            self.assertNotContains(student, self.foreign_course.title)
            self.assertEqual(self.client.get(reverse('backoffice_workspace_student',
                                                     args=[self.foreign_learner.pk])).status_code, 404)

    def test_full_rollback_preserves_saved_lesson_then_restores_same_editor(self):
        self.rollout()
        self.client.force_login(self.teacher)
        url = reverse('backoffice_workspace_course', args=[self.course.pk])
        selected = {'lesson': self.lesson.pk}
        page = self.client.get(url, selected)
        data = {
            'action': 'lesson_save', 'lesson_id': self.lesson.pk,
            'lesson_revision': page.context['lesson_revision'], 'module': self.module.pk,
            'title': 'Saved through the unified workspace', 'content': '<p>Merhaba acceptance</p>',
            'video_url': '', 'order': 1, 'xp_reward': 10,
        }
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.rollout(course=False, support=False, design=False, navigation=False)
        self.assertEqual(self.client.get(url, selected).status_code, 404)
        self.assertEqual(self.client.post(url, {**data, 'title': 'Must not overwrite'}).status_code, 409)
        legacy = self.client.get(reverse('backoffice_lesson_edit', args=[self.lesson.pk]))
        self.assertEqual(legacy.status_code, 200)
        self.assertContains(legacy, 'Saved through the unified workspace')
        self.assertContains(legacy, 'Merhaba acceptance')
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, data['title'])
        self.rollout()
        restored = self.client.get(url, selected)
        self.assertEqual(restored.context['lesson'].pk, self.lesson.pk)
        self.assertContains(restored, data['title'])
        self.assertContains(restored, 'Merhaba acceptance')
        self.assert_links_open(restored)

    def test_design_draft_publication_and_receipts_survive_full_rollout_cycle(self):
        self.rollout()
        self.client.force_login(self.owner)
        value = defaults()
        value['values']['button-radius'] = 17
        operation = str(uuid4())
        command_url = reverse('backoffice_design_command')
        save = {'operation': operation, 'command': 'save_draft', 'payload': {
            'value': value, 'draft_revision': 0, 'base_version': 0,
        }}
        self.assertEqual(self.client.post(command_url, json.dumps(save), content_type='application/json').status_code, 200)
        publish = {'operation': str(uuid4()), 'command': 'publish', 'payload': {
            'draft_revision': 1, 'base_version': 0, 'reason': 'Synthetic acceptance theme', 'confirmed': True,
        }}
        self.assertEqual(self.client.post(command_url, json.dumps(publish), content_type='application/json').status_code, 200)
        state_url = reverse('backoffice_design_state')
        before = self.client.get(state_url, {'operation': operation}).json()
        css_before = self.client.get(reverse('design_theme_css')).content
        counts = tuple(model.objects.count() for model in (DesignDraft, DesignVersion, DesignOperation, DesignState))
        self.rollout(course=False, support=False, design=False, navigation=False)
        self.assertEqual(self.client.get(state_url).status_code, 404)
        self.assertEqual(self.client.post(command_url, json.dumps(save), content_type='application/json').status_code, 404)
        self.assertEqual(self.client.get(reverse('design_theme_css')).content, b'')
        self.assertEqual(tuple(model.objects.count() for model in
                               (DesignDraft, DesignVersion, DesignOperation, DesignState)), counts)
        self.rollout()
        restored = self.client.get(state_url, {'operation': operation}).json()
        self.assertEqual(restored, before)
        self.assertEqual(self.client.get(reverse('design_theme_css')).content, css_before)
        self.assertIn(b'--dc-button-radius:17px;', css_before)
