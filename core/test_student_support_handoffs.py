"""Targeted support handoffs reuse the existing payment and membership writers."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from aicontrol.models import SystemAuditEvent
from cohorts.models import Cohort, Enrollment, PaymentReceipt
from core.flags import set_flag
from courses.models import Assignment, AssignmentSubmission, Course, Lesson, LessonProgress, Module


class StudentSupportHandoffTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user('handoff-owner', 'handoff-owner@example.test', is_staff=True, is_superuser=True)
        cls.teacher = User.objects.create_user('handoff-teacher', 'handoff-teacher@example.test', is_staff=True)
        cls.other_teacher = User.objects.create_user('handoff-other-teacher', 'handoff-other-teacher@example.test', is_staff=True)
        cls.student = User.objects.create_user('handoff-selected-student', 'handoff-selected@example.test')
        cls.other_student = User.objects.create_user('handoff-other-student', 'handoff-other@example.test')
        cls.foreign_student = User.objects.create_user('handoff-foreign-student', 'handoff-foreign@example.test')
        cls.course = Course.objects.create(title='Selected course', instructor=cls.teacher)
        cls.foreign_course = Course.objects.create(title='Foreign course', instructor=cls.other_teacher)
        cls.cohort = Cohort.objects.create(course=cls.course, name='Selected group', start_date=date(2026, 10, 1))
        cls.second_cohort = Cohort.objects.create(course=cls.course, name='Second group', start_date=date(2026, 10, 1))
        cls.foreign_cohort = Cohort.objects.create(course=cls.foreign_course, name='Foreign group', start_date=date(2026, 10, 1))
        cls.enrollment = Enrollment.objects.create(student=cls.student, cohort=cls.cohort, status='pending')
        cls.other_enrollment = Enrollment.objects.create(student=cls.other_student, cohort=cls.cohort, status='pending')
        cls.second_enrollment = Enrollment.objects.create(student=cls.student, cohort=cls.second_cohort, status='pending')
        cls.foreign_enrollment = Enrollment.objects.create(student=cls.foreign_student, cohort=cls.foreign_cohort, status='pending')
        cls.receipt = PaymentReceipt.objects.create(enrollment=cls.enrollment, amount=250000)
        cls.other_receipt = PaymentReceipt.objects.create(enrollment=cls.other_enrollment, amount=260000)
        cls.foreign_receipt = PaymentReceipt.objects.create(enrollment=cls.foreign_enrollment, amount=270000)

    def setUp(self):
        set_flag('backoffice_student_support', enabled=True, reason='Isolated handoff regression')
        self.client.force_login(self.owner)

    def receipts_url(self, *, enrollment=None, receipt=None):
        enrollment = enrollment or self.enrollment
        result = reverse('backoffice_receipts') + f'?enrollment={enrollment.pk}'
        return result + f'&receipt={receipt.pk}' if receipt is not None else result

    def members_url(self, *, enrollment=None, cohort=None):
        enrollment = enrollment or self.enrollment
        cohort = cohort or self.cohort
        return reverse('backoffice_cohort_members', args=[cohort.pk]) + f'?enrollment={enrollment.pk}'

    def support_url(self):
        return reverse('backoffice_workspace_student', kwargs={'student_id': self.student.pk}) + f'?course={self.course.pk}'

    def receipt_data(self, *, receipt=None, **changes):
        result = {'receipt_id': (receipt or self.receipt).pk, 'action': 'verify',
                  'change_reason': 'Synthetic receipt reviewed', 'confirm_change': 'on'}
        result.update(changes)
        return result

    def member_data(self, **changes):
        result = {'enrollment_id': self.enrollment.pk, 'action': 'restore',
                  'change_reason': 'Synthetic membership review', 'confirm_change': 'on'}
        result.update(changes)
        return result

    def test_receipt_focus_filters_one_enrollment_and_has_scoped_recheck_link(self):
        self.client.force_login(self.teacher)
        response = self.client.get(self.receipts_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row.pk for row in response.context['pending_receipts']], [self.receipt.pk])
        self.assertEqual(response.context['selected_enrollment'].pk, self.enrollment.pk)
        self.assertEqual(response.context['support_return_url'], self.support_url())
        self.assertContains(response, self.student.username)
        self.assertNotContains(response, self.other_student.username)
        self.assertNotContains(response, self.foreign_student.username)
        self.assertContains(response, 'O‘quvchini qayta tekshirish')
        self.receipt.refresh_from_db()
        self.assertFalse(self.receipt.is_verified)

    def test_optional_receipt_focus_does_not_select_another_receipt_of_same_enrollment(self):
        difference = PaymentReceipt.objects.create(
            enrollment=self.enrollment, amount=10000, kind=PaymentReceipt.KIND_DIFFERENCE,
        )
        response = self.client.get(self.receipts_url(receipt=difference))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row.pk for row in response.context['pending_receipts']], [difference.pk])
        response = self.client.post(self.receipts_url(receipt=difference), self.receipt_data())
        self.assertEqual(response.status_code, 404)
        self.receipt.refresh_from_db()
        difference.refresh_from_db()
        self.assertFalse(self.receipt.is_verified)
        self.assertFalse(difference.is_verified)

    def test_targeted_receipt_rejects_foreign_course_or_foreign_enrollment(self):
        self.client.force_login(self.teacher)
        foreign_url = self.receipts_url(enrollment=self.foreign_enrollment)
        self.assertEqual(self.client.get(foreign_url).status_code, 404)
        self.assertEqual(self.client.post(foreign_url, self.receipt_data(receipt=self.foreign_receipt)).status_code, 404)
        for receipt in (self.other_receipt, self.foreign_receipt):
            with self.subTest(receipt=receipt.pk):
                self.assertEqual(self.client.get(self.receipts_url(receipt=receipt)).status_code, 404)
                self.assertEqual(self.client.post(self.receipts_url(), self.receipt_data(receipt=receipt)).status_code, 404)
        self.assertFalse(PaymentReceipt.objects.filter(is_verified=True).exists())

    def test_receipt_invalid_missing_and_ambiguous_targets_fail_closed(self):
        base = reverse('backoffice_receipts')
        for query in ('enrollment=', 'enrollment=0', 'enrollment=-1', 'enrollment=wrong',
                      'enrollment=１', 'enrollment=999999999',
                      f'enrollment={self.enrollment.pk}&enrollment={self.other_enrollment.pk}',
                      f'receipt={self.receipt.pk}', f'enrollment={self.enrollment.pk}&receipt=',
                      f'enrollment={self.enrollment.pk}&receipt={self.receipt.pk}&receipt={self.other_receipt.pk}'):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(base + '?' + query).status_code, 404)
        self.assertEqual(self.client.post(self.receipts_url(), self.receipt_data(receipt_id='')).status_code, 404)
        self.assertEqual(self.client.post(self.receipts_url(), self.receipt_data(receipt_id=[self.receipt.pk, self.other_receipt.pk])).status_code, 404)

    def test_targeted_verify_uses_existing_writer_and_keeps_membership_focus(self):
        response = self.client.post(self.receipts_url(receipt=self.receipt), self.receipt_data())
        self.assertRedirects(response, self.receipts_url())
        self.receipt.refresh_from_db()
        self.enrollment.refresh_from_db()
        self.other_receipt.refresh_from_db()
        self.assertTrue(self.receipt.is_verified)
        self.assertTrue(self.enrollment.has_active_access())
        self.assertFalse(self.other_receipt.is_verified)
        self.assertTrue(SystemAuditEvent.objects.filter(action='receipt.verify', actor=self.owner).exists())

    def test_pending_diagnosis_receipt_decision_and_original_recheck_open_lesson(self):
        module = Module.objects.create(course=self.course, title='Support module')
        lesson = Lesson.objects.create(module=module, title='Support lesson')
        self.client.force_login(self.teacher)
        card = self.client.get(self.support_url() + f'&lesson={lesson.pk}&q=handoff&page=2')
        self.assertEqual(card.context['diagnosis']['code'], 'pending')
        handoff = card.context['next_steps'][0]['url']
        self.assertEqual(handoff, self.receipts_url(receipt=self.receipt))
        decision_page = self.client.get(handoff)
        self.assertEqual([row.pk for row in decision_page.context['pending_receipts']], [self.receipt.pk])
        response = self.client.post(handoff, self.receipt_data())
        self.assertEqual(response.status_code, 302)
        recheck = self.client.get(card.context['recheck_url'])
        self.assertEqual(recheck.context['diagnosis']['code'], 'open')
        self.assertEqual(recheck.context['student'].pk, self.student.pk)
        self.assertEqual(recheck.context['selected_lesson'].pk, lesson.pk)
        self.assertEqual(recheck.context['effective_enrollment'].pk, self.enrollment.pk)
        self.assertEqual(recheck.context['list_context']['q'], 'handoff')
        self.assertEqual(recheck.context['list_context']['page'], '2')
        self.assertFalse(LessonProgress.objects.filter(enrollment__student=self.student).exists())

    def test_sequence_diagnosis_assignment_approval_and_original_recheck_open_lesson(self):
        Enrollment.objects.filter(pk=self.enrollment.pk).update(status=Enrollment.STATUS_ACTIVE)
        module = Module.objects.create(course=self.course, title='Sequence module')
        first = Lesson.objects.create(module=module, title='First lesson', order=1)
        second = Lesson.objects.create(module=module, title='Second lesson', order=2)
        assignment = Assignment.objects.create(lesson=first, title='First assignment', description='Synthetic work', max_xp=25)
        submission = AssignmentSubmission.objects.create(assignment=assignment, student=self.student,
                                                        answer_text='Synthetic answer', status='pending')
        set_flag('frontend_v1_teacher', enabled=True, reason='Existing assignment confirmation flow')
        self.client.force_login(self.teacher)
        card = self.client.get(self.support_url() + f'&lesson={second.pk}')
        self.assertEqual(card.context['diagnosis']['code'], 'sequence')
        handoff = card.context['next_steps'][0]['url']
        self.assertEqual(handoff, reverse('teacher_grade_assignment', args=[submission.pk]))
        review = self.client.get(handoff)
        self.assertEqual(review.context['submission'].pk, submission.pk)
        self.assertEqual(review.context['submission'].status, 'pending')
        response = self.client.post(handoff, {
            'action': 'approve', 'teacher_feedback': 'Reviewed synthetic work', 'awarded_xp': 15,
            'revision': review.context['revision'], 'confirm_review': 'on',
        })
        self.assertEqual(response.status_code, 302)
        submission.refresh_from_db()
        self.assertEqual(submission.status, AssignmentSubmission.STATUS_APPROVED)
        self.assertEqual(submission.awarded_xp, 15)
        recheck = self.client.get(card.context['recheck_url'])
        self.assertEqual(recheck.context['diagnosis']['code'], 'open')
        self.assertEqual(recheck.context['selected_lesson'].pk, second.pk)
        self.assertFalse(LessonProgress.objects.filter(enrollment__student=self.student).exists())

    def test_rejected_receipt_is_deleted_but_redirect_and_recheck_still_work(self):
        response = self.client.post(self.receipts_url(receipt=self.receipt), self.receipt_data(action='reject'))
        self.assertRedirects(response, self.receipts_url())
        self.assertFalse(PaymentReceipt.objects.filter(pk=self.receipt.pk).exists())
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.STATUS_PENDING)
        page = self.client.get(response['Location'])
        self.assertEqual(page.status_code, 200)
        self.assertEqual(list(page.context['pending_receipts']), [])
        self.assertEqual(page.context['support_return_url'], self.support_url())
        self.assertNotContains(page, self.other_student.username)
        self.assertTrue(SystemAuditEvent.objects.filter(action='receipt.reject', actor=self.owner).exists())

    def test_targeted_receipt_confirmation_and_csrf_remain_required(self):
        response = self.client.post(self.receipts_url(), self.receipt_data(confirm_change=''))
        self.assertRedirects(response, self.receipts_url())
        self.receipt.refresh_from_db()
        self.assertFalse(self.receipt.is_verified)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        self.assertEqual(csrf.post(self.receipts_url(), self.receipt_data()).status_code, 403)

    def test_membership_focus_only_shows_selected_member(self):
        response = self.client.get(self.members_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row.pk for row in response.context['members']], [self.enrollment.pk])
        self.assertEqual(response.context['support_return_url'], self.support_url())
        self.assertContains(response, self.student.username)
        self.assertNotContains(response, self.other_student.username)

    def test_membership_focus_rejects_other_cohort_and_forged_post_member(self):
        for enrollment in (self.second_enrollment, self.foreign_enrollment):
            with self.subTest(enrollment=enrollment.pk):
                self.assertEqual(self.client.get(self.members_url(enrollment=enrollment)).status_code, 404)
        for target in (self.other_enrollment.pk, self.foreign_enrollment.pk, '',
                       [self.enrollment.pk, self.other_enrollment.pk]):
            with self.subTest(target=target):
                response = self.client.post(self.members_url(), self.member_data(enrollment_id=target))
                self.assertEqual(response.status_code, 404)
        self.assertFalse(SystemAuditEvent.objects.filter(action__in=['membership.release', 'membership.restore']).exists())

    def test_membership_invalid_and_ambiguous_query_rejected(self):
        base = reverse('backoffice_cohort_members', args=[self.cohort.pk])
        for query in ('enrollment=', 'enrollment=-1', 'enrollment=wrong', 'enrollment=１',
                      'enrollment=99999999', f'enrollment={self.enrollment.pk}&enrollment={self.other_enrollment.pk}'):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(base + '?' + query).status_code, 404)

    def test_targeted_restore_keeps_existing_expired_result_and_focus(self):
        self.enrollment.status = Enrollment.STATUS_FROZEN
        self.enrollment.save(update_fields=['status'])
        response = self.client.post(self.members_url(), self.member_data())
        self.assertRedirects(response, self.members_url())
        self.enrollment.refresh_from_db()
        self.other_enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.STATUS_EXPIRED)
        self.assertFalse(self.enrollment.has_active_access())
        self.assertEqual(self.other_enrollment.status, Enrollment.STATUS_PENDING)
        self.assertTrue(SystemAuditEvent.objects.filter(action='membership.restore', actor=self.owner).exists())

    def test_membership_owner_only_guard_and_confirmation_stay_in_place(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(self.members_url()).status_code, 403)
        self.assertEqual(self.client.post(self.members_url(), self.member_data()).status_code, 403)
        self.client.force_login(self.owner)
        self.enrollment.status = Enrollment.STATUS_FROZEN
        self.enrollment.save(update_fields=['status'])
        response = self.client.post(self.members_url(), self.member_data(confirm_change=''))
        self.assertRedirects(response, self.members_url())
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, Enrollment.STATUS_FROZEN)

    def test_flag_off_omits_support_backlinks_but_existing_resolvers_still_work(self):
        set_flag('backoffice_student_support', enabled=False, reason='Support rollback')
        for url in (self.receipts_url(), self.members_url()):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['support_return_url'], '')
                self.assertNotContains(response, 'O‘quvchini qayta tekshirish')

    def test_targeted_pages_and_error_responses_are_private_and_not_stored(self):
        responses = [self.client.get(self.receipts_url()), self.client.get(self.members_url()),
                     self.client.get(reverse('backoffice_receipts') + '?enrollment=bad'),
                     self.client.get(self.members_url(enrollment=self.foreign_enrollment)),
                     self.client.post(self.receipts_url(), self.receipt_data(confirm_change='')),
                     self.client.post(self.members_url(), self.member_data(enrollment_id=self.other_enrollment.pk))]
        self.assertEqual([response.status_code for response in responses], [200, 200, 404, 404, 302, 404])
        self.client.force_login(self.teacher)
        forbidden = self.client.get(self.members_url())
        self.assertEqual(forbidden.status_code, 403)
        responses.append(forbidden)
        self.client.logout()
        redirected = self.client.get(self.receipts_url())
        self.assertEqual(redirected.status_code, 302)
        responses.append(redirected)
        for response in responses:
            with self.subTest(status=response.status_code):
                self.assertIn('private', response['Cache-Control'])
                self.assertIn('no-store', response['Cache-Control'])

    def test_unfiltered_global_routes_keep_existing_behavior(self):
        self.client.force_login(self.teacher)
        response = self.client.get(reverse('backoffice_receipts'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(row.pk for row in response.context['pending_receipts']),
                         {self.receipt.pk, self.other_receipt.pk, self.foreign_receipt.pk})
        self.assertEqual(response.context['support_return_url'], '')
        self.client.force_login(self.owner)
        response = self.client.get(reverse('backoffice_cohort_members', args=[self.cohort.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(row.pk for row in response.context['members']),
                         {self.enrollment.pk, self.other_enrollment.pk})
