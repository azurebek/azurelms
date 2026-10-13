"""Support -> existing decision -> same learner/context, without a second writer."""
from datetime import date
from urllib.parse import parse_qs, urlencode, urlsplit

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from bot.models import BotRuntimeSettings, TelegramOutbox
from cohorts.models import Cohort, Enrollment
from core.backoffice_return import make_return
from core.flags import set_flag
from core.student_support_return import SALT, make_support_return, support_return_context
from courses.models import (
    Assignment, AssignmentSubmission, Course, Exam, ExamAttempt, ExamResultPublication,
    ExamSection, ExamSectionReview, Lesson, Module,
)
from users.models import Notification


@override_settings(GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='')
class StudentSupportReturnTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.teacher = User.objects.create_user('support-return-teacher', 'srt@example.test', is_staff=True)
        cls.other = User.objects.create_user('support-return-other', 'sro@example.test', is_staff=True)
        cls.owner = User.objects.create_user('support-return-owner', 'sra@example.test', is_staff=True, is_superuser=True)
        cls.student = User.objects.create_user('support-return-student', 'srs@example.test')
        cls.second = User.objects.create_user('support-return-second', 'sr2@example.test')
        cls.course = Course.objects.create(title='Support return course', instructor=cls.teacher)
        cls.foreign_course = Course.objects.create(title='Foreign return course', instructor=cls.other)
        cls.module = Module.objects.create(course=cls.course, title='Support module')
        cls.lesson = Lesson.objects.create(module=cls.module, title='Support lesson')
        cls.foreign_module = Module.objects.create(course=cls.foreign_course, title='Foreign module')
        cohort = Cohort.objects.create(course=cls.course, name='Support group', start_date=date(2026, 1, 1))
        for learner in (cls.student, cls.second):
            Enrollment.objects.create(student=learner, cohort=cohort, status='active')
        cls.assignment = Assignment.objects.create(lesson=cls.lesson, title='Support assignment', description='A task')
        cls.submission = AssignmentSubmission.objects.create(
            assignment=cls.assignment, student=cls.student, answer_text='A submitted answer')
        cls.exam = Exam.objects.create(course=cls.course, title='Support exam', exam_type='final', weight_percentage=100)
        cls.section = ExamSection.objects.create(exam=cls.exam, title='Writing', section_type='writing', max_score=10)
        cls.attempt = ExamAttempt.objects.create(exam=cls.exam, student=cls.student,
                                               is_completed=True, completed_time=timezone.now())

    def setUp(self):
        for slug in ('backoffice_student_support', 'backoffice_unified_navigation',
                     'frontend_v1_teacher', 'frontend_v1_exam_review'):
            set_flag(slug, enabled=True, reason='Support return regression')
        self.actor = self.teacher
        self.client.force_login(self.actor)
        self.factory = RequestFactory()

    def request(self, params=None, *, actor=None, session=None):
        request = self.factory.get('/backoffice/', params or {})
        request.user = actor or self.actor
        request.session = session if session is not None else self.client.session
        return request

    def token(self, *, params=None, **overrides):
        values = dict(student_id=self.student.pk, course_id=self.course.pk,
                      lesson_id=self.lesson.pk, topic='results')
        values.update(overrides)
        return make_support_return(self.request(params), **values)

    def context(self, token, **kwargs):
        return support_return_context(self.request({'support_from': token}, **kwargs),
                                      self.student.pk, self.course.pk)

    def action_url(self, kind='assignment', token=None):
        name, pk = ('teacher_grade_assignment', self.submission.pk) if kind == 'assignment' else ('teacher_grade_exam', self.attempt.pk)
        return reverse(name, args=[pk]) + '?' + urlencode({'support_from': token or self.token()})

    def test_round_trip_preserves_only_valid_context_and_upstream_search(self):
        upstream = make_return(self.request(), 'search', q='Madina & dars', kind='student', page=2)
        token = self.token(params={'q': 'Madina & dars', 'page': 3, 'filter_course': self.course.pk,
                                  'result_kind': 'exams', 'assignment_page': 2, 'quiz_page': 4,
                                  'exam_page': 5, 'delivery_page': 6, 'delivery_filter': 'failed', 'return_to': upstream,
                                  'next': 'https://example.test/private'})
        context = self.context(token)
        url = urlsplit(context['support_return_url'])
        self.assertEqual(url.path, reverse('backoffice_workspace_student', args=[self.student.pk]))
        self.assertEqual(parse_qs(url.query), {
            'topic': ['results'], 'course': [str(self.course.pk)], 'lesson': [str(self.lesson.pk)],
            'q': ['Madina & dars'], 'page': ['3'], 'filter_course': [str(self.course.pk)],
            'result_kind': ['exams'], 'assignment_page': ['2'], 'quiz_page': ['4'],
            'exam_page': ['5'], 'delivery_page': ['6'], 'delivery_filter': ['failed'], 'return_to': [upstream],
        })
        self.assertEqual(context['support_return_label'], 'O‘quvchiga qaytib tekshirish')

    def test_tokens_cannot_cross_actor_session_or_action_target(self):
        token = self.token()
        second_client = Client()
        second_client.force_login(self.teacher)
        self.assertEqual(self.context(token, actor=self.other), {})
        self.assertEqual(self.context(token, session=second_client.session), {})
        request = self.request({'support_from': token})
        self.assertEqual(support_return_context(request, self.second.pk, self.course.pk), {})
        self.assertEqual(support_return_context(request, self.student.pk, self.foreign_course.pk), {})

    def test_malformed_ambiguous_and_signed_invalid_tokens_are_ignored(self):
        token = self.token()
        for value in (token + 'bad', 'https://example.test/', 'x' * 4097, [token, token]):
            self.assertEqual(self.context(value), {})
        payload = signing.loads(token, salt=SALT)
        for extra in ({'topic': 'admin'}, {'topic': []}, {'lesson': True}, {'q': 'x\n'},
                      {'exam_page': 0}, {'exam_page': '１'}, {'course': None},
                      {'result_kind': 'private'}, {'delivery_filter': 'private'},
                      {'next': 'https://example.test/'}, {'return_to': 'x' * 2049}):
            with self.subTest(extra=extra):
                invalid = signing.dumps({**payload, 'params': {**payload['params'], **extra}}, salt=SALT)
                self.assertEqual(self.context(invalid), {})
        self.assertEqual(self.token(params={'page': ['1', '2']}), '')
        self.assertEqual(self.token(params={'result_kind': 'invalid'}), '')

    def test_scope_and_parent_are_rechecked_after_token_is_minted(self):
        token = self.token()
        Course.objects.filter(pk=self.course.pk).update(instructor=self.other)
        self.assertEqual(self.context(token), {})
        Course.objects.filter(pk=self.course.pk).update(instructor=self.teacher)
        Lesson.objects.filter(pk=self.lesson.pk).update(module=self.foreign_module)
        self.assertEqual(self.context(token), {})
        Lesson.objects.filter(pk=self.lesson.pk).update(module=self.module)
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_active=False)
        self.assertEqual(self.context(token), {})
        get_user_model().objects.filter(pk=self.teacher.pk).update(is_active=True)
        get_user_model().objects.filter(pk=self.student.pk).update(is_staff=True)
        self.assertEqual(self.context(token), {})

    def test_support_flag_closes_return_but_navigation_flag_only_drops_search(self):
        upstream = make_return(self.request(), 'search', q='Madina')
        token = self.token(params={'return_to': upstream})
        set_flag('backoffice_unified_navigation', enabled=False, reason='Return test')
        self.assertNotIn('return_to', parse_qs(urlsplit(self.context(token)['support_return_url']).query))
        self.assertTrue(self.token())
        set_flag('backoffice_student_support', enabled=False, reason='Return test')
        self.assertEqual(self.context(token), {})
        self.assertEqual(self.token(), '')

    def test_delivery_context_is_owner_only_and_invalid_upstream_is_removed(self):
        self.assertEqual(self.token(topic='delivery'), '')
        self.actor = self.owner
        self.client.force_login(self.actor)
        token = self.token(topic='delivery', params={'return_to': 'https://example.test/'})
        context = self.context(token)
        self.assertEqual(parse_qs(urlsplit(context['support_return_url']).query)['topic'], ['delivery'])
        self.assertNotIn('return_to', context['support_return_url'])

    def test_assignment_get_shows_return_in_both_renderers_without_changing_work(self):
        before = list(AssignmentSubmission.objects.values())
        notes_before = list(Notification.objects.values())
        for enabled in (True, False):
            set_flag('frontend_v1_teacher', enabled=enabled, reason='Renderer parity')
            response = self.client.get(self.action_url())
            self.assertContains(response, 'O‘quvchiga qaytib tekshirish')
            self.assertNotContains(response, 'Tekshiruv navbatiga qaytish')
            self.assertNotContains(response, 'aria-label="Orqaga"')
            self.assertTrue(response.context['support_return_url'])
            self.assertEqual(list(AssignmentSubmission.objects.values()), before)
            self.assertEqual(list(Notification.objects.values()), notes_before)
        self.assertFalse(SystemAuditEvent.objects.filter(action='assignment.review').exists())

    def test_assignment_validation_stale_and_success_keep_same_learner(self):
        token = self.token(params={'result_kind': 'assignments', 'assignment_page': 2})
        url = self.action_url(token=token)
        payload = {'v1_review': '1', 'action': 'approve', 'awarded_xp': '8',
                   'teacher_feedback': 'Good', 'revision': self.submission.review_revision_token}
        invalid = self.client.post(url, payload)
        self.assertEqual(invalid.status_code, 400)
        self.assertContains(invalid, 'O‘quvchiga qaytib tekshirish', status_code=400)
        stale = self.client.post(url, {**payload, 'confirm_review': 'on', 'revision': 'old'})
        self.assertEqual(stale.status_code, 409)
        self.assertContains(stale, 'O‘quvchiga qaytib tekshirish', status_code=409)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, 'pending')
        result = self.client.post(url, {**payload, 'confirm_review': 'on'})
        self.assertEqual(result.status_code, 302)
        self.assertEqual(result.url, self.context(token)['support_return_url'])
        self.submission.refresh_from_db()
        self.assertEqual((self.submission.status, self.submission.awarded_xp), ('approved', 8))

    def test_legacy_assignment_success_and_invalid_token_keep_existing_contract(self):
        set_flag('frontend_v1_teacher', enabled=False, reason='Legacy parity')
        token = self.token()
        response = self.client.post(self.action_url(token=token), {'action': 'revision', 'awarded_xp': 0})
        self.assertEqual(response.url, self.context(token)['support_return_url'])
        response = self.client.post(self.action_url(token=token + 'bad'), {'action': 'approve', 'awarded_xp': 5})
        self.assertEqual(response.url, reverse('teacher_grading'))

    def test_exam_get_save_and_publish_return_without_get_initialization(self):
        token = self.token(params={'result_kind': 'exams', 'exam_page': 2})
        url = self.action_url('exam', token)
        response = self.client.get(url)
        self.assertContains(response, 'O‘quvchiga qaytib tekshirish')
        self.assertNotContains(response, 'Tekshiruv navbatiga qaytish')
        self.assertFalse(ExamSectionReview.objects.exists())
        form = response.context['review_form']
        data = {name: form[name].value() for name in form.fields}
        data.update(v1_exam_review='1', confirm_scope='on', **{f'score_{self.section.pk}': '8'})
        saved = self.client.post(url, data)
        self.assertEqual(saved.url, self.context(token)['support_return_url'])
        self.assertFalse(ExamResultPublication.objects.exists())
        form = self.client.get(url).context['publish_form']
        data = {name: form[name].value() for name in form.fields}
        data.update(v1_exam_review='1', confirm_scope='on')
        published = self.client.post(url, data)
        self.assertEqual(published.url, self.context(token)['support_return_url'])
        self.assertEqual(ExamResultPublication.objects.get(attempt=self.attempt).payload['score'], '80.00')

    def test_exam_flag_switched_off_after_link_does_not_enter_legacy_get_writer(self):
        token = self.token(params={'result_kind': 'exams'})
        set_flag('frontend_v1_exam_review', enabled=False, reason='Stale support link')
        response = self.client.get(self.action_url('exam', token))
        self.assertEqual(response.url, self.context(token)['support_return_url'])
        self.assertFalse(ExamSectionReview.objects.exists())
        self.assertFalse(ExamResultPublication.objects.exists())

    def test_invalid_or_disabled_support_link_never_enters_disabled_exam_get_writer(self):
        token = self.token(params={'result_kind': 'exams'})
        before = list(ExamAttempt.objects.values())
        set_flag('frontend_v1_exam_review', enabled=False, reason='Disabled review renderer')
        for support_enabled, candidate in ((True, token + 'invalid'), (False, token)):
            set_flag('backoffice_student_support', enabled=support_enabled, reason='Support return gate regression')
            for method in ('get', 'head'):
                with self.subTest(support_enabled=support_enabled, method=method):
                    response = getattr(self.client, method)(self.action_url('exam', candidate))
                    self.assertEqual(response.status_code, 400)
                    self.assertFalse(ExamSectionReview.objects.exists())
                    self.assertFalse(ExamResultPublication.objects.exists())
                    self.assertEqual(list(ExamAttempt.objects.values()), before)

    def delivery_fixtures(self):
        self.actor = self.owner
        self.client.force_login(self.owner)
        first = Notification.objects.create(recipient=self.student, title='Selected old notification', message='Private body')
        other = Notification.objects.create(recipient=self.second, title='Other notification', message='Other body')
        old_row = TelegramOutbox.objects.create(notification=first, telegram_id=1001, status='failed', failure_kind='transient')
        other_row = TelegramOutbox.objects.create(notification=other, telegram_id=1002, status='failed', failure_kind='transient')
        BotRuntimeSettings.objects.create(pk=1, dead_letter_replay_limit=1)
        token = self.token(topic='delivery', params={'delivery_page': 3})
        url = reverse('backoffice_dead_letter') + '?' + urlencode({
            'student': self.student.pk, 'notification': first.pk, 'support_from': token})
        return first, old_row, other_row, token, url

    def test_old_failed_notification_is_visible_without_replaying_or_marking_read(self):
        note, row, other, token, url = self.delivery_fixtures()
        before = list(TelegramOutbox.objects.values())
        response = self.client.get(url)
        self.assertContains(response, 'Selected old notification')
        self.assertNotContains(response, 'Other notification')
        self.assertContains(response, 'O‘quvchiga qaytib tekshirish')
        self.assertEqual([item.pk for item in response.context['rows']], [row.pk])
        self.assertEqual(response.context['summary']['total'], 1)
        self.assertEqual(list(TelegramOutbox.objects.values()), before)
        note.refresh_from_db()
        self.assertFalse(note.is_read)
        self.assertIn('no-store', response['Cache-Control'])

    def test_scoped_replay_requires_existing_confirmation_and_cannot_pick_other_person(self):
        note, row, other, token, url = self.delivery_fixtures()
        payload = {'rows': [f'dm:{row.pk}'], 'change_reason': 'Synthetic issue resolved', 'confirm_change': 'on'}
        for change in ({'rows': [f'dm:{other.pk}']}, {'confirm_change': ''}):
            response = self.client.post(url, {**payload, **change})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
            row.refresh_from_db()
            self.assertEqual(row.status, 'failed')
        response = self.client.post(url, payload)
        self.assertEqual(response.url, self.context(token)['support_return_url'])
        row.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(row.status, 'pending')
        self.assertEqual(other.status, 'failed')
        self.assertEqual(SystemAuditEvent.objects.get(action='telegram.dead_letter.replay').after['replayed'], 1)
        note.refresh_from_db()
        self.assertFalse(note.is_read)

    def test_focused_delivery_uses_learner_name_and_never_falls_back_to_body(self):
        note, row, other, token, url = self.delivery_fixtures()
        Notification.objects.filter(pk=note.pk).update(title='', message='PRIVATE-BODY-MUST-STAY-HIDDEN')
        TelegramOutbox.objects.filter(pk=row.pk).update(last_error='PRIVATE-PROVIDER-ERROR-MUST-STAY-HIDDEN')
        get_user_model().objects.filter(pk=self.student.pk).update(first_name='Madina', last_name='Karimova')
        response = self.client.get(url)
        self.assertContains(response, 'Madina Karimova')
        self.assertContains(response, 'Bildirishnoma')
        self.assertNotContains(response, 'PRIVATE-BODY-MUST-STAY-HIDDEN')
        self.assertNotContains(response, 'PRIVATE-PROVIDER-ERROR-MUST-STAY-HIDDEN')
        self.assertNotContains(response, '<th>Navbat</th>', html=True)
        self.assertNotContains(response, '1001')
        row.refresh_from_db()
        self.assertEqual(row.last_error, 'PRIVATE-PROVIDER-ERROR-MUST-STAY-HIDDEN')

    def test_delivery_filter_invalid_or_mismatched_target_never_opens_other_message(self):
        note, row, other, token, url = self.delivery_fixtures()
        base = reverse('backoffice_dead_letter')
        for params in ({'notification': note.pk}, {'student': 0}, {'student': '１'},
                       {'student': [self.student.pk, self.second.pk]}):
            self.assertEqual(self.client.get(base, params).status_code, 400)
        self.assertEqual(self.client.get(base, {'student': self.second.pk, 'notification': note.pk}).status_code, 404)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(url).status_code, 302)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        self.assertEqual(csrf.post(url, {'rows': [f'dm:{row.pk}'], 'change_reason': 'Test', 'confirm_change': 'on'}).status_code, 403)

    def test_filtered_replay_without_return_keeps_validated_filters(self):
        note, row, other, token, url = self.delivery_fixtures()
        filters = {'student': self.student.pk, 'notification': note.pk}
        url = reverse('backoffice_dead_letter') + '?' + urlencode(filters)
        response = self.client.post(url, {'rows': [f'dm:{row.pk}'], 'change_reason': 'Synthetic issue resolved', 'confirm_change': 'on'})
        self.assertEqual(response.url, url)
        self.assertContains(self.client.get(url), 'Tanlangan xabar hozir yuborilishi to‘xtagan holatda emas')
