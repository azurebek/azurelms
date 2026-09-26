"""Records V1 consumes canonical data; synthetic DB, no live services."""
import datetime

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Attendance, Cohort, Enrollment, PaymentReceipt
from core.flags import flag_by_slug, set_flag
from courses.models import Certificate, Course, Lesson, LessonProgress, Module
from frontend.models import LegalPage, SiteSettings
from gamification.models import Badge, EarnedBadge
from subscriptions.models import Plan
from users.models import Notification

User = get_user_model()
ROUTES = {'certificates': 'certificates', 'attendance_calendar': 'attendance',
          'subscriptions': 'subscriptions', 'leaderboard': 'leaderboard',
          'notifications': 'notifications', 'help_center': 'help'}


class RecordsV1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('record-learner', 'record@example.test', 'Local-test-43', total_xp=999999)
        cls.other = User.objects.create_user('record-other', 'other@example.test', 'Local-test-43')
        cls.teacher = User.objects.create_user('record-teacher', 'teacher@example.test', 'Local-test-43', is_staff=True)
        cls.today = timezone.localdate()
        cls.course = Course.objects.create(title='Real course', instructor=cls.teacher, level='beginner')
        cls.module = Module.objects.create(course=cls.course, title='Module', order=1)
        cls.lesson = Lesson.objects.create(module=cls.module, title='Lesson', order=1, xp_reward=20)
        cls.cohort = Cohort.objects.create(course=cls.course, name='Own group', start_date=cls.today)
        other_course = Course.objects.create(title='Second course', instructor=cls.teacher, level='beginner')
        cls.second = Cohort.objects.create(course=other_course, name='Second group', start_date=cls.today)
        cls.foreign = Cohort.objects.create(course=cls.course, name='FOREIGN PRIVATE GROUP', start_date=cls.today)
        cls.enrollment = Enrollment.objects.create(student=cls.user, cohort=cls.cohort, status='active')
        cls.enrollment2 = Enrollment.objects.create(student=cls.user, cohort=cls.second, status='active')
        cls.other_enrollment = Enrollment.objects.create(student=cls.other, cohort=cls.foreign, status='active')
        cls.notice = Notification.objects.create(recipient=cls.user, title='Own notice', message='Own message', url='/users/dashboard/')
        cls.other_notice = Notification.objects.create(recipient=cls.other, title='FOREIGN PRIVATE NOTICE')

    def setUp(self):
        set_flag('frontend_v1_records', enabled=True, reason='Records regression')
        self.client.force_login(self.user)

    def test_all_routes_private_real_renderer_and_no_demo_assets(self):
        for name, template in ROUTES.items():
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, f'frontend_v1/records/{template}.html')
                self.assertIn('no-store', response['Cache-Control'])
                self.assertNotContains(response, '/_preview/')
                self.assertNotContains(response, '/static/js/app.js')
                self.assertNotContains(response, 'FOREIGN PRIVATE')

    def test_default_off_and_independent_rollback(self):
        self.assertFalse(flag_by_slug('frontend_v1_records').default)
        set_flag('frontend_v1_records', enabled=False, reason='Rollback')
        set_flag('frontend_v1_learning', enabled=True, reason='Independent shell')
        for name in ROUTES:
            legacy = name if name != 'subscriptions' else 'subscriptions'
            self.assertTemplateUsed(self.client.get(reverse(name)), f'users/{legacy}.html')
        self.notice.refresh_from_db()
        self.assertFalse(self.notice.is_read)

    def test_all_routes_require_login(self):
        self.client.logout()
        for name in ROUTES:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)

    def test_staff_shell_and_shared_navigation_promoted_only_when_enabled(self):
        response = self.client.get(reverse('certificates'))
        promoted = {item['name'] for item in response.context['frontend_v1_nav']}
        self.assertTrue({'certificates', 'leaderboard', 'attendance_calendar', 'subscriptions', 'help_center'} <= promoted)
        set_flag('frontend_v1_teacher', enabled=True, reason='Staff shell')
        self.client.force_login(self.teacher)
        for name in ROUTES:
            response = self.client.get(reverse(name))
            self.assertEqual(response.context['frontend_v1_workspace'], 'Ustoz maydoni')
            self.assertEqual(response.context['frontend_v1_home'], reverse('teacher_dashboard'))

    def test_empty_states_do_not_invent_records(self):
        self.client.force_login(self.teacher)
        for name, text in [('certificates', 'Hali sertifikat yo‘q'), ('attendance_calendar', 'Davomat ma’lumoti yo‘q'),
                           ('subscriptions', 'Obuna yozuvlari yo‘q'), ('notifications', 'Hozircha bildirishnoma yo‘q')]:
            self.assertContains(self.client.get(reverse(name)), text)

    def test_certificate_badges_are_owned_escaped_and_use_real_document_links(self):
        cert = Certificate.objects.create(student=self.user, course=self.course, final_score=87, certificate_id='RECORD-OWN')
        Certificate.objects.create(student=self.other, course=self.course, final_score=99, certificate_id='FOREIGN-CERT')
        badge = Badge.objects.create(name='<b>Owned badge</b>', description='<p>Earned</p>')
        EarnedBadge.objects.create(student=self.user, badge=badge)
        response = self.client.get(reverse('certificates'))
        self.assertContains(response, '87 / 100')
        self.assertContains(response, '&lt;b&gt;Owned badge&lt;/b&gt;')
        self.assertNotContains(response, 'FOREIGN-CERT')
        for name in ('certificate_detail', 'certificate_appendix'):
            self.assertContains(response, reverse(name, kwargs={'certificate_id': cert.certificate_id}))
        self.assertEqual(Certificate.objects.count(), 2)

    def test_cohort_filters_cannot_leak_foreign_data_and_explain_fallback(self):
        for name in ('attendance_calendar', 'leaderboard'):
            for value in ('bad', str(self.foreign.pk)):
                response = self.client.get(reverse(name), {'cohort': value})
                self.assertTrue(response.context['records_filter_notice'])
                self.assertEqual(response.context['records_selected_cohort'], self.second.pk)
                self.assertNotContains(response, 'FOREIGN PRIVATE GROUP')
            response = self.client.get(reverse(name), {'cohort': self.cohort.pk})
            self.assertFalse(response.context['records_filter_notice'])
            self.assertContains(response, 'data-record-filter')
            self.assertContains(response, 'Qo‘llash')

    def test_duplicate_and_invalid_calendar_filters_are_visible(self):
        url = reverse('attendance_calendar')
        response = self.client.get(url + '?cohort=bad&cohort=' + str(self.cohort.pk) + '&year=bad&month=13')
        self.assertTrue(response.context['records_filter_notice'])
        self.assertEqual(response.context['selected_month'], self.today.replace(day=1))

    def test_calendar_boundaries_do_not_overflow(self):
        for year, month in ((1, 1), (9999, 12)):
            response = self.client.get(reverse('attendance_calendar'), {'year': year, 'month': month, 'cohort': self.cohort.pk})
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.context['prev_month' if year == 1 else 'next_month'])
        response = self.client.get(reverse('attendance_calendar'), {'year': '9' * 100, 'month': 1})
        self.assertEqual(response.context['selected_month'], self.today.replace(day=1))
        self.assertTrue(response.context['records_filter_notice'])

    def test_attendance_daily_summary_and_legacy_parity(self):
        Attendance.objects.create(enrollment=self.enrollment, lesson=self.lesson, date=self.today, status='present', xp_awarded=20)
        second_lesson = Lesson.objects.create(module=self.module, title='Second', order=2)
        Attendance.objects.create(enrollment=self.enrollment, lesson=second_lesson, date=self.today, status='partial', xp_awarded=3)
        Attendance.objects.create(enrollment=self.other_enrollment, lesson=self.lesson, date=self.today, status='absent')
        params = {'cohort': self.cohort.pk}
        response = self.client.get(reverse('attendance_calendar'), params)
        self.assertEqual(response.context['attendance_summary'], {'present': 1, 'partial': 0, 'absent': 0})
        set_flag('frontend_v1_records', enabled=False, reason='Parity')
        legacy = self.client.get(reverse('attendance_calendar'), params)
        for key in ('attendance_day_status', 'attendance_summary', 'calendar_weeks'):
            self.assertEqual(response.context[key], legacy.context[key])

    def test_frozen_enrollment_not_offered_in_attendance_or_rank(self):
        Enrollment.objects.filter(student=self.user).update(status='frozen')
        for name in ('attendance_calendar', 'leaderboard'):
            response = self.client.get(reverse(name), {'cohort': self.cohort.pk})
            self.assertFalse(response.context['records_choices'])
            self.assertIsNone(response.context['records_cohort'])

    def test_rank_uses_canonical_cohort_score_not_global_xp(self):
        LessonProgress.objects.create(enrollment=self.enrollment, lesson=self.lesson, is_completed=True)
        Attendance.objects.create(enrollment=self.enrollment, lesson=self.lesson, date=self.today, status='present', xp_awarded=10)
        response = self.client.get(reverse('leaderboard'), {'cohort': self.cohort.pk})
        self.assertEqual(response.context['leaderboard_my_row']['cohort_score'], 20)
        set_flag('frontend_v1_records', enabled=False, reason='Parity')
        legacy = self.client.get(reverse('leaderboard'), {'cohort': self.cohort.pk})
        self.assertEqual(response.context['leaderboard_top'], legacy.context['leaderboard_top'])

    def test_rank_outside_top_ten_still_shown(self):
        for i in range(11):
            peer = User.objects.create_user(f'peer{i}', f'peer{i}@example.test')
            enrollment = Enrollment.objects.create(student=peer, cohort=self.cohort, status='active')
            LessonProgress.objects.create(enrollment=enrollment, lesson=self.lesson, is_completed=True)
        response = self.client.get(reverse('leaderboard'), {'cohort': self.cohort.pk})
        self.assertEqual(len(response.context['leaderboard_top']), 10)
        self.assertEqual(response.context['leaderboard_my_row']['rank'], 12)

    def test_subscription_plan_history_and_pending_receipt_not_access(self):
        plan = Plan.objects.create(code='record-plan', name='Historical plan', price=10000)
        self.enrollment.plan = plan
        self.enrollment.save(update_fields=['plan'])
        receipt = PaymentReceipt.objects.create(enrollment=self.enrollment, plan=plan, amount=10000)
        Plan.objects.filter(pk=plan.pk).update(name='Renamed catalog')
        Enrollment.objects.filter(pk=self.enrollment.pk).update(status='frozen')
        response = self.client.get(reverse('subscriptions'))
        self.assertContains(response, 'Historical plan')
        self.assertContains(response, 'Chek kutilmoqda')
        self.assertContains(response, 'Cheklangan')
        self.assertEqual(len(response.context['record_enrollments']), 2)
        self.assertNotContains(response, reverse('cohorts:receipt_file', args=[receipt.pk]))
        receipt.refresh_from_db()
        self.assertFalse(receipt.is_verified)

    def test_difference_upload_remains_native_csrf_and_owner_scoped(self):
        receipt = PaymentReceipt.objects.create(enrollment=self.enrollment, kind='difference', amount=5000)
        response = self.client.get(reverse('subscriptions'))
        url = reverse('cohorts:difference_upload', args=[receipt.pk])
        self.assertContains(response, f'action="{url}"')
        self.assertContains(response, 'multipart/form-data')
        self.assertContains(response, 'name="receipt_image"')
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(url, {}).status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url, {}).status_code, 404)

    def test_notifications_stable_page_and_same_page_read_return(self):
        for i in range(25):
            Notification.objects.create(recipient=self.user, title=f'Notice {i}')
        url = reverse('notifications')
        before = self.client.get(url, {'page': 2})
        ids = [n.pk for n in before.context['notice_page']]
        response = self.client.post(reverse('notification_open', args=[ids[0]]), {'page': 2})
        self.assertRedirects(response, url + f'?page=2#notice-{ids[0]}')
        after = self.client.get(url, {'page': 2})
        self.assertEqual(ids, [n.pk for n in after.context['notice_page']])
        self.assertNotContains(after, 'FOREIGN PRIVATE NOTICE')

    def test_single_read_idempotent_owned_and_survives_flag_rollback(self):
        url = reverse('notification_open', args=[self.notice.pk])
        self.client.post(url, {'page': 'bad', 'next': 'https://evil.test'})
        self.notice.refresh_from_db()
        first = self.notice.read_at
        set_flag('frontend_v1_records', enabled=False, reason='In-flight rollback')
        response = self.client.post(url, {'page': '-2'})
        self.assertEqual(response['Location'], reverse('notifications') + f'?page=1#notice-{self.notice.pk}')
        self.notice.refresh_from_db()
        self.assertEqual(self.notice.read_at, first)
        self.assertEqual(self.client.post(reverse('notification_open', args=[self.other_notice.pk])).status_code, 404)

    def test_notification_writes_require_csrf_and_readall_is_post_only(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        for url in (reverse('notification_open', args=[self.notice.pk]), reverse('notifications_read_all')):
            self.assertEqual(client.post(url, {}).status_code, 403)
        self.assertEqual(self.client.get(reverse('notifications_read_all')).status_code, 405)

    def test_read_all_uses_all_recipient_unread_not_only_current_page(self):
        for i in range(23):
            Notification.objects.create(recipient=self.user, title=f'Notice {i}')
        response = self.client.post(reverse('notifications_read_all'), {'frontend_v1': 'records', 'page': 2})
        self.assertEqual(response['Location'], reverse('notifications') + '?page=2')
        self.assertFalse(self.user.notifications.filter(is_read=False).exists())
        self.other_notice.refresh_from_db()
        self.assertFalse(self.other_notice.is_read)

    def test_notification_targets_escaped_safe_and_direct_get_does_not_mark_read(self):
        response = self.client.get(reverse('notifications'))
        self.assertContains(response, 'href="/users/dashboard/"')
        self.client.get('/users/dashboard/')
        self.notice.refresh_from_db()
        self.assertFalse(self.notice.is_read)
        for target in ('javascript:alert(1)', '//evil.test/', 'https://evil.test/', 'data:text/html,hi'):
            Notification.objects.filter(pk=self.notice.pk).update(url=target, title='<script>bad</script>')
            response = self.client.get(reverse('notifications'))
            self.assertContains(response, '&lt;script&gt;bad&lt;/script&gt;')
            self.assertNotContains(response, 'Tegishli sahifani ochish')
            legacy = self.client.get(reverse('notification_open', args=[self.notice.pk]))
            self.assertEqual(legacy['Location'], reverse('notifications'))

    def test_help_canonical_faq_sanitized_and_configured_contact_preserved(self):
        LegalPage.objects.update_or_create(page_type='faq', defaults={'title': 'Owner FAQ', 'content': '<p>Canonical FAQ</p><script>alert(1)</script><img src="x" onerror="alert(1)">'})
        site = SiteSettings.load()
        site.telegram_url = 'https://t.me/example'
        site.save()
        response = self.client.get(reverse('help_center'))
        self.assertContains(response, 'Canonical FAQ')
        self.assertContains(response, 'https://t.me/example')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertNotContains(response, 'onerror=')
        self.assertNotContains(response, '3 soat')
        site.telegram_url = 'javascript:alert(1)'
        site.save()
        self.assertNotContains(self.client.get(reverse('help_center')), 'href="javascript:')
