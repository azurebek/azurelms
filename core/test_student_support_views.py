"""Learner support navigation, privacy and diagnosis/action/readback contracts."""
from datetime import date
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from cohorts.models import Cohort, Enrollment, PaymentReceipt
from core.flags import flag_by_slug, set_flag
from courses.models import Course, Module, Lesson, CohortLessonRelease, LessonProgress


@override_settings(GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='')
class StudentSupportViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user('support-teacher', 'support-teacher@example.test', is_staff=True)
        cls.other = User.objects.create_user('support-other', 'support-other@example.test', is_staff=True)
        cls.owner = User.objects.create_user('support-owner', 'support-owner@example.test', is_staff=True, is_superuser=True)
        cls.learner = User.objects.create_user('madina', 'madina@example.test', first_name='Madina', phone_number='998901234567')
        cls.foreign = User.objects.create_user('hidden-target', 'secret-target@example.test')
        cls.unenrolled = User.objects.create_user('unregistered', 'unregistered@example.test')
        cls.course = Course.objects.create(title='Turk tili', instructor=cls.teacher)
        cls.other_course = Course.objects.create(title='Private course', instructor=cls.other)
        cls.cohort = Cohort.objects.create(name='Kechki guruh', course=cls.course, start_date=date(2026, 1, 1))
        cls.other_cohort = Cohort.objects.create(name='Private group', course=cls.other_course, start_date=date(2026, 1, 1))
        cls.enrollment = Enrollment.objects.create(student=cls.learner, cohort=cls.cohort, status='active')
        Enrollment.objects.create(student=cls.learner, cohort=cls.other_cohort, status='pending')
        Enrollment.objects.create(student=cls.foreign, cohort=cls.other_cohort, status='active')
        module = Module.objects.create(course=cls.course, title='Tanishuv')
        cls.first = Lesson.objects.create(module=module, title='Birinchi dars', order=1)
        cls.lesson = Lesson.objects.create(module=module, title='Ikkinchi dars', order=2)
        other_module = Module.objects.create(course=cls.other_course, title='Private module')
        cls.other_lesson = Lesson.objects.create(module=other_module, title='Private lesson')

    def setUp(self):
        set_flag('backoffice_student_support', enabled=True, reason='Support view regression')
        self.client.force_login(self.teacher)

    def url(self, target=None):
        return reverse('backoffice_workspace_student', kwargs={'student_id': (target or self.learner).pk})

    def test_search_scopes_people_and_course_labels_before_rendering(self):
        url = reverse('backoffice_workspace_students')
        for query in ('Madina', 'madina@example.test', '998901234567'):
            response = self.client.get(url, {'q': query})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['page_obj'].paginator.count, 1)
            self.assertContains(response, 'Madina')
            self.assertNotContains(response, 'Private course')
            self.assertNotContains(response, 'Private group')
            self.assertNotContains(response, 'secret-target@example.test')
        self.assertEqual(self.client.get(url, {'q': 'secret-target'}).context['page_obj'].paginator.count, 0)

    def test_owner_finds_unenrolled_learner_but_never_staff_targets(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url(self.unenrolled))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['diagnosis']['code'], 'no_course')
        self.assertEqual(self.client.get(self.url(self.teacher)).status_code, 404)
        listing = self.client.get(reverse('backoffice_workspace_students'))
        self.assertEqual(listing.context['page_obj'].paginator.count, 3)

    def test_teacher_cannot_open_foreign_or_unenrolled_student(self):
        for student in (self.foreign, self.unenrolled, self.owner):
            self.assertEqual(self.client.get(self.url(student)).status_code, 404)

    def test_parent_ids_and_ambiguous_query_fail_without_disclosure(self):
        for query in ({'course': self.other_course.pk},
                      {'course': self.course.pk, 'lesson': self.other_lesson.pk},
                      {'filter_course': self.other_course.pk}, {'course': 'bad'}, {'lesson': '-1'}):
            response = self.client.get(self.url(), query)
            self.assertEqual(response.status_code, 404)
            self.assertNotContains(response, 'Private lesson', status_code=404)
        self.assertEqual(self.client.get(self.url() + '?course=1&course=2').status_code, 400)
        self.assertEqual(self.client.get(self.url(), {'cohort': self.cohort.pk}).status_code, 400)

    def test_card_limits_contact_and_related_data_to_permission_scope(self):
        response = self.client.get(self.url(), {'course': self.course.pk})
        self.assertContains(response, 'Madina')
        self.assertNotContains(response, 'Private group')
        self.assertNotContains(response, '998901234567')
        self.assertFalse(response.context['enrollment_rows'][0]['membership_url'])
        self.client.force_login(self.owner)
        response = self.client.get(self.url(), {'course': self.course.pk})
        self.assertContains(response, '998901234567')
        self.assertTrue(response.context['enrollment_rows'][0]['membership_url'])

    def test_back_and_recheck_links_preserve_selected_person_and_search(self):
        response = self.client.get(self.url(), {'q': 'Madina', 'page': '2', 'filter_course': self.course.pk,
                                              'course': self.course.pk, 'lesson': self.lesson.pk})
        back = urlsplit(response.context['back_url'])
        self.assertEqual(back.path, reverse('backoffice_workspace_students'))
        self.assertEqual(parse_qs(back.query), {'q': ['Madina'], 'page': ['2'], 'course': [str(self.course.pk)]})
        recheck = urlsplit(response.context['recheck_url'])
        self.assertEqual(recheck.path, self.url())
        self.assertEqual(parse_qs(recheck.query)['lesson'], [str(self.lesson.pk)])
        self.assertEqual(parse_qs(recheck.query)['filter_course'], [str(self.course.pk)])

    def test_diagnose_release_then_recheck_uses_actual_policy_and_never_records_visit(self):
        CohortLessonRelease.objects.create(cohort=self.cohort, lesson=self.lesson, is_released=False)
        set_flag('frontend_v1_teacher', enabled=True, reason='Existing release confirmation')
        page = self.client.get(self.url(), {'course': self.course.pk, 'lesson': self.lesson.pk})
        self.assertEqual(page.context['diagnosis']['code'], 'drip')
        handoff = page.context['next_steps'][0]
        target = urlsplit(handoff['url'])
        self.assertEqual(parse_qs(target.query), {'cohort': [str(self.cohort.pk)], 'lesson': [str(self.lesson.pk)], 'action': ['release']})
        self.assertEqual(target.fragment, 'release-confirm')
        self.assertIn('butun guruhga', handoff['note'])
        confirmation = self.client.get(handoff['url'])
        self.assertEqual(confirmation.context['release_target'].pk, self.lesson.pk)
        self.assertFalse(CohortLessonRelease.objects.get(cohort=self.cohort, lesson=self.lesson).is_released)
        # The support route itself accepts no writes.
        self.assertEqual(self.client.post(self.url(), {'action': 'release'}).status_code, 405)
        self.assertFalse(LessonProgress.objects.exists())
        result = self.client.post(target.path + '?' + target.query, {
            'cohort': self.cohort.pk, 'lesson': self.lesson.pk, 'action': 'release', 'confirm_scope': 'yes',
        })
        self.assertEqual(result.status_code, 302)
        recheck = self.client.get(page.context['recheck_url'])
        self.assertEqual(recheck.context['diagnosis']['code'], 'open')
        self.assertFalse(LessonProgress.objects.exists())

    def test_inactive_group_has_no_broken_teacher_release_link(self):
        CohortLessonRelease.objects.create(cohort=self.cohort, lesson=self.lesson, is_released=False)
        Cohort.objects.filter(pk=self.cohort.pk).update(is_active=False)
        page = self.client.get(self.url(), {'course': self.course.pk, 'lesson': self.lesson.pk})
        self.assertEqual(page.context['diagnosis']['code'], 'drip')
        self.assertEqual(page.context['next_steps'], [])
        self.client.force_login(self.owner)
        page = self.client.get(self.url(), {'course': self.course.pk, 'lesson': self.lesson.pk})
        self.assertEqual(page.context['next_steps'][0]['url'], reverse('backoffice_cohort_edit', kwargs={'cohort_id': self.cohort.pk}))

    def test_primary_receipt_action_matches_diagnosed_enrollment_not_newest_receipt(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).update(status=Enrollment.STATUS_PENDING)
        current_cohort = Cohort.objects.create(
            name='Hozirgi guruh', course=self.course, start_date=date(2026, 2, 1))
        current = Enrollment.objects.create(
            student=self.learner, cohort=current_cohort, status=Enrollment.STATUS_PENDING)
        current_receipt = PaymentReceipt.objects.create(
            enrollment=current, amount=1000, receipt_image='receipts/current-synthetic.png')
        historical_receipt = PaymentReceipt.objects.create(
            enrollment=self.enrollment, amount=1000, receipt_image='receipts/historical-synthetic.png')

        for actor in (self.teacher, self.owner):
            with self.subTest(actor=actor.pk):
                self.client.force_login(actor)
                page = self.client.get(self.url(), {'course': self.course.pk})
                self.assertEqual(page.status_code, 200)
                self.assertEqual(page.context['diagnosis']['code'], 'pending')
                self.assertEqual(page.context['relevant_enrollment'].pk, current.pk)
                self.assertEqual([receipt.pk for receipt in page.context['pending_receipts']],
                                 [historical_receipt.pk, current_receipt.pk])
                primary = urlsplit(page.context['next_steps'][0]['url'])
                self.assertEqual(primary.path, reverse('backoffice_receipts'))
                self.assertEqual(parse_qs(primary.query), {
                    'enrollment': [str(current.pk)], 'receipt': [str(current_receipt.pk)],
                    'lesson': [str(self.first.pk)],
                })
                historical_row = next(row for row in page.context['receipt_rows']
                                      if row['id'] == historical_receipt.pk)
                self.assertEqual(historical_row['label'], self.cohort.name)
                self.assertEqual(parse_qs(urlsplit(historical_row['action_url']).query), {
                    'enrollment': [str(self.enrollment.pk)], 'receipt': [str(historical_receipt.pk)],
                    'lesson': [str(self.first.pk)],
                })

    def test_primary_action_never_substitutes_another_enrollments_pending_receipt(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).update(status=Enrollment.STATUS_PENDING)
        current_cohort = Cohort.objects.create(
            name='Cheksiz hozirgi guruh', course=self.course, start_date=date(2026, 2, 1))
        current = Enrollment.objects.create(
            student=self.learner, cohort=current_cohort, status=Enrollment.STATUS_PENDING)
        historical_receipt = PaymentReceipt.objects.create(
            enrollment=self.enrollment, amount=1000, receipt_image='receipts/historical-synthetic.png')

        for actor in (self.teacher, self.owner):
            with self.subTest(actor=actor.pk):
                self.client.force_login(actor)
                page = self.client.get(self.url(), {'course': self.course.pk})
                self.assertEqual(page.status_code, 200)
                self.assertEqual(page.context['diagnosis']['code'], 'pending')
                self.assertEqual(page.context['relevant_enrollment'].pk, current.pk)
                self.assertEqual([receipt.pk for receipt in page.context['pending_receipts']],
                                 [historical_receipt.pk])
                self.assertFalse(any(urlsplit(step['url']).path == reverse('backoffice_receipts')
                                     for step in page.context['next_steps']))
                historical_row = page.context['receipt_rows'][0]
                self.assertEqual(historical_row['id'], historical_receipt.pk)
                self.assertEqual(historical_row['label'], self.cohort.name)

    def test_flag_rollback_and_read_errors_fail_closed(self):
        self.assertFalse(flag_by_slug('backoffice_student_support').default)
        set_flag('backoffice_student_support', enabled=False, reason='Rollback')
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.assertEqual(self.client.get(reverse('backoffice_workspace_students')).status_code, 404)
        from aicontrol.models import FeatureFlag
        with patch.object(FeatureFlag.objects, 'filter', side_effect=DatabaseError('unreadable')):
            self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_course_workspace_and_support_flags_are_independent(self):
        set_flag('backoffice_course_workspace', enabled=False, reason='Course UI rollback only')
        page = self.client.get(self.url())
        self.assertEqual(page.status_code, 200)
        nav = {item['label']: item for item in page.context['workspace_nav']}
        self.assertTrue(nav['O‘quvchilar']['active'])
        self.assertEqual(nav['Kurslar']['url'], reverse('backoffice_courses'))
        self.assertContains(page, 'class="ws-brand" href="' + reverse('backoffice_dashboard') + '"')
        set_flag('backoffice_course_workspace', enabled=True, reason='Both workspaces')
        home = self.client.get(reverse('backoffice_workspace_home'))
        self.assertContains(home, reverse('backoffice_workspace_students'))

    def test_legacy_student_entry_redirects_but_staff_directory_remains(self):
        self.assertRedirects(self.client.get(reverse('backoffice_users'), {'role': 'students', 'q': 'Madina'}),
                             reverse('backoffice_workspace_students') + '?q=Madina')
        self.assertEqual(self.client.get(reverse('backoffice_users'), {'role': 'teachers'}).status_code, 200)

    def test_guest_student_and_deactivated_staff_are_denied(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url()).status_code, 302)
        self.client.force_login(self.learner)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.teacher.is_active = False
        self.teacher.save(update_fields=['is_active'])
        self.client.force_login(self.teacher)
        self.assertIn(self.client.get(self.url()).status_code, (302, 403))

    def test_private_responses_are_not_browser_cached(self):
        for url in (self.url(), reverse('backoffice_workspace_students'),
                    self.url() + '?course=bad', self.url() + '?course=1&course=2'):
            page = self.client.get(url)
            self.assertIn('no-store', page['Cache-Control'])
            self.assertIn('private', page['Cache-Control'])
        self.assertIn('no-store', self.client.post(self.url())['Cache-Control'])

    def test_stale_owner_is_refreshed_before_scope_and_presentation(self):
        from core.student_support_views import students, student
        get_user_model().objects.filter(pk=self.owner.pk).update(is_superuser=False)
        Course.objects.filter(pk=self.course.pk).update(instructor=self.owner)
        for view, url, kwargs in ((students, reverse('backoffice_workspace_students'), {}),
                                 (student, self.url() + '?course=' + str(self.course.pk), {'student_id': self.learner.pk})):
            request = RequestFactory().get(url)
            request.user = self.owner  # Deliberately stale owner object.
            response = view(request, **kwargs)
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'Private course')
            self.assertNotContains(response, '998901234567')
            self.assertFalse(request.user.is_superuser)
