"""Catalog navigation changes destinations, never payment or membership writers."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from aicontrol.models import SystemAuditEvent
from cohorts.models import Cohort, Enrollment
from core.flags import set_flag
from courses.models import Course, Lesson, Module
from subscriptions.models import Plan


class CatalogNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(
            'navigation-owner', 'navigation-owner@example.test', is_staff=True, is_superuser=True,
        )
        cls.teacher = User.objects.create_user(
            'navigation-teacher', 'navigation-teacher@example.test', is_staff=True,
        )
        cls.student = User.objects.create_user('navigation-student', 'navigation-student@example.test')
        cls.plan = Plan.objects.get(code='standard')
        cls.course = Course.objects.create(title='Navigation course', instructor=cls.teacher)
        cls.module = Module.objects.create(course=cls.course, title='Navigation module')
        cls.lesson = Lesson.objects.create(module=cls.module, title='Navigation lesson')
        cls.cohort = Cohort.objects.create(
            course=cls.course, name='Navigation group', start_date=date(2026, 10, 1),
        )
        cls.target = Cohort.objects.create(
            course=cls.course, name='Second group', start_date=date(2026, 10, 1),
        )
        cls.enrollment = Enrollment.objects.create(
            student=cls.student, cohort=cls.cohort, status=Enrollment.STATUS_FROZEN,
        )

    def setUp(self):
        self.client.force_login(self.owner)

    def navigation(self, enabled):
        set_flag('backoffice_unified_navigation', enabled=enabled, reason='Isolated navigation regression')

    def plan_data(self, **changes):
        data = {
            'name': self.plan.name, 'price': '270000', 'description': 'To‘liq darslar',
            'cohort_capacity_limit': str(self.plan.cohort_capacity_limit),
            'button_text': 'Tanlash', 'order': '2', 'features_text': 'Darslar\nSertifikat',
            'change_reason': 'Synthetic catalog price review', 'confirm_change': 'on',
        }
        data.update(changes)
        return data

    def cohort_data(self, **changes):
        data = {
            'name': 'New navigation group', 'course': str(self.course.pk), 'plan': str(self.plan.pk),
            'capacity': '8', 'start_date': '2026-10-01', 'is_active': 'on',
            'change_reason': 'Synthetic group review', 'confirm_change': 'on',
        }
        data.update(changes)
        return data

    def members_url(self):
        return reverse('backoffice_cohort_members', args=[self.cohort.pk]) + (
            f'?enrollment={self.enrollment.pk}&lesson={self.lesson.pk}'
        )

    def test_plan_save_returns_to_plans_only_when_enabled_and_keeps_audit(self):
        for enabled, price in ((False, '271000'), (True, '272000')):
            with self.subTest(enabled=enabled):
                self.navigation(enabled)
                response = self.client.post(
                    reverse('backoffice_plan_edit', args=[self.plan.pk]), self.plan_data(price=price),
                )
                self.assertRedirects(response, reverse(
                    'backoffice_workspace_plans' if enabled else 'backoffice_catalog',
                ), fetch_redirect_response=False)
                self.plan.refresh_from_db()
                self.assertEqual(self.plan.price, int(price))
                audit = SystemAuditEvent.objects.filter(action='catalog.plan.update').latest('pk')
                self.assertEqual(audit.actor_id, self.owner.pk)
                self.assertEqual(audit.reason, 'Synthetic catalog price review')
                self.assertEqual(audit.after['price'], price)

    def test_group_create_and_edit_return_to_groups_only_when_enabled(self):
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                self.navigation(enabled)
                response = self.client.post(reverse('backoffice_cohort_create'), self.cohort_data())
                expected = reverse('backoffice_workspace_groups' if enabled else 'backoffice_catalog')
                self.assertRedirects(response, expected, fetch_redirect_response=False)
                cohort = Cohort.objects.filter(name='New navigation group').latest('pk')
                response = self.client.post(
                    reverse('backoffice_cohort_edit', args=[cohort.pk]),
                    self.cohort_data(name='Edited navigation group'),
                )
                self.assertRedirects(response, expected, fetch_redirect_response=False)
                cohort.refresh_from_db()
                self.assertEqual(cohort.name, 'Edited navigation group')
                self.assertEqual(cohort.course_id, self.course.pk)
                self.assertEqual(cohort.plan_id, self.plan.pk)
                audit = SystemAuditEvent.objects.filter(action='catalog.cohort.save').latest('pk')
                self.assertEqual(audit.actor_id, self.owner.pk)
                self.assertEqual(audit.reason, 'Synthetic group review')
                self.assertEqual(audit.after['name'], cohort.name)

    def test_invalid_forms_keep_input_and_new_section_return_without_writing(self):
        self.navigation(True)
        initial_price = self.plan.price
        initial_cohorts = Cohort.objects.count()
        response = self.client.post(
            reverse('backoffice_plan_edit', args=[self.plan.pk]), self.plan_data(confirm_change=''),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('confirm_change', response.context['form'].errors)
        self.assertEqual(response.context['form']['price'].value(), '270000')
        self.assertContains(response, f'href="{reverse("backoffice_workspace_plans")}"')
        response = self.client.post(reverse('backoffice_cohort_create'), self.cohort_data(capacity='0'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('capacity', response.context['form'].errors)
        self.assertEqual(response.context['form']['name'].value(), 'New navigation group')
        self.assertContains(response, f'href="{reverse("backoffice_workspace_groups")}"')
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.price, initial_price)
        self.assertEqual(Cohort.objects.count(), initial_cohorts)
        self.assertFalse(SystemAuditEvent.objects.filter(
            action__in=['catalog.plan.update', 'catalog.cohort.save'],
        ).exists())

    def test_staff_and_student_cannot_write_catalog_with_either_navigation(self):
        initial_price = self.plan.price
        initial_cohorts = Cohort.objects.count()
        for enabled in (False, True):
            self.navigation(enabled)
            for actor in (self.teacher, self.student):
                with self.subTest(enabled=enabled, actor=actor.username):
                    self.client.force_login(actor)
                    self.assertEqual(self.client.post(
                        reverse('backoffice_plan_edit', args=[self.plan.pk]), self.plan_data(),
                    ).status_code, 403)
                    self.assertEqual(self.client.post(
                        reverse('backoffice_cohort_create'), self.cohort_data(),
                    ).status_code, 403)
                    self.assertEqual(self.client.get(self.members_url()).status_code, 403)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.price, initial_price)
        self.assertEqual(Cohort.objects.count(), initial_cohorts)
        self.assertFalse(SystemAuditEvent.objects.filter(
            action__in=['catalog.plan.update', 'catalog.cohort.save'],
        ).exists())

    def test_member_return_and_plain_tariff_copy_keep_focused_support_link(self):
        set_flag('backoffice_student_support', enabled=True, reason='Isolated support return regression')
        support_url = reverse('backoffice_workspace_student', args=[self.student.pk]) + (
            f'?course={self.course.pk}&lesson={self.lesson.pk}'
        )
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                self.navigation(enabled)
                response = self.client.get(self.members_url())
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['support_return_url'], support_url)
                self.assertEqual(response.context['selected_enrollment'].pk, self.enrollment.pk)
                self.assertContains(response, f'href="{reverse("backoffice_workspace_groups" if enabled else "backoffice_catalog")}"')
                self.assertContains(response, 'Tarif belgilanmagan' if enabled else 'Legacy')
                self.assertContains(response, 'name="allow_tier_change"')
                self.assertContains(response, 'name="confirm_change"')

    def test_member_restore_keeps_focused_post_redirect_and_existing_expired_result(self):
        self.navigation(True)
        response = self.client.post(self.members_url(), {
            'enrollment_id': self.enrollment.pk, 'action': 'restore',
            'change_reason': 'Synthetic membership review', 'confirm_change': 'on',
        })
        self.assertRedirects(response, self.members_url(), fetch_redirect_response=False)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.STATUS_EXPIRED)
        self.assertFalse(self.enrollment.has_active_access())
        audit = SystemAuditEvent.objects.get(action='membership.restore')
        self.assertEqual(audit.actor_id, self.owner.pk)
        self.assertEqual(audit.reason, 'Synthetic membership review')

    def test_flag_off_catalog_editor_keeps_legacy_return(self):
        self.navigation(False)
        for name, args in (('backoffice_plan_edit', [self.plan.pk]), ('backoffice_cohort_create', [])):
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=args))
                self.assertContains(response, 'Katalogga qaytish')
                self.assertNotContains(response, 'Tariflarga qaytish')
                self.assertNotContains(response, 'Guruhlarga qaytish')
