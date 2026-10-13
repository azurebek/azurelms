"""Scope, bounded reads and destination contracts for unified search."""
from datetime import date
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse

from cohorts.models import Cohort, Enrollment
from core.backoffice_search import PAGE_SIZE, search, search_context
from core.flags import set_flag
from courses.models import Course, Lesson, Module
from frontend.models import AuthPageSettings, LandingPage, SiteSettings


@override_settings(GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='')
class BackofficeSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user('search-owner', 'search-owner@example.test', is_superuser=True, is_staff=True)
        cls.teacher = User.objects.create_user('search-teacher', 'search-teacher@example.test', is_staff=True)
        cls.other = User.objects.create_user('search-other', 'search-other@example.test', is_staff=True)
        cls.unassigned = User.objects.create_user('search-unassigned', 'search-unassigned@example.test', is_staff=True)
        cls.student = User.objects.create_user('madina', first_name='Madina', last_name='Karimova',
                                             email='only-contact@example.test', phone_number='998999001234')
        cls.foreign_student = User.objects.create_user('hidden-madina', 'hidden-madina@example.test', first_name='Madina', last_name='Secret')
        cls.unenrolled = User.objects.create_user('unenrolled', 'unenrolled@example.test', first_name='Unenrolled')
        cls.course = Course.objects.create(title='Tanishuv kursi', instructor=cls.teacher, is_active=False)
        cls.foreign_course = Course.objects.create(title='Secret kurs', instructor=cls.other)
        cls.module = Module.objects.create(title='Birinchi modul', course=cls.course)
        cls.lesson = Lesson.objects.create(title='Salom aytish', module=cls.module, content='PRIVATE BODY')
        cls.foreign_module = Module.objects.create(title='Secret modul', course=cls.foreign_course)
        cls.foreign_lesson = Lesson.objects.create(title='Salom SECRET', module=cls.foreign_module)
        cls.cohort = Cohort.objects.create(name='Visible group', course=cls.course, start_date=date(2026, 1, 1))
        cls.other_cohort = Cohort.objects.create(name='Secret group', course=cls.foreign_course, start_date=date(2026, 2, 1))
        Enrollment.objects.create(student=cls.student, cohort=cls.cohort, status=Enrollment.STATUS_EXPIRED)
        # Newest foreign membership must not leak into the visible learner caption.
        Enrollment.objects.create(student=cls.student, cohort=cls.other_cohort)
        Enrollment.objects.create(student=cls.foreign_student, cohort=cls.other_cohort)
        SiteSettings.load()
        AuthPageSettings.load()
        LandingPage.load()

    def setUp(self):
        for flag in ('backoffice_unified_navigation', 'backoffice_course_workspace', 'backoffice_student_support'):
            set_flag(flag, enabled=True, reason='Unified search regression')
        self.client.force_login(self.teacher)

    @property
    def url(self):
        return reverse('backoffice_workspace_search')

    def request(self, actor=None):
        request = RequestFactory().get(self.url)
        request.user = actor or self.teacher
        request.resolver_match = resolve(self.url)
        return request

    def context(self, query, *, actor=None, kind='all', page='1'):
        return search_context(self.request(actor), query=query, kind=kind, page=page)

    def get(self, query='', **params):
        return self.client.get(self.url, {'q': query, **params})

    def test_course_and_lesson_results_use_scope_before_matching_and_direct_destinations(self):
        courses = self.context('kurs', kind='course')['search_rows']
        self.assertEqual([row['title'] for row in courses], [self.course.title])
        self.assertEqual(courses[0]['subtitle'], 'Katalogda yashirilgan')
        lessons = self.context('Salom', kind='lesson')['search_rows']
        self.assertEqual([row['title'] for row in lessons], [self.lesson.title])
        self.assertEqual(lessons[0]['subtitle'], 'Tanishuv kursi · Birinchi modul')
        destination = urlsplit(lessons[0]['url'])
        self.assertEqual(destination.path, reverse('backoffice_workspace_course', kwargs={'course_id': self.course.pk}))
        self.assertEqual(parse_qs(destination.query), {'lesson': [str(self.lesson.pk)]})
        self.assertNotIn('PRIVATE BODY', str(lessons))

    def test_lesson_matches_course_module_and_title_terms_in_one_scoped_record(self):
        self.assertEqual([row['title'] for row in self.context('Tanishuv Birinchi Salom', kind='lesson')['rows']],
                         [self.lesson.title])
        self.assertEqual(self.context('Salom Secret', kind='lesson')['rows'], [])

    def test_keyboard_and_typographic_apostrophes_match_in_either_direction(self):
        Lesson.objects.filter(pk=self.lesson.pk).update(title='O‘zingizni tanishtiring')
        for query in ("O'zingizni", 'O‘zingizni', 'O’zingizni', 'Oʻzingizni', 'Oʼzingizni', 'O`zingizni'):
            with self.subTest(query=query):
                self.assertEqual([row['title'] for row in self.context(query, kind='lesson')['rows']],
                                 ['O‘zingizni tanishtiring'])
        Lesson.objects.filter(pk=self.lesson.pk).update(title="O'zingizni tanishtiring")
        self.assertEqual(len(self.context('O‘zingizni', kind='lesson')['rows']), 1)
        get_user_model().objects.filter(pk=self.student.pk).update(first_name='O‘tkir', last_name='Karimov')
        self.assertEqual([row['title'] for row in self.context("Karimov O'tkir", kind='student')['rows']],
                         ['O‘tkir Karimov'])
        self.assertTrue(self.context("O'quvchilar", kind='section')['rows'])

    def test_student_full_name_terms_and_visible_course_caption(self):
        for query in ('Madina Karimova', 'Karimova Madina', 'madina karim', 'madina'):
            with self.subTest(query=query):
                rows = self.context(query, kind='student')['rows']
                self.assertEqual([row['title'] for row in rows], ['Madina Karimova'])
                self.assertEqual(rows[0]['subtitle'], '@madina · Tanishuv kursi')
                self.assertEqual(rows[0]['url'], reverse('backoffice_workspace_student', kwargs={'student_id': self.student.pk}))
                self.assertNotIn('Secret', str(rows))
        self.assertEqual(self.context('Madina Missing', kind='student')['rows'], [])

    def test_contact_and_body_content_are_neither_searchable_nor_returned(self):
        for query in ('only-contact', '998999001234', 'PRIVATE BODY'):
            self.assertEqual(self.context(query)['rows'], [])
        rows = self.context('Madina', kind='student')['rows']
        self.assertNotIn(self.student.email, str(rows))
        self.assertNotIn(self.student.phone_number, str(rows))

    def test_owner_can_find_unenrolled_inactive_students_but_not_staff(self):
        get_user_model().objects.filter(pk=self.unenrolled.pk).update(is_active=False)
        self.assertEqual(self.context('Unenrolled', kind='student')['rows'], [])
        rows = self.context('Unenrolled', actor=self.owner, kind='student')['rows']
        self.assertEqual([row['title'] for row in rows], ['Unenrolled'])
        self.assertIn('Kursga yozilmagan', rows[0]['subtitle'])
        self.assertEqual(self.context('search-teacher', actor=self.owner, kind='student')['rows'], [])

    def test_owner_scope_and_unassigned_staff_scope_are_distinct(self):
        self.assertEqual(self.context('Secret', kind='course')['rows'], [])
        self.assertEqual(len(self.context('Secret', actor=self.owner, kind='course')['rows']), 1)
        for kind, query in (('course', 'kurs'), ('lesson', 'Salom'), ('student', 'Madina')):
            self.assertEqual(self.context(query, actor=self.unassigned, kind=kind)['rows'], [])

    def test_section_results_only_use_permitted_registry_routes_and_deduplicate(self):
        staff_rows = self.context('', kind='section')['rows']
        all_staff = self.context('Sozlamalar', kind='section')['rows']
        self.assertEqual(all_staff, [])
        self.assertTrue(self.context('Sozlamalar', actor=self.owner, kind='section')['rows'])
        self.assertEqual(self.context('Logo', kind='section')['rows'], [])
        self.assertTrue(self.context('Logo', actor=self.owner, kind='section')['rows'])
        self.assertEqual(len({row['url'] for row in staff_rows}), len(staff_rows))
        self.assertTrue(all(row['kind'] == 'section' for row in staff_rows))

    def test_blank_query_does_not_list_people_or_courses(self):
        rows = self.context('')['rows']
        self.assertTrue(rows)
        self.assertTrue(all(row['kind'] == 'section' for row in rows))
        for kind in ('course', 'lesson', 'student'):
            self.assertEqual(self.context('', kind=kind)['rows'], [])

    def test_surface_flags_omit_object_results_and_keep_legacy_section_destinations(self):
        set_flag('backoffice_course_workspace', enabled=False, reason='Search rollback')
        set_flag('backoffice_student_support', enabled=False, reason='Search rollback')
        for kind, query in (('course', 'kurs'), ('lesson', 'Salom'), ('student', 'Madina')):
            context = self.context(query, kind=kind)
            self.assertEqual(context['rows'], [])
            self.assertNotIn(kind, [tab['key'] for tab in context['tabs']])
        self.assertIn(reverse('backoffice_courses'), [row['url'] for row in self.context('Kurslar')['rows']])
        self.assertIn(reverse('backoffice_users'), [row['url'] for row in self.context('O‘quvchilar')['rows']])

    def test_pagination_crosses_type_boundaries_without_duplicate_or_dropped_rows(self):
        for index in range(14):
            Course.objects.create(title=f'Needle {index:02d}', instructor=self.teacher)
        for index in range(8):
            Lesson.objects.create(title=f'Needle lesson {index:02d}', module=self.module, order=index)
        pages = [self.context('Needle', page=str(number)) for number in (1, 2)]
        self.assertEqual(pages[0]['page_obj'].paginator.count, 22)
        self.assertEqual([len(context['rows']) for context in pages], [12, 10])
        joined = pages[0]['rows'] + pages[1]['rows']
        self.assertEqual(len({row['url'] for row in joined}), 22)
        self.assertEqual([row['kind'] for row in pages[1]['rows']], ['course'] * 2 + ['lesson'] * 8)
        self.assertEqual(self.context('Needle', page='999')['page_obj'].number, 2)

    def test_student_query_count_stays_fixed_as_result_and_enrollment_counts_grow(self):
        with CaptureQueriesContext(connection) as small_queries:
            small = self.context('Madina', kind='student')
        for index in range(20):
            learner = get_user_model().objects.create_user(f'madina-{index}', f'madina-{index}@example.test', first_name='Madina', last_name=f'{index:02d}')
            Enrollment.objects.create(student=learner, cohort=self.cohort)
        with CaptureQueriesContext(connection) as large_queries:
            large = self.context('Madina', kind='student')
        self.assertEqual(len(small['rows']), 1)
        self.assertEqual(len(large['rows']), PAGE_SIZE)
        self.assertEqual(len(small_queries), len(large_queries))
        selects = [entry['sql'].upper() for entry in large_queries if entry['sql'].lstrip().upper().startswith('SELECT')]
        self.assertTrue(any('LIMIT 12' in sql for sql in selects))
        self.assertFalse(any('PHONE_NUMBER' in sql or 'EMAIL' in sql for sql in selects if 'LIMIT 12' in sql))

    def test_read_projection_does_not_write_canonical_or_session_state(self):
        with CaptureQueriesContext(connection) as queries:
            self.context('Madina')
        writes = [entry['sql'] for entry in queries if entry['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))]
        self.assertEqual(writes, [])

    def test_http_is_private_no_store_and_has_normalized_query_and_signed_return(self):
        response = self.get('  Tanishuv   kursi  ', kind='course')
        self.assertEqual(response.status_code, 200)
        self.assertIn('private', response['Cache-Control'])
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(response.context['q'], 'Tanishuv kursi')
        row = response.context['search_rows'][0]
        self.assertIn('return_to', parse_qs(urlsplit(row['url']).query))
        self.assertTrue(response.context['workspace_search_enabled'])

    def test_auth_flag_and_post_denials_are_private(self):
        self.client.logout()
        response = self.get('Madina')
        self.assertEqual(response.status_code, 302)
        self.assertIn('no-store', response['Cache-Control'])
        self.client.force_login(self.student)
        response = self.get('Madina')
        self.assertEqual(response.status_code, 403)
        self.assertIn('no-store', response['Cache-Control'])
        self.client.force_login(self.teacher)
        response = self.client.post(self.url, {'q': 'Madina'})
        self.assertEqual(response.status_code, 405)
        self.assertIn('no-store', response['Cache-Control'])
        set_flag('backoffice_unified_navigation', enabled=False, reason='Search rollout off')
        response = self.get('Madina')
        self.assertEqual(response.status_code, 404)
        self.assertIn('no-store', response['Cache-Control'])

    def test_fresh_actor_recheck_rejects_stale_staff_and_inactive_instances(self):
        for updates in ({'is_staff': False}, {'is_staff': True, 'is_active': False}):
            get_user_model().objects.filter(pk=self.teacher.pk).update(**updates)
            response = search(self.request())
            self.assertEqual(response.status_code, 403)
            self.assertIn('no-store', response['Cache-Control'])

    def test_malformed_query_choices_and_duplicates_fail_without_disclosure(self):
        for params in ({'q': 'x' * 201}, {'kind': 'unknown'}, {'page': '-1'}, {'page': 'x'},
                       {'page': '1' * 20}, {'page': '٠١'}):
            response = self.client.get(self.url, params)
            self.assertEqual(response.status_code, 400)
            self.assertIn('no-store', response['Cache-Control'])
            self.assertNotContains(response, 'Madina Karimova', status_code=400)
            self.assertTrue(response.context['search_error'])
            self.assertTrue(all(row['kind'] == 'section' for row in response.context['search_rows']))
        for suffix in ('?q=one&q=two', '?kind=all&kind=course', '?page=1&page=2'):
            self.assertEqual(self.client.get(self.url + suffix).status_code, 400)

    def test_ascii_control_characters_are_rejected_with_a_usable_search_form(self):
        for character in ('\x00', '\n', '\r', '\t', '\x1f', '\x7f'):
            with self.subTest(character=repr(character)):
                response = self.get('Madina' + character)
                self.assertEqual(response.status_code, 400)
                self.assertIn('no-store', response['Cache-Control'])
                self.assertContains(response, 'Qidiruvni bir qatorda yozing', status_code=400)
                self.assertContains(response, 'name="q"', status_code=400)
                self.assertTrue(all(row['kind'] == 'section' for row in response.context['rows']))
