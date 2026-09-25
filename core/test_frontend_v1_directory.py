"""I3b scoped directory and atomic native attendance regressions."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connections
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from cohorts.attendance_service import attendance_sheet_state, save_attendance_sheet, upsert_attendance_and_xp
from cohorts.models import Attendance, Cohort, Enrollment
from core.flags import set_flag
from courses.models import Course, Lesson, Module, CohortLessonRelease
from courses.test_frontend_v1_practice import fixtures


class DirectoryAttendanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures(cls)
        cls.lesson.xp_reward = 100; cls.lesson.save()
        cls.other_enrollment = Enrollment.objects.create(student=cls.other, cohort=cls.cohort, status='active')
        cls.foreign_teacher = get_user_model().objects.create_user('foreign-teacher', 'foreign@example.test', is_staff=True)
        cls.foreign_course = Course.objects.create(title='Hidden course', instructor=cls.foreign_teacher)
        cls.foreign_cohort = Cohort.objects.create(course=cls.foreign_course, name='Hidden cohort', start_date=timezone.localdate())
        cls.foreign_lesson = Lesson.objects.create(module=Module.objects.create(course=cls.foreign_course, title='Foreign'), title='Hidden lesson')

    def setUp(self):
        set_flag('frontend_v1_teacher', enabled=True, reason='I3b regression')
        self.client.force_login(self.teacher)
        self.url = reverse('teacher_attendance')
        self.target = {'cohort':self.cohort.pk, 'lesson':self.lesson.pk}

    def payload(self, **extra):
        response = self.client.get(self.url, self.target)
        data = {**self.target, 'v1_attendance':'1', 'confirm_attendance':'on',
                'revision':response.context['attendance_revision'],
                f'att_{self.enrollment.pk}':'present', f'att_{self.other_enrollment.pk}':'partial'}
        data.update(extra)
        return data

    def test_four_renderers_scope_and_rollback_no_get_writes(self):
        for page in ('courses', 'cohorts', 'students', 'attendance'):
            path = reverse('teacher_' + page)
            response = self.client.get(path)
            self.assertTemplateUsed(response, f'frontend_v1/teacher/{page}.html')
            self.assertIn('no-store', response['Cache-Control'])
            self.assertNotContains(response, 'Hidden cohort'); self.assertNotContains(response, 'Hidden course')
        self.assertFalse(Attendance.objects.exists())
        self.assertFalse(CohortLessonRelease.objects.exists())
        set_flag('frontend_v1_teacher', enabled=False, reason='Rollback')
        for page in ('courses', 'cohorts', 'students', 'attendance'):
            self.assertTemplateUsed(self.client.get(reverse('teacher_' + page)), f'teacher/{page}.html')

    def test_empty_unassigned_staff_learner_anonymous_owner(self):
        staff = get_user_model().objects.create_user('empty-staff', 'empty@example.test', is_staff=True)
        for user in (staff, self.student):
            self.client.force_login(user)
            for page in ('courses', 'cohorts', 'students', 'attendance'):
                self.assertEqual(self.client.get(reverse('teacher_' + page)).status_code, 200 if user.is_staff else 302)
        self.client.logout(); self.assertEqual(self.client.get(self.url).status_code, 302)
        owner = get_user_model().objects.create_superuser('directory-owner', 'owner@example.test', 'test')
        self.client.force_login(owner)
        self.assertContains(self.client.get(reverse('teacher_cohorts')), 'Hidden cohort')

    def test_students_filter_search_pagination_and_real_counts(self):
        for i in range(25):
            user = get_user_model().objects.create_user(f'search-person-{i}', f'person-{i}@example.test', first_name='Needle')
            Enrollment.objects.create(student=user, cohort=self.cohort, status='pending')
        response = self.client.get(reverse('teacher_students'), {'cohort':self.cohort.pk,'q':'Needle','page':2})
        self.assertEqual(response.context['total_count'], 25)
        response = self.client.get(reverse('teacher_students'), {'cohort':self.cohort.pk,'page':2})
        self.assertEqual(len(response.context['page_obj']), 2)
        self.assertContains(response, f'cohort={self.cohort.pk}')
        self.assertContains(self.client.get(reverse('teacher_students'), {'q':'no match', 'cohort':self.cohort.pk}), 'Qidiruvga mos yozuv topilmadi')
        cohort = self.client.get(reverse('teacher_cohorts')).context['cohorts'][0]
        self.assertEqual((cohort.members_count, cohort.pending_count, cohort.enrollment_count), (2,25,27))
        course = self.client.get(reverse('teacher_courses')).context['courses'][0]
        self.assertEqual(course.students_total, 2)

    def test_invalid_explicit_get_targets_never_fall_back(self):
        for raw in (str(self.foreign_cohort.pk), '99999', '²', '9' * 4400):
            self.assertEqual(self.client.get(reverse('teacher_students'), {'cohort':raw}).status_code, 404)
            self.assertEqual(self.client.get(self.url, {'cohort':raw}).status_code, 404)
        for raw in ('', '²', str(self.foreign_lesson.pk), '99999'):
            self.assertEqual(self.client.get(self.url, {'cohort':self.cohort.pk,'lesson':raw}).status_code, 404)
        self.cohort.is_active = False; self.cohort.save()
        self.assertEqual(self.client.get(self.url, self.target).status_code, 404)

    def test_post_targets_strict_in_both_renderers(self):
        for enabled in (True, False):
            set_flag('frontend_v1_teacher', enabled=enabled, reason='Target regression')
            for data in ({}, {'cohort':self.cohort.pk}, {**self.target,'cohort':self.foreign_cohort.pk},
                         {**self.target,'lesson':self.foreign_lesson.pk}, {**self.target,'cohort':'²'}):
                self.assertIn(self.client.post(self.url, data).status_code, (400,404))
            self.assertEqual(self.client.post(self.url + '?lesson=999', self.target).status_code, 400)
        self.assertFalse(Attendance.objects.exists())

    def test_native_save_xp_streak_result_and_no_release(self):
        response = self.client.post(self.url, self.payload(release_lesson='on'), follow=True)
        self.assertContains(response, 'data-draft-confirmed="true"')
        self.assertContains(response, 'Server: Keldi')
        self.assertContains(response, '100 XP')
        self.student.refresh_from_db(); self.other.refresh_from_db()
        self.assertEqual((self.student.total_xp, self.other.total_xp), (100,30))
        self.assertEqual(Attendance.objects.count(), 2)
        self.assertFalse(CohortLessonRelease.objects.exists())
        self.assertEqual(SystemAuditEvent.objects.filter(action='attendance.sheet').count(), 1)
        self.assertFalse(response.context['attendance_form']['confirm_attendance'].value())

    def test_invalid_status_foreign_row_revision_or_confirmation_are_all_or_nothing(self):
        for extra in ({f'att_{self.other_enrollment.pk}':'bogus'}, {'att_99999':'present'},
                      {'confirm_attendance':''}, {'revision':''}):
            response = self.client.post(self.url, self.payload(**extra))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.context['attendance_form'][f'att_{self.enrollment.pk}'].value(), 'present')
            self.assertFalse(response.context['attendance_form']['confirm_attendance'].value())
        self.assertFalse(Attendance.objects.exists())
        self.student.refresh_from_db(); self.assertEqual(self.student.total_xp, 0)

    def test_csrf_and_mid_form_flag_rollback(self):
        data = self.payload()
        csrf_client = Client(enforce_csrf_checks=True); csrf_client.force_login(self.teacher)
        self.assertEqual(csrf_client.post(self.url, data).status_code, 403)
        set_flag('frontend_v1_teacher', enabled=False, reason='Mid-form rollback')
        self.assertEqual(self.client.post(self.url, data).status_code, 400)
        self.assertFalse(Attendance.objects.exists())

    def test_unchanged_retry_rejected_no_double_xp_or_audit(self):
        data = self.payload()
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        self.assertEqual(self.client.post(self.url, data).status_code, 409)
        self.student.refresh_from_db(); self.assertEqual(self.student.total_xp, 100)
        self.assertEqual(SystemAuditEvent.objects.filter(action='attendance.sheet').count(), 1)

    def test_stale_other_writer_and_roster_changes_preserve_inputs(self):
        data = self.payload()
        upsert_attendance_and_xp(enrollment=self.enrollment, lesson=self.lesson, date=timezone.localdate(), status='absent', marked_by=self.teacher)
        response = self.client.post(self.url, data)
        self.assertContains(response, 'Server: Kelmadi', status_code=409)
        self.assertEqual(response.context['attendance_form'][f'att_{self.enrollment.pk}'].value(), 'present')
        self.assertFalse(response.context['attendance_form']['confirm_attendance'].value())
        data = self.payload()
        self.other_enrollment.status = 'pending'; self.other_enrollment.save()
        self.assertEqual(self.client.post(self.url, data).status_code, 409)
        self.assertEqual(Attendance.objects.get().status, 'absent')

    def test_latest_date_preserved_blank_does_not_erase_and_xp_delta(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        upsert_attendance_and_xp(enrollment=self.enrollment, lesson=self.lesson, date=yesterday, status='partial', marked_by=self.teacher)
        self.client.post(self.url, self.payload(**{f'att_{self.other_enrollment.pk}':''}))
        record = Attendance.objects.get(); self.assertEqual((record.date, record.status), (yesterday,'present'))
        self.student.refresh_from_db(); self.assertEqual(self.student.total_xp, 100)
        self.client.post(self.url, self.payload(**{f'att_{self.enrollment.pk}':'', f'att_{self.other_enrollment.pk}':''}))
        record.refresh_from_db(); self.assertEqual(record.status, 'present')

    def test_mid_batch_exception_rolls_back_every_row_and_xp(self):
        data = self.payload()
        def fail_second(**kwargs):
            if kwargs['enrollment'].pk == self.other_enrollment.pk:
                raise ValidationError('Sinovdagi rad javobi')
            return upsert_attendance_and_xp(**kwargs)
        with patch('cohorts.attendance_service.upsert_attendance_and_xp', side_effect=fail_second):
            self.assertEqual(self.client.post(self.url, data).status_code, 409)
        self.assertFalse(Attendance.objects.exists())
        self.student.refresh_from_db(); self.assertEqual(self.student.total_xp, 0)
        self.assertFalse(SystemAuditEvent.objects.filter(action='attendance.sheet').exists())

    def test_admin_save_advances_snapshot_and_blocks_old_sheet(self):
        from cohorts.admin import AttendanceAdmin
        self.client.post(self.url, self.payload())
        data = self.payload()
        record = Attendance.objects.get(enrollment=self.enrollment)
        record.status = 'absent'
        request = RequestFactory().post('/admin/cohorts/attendance/'); request.user = self.teacher
        AttendanceAdmin(Attendance, admin.site).save_model(request, record, None, True)
        self.assertEqual(self.client.post(self.url, data).status_code, 409)
        record.refresh_from_db(); self.assertEqual(record.status, 'absent')

    def test_sheet_writes_shared_users_in_global_order_not_enrollment_order(self):
        course = Course.objects.create(title='Second course', instructor=self.teacher)
        lesson = Lesson.objects.create(module=Module.objects.create(course=course, title='Second'), title='Second lesson')
        group = Cohort.objects.create(course=course, name='Reverse roster', start_date=timezone.localdate())
        users = sorted([self.student, self.other], key=lambda user: user.pk, reverse=True)
        members = [Enrollment.objects.create(student=user, cohort=group, status='active') for user in users]
        revision = attendance_sheet_state(cohort=group, lesson=lesson)[2]
        with patch('cohorts.attendance_service.upsert_attendance_and_xp', wraps=upsert_attendance_and_xp) as writer:
            save_attendance_sheet(cohort=group, lesson=lesson, actor=self.teacher,
                marks={member.pk: 'present' for member in members}, expected_revision=revision)
        self.assertEqual([call.kwargs['enrollment'].student_id for call in writer.call_args_list],
                         sorted(user.pk for user in users))


@skipUnlessDBFeature('has_select_for_update')
class AttendanceSheetConcurrencyTests(TransactionTestCase):
    def test_only_one_write_for_the_same_sheet_revision(self):
        fixtures(self)
        revision = attendance_sheet_state(cohort=self.cohort, lesson=self.lesson)[2]
        barrier = Barrier(2)
        def save():
            try:
                cohort = Cohort.objects.get(pk=self.cohort.pk)
                lesson = Lesson.objects.get(pk=self.lesson.pk)
                actor = get_user_model().objects.get(pk=self.teacher.pk)
                barrier.wait(timeout=10)
                try:
                    save_attendance_sheet(cohort=cohort, lesson=lesson, actor=actor,
                        marks={self.enrollment.pk:'present'}, expected_revision=revision)
                    return 'saved'
                except ValidationError as exc:
                    return exc.code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(save) for _ in range(2)]
            self.assertEqual(sorted(f.result(timeout=20) for f in futures), ['saved','stale_sheet'])
        self.assertEqual(Attendance.objects.count(), 1)
        self.student.refresh_from_db(); self.assertEqual(self.student.total_xp, self.lesson.xp_reward)
