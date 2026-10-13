"""Cross-page return links stay private, scoped and attached to real form flows."""
from datetime import date
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urlsplit

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from cohorts.models import Cohort, Enrollment
from core.backoffice_forms import CourseBackofficeForm
from core.backoffice_recent import SESSION_KEY
from core.backoffice_return import SALT, make_return, return_context, with_return
from core.flags import set_flag
from courses.models import Course, Lesson, Module


class _Markup(HTMLParser):
    """Read actual destinations and hidden values instead of recreating UI links."""
    def __init__(self, response):
        super().__init__()
        self.links = []
        self.forms = []
        self.form = None
        self.feed(response.content.decode())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs)
        if tag == 'form':
            self.form = {'attrs': attrs, 'hidden': {}, 'names': set()}
            self.forms.append(self.form)
        if self.form is not None and tag in {'input', 'select', 'textarea', 'button'}:
            name = attrs.get('name')
            if name:
                self.form['names'].add(name)
                if tag == 'input' and attrs.get('type') == 'hidden':
                    self.form['hidden'][name] = attrs.get('value', '')

    def handle_endtag(self, tag):
        if tag == 'form':
            self.form = None


@override_settings(GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='')
class BackofficeReturnTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user('return-teacher', 'return-teacher@example.test', is_staff=True)
        cls.other = User.objects.create_user('return-other', 'return-other@example.test', is_staff=True)
        cls.student = User.objects.create_user('return-madina', 'return-madina@example.test', first_name='Madina')
        cls.course = Course.objects.create(
            title='Return cohort target', description='A synthetic course for return navigation.',
            instructor=cls.teacher, is_active=False,
        )
        cls.module = Module.objects.create(course=cls.course, title='Tanishuv')
        cls.lesson = Lesson.objects.create(module=cls.module, title='Return introduction', order=1)
        cls.second_lesson = Lesson.objects.create(module=cls.module, title='Return second lesson', order=2)
        cls.cohort = Cohort.objects.create(
            course=cls.course, name='Synthetic support group', start_date=date(2026, 1, 1),
        )
        Enrollment.objects.create(student=cls.student, cohort=cls.cohort, status='active')

    def setUp(self):
        for slug in ('backoffice_unified_navigation', 'backoffice_course_workspace',
                     'backoffice_student_support', 'backoffice_practice_authoring'):
            set_flag(slug, enabled=True, reason='Isolated return-flow regression')
        self.client.force_login(self.teacher)
        self.factory = RequestFactory()

    def request(self, token=None, *, actor=None, session=None):
        request = self.factory.get('/backoffice/', {'return_to': token} if token else {})
        request.user = actor or self.teacher
        request.session = session if session is not None else self.client.session
        return request

    def token(self, source='search', **params):
        return make_return(self.request(), source, **params)

    def course_url(self):
        return reverse('backoffice_workspace_course', args=[self.course.pk])

    def assert_return(self, response, *, source='search', **params):
        self.assertEqual(response.status_code, 200)
        back = urlsplit(response.context['workspace_return_url'])
        self.assertEqual(back.path, reverse('backoffice_workspace_' + source))
        self.assertEqual(parse_qs(back.query, keep_blank_values=True),
                         {key: [str(value)] for key, value in params.items()})
        self.assertIn(response.context['workspace_return_url'],
                      [item['href'] for item in _Markup(response).links])

    def test_search_return_round_trip_encodes_literal_text(self):
        query = 'Madina & <kurs> + / ?'
        token = self.token(q=query, kind='student', page=3)
        context = return_context(self.request(token))
        parsed = urlsplit(context['workspace_return_url'])
        self.assertEqual(parsed.path, reverse('backoffice_workspace_search'))
        self.assertEqual(parse_qs(parsed.query), {'q': [query], 'kind': ['student'], 'page': ['3']})
        self.assertNotIn('<kurs>', context['workspace_return_url'])
        self.assertEqual(context['workspace_return_token'], token)

    def test_return_token_cannot_be_reused_by_another_actor_or_session(self):
        token = self.token(q='Madina', kind='student')
        other_session = Client()
        other_session.force_login(self.teacher)
        for request in (self.request(token, actor=self.other),
                        self.request(token, session=other_session.session)):
            with self.subTest(actor=request.user.pk, session=request.session.session_key):
                self.assertEqual(return_context(request), {})
                self.assertEqual(with_return(request, self.course_url()), self.course_url())

    def test_tampered_oversized_or_ambiguous_token_is_ignored(self):
        token = self.token(q='Madina')
        bad_tokens = (token + 'tampered', 'https://example.test/stolen', 'x' * 2049)
        for value in bad_tokens:
            with self.subTest(token=value[:30]):
                self.assertEqual(return_context(self.request(value)), {})
        duplicated = self.factory.get('/backoffice/', {'return_to': [token, token]})
        duplicated.user, duplicated.session = self.teacher, self.client.session
        self.assertEqual(return_context(duplicated), {})

    def test_signed_but_unrecognized_or_invalid_payload_cannot_choose_a_destination(self):
        valid = signing.loads(self.token(q='Madina'), salt=SALT)
        invalid = (
            {'source': 'https://example.test/'},
            {'source': '//example.test/'},
            {'source': 'admin'},
            {'params': {'q': 'Madina', 'kind': 'private', 'page': 1}},
            {'params': {'q': 'Madina', 'kind': ['student'], 'page': 1}},
            {'params': {'q': 'Madina\nprivate', 'page': 1}},
            {'params': {'q': 'x' * 201, 'page': 1}},
            {'params': {'q': 'Madina', 'page': 0}},
            {'params': {'q': 'Madina', 'page': '１'}},
            {'params': []},
        )
        for replacement in invalid:
            with self.subTest(replacement=replacement):
                token = signing.dumps({**valid, **replacement}, salt=SALT)
                self.assertEqual(return_context(self.request(token)), {})

    def test_extra_payload_keys_are_not_promoted_to_url_parameters(self):
        payload = signing.loads(self.token(q='Madina'), salt=SALT)
        payload['params'].update(next='https://example.test/', token='private-value', lesson=99)
        token = signing.dumps(payload, salt=SALT)
        params = parse_qs(urlsplit(return_context(self.request(token))['workspace_return_url']).query)
        self.assertEqual(params, {'q': ['Madina'], 'kind': ['all'], 'page': ['1']})

    def test_navigation_flag_off_discards_return_and_course_flag_off_discards_list_return(self):
        search_token = self.token(q='Madina')
        course_token = self.token('courses', q='Return', status='draft', page=2)
        set_flag('backoffice_course_workspace', enabled=False, reason='Isolated source disabled')
        self.assertEqual(return_context(self.request(course_token)), {})
        self.assertTrue(return_context(self.request(search_token)))
        set_flag('backoffice_unified_navigation', enabled=False, reason='Isolated navigation disabled')
        self.assertEqual(return_context(self.request(search_token)), {})
        self.assertEqual(self.token(q='Madina'), '')

    def test_propagation_keeps_lesson_and_anchor_without_duplicate_return(self):
        token = self.token(q='Return', kind='lesson', page=2)
        request = self.request(token)
        original = self.course_url() + f'?lesson={self.lesson.pk}&return_to=old&resource_q=book#materials'
        result = urlsplit(with_return(request, original))
        self.assertEqual(result.path, self.course_url())
        self.assertEqual(result.fragment, 'materials')
        self.assertEqual(parse_qs(result.query), {
            'lesson': [str(self.lesson.pk)], 'resource_q': ['book'], 'return_to': [token],
        })

    def test_propagation_does_not_attach_private_query_to_other_routes_or_external_urls(self):
        request = self.request(self.token(q='Madina'))
        destinations = (
            'https://example.test' + self.course_url(), '//example.test' + self.course_url(),
            'relative/path', '/missing/route/', reverse('backoffice_workspace_courses'),
            reverse('backoffice_workspace_home'), reverse('backoffice_design'),
        )
        for url in destinations:
            with self.subTest(url=url):
                self.assertEqual(with_return(request, url), url)

    def test_course_filter_survives_outline_selection_save_and_return(self):
        Course.objects.bulk_create([
            Course(title=f'Return cohort {number}', instructor=self.teacher, is_active=False)
            for number in range(12)
        ])
        listing = self.client.get(reverse('backoffice_workspace_courses'),
                                  {'q': 'Return cohort', 'status': 'draft', 'page': 2})
        self.assertEqual([row.pk for row in listing.context['page_obj']], [self.course.pk])
        course_link = next(item['href'] for item in _Markup(listing).links
                           if urlsplit(item['href']).path == self.course_url())
        course = self.client.get(course_link)
        lesson_link = next(item['href'] for item in _Markup(course).links
                           if 'ws-lesson-link' in item.get('class', '').split()
                           and parse_qs(urlsplit(item['href']).query).get('lesson') == [str(self.lesson.pk)])
        lesson = self.client.get(lesson_link)
        self.assert_return(lesson, source='courses', q='Return cohort', status='draft', page=2)
        form = next(form for form in _Markup(lesson).forms if form['attrs'].get('id') == 'lesson-editor')
        data = {**form['hidden'], 'action': 'lesson_save', 'title': 'Saved through filtered course',
                'module': self.module.pk, 'content': 'Changed lesson content', 'video_url': '',
                'order': 1, 'xp_reward': 15}
        saved = self.client.post(form['attrs'].get('action') or lesson_link, data)
        self.assertEqual(saved.status_code, 302)
        self.assertEqual(parse_qs(urlsplit(saved['Location']).query)['lesson'], [str(self.lesson.pk)])
        reopened = self.client.get(saved['Location'])
        self.assert_return(reopened, source='courses', q='Return cohort', status='draft', page=2)
        returned = self.client.get(reopened.context['workspace_return_url'])
        self.assertEqual(returned.context['page_obj'].number, 2)
        self.assertEqual([row.pk for row in returned.context['page_obj']], [self.course.pk])
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, data['title'])

    def test_search_lesson_context_survives_outline_post_and_practice_editor(self):
        found = self.client.get(reverse('backoffice_workspace_search'), {'q': 'Return introduction', 'kind': 'lesson'})
        lesson_link = found.context['search_rows'][0]['url']
        opened = self.client.get(lesson_link)
        self.assert_return(opened, q='Return introduction', kind='lesson', page=1)
        markup = _Markup(opened)
        outline_form = next(form for form in markup.forms if form['hidden'].get('action') == 'module_update')
        saved = self.client.post(outline_form['attrs']['action'], {**outline_form['hidden'], 'title': 'Renamed module'})
        self.assertEqual(saved.status_code, 302)
        self.assertEqual(parse_qs(urlsplit(saved['Location']).query)['lesson'], [str(self.lesson.pk)])
        reopened = self.client.get(saved['Location'])
        self.assert_return(reopened, q='Return introduction', kind='lesson', page=1)
        assignment_path = reverse('backoffice_workspace_assignment_new', args=[self.course.pk, self.lesson.pk])
        assignment_link = next(item['href'] for item in _Markup(reopened).links
                               if urlsplit(item['href']).path == assignment_path)
        assignment = self.client.get(assignment_link)
        self.assert_return(assignment, q='Return introduction', kind='lesson', page=1)

    def test_material_search_get_keeps_return_context(self):
        token = self.token(q='Return introduction', kind='lesson')
        url = self.course_url() + '?' + urlencode({'lesson': self.lesson.pk, 'return_to': token})
        opened = self.client.get(url)
        form = next(form for form in _Markup(opened).forms if 'resource_q' in form['names'])
        response = self.client.get(form['attrs'].get('action') or url,
                                   {**form['hidden'], 'resource_q': 'synthetic worksheet'})
        self.assert_return(response, q='Return introduction', kind='lesson', page=1)

    def test_course_information_back_and_save_keep_selected_lesson_and_search(self):
        found = self.client.get(reverse('backoffice_workspace_search'),
                                {'q': 'Return introduction', 'kind': 'lesson'})
        lesson = self.client.get(found.context['search_rows'][0]['url'])
        editor_path = reverse('backoffice_workspace_course_edit', args=[self.course.pk])
        editor_url = next(item['href'] for item in _Markup(lesson).links
                          if urlsplit(item['href']).path == editor_path)
        editor = self.client.get(editor_url)
        self.assert_return(editor, q='Return introduction', kind='lesson', page=1)
        back_url = next(item['href'] for item in _Markup(editor).links
                        if 'ws-back' in item.get('class', '').split())
        back = self.client.get(back_url)
        self.assertEqual(back.context['lesson'].pk, self.lesson.pk)
        self.assert_return(back, q='Return introduction', kind='lesson', page=1)
        form = next(form for form in _Markup(editor).forms
                    if 'course_revision' in form['hidden'])
        data = {name: getattr(self.course, name) for name in CourseBackofficeForm.Meta.fields}
        data.update(form['hidden'], instructor=self.teacher.pk, title='Edited from the selected lesson')
        saved = self.client.post(form['attrs'].get('action') or editor_url, data)
        self.assertEqual(saved.status_code, 302)
        reopened = self.client.get(saved['Location'])
        self.assertEqual(reopened.context['lesson'].pk, self.lesson.pk)
        self.assert_return(reopened, q='Return introduction', kind='lesson', page=1)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, data['title'])

    def test_course_editor_rejects_invalid_selected_lesson_before_writing(self):
        second_course = Course.objects.create(title='Another owned course', instructor=self.teacher)
        second_module = Module.objects.create(course=second_course, title='Another module')
        other_lesson = Lesson.objects.create(module=second_module, title='Other course lesson')
        editor_path = reverse('backoffice_workspace_course_edit', args=[self.course.pk])
        editor = self.client.get(editor_path)
        data = {name: getattr(self.course, name) for name in CourseBackofficeForm.Meta.fields}
        data.update(instructor=self.teacher.pk, title='Must not be written',
                    course_revision=editor.context['course_revision'])
        original_title = self.course.title
        for selection in (other_lesson.pk, 'invalid', -1):
            with self.subTest(lesson=selection):
                editor_url = editor_path + '?' + urlencode({'lesson': selection})
                self.assertEqual(self.client.get(editor_url).status_code, 404)
                self.assertEqual(self.client.post(editor_url, data).status_code, 404)
                self.course.refresh_from_db()
                self.assertEqual(self.course.title, original_title)

    def test_conflict_reload_keeps_selected_lesson_and_search_return(self):
        token = self.token(q='Return introduction', kind='lesson')
        selected_url = self.course_url() + '?' + urlencode({'lesson': self.lesson.pk, 'return_to': token})
        conflict = self.client.post(selected_url, {
            'action': 'module_update', 'module_id': self.module.pk,
            'title': 'Unsaved module title', 'outline_revision': 'stale-revision',
        })
        self.assertEqual(conflict.status_code, 409)
        reload_url = next(item['href'] for item in _Markup(conflict).links
                          if item.get('class') == 'ws-link' and urlsplit(item['href']).path == self.course_url())
        reopened = self.client.get(reload_url)
        self.assertEqual(reopened.context['lesson'].pk, self.lesson.pk)
        self.assert_return(reopened, q='Return introduction', kind='lesson', page=1)
        self.module.refresh_from_db()
        self.assertEqual(self.module.title, 'Tanishuv')

    def test_student_search_course_lesson_selectors_and_recheck_keep_return(self):
        found = self.client.get(reverse('backoffice_workspace_search'), {'q': 'Madina', 'kind': 'student'})
        student_url = found.context['search_rows'][0]['url']
        opened = self.client.get(student_url)
        self.assert_return(opened, q='Madina', kind='student', page=1)
        course_form = next(form for form in _Markup(opened).forms if 'course' in form['names'] and 'lesson' not in form['names'])
        selected = self.client.get(course_form['attrs'].get('action') or urlsplit(student_url).path,
                                   {**course_form['hidden'], 'course': self.course.pk})
        lesson_form = next(form for form in _Markup(selected).forms if 'lesson' in form['names'])
        diagnosed = self.client.get(lesson_form['attrs'].get('action') or urlsplit(student_url).path,
                                    {**lesson_form['hidden'], 'lesson': self.second_lesson.pk})
        self.assert_return(diagnosed, q='Madina', kind='student', page=1)
        self.assertEqual(diagnosed.context['selected_course'].pk, self.course.pk)
        self.assertEqual(diagnosed.context['selected_lesson'].pk, self.second_lesson.pk)
        rechecked = self.client.get(diagnosed.context['recheck_url'])
        self.assert_return(rechecked, q='Madina', kind='student', page=1)
        self.assertEqual(rechecked.context['selected_lesson'].pk, self.second_lesson.pk)
        recent = self.client.session[SESSION_KEY]
        self.assertEqual(recent['items'][0], {
            'kind': 'student', 'student_id': self.student.pk, 'course_id': self.course.pk,
            'lesson_id': self.second_lesson.pk, 'page': 1,
        })
        self.assertNotIn('Madina', str(recent))
        self.assertNotIn('return_to', str(recent))
        self.assertNotIn('workspace_return_token', str(recent))

    def test_search_history_does_not_enter_recent_work_or_override_current_scope(self):
        secret_query = 'Private search phrase'
        token = self.token(q=secret_query, kind='course')
        self.client.get(self.course_url(), {'lesson': self.lesson.pk, 'return_to': token,
                                          'resource_q': 'Unsubmitted resource search'})
        state = self.client.session[SESSION_KEY]
        self.assertEqual(state['items'][0], {
            'kind': 'course', 'course_id': self.course.pk, 'lesson_id': self.lesson.pk,
        })
        self.assertNotIn(secret_query, str(state))
        self.assertNotIn(token, str(state))
        self.assertNotIn('resource_q', str(state))
        Course.objects.filter(pk=self.course.pk).update(instructor=self.other)
        self.assertEqual(self.client.get(self.course_url(), {'return_to': token}).status_code, 404)
        home = self.client.get(reverse('backoffice_workspace_home'))
        self.assertEqual(home.context['recent_work'], [])
