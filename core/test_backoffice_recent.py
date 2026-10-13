"""Opened-work history is session navigation state, never learner/content state."""
from datetime import date
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.db import connection
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from cohorts.models import Cohort, Enrollment
from core.backoffice_recent import MAX_ITEMS, SESSION_KEY, recent_work, record_opened
from core.flags import set_flag
from courses.models import Course, Lesson, LessonProgress, Module
from frontend.models import AuthPageSettings, LandingPage, SiteSettings


@override_settings(GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='')
class BackofficeRecentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user('recent-teacher', 'recent-teacher@example.test', is_staff=True)
        cls.other = User.objects.create_user('recent-other', 'recent-other@example.test', is_staff=True)
        cls.owner = User.objects.create_user('recent-owner', 'recent-owner@example.test', is_staff=True, is_superuser=True)
        cls.student = User.objects.create_user('recent-student', first_name='Madina', email='private@example.test',
                                               phone_number='998901234567')
        cls.course = Course.objects.create(title='Turk tili', instructor=cls.teacher)
        cls.module = Module.objects.create(course=cls.course, title='Tanishuv')
        cls.lesson = Lesson.objects.create(module=cls.module, title='Birinchi dars')
        cls.other_course = Course.objects.create(title='Private course', instructor=cls.other)
        cls.other_module = Module.objects.create(course=cls.other_course, title='Private module')
        cls.other_lesson = Lesson.objects.create(module=cls.other_module, title='Private lesson')
        cls.cohort = Cohort.objects.create(name='Guruh', course=cls.course, start_date=date(2026, 1, 1))
        cls.enrollment = Enrollment.objects.create(student=cls.student, cohort=cls.cohort, status='pending')
        SiteSettings.load()
        AuthPageSettings.load()
        LandingPage.load()

    def setUp(self):
        for flag in ('backoffice_unified_navigation', 'backoffice_course_workspace',
                     'backoffice_student_support', 'backoffice_design_workspace'):
            set_flag(flag, enabled=True, reason='Recent navigation regression')
        self.client.force_login(self.teacher)

    def url(self, course=None):
        return reverse('backoffice_workspace_course', kwargs={'course_id': (course or self.course).pk})

    def request(self, *, actor=None, state=None, method='get'):
        request = getattr(RequestFactory(), method)('/backoffice/workspace/')
        request.user = actor or self.teacher
        request.session = {} if state is None else {SESSION_KEY: state}
        return request

    def state(self, *items, actor=None):
        return {'actor_id': (actor or self.teacher).pk, 'items': list(items)}

    def course_entry(self):
        return {'kind': 'course', 'course_id': self.course.pk, 'lesson_id': self.lesson.pk}

    def test_successful_course_get_records_resolved_ids_and_not_query_or_content(self):
        response = self.client.get(self.url(), {'lesson': self.lesson.pk, 'q': 'private@example.test',
                                               'resource_q': '998901234567', 'token': 'secret-query'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session[SESSION_KEY], self.state(self.course_entry()))
        self.assertFalse(LessonProgress.objects.exists())

    def test_home_returns_actual_opened_work_and_never_newest_created_course_as_recent(self):
        self.assertEqual(self.client.get(reverse('backoffice_workspace_home')).context['recent_work'], [])
        self.client.get(self.url(), {'lesson': self.lesson.pk})
        latest = Course.objects.create(title='Never opened', instructor=self.teacher)
        response = self.client.get(reverse('backoffice_workspace_home'))
        self.assertEqual([row['title'] for row in response.context['recent_work']], [self.lesson.title])
        self.assertNotIn(latest.title, str(response.context['recent_work']))
        self.assertEqual(parse_qs(urlsplit(response.context['recent_work'][0]['url']).query),
                         {'lesson': [str(self.lesson.pk)]})

    def test_student_default_course_lesson_recorded_without_contact_or_search(self):
        url = reverse('backoffice_workspace_student', kwargs={'student_id': self.student.pk})
        response = self.client.get(url, {'q': self.student.email, 'page': '2', 'filter_course': self.course.pk})
        self.assertEqual(response.status_code, 200)
        item = {'kind': 'student', 'student_id': self.student.pk, 'course_id': self.course.pk,
                'lesson_id': self.lesson.pk, 'filter_course_id': self.course.pk, 'page': 2}
        self.assertEqual(self.client.session[SESSION_KEY], self.state(item))
        rows = recent_work(self.request(state=self.state(item)))
        self.assertEqual(rows[0]['title'], 'Madina')
        self.assertEqual(parse_qs(urlsplit(rows[0]['url']).query), {
            'course': [str(self.course.pk)], 'lesson': [str(self.lesson.pk)],
            'filter_course': [str(self.course.pk)], 'page': ['2']})
        self.assertNotIn(self.student.email, str(rows))
        self.assertNotIn(self.student.phone_number, str(rows))

    def test_new_lesson_tracks_only_validated_parent_and_preview_enum(self):
        response = self.client.get(self.url(), {'module': self.module.pk, 'new': '1', 'view': 'preview'})
        self.assertEqual(response.status_code, 200)
        item = self.client.session[SESSION_KEY]['items'][0]
        self.assertEqual(item, {'kind': 'course', 'course_id': self.course.pk,
                                'module_id': self.module.pk, 'view': 'preview'})
        rows = recent_work(self.request(state=self.state(item)))
        self.assertEqual(rows[0]['title'], 'Yangi dars')
        self.assertEqual(parse_qs(urlsplit(rows[0]['url']).query),
                         {'module': [str(self.module.pk)], 'new': ['1'], 'view': ['preview']})

    def test_only_get_200_records_and_invalid_http_navigation_keeps_previous_work(self):
        state = self.state(self.course_entry())
        for method, status in [('post', 200), ('post', 302), ('get', 302), ('get', 400),
                               ('get', 403), ('get', 404), ('get', 409), ('get', 500)]:
            with self.subTest(method=method, status=status):
                request = self.request(state=state, method=method)
                record_opened(request, HttpResponse(status=status), kind='course', course_id=self.course.pk)
                self.assertEqual(request.session[SESSION_KEY], state)
        self.client.get(self.url(), {'lesson': self.lesson.pk})
        old = self.client.session[SESSION_KEY]
        self.assertEqual(self.client.get(self.url(), {'lesson': self.other_lesson.pk}).status_code, 404)
        self.assertEqual(self.client.get(self.url() + '?lesson=1&lesson=2').status_code, 400)
        self.assertEqual(self.client.session[SESSION_KEY], old)

    def test_recent_is_bounded_deduplicated_and_reopening_moves_item_first(self):
        request = self.request()
        lessons = [Lesson.objects.create(module=self.module, title=f'Lesson {i}') for i in range(MAX_ITEMS + 2)]
        for lesson in lessons:
            record_opened(request, HttpResponse(), kind='course', course_id=self.course.pk, lesson_id=lesson.pk)
        self.assertEqual(len(request.session[SESSION_KEY]['items']), MAX_ITEMS)
        oldest = lessons[-MAX_ITEMS]
        record_opened(request, HttpResponse(), kind='course', course_id=self.course.pk, lesson_id=oldest.pk)
        self.assertEqual(request.session[SESSION_KEY]['items'][0]['lesson_id'], oldest.pk)
        self.assertEqual(len(request.session[SESSION_KEY]['items']), MAX_ITEMS)

    def test_student_new_selection_replaces_same_student_history_entry(self):
        request = self.request()
        second = Lesson.objects.create(module=self.module, title='Second')
        for lesson in (self.lesson, second):
            record_opened(request, HttpResponse(), kind='student', student_id=self.student.pk,
                          course_id=self.course.pk, lesson_id=lesson.pk)
        self.assertEqual(len(request.session[SESSION_KEY]['items']), 1)
        self.assertEqual(request.session[SESSION_KEY]['items'][0]['lesson_id'], second.pk)

    def test_labels_and_parent_relationships_are_revalidated_live(self):
        request = self.request(state=self.state(self.course_entry()))
        Course.objects.filter(pk=self.course.pk).update(title='Renamed course')
        Lesson.objects.filter(pk=self.lesson.pk).update(title='Renamed lesson')
        self.assertEqual(recent_work(request)[0]['title'], 'Renamed lesson')
        self.assertEqual(recent_work(request)[0]['subtitle'], 'Renamed course')
        Lesson.objects.filter(pk=self.lesson.pk).update(module=self.other_module)
        self.assertEqual(recent_work(request), [])

    def test_deleted_object_and_revoked_course_scope_are_omitted(self):
        request = self.request(state=self.state(self.course_entry()))
        Course.objects.filter(pk=self.course.pk).update(instructor=self.other)
        self.assertEqual(recent_work(request), [])
        Course.objects.filter(pk=self.course.pk).update(instructor=self.teacher)
        self.lesson.delete()
        self.assertEqual(recent_work(request), [])

    def test_student_scope_role_and_selected_filter_are_revalidated(self):
        item = {'kind': 'student', 'student_id': self.student.pk, 'course_id': self.course.pk,
                'lesson_id': self.lesson.pk}
        request = self.request(state=self.state(item))
        self.assertEqual(len(recent_work(request)), 1)
        # Inactive learner is a supported diagnosis, not permission revocation.
        get_user_model().objects.filter(pk=self.student.pk).update(is_active=False)
        self.assertEqual(len(recent_work(request)), 1)
        request.session[SESSION_KEY] = self.state({**item, 'filter_course_id': self.other_course.pk})
        self.assertEqual(recent_work(request), [])
        request.session[SESSION_KEY] = self.state(item)
        get_user_model().objects.filter(pk=self.student.pk).update(is_staff=True)
        self.assertEqual(recent_work(request), [])
        get_user_model().objects.filter(pk=self.student.pk).update(is_staff=False)
        self.enrollment.delete()
        self.assertEqual(recent_work(request), [])

    def test_owner_can_resume_unenrolled_student_and_in_scope_no_enrollment_diagnosis(self):
        unenrolled = get_user_model().objects.create_user('recent-unenrolled', 'recent-unenrolled@example.test')
        request = self.request(actor=self.owner, state=self.state(
            {'kind': 'student', 'student_id': unenrolled.pk, 'course_id': self.course.pk,
             'lesson_id': self.lesson.pk}, actor=self.owner))
        self.assertEqual(len(recent_work(request)), 1)

    def test_destination_and_navigation_flag_rollback_hide_but_preserve_ids(self):
        state = self.state(self.course_entry())
        request = self.request(state=state)
        for flag in ('backoffice_course_workspace', 'backoffice_unified_navigation'):
            set_flag(flag, enabled=False, reason='Recent rollback')
            self.assertEqual(recent_work(request), [])
            record_opened(request, HttpResponse(), kind='course', course_id=self.course.pk)
            self.assertEqual(request.session[SESSION_KEY], state)
            set_flag(flag, enabled=True, reason='Recent restored')
            self.assertEqual(len(recent_work(request)), 1)

    def test_design_entry_requires_current_owner_and_design_flag(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('backoffice_design'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session[SESSION_KEY], self.state({'kind': 'design'}, actor=self.owner))
        request = self.request(actor=self.owner, state=self.client.session[SESSION_KEY])
        self.assertEqual(recent_work(request)[0]['url'], reverse('backoffice_design'))
        set_flag('backoffice_design_workspace', enabled=False, reason='Design rollback')
        self.assertEqual(recent_work(request), [])
        set_flag('backoffice_design_workspace', enabled=True, reason='Design restored')
        get_user_model().objects.filter(pk=self.owner.pk).update(is_superuser=False)
        self.assertEqual(recent_work(request), [])

    def test_stale_actor_permissions_and_actor_mismatch_cannot_disclose_history(self):
        state = self.state(self.course_entry())
        request = self.request(state=state)
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_staff=False)
        self.assertEqual(recent_work(request), [])
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_staff=True, is_active=False)
        self.assertEqual(recent_work(request), [])
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_active=True)
        request.user = self.other
        self.assertEqual(recent_work(request), [])
        record_opened(request, HttpResponse(), kind='course', course_id=self.other_course.pk)
        self.assertEqual(request.session[SESSION_KEY], self.state(
            {'kind': 'course', 'course_id': self.other_course.pk}, actor=self.other))

    def test_logout_and_changed_login_drop_history(self):
        self.client.get(self.url(), {'lesson': self.lesson.pk})
        self.assertIn(SESSION_KEY, self.client.session)
        self.client.post(reverse('logout'))
        self.client.force_login(self.teacher)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.client.get(self.url(), {'lesson': self.lesson.pk})
        self.client.force_login(self.other)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_recent_read_is_write_free_even_for_invalid_entries(self):
        state = self.state(self.course_entry(), {'kind': 'course', 'course_id': self.other_course.pk})
        request = self.request(state=state)
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(len(recent_work(request)), 1)
        writes = [row['sql'] for row in queries if row['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'REPLACE'))]
        self.assertEqual(writes, [])
        self.assertEqual(request.session[SESSION_KEY], state)

    def test_malformed_and_overwide_session_values_fail_closed(self):
        bad_items = [None, [], {'kind': []}, {'kind': 'unexpected'},
                     {'kind': 'course', 'course_id': True}, {'kind': 'course', 'course_id': -1},
                     {'kind': 'course', 'course_id': '1' * 19},
                     {**self.course_entry(), 'url': 'https://example.test'},
                     {**self.course_entry(), 'q': self.student.email},
                     {**self.course_entry(), 'module_id': self.module.pk},
                     {'kind': 'student', 'student_id': self.student.pk, 'lesson_id': self.lesson.pk}]
        for item in bad_items:
            with self.subTest(item=item):
                self.assertEqual(recent_work(self.request(state=self.state(item))), [])
        for state in ([], None, {'actor_id': True, 'items': []},
                      self.state(*([self.course_entry()] * (MAX_ITEMS + 1))),
                      {'actor_id': self.teacher.pk, 'items': 'bad'}):
            with self.subTest(state=state):
                self.assertEqual(recent_work(self.request(state=state)), [])

    def test_reopening_same_successful_page_does_not_update_session(self):
        self.client.get(self.url(), {'lesson': self.lesson.pk})
        with CaptureQueriesContext(connection) as queries:
            self.client.get(self.url(), {'lesson': self.lesson.pk})
        session_writes = [row['sql'] for row in queries if row['sql'].lstrip().upper().startswith(('UPDATE', 'INSERT'))
                          and 'django_session' in row['sql']]
        self.assertEqual(session_writes, [])
