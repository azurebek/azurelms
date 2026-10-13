"""Real support-page reads, navigation and privacy across B2.4 help topics."""
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urlsplit

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from bot.models import TelegramOutbox
from cohorts.models import Cohort, Enrollment
from core.backoffice_recent import SESSION_KEY
from core.backoffice_return import make_return
from core.flags import set_flag
from courses.models import (
    Assignment, AssignmentSubmission, Course, Exam, ExamAttempt,
    ExamResultPublication, Lesson, LessonProgress, Module, Quiz, QuizAttempt,
)
from users.models import Notification


class _Controls(HTMLParser):
    def __init__(self, response):
        super().__init__()
        self.forms, self.links, self.current = [], [], None
        self.feed(response.content.decode())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs)
        if tag == 'form':
            self.current = {'attrs': attrs, 'hidden': {}, 'fields': set()}
            self.forms.append(self.current)
        if self.current is not None and tag in ('input', 'select') and attrs.get('name'):
            self.current['fields'].add(attrs['name'])
            if tag == 'input' and attrs.get('type') == 'hidden':
                self.current['hidden'][attrs['name']] = attrs.get('value', '')

    def handle_endtag(self, tag):
        if tag == 'form':
            self.current = None


@override_settings(GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='')
class StudentSupportEvidenceViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user('evidence-owner', 'evidence-owner@example.test', is_staff=True, is_superuser=True)
        cls.teacher = User.objects.create_user('evidence-teacher', 'evidence-teacher@example.test', is_staff=True)
        cls.other_teacher = User.objects.create_user('evidence-other', 'evidence-other@example.test', is_staff=True)
        cls.student = User.objects.create_user('evidence-madina', 'evidence-madina@example.test', first_name='Madina')
        cls.foreign = User.objects.create_user('evidence-foreign', 'evidence-foreign@example.test')
        cls.unenrolled = User.objects.create_user('evidence-unenrolled', 'evidence-unenrolled@example.test')
        cls.course = Course.objects.create(title='Asosiy kurs', description='Darslar', instructor=cls.teacher)
        cls.foreign_course = Course.objects.create(title='PRIVATE FOREIGN COURSE', description='Private', instructor=cls.other_teacher)
        module = Module.objects.create(course=cls.course, title='Asosiy modul')
        cls.lesson = Lesson.objects.create(module=module, title='Tanlangan dars', order=1)
        cls.second_lesson = Lesson.objects.create(module=module, title='Keyingi dars', order=2)
        foreign_module = Module.objects.create(course=cls.foreign_course, title='Private module')
        cls.foreign_lesson = Lesson.objects.create(module=foreign_module, title='PRIVATE FOREIGN LESSON')
        cohort = Cohort.objects.create(course=cls.course, name='Asosiy guruh', start_date=timezone.localdate())
        foreign_cohort = Cohort.objects.create(course=cls.foreign_course, name='Private group', start_date=timezone.localdate())
        Enrollment.objects.create(student=cls.student, cohort=cohort, status=Enrollment.STATUS_ACTIVE)
        Enrollment.objects.create(student=cls.foreign, cohort=foreign_cohort, status=Enrollment.STATUS_ACTIVE)
        cls.assignment = Assignment.objects.create(lesson=cls.lesson, title='Yozma mashq dalili', description='PRIVATE TASK DESCRIPTION')
        cls.submission = AssignmentSubmission.objects.create(
            student=cls.student, assignment=cls.assignment,
            answer_text='PRIVATE STUDENT ANSWER', teacher_feedback='PRIVATE TEACHER FEEDBACK',
        )
        cls.quiz = Quiz.objects.create(lesson=cls.lesson, title='Dars testi dalili')
        QuizAttempt.objects.create(student=cls.student, quiz=cls.quiz, score=75, total_correct=3, total_questions=4)
        cls.exam = Exam.objects.create(course=cls.course, title='Imtihon dalili', exam_type='visa', weight_percentage=40)
        cls.exam_attempt = ExamAttempt.objects.create(
            student=cls.student, exam=cls.exam, is_completed=True,
            completed_time=timezone.now(), score='98.73', review_notes='PRIVATE DRAFT FEEDBACK',
        )
        cls.note = Notification.objects.create(
            recipient=cls.student, title='Bildirishnoma dalili', message='PRIVATE NOTIFICATION BODY',
            external_key='PRIVATE EXTERNAL KEY', url='/private-notification-destination/',
        )
        cls.outbox = TelegramOutbox.objects.create(
            notification=cls.note, telegram_id=97773311, status=TelegramOutbox.STATUS_FAILED,
            last_error='PRIVATE PROVIDER ERROR', claim_token='PRIVATE CLAIM TOKEN', failure_kind='permanent',
        )

    def setUp(self):
        for slug in ('backoffice_student_support', 'backoffice_unified_navigation',
                     'backoffice_course_workspace', 'frontend_v1_teacher', 'frontend_v1_exam_review'):
            set_flag(slug, enabled=True, reason='Synthetic evidence-page regression')
        self.client.force_login(self.teacher)

    def url(self, student=None):
        return reverse('backoffice_workspace_student', args=[(student or self.student).pk])

    def get(self, **changes):
        params = {'course': self.course.pk, 'lesson': self.lesson.pk, 'topic': 'results'}
        params.update(changes)
        return self.client.get(self.url(), params)

    def assert_private(self, response):
        self.assertIn('private', response.headers['Cache-Control'])
        self.assertIn('no-store', response.headers['Cache-Control'])

    def query(self, url):
        return parse_qs(urlsplit(url).query, keep_blank_values=True)

    def search_token(self, actor=None):
        request = RequestFactory().get('/backoffice/')
        request.user = actor or self.teacher
        request.session = self.client.session
        return make_return(request, 'search', q='Madina & tanishuv', kind='student', page=3)

    def test_results_are_staff_scoped_but_delivery_is_owner_only_in_links_and_direct_get(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assert_private(response)
        self.assertEqual([item['key'] for item in response.context['support_topics']], ['access', 'results'])
        self.assertNotContains(response, 'Bildirishnoma dalili')
        denied = self.get(topic='delivery')
        self.assertEqual(denied.status_code, 403)
        self.assert_private(denied)
        self.client.force_login(self.owner)
        response = self.get(topic='delivery')
        self.assertEqual(response.status_code, 200)
        self.assert_private(response)
        self.assertEqual(len(response.context['support_topics']), 3)
        self.assertContains(response, 'Bildirishnoma dalili')

    def test_anonymous_learner_revoked_owner_and_non_get_requests_fail_private(self):
        self.client.logout()
        response = self.get()
        self.assertEqual(response.status_code, 302)
        self.assert_private(response)
        self.client.force_login(self.student)
        response = self.get()
        self.assertEqual(response.status_code, 403)
        self.assert_private(response)
        self.client.force_login(self.owner)
        get_user_model().objects.filter(pk=self.owner.pk).update(is_superuser=False)
        response = self.get(topic='delivery')
        self.assertEqual(response.status_code, 403)
        self.assert_private(response)
        for method in ('post', 'put', 'delete'):
            response = getattr(self.client, method)(self.url(), {'topic': 'results'})
            self.assertEqual(response.status_code, 405)
            self.assert_private(response)

    def test_support_flag_blocks_both_new_topics_even_with_existing_objects(self):
        self.client.force_login(self.owner)
        set_flag('backoffice_student_support', enabled=False, reason='Synthetic rollback')
        for topic in ('results', 'delivery'):
            response = self.get(topic=topic)
            self.assertEqual(response.status_code, 404)
            self.assert_private(response)
            self.assertNotContains(response, 'Bildirishnoma dalili', status_code=404)

    def test_invalid_topics_duplicate_selectors_and_invalid_pages_fail_closed(self):
        for params, code in (({'topic': 'sql'}, 400), ({'result_kind': 'private'}, 400),
                             ({'assignment_page': '0'}, 404), ({'quiz_page': '-1'}, 404),
                             ({'exam_page': '1.5'}, 404), ({'delivery_page': '١'}, 404)):
            with self.subTest(params=params):
                response = self.get(**params)
                self.assertEqual(response.status_code, code)
                self.assert_private(response)
        for query in ('topic=results&topic=delivery', 'result_kind=quizzes&result_kind=exams',
                      'assignment_page=1&assignment_page=2'):
            response = self.client.get(self.url() + '?' + query)
            self.assertEqual(response.status_code, 400)
            self.assert_private(response)

    def test_foreign_student_course_and_mismatched_lesson_are_not_disclosed(self):
        targets = (
            self.client.get(self.url(self.foreign), {'topic': 'results'}),
            self.get(course=self.foreign_course.pk),
            self.get(lesson=self.foreign_lesson.pk),
            self.get(filter_course=self.foreign_course.pk),
        )
        for response in targets:
            self.assertEqual(response.status_code, 404)
            self.assert_private(response)
            self.assertNotContains(response, 'PRIVATE', status_code=404)

    def test_only_selected_result_category_renders_and_other_topics_are_absent(self):
        titles = {'assignments': self.assignment.title, 'quizzes': self.quiz.title, 'exams': self.exam.title}
        for kind, title in titles.items():
            with self.subTest(kind=kind):
                response = self.get(result_kind=kind)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, title)
                for other_kind, other_title in titles.items():
                    if kind != other_kind:
                        self.assertNotContains(response, other_title)
                self.assertNotContains(response, 'id="diagnosis-title"')
                self.assertNotContains(response, 'id="delivery-title"')
                self.assertEqual(sum(item['active'] for item in response.context['result_groups']), 1)

    def test_result_titles_escape_markup_and_private_answers_and_draft_scores_stay_hidden(self):
        malicious = '<img src=x onerror="alert(1)">'
        Assignment.objects.filter(pk=self.assignment.pk).update(title=malicious)
        response = self.get()
        self.assertContains(response, '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;')
        self.assertNotContains(response, malicious)
        for kind in ('assignments', 'quizzes', 'exams'):
            response = self.get(result_kind=kind)
            self.assertNotContains(response, 'PRIVATE')
            self.assertNotContains(response, '98.73')
        ExamResultPublication.objects.create(attempt=self.exam_attempt, payload={
            'version': 1, 'score': '82.50', 'passed': True, 'passing_score': 60,
            'review_notes': 'PRIVATE PUBLISHED FEEDBACK', 'reviewed_at': timezone.now().isoformat(),
            'section_reviews': [], 'feedback_answers': [],
        })
        unapproved = self.get(result_kind='exams')
        self.assertIsNone(unapproved.context['result_rows'][0]['score'])
        ExamAttempt.objects.filter(pk=self.exam_attempt.pk).update(is_reviewed=True)
        published = self.get(result_kind='exams')
        self.assertEqual(str(published.context['result_rows'][0]['score']), '82.50')
        self.assertNotContains(published, 'PRIVATE PUBLISHED FEEDBACK')

    def test_delivery_escapes_title_and_hides_raw_payloads_while_preserving_selected_course(self):
        self.client.force_login(self.owner)
        title = '<script>window.private=1</script>'
        Notification.objects.filter(pk=self.note.pk).update(title=title)
        response = self.get(topic='delivery')
        self.assertContains(response, '&lt;script&gt;window.private=1&lt;/script&gt;')
        self.assertNotContains(response, title)
        for private in ('PRIVATE NOTIFICATION BODY', 'PRIVATE PROVIDER ERROR', 'PRIVATE CLAIM TOKEN',
                        'PRIVATE EXTERNAL KEY', '97773311', '/private-notification-destination/'):
            self.assertNotContains(response, private)
        self.assertNotContains(response, 'id="support-course"')
        self.assertContains(response, 'Kurs tanlovi bu ro‘yxatni cheklamaydi')
        for item in response.context['support_topics']:
            self.assertEqual(self.query(item['url'])['course'], [str(self.course.pk)])
            self.assertEqual(self.query(item['url'])['lesson'], [str(self.lesson.pk)])

    def test_tabs_recheck_and_result_paging_preserve_search_return_and_selected_context(self):
        for index in range(6):
            Assignment.objects.create(lesson=self.lesson, title=f'Yangi topshiriq {index}', description='Task')
        token = self.search_token()
        params = {'return_to': token, 'q': 'Madina & kurs', 'page': '2',
                  'filter_course': self.course.pk, 'assignment_page': '1',
                  'quiz_page': '2', 'exam_page': '3', 'delivery_page': '4'}
        response = self.get(**params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.query(response.context['workspace_return_url']),
                         {'q': ['Madina & tanishuv'], 'kind': ['student'], 'page': ['3']})
        links = [item['url'] for item in response.context['support_topics']]
        links += [item['url'] for item in response.context['result_groups']]
        links += [response.context['recheck_url'], response.context['result_next_url']]
        for link in links:
            values = self.query(link)
            for key in ('return_to', 'q', 'page', 'filter_course', 'quiz_page', 'exam_page', 'delivery_page'):
                self.assertEqual(values[key], [str(params[key])], (link, key))
            self.assertEqual(values['course'], [str(self.course.pk)])
            self.assertEqual(values['lesson'], [str(self.lesson.pk)])
        next_page = self.client.get(response.context['result_next_url'])
        self.assertEqual(next_page.context['result_page'].number, 2)
        self.assertEqual(len(next_page.context['result_rows']), 1)
        previous = self.client.get(next_page.context['result_previous_url'])
        self.assertEqual(previous.context['result_page'].number, 1)

    def test_selector_forms_keep_topic_search_and_category_when_changing_lesson(self):
        token = self.search_token()
        response = self.get(result_kind='quizzes', return_to=token, q='Madina', page='2', filter_course=self.course.pk)
        forms = [form for form in _Controls(response).forms if 'sp-selector' in form['attrs'].get('class', '')]
        self.assertEqual(len(forms), 2)
        for form in forms:
            for key, value in {'topic': 'results', 'result_kind': 'quizzes', 'return_to': token,
                               'q': 'Madina', 'page': '2', 'filter_course': str(self.course.pk)}.items():
                self.assertEqual(form['hidden'][key], value)
        lesson_form = next(form for form in forms if 'lesson' in form['fields'])
        changed = self.client.get(self.url(), {**lesson_form['hidden'], 'lesson': self.second_lesson.pk})
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.context['selected_lesson'].pk, self.second_lesson.pk)
        self.assertEqual(changed.context['result_kind'], 'quizzes')
        self.assertEqual(changed.context['support_topic'], 'results')

    def test_assignment_action_returns_to_same_evidence_and_upstream_search(self):
        token = self.search_token()
        response = self.get(return_to=token, q='Madina', page=2, filter_course=self.course.pk,
                            result_kind='assignments', assignment_page=1, quiz_page=2, exam_page=3)
        action_url = response.context['result_rows'][0]['action_url']
        self.assertIn('support_from', self.query(action_url))
        action = self.client.get(action_url)
        self.assertEqual(action.status_code, 200)
        back = action.context['support_return_url']
        self.assertIn(back, [link['href'] for link in _Controls(action).links])
        values = self.query(back)
        for key, value in {'topic': 'results', 'result_kind': 'assignments', 'q': 'Madina', 'page': '2',
                           'course': str(self.course.pk), 'lesson': str(self.lesson.pk), 'return_to': token,
                           'assignment_page': '1', 'quiz_page': '2', 'exam_page': '3'}.items():
            self.assertEqual(values[key], [value])
        returned = self.client.get(back)
        self.assertEqual(returned.status_code, 200)
        self.assertEqual(returned.context['student'].pk, self.student.pk)
        self.assertEqual(returned.context['support_topic'], 'results')

    def test_delivery_paging_and_targeted_action_return_to_same_learner(self):
        self.client.force_login(self.owner)
        for index in range(10):
            Notification.objects.create(recipient=self.student, title=f'Yangi xabar {index}', message='Private')
        response = self.get(topic='delivery', delivery_page=2, q='Madina', page=2, filter_course=self.course.pk)
        self.assertEqual(response.context['delivery']['page_obj'].number, 2)
        row = response.context['delivery']['rows'][0]
        values = self.query(row['action_url'])
        self.assertEqual(values['student'], [str(self.student.pk)])
        self.assertEqual(values['notification'], [str(self.note.pk)])
        action = self.client.get(row['action_url'])
        self.assertEqual(action.status_code, 200)
        back = action.context['support_return_url']
        self.assertEqual(self.query(back)['topic'], ['delivery'])
        self.assertEqual(self.query(back)['delivery_page'], ['2'])
        self.assertEqual(self.query(back)['course'], [str(self.course.pk)])
        returned = self.client.get(back)
        self.assertEqual(returned.context['delivery']['rows'][0]['id'], self.note.pk)

    def test_recent_restores_topic_kind_and_pages_but_drops_query_and_tokens(self):
        token = self.search_token()
        response = self.get(result_kind='quizzes', quiz_page=2, q='Private search', return_to=token)
        self.assertEqual(response.status_code, 200)
        entry = self.client.session[SESSION_KEY]['items'][0]
        self.assertEqual(entry['topic'], 'results')
        self.assertEqual(entry['result_kind'], 'quizzes')
        self.assertEqual(entry['quiz_page'], 2)
        self.assertNotIn('q', entry)
        self.assertNotIn('return_to', entry)
        home = self.client.get(reverse('backoffice_workspace_home'))
        link = home.context['recent_work'][0]['url']
        self.assertEqual(self.query(link)['topic'], ['results'])
        self.assertEqual(self.query(link)['result_kind'], ['quizzes'])
        reopened = self.client.get(link)
        self.assertEqual(reopened.context['support_topic'], 'results')
        self.assertEqual(reopened.context['selected_lesson'].pk, self.lesson.pk)
        self.assertEqual(reopened.context['list_context']['q'], '')

    def test_recent_delivery_entry_disappears_after_owner_role_is_revoked(self):
        self.client.force_login(self.owner)
        self.get(topic='delivery', delivery_page=2)
        home = self.client.get(reverse('backoffice_workspace_home'))
        self.assertEqual(self.query(home.context['recent_work'][0]['url'])['topic'], ['delivery'])
        Course.objects.filter(pk=self.course.pk).update(instructor=self.owner)
        get_user_model().objects.filter(pk=self.owner.pk).update(is_superuser=False)
        home = self.client.get(reverse('backoffice_workspace_home'))
        self.assertEqual(home.context['recent_work'], [])

    def test_support_gets_do_not_write_learning_notification_or_settings_state(self):
        self.client.force_login(self.owner)
        set_flag('backoffice_unified_navigation', enabled=False, reason='Separate read projection from recent navigation')
        # Warm existing shared shell lazy configuration before observing the new flow.
        self.get(topic='access')
        models = (AssignmentSubmission, QuizAttempt, ExamAttempt, ExamResultPublication,
                  LessonProgress, Notification, TelegramOutbox)
        before = {model: list(model.objects.order_by('pk').values()) for model in models}
        with CaptureQueriesContext(connection) as queries:
            for topic, kind in (('results', 'assignments'), ('results', 'quizzes'), ('results', 'exams'), ('delivery', 'assignments')):
                response = self.get(topic=topic, result_kind=kind)
                self.assertEqual(response.status_code, 200)
        writes = [query['sql'] for query in queries
                  if query['sql'].lstrip().upper().startswith(('UPDATE', 'INSERT', 'DELETE'))]
        self.assertEqual(writes, [])
        self.assertEqual({model: list(model.objects.order_by('pk').values()) for model in models}, before)

    def test_unenrolled_owner_target_gets_explanatory_empty_result_and_delivery_states(self):
        self.client.force_login(self.owner)
        results = self.client.get(self.url(self.unenrolled), {'topic': 'results'})
        self.assertEqual(results.status_code, 200)
        self.assertContains(results, 'Avval kursni tanlang')
        delivery = self.client.get(self.url(self.unenrolled), {'topic': 'delivery'})
        self.assertEqual(delivery.status_code, 200)
        self.assertContains(delivery, 'Bildirishnoma topilmadi')
        self.assertContains(delivery, 'isbotlamaydi')

    def test_failed_delivery_filter_survives_paging_action_return_and_recent(self):
        self.client.force_login(self.owner)
        for index in range(10):
            note = Notification.objects.create(recipient=self.student, title=f'Eski to‘xtagan xabar {index}', message='Private')
            TelegramOutbox.objects.create(notification=note, telegram_id=97773311, status=TelegramOutbox.STATUS_FAILED)
        for index in range(20):
            Notification.objects.create(recipient=self.student, title=f'Yangi oddiy xabar {index}', message='Private')
        token = self.search_token(self.owner)
        first = self.get(topic='delivery', delivery_filter='failed', return_to=token,
                         q='Madina', page=2, filter_course=self.course.pk)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.context['delivery']['summary']['total'], 31)
        self.assertEqual(first.context['delivery']['summary']['failed'], 11)
        self.assertEqual(first.context['delivery']['page_obj'].paginator.count, 11)
        self.assertEqual(first.context['delivery']['selected_status'], 'failed')
        self.assertNotContains(first, 'Yangi oddiy xabar')
        links = [item['url'] for item in first.context['support_topics']]
        links += [first.context['recheck_url'], first.context['delivery_next_url']]
        for link in links:
            self.assertEqual(self.query(link)['delivery_filter'], ['failed'])
            self.assertEqual(self.query(link)['return_to'], [token])
        second = self.client.get(first.context['delivery_next_url'])
        self.assertEqual(second.context['delivery']['page_obj'].number, 2)
        row = second.context['delivery']['rows'][0]
        self.assertEqual(row['id'], self.note.pk)
        action = self.client.get(row['action_url'])
        self.assertEqual(action.status_code, 200)
        back = action.context['support_return_url']
        self.assertEqual(self.query(back)['delivery_filter'], ['failed'])
        self.assertEqual(self.query(back)['delivery_page'], ['2'])
        self.assertEqual(self.query(back)['return_to'], [token])
        returned = self.client.get(back)
        self.assertEqual(returned.context['delivery']['rows'][0]['id'], self.note.pk)
        home = self.client.get(reverse('backoffice_workspace_home'))
        recent = home.context['recent_work'][0]['url']
        self.assertEqual(self.query(recent)['delivery_filter'], ['failed'])
        self.assertEqual(self.query(recent)['delivery_page'], ['2'])
        self.assertNotIn('return_to', self.query(recent))
        self.assertNotIn('q', self.query(recent))

    def test_invalid_delivery_filter_fails_without_disclosing_notification(self):
        self.client.force_login(self.owner)
        response = self.get(topic='delivery', delivery_filter='sent')
        self.assertEqual(response.status_code, 400)
        self.assert_private(response)
        self.assertNotContains(response, 'Bildirishnoma dalili', status_code=400)
        duplicate = self.client.get(self.url() + '?topic=delivery&delivery_filter=all&delivery_filter=failed')
        self.assertEqual(duplicate.status_code, 400)
        self.assert_private(duplicate)
