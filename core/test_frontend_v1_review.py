"""I3a native teacher queue/review: access, stale writes and learner outcome."""
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
from threading import Barrier

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connections
from django.test import Client, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from aicontrol.models import SystemAuditEvent
from core.flags import set_flag
from courses.models import Assignment, AssignmentSubmission, Course, Exam, ExamAttempt, Lesson, Module
from courses.submission_service import review_assignment_submission, submit_assignment
from courses.test_frontend_v1_practice import fixtures
from library.test_resources import PDF_BYTES, pdf_upload
from users.models import Notification


class TeacherReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures(cls)
        cls.assignment.max_xp = 50
        cls.assignment.save()
        cls.submission = AssignmentSubmission.objects.create(assignment=cls.assignment, student=cls.student, answer_text='<learner answer>')
        cls.exam = Exam.objects.create(course=cls.course, title='Exam waiting', exam_type='final', weight_percentage=100)
        cls.attempt = ExamAttempt.objects.create(exam=cls.exam, student=cls.student, is_completed=True, completed_time=timezone.now())

    def setUp(self):
        scratch = TemporaryDirectory(prefix='v1-review-')
        self.addCleanup(scratch.cleanup)
        settings_override = override_settings(PRIVATE_MEDIA_ROOT=scratch.name)
        settings_override.enable(); self.addCleanup(settings_override.disable)
        set_flag('frontend_v1_teacher', enabled=True, reason='I3a regression')
        self.client.force_login(self.teacher)
        self.queue_url = reverse('teacher_grading')
        self.url = reverse('teacher_grade_assignment', args=[self.submission.pk])

    def payload(self, **extra):
        self.submission.refresh_from_db()
        data = dict(v1_review='1', action='approve', teacher_feedback='Yaxshi!', awarded_xp='15',
                    revision=self.submission.updated_at.isoformat(), confirm_review='on')
        data.update(extra)
        return data

    def test_v1_and_off_renderers_no_get_writes(self):
        stamp = self.submission.updated_at
        for name, path in (('grading', self.queue_url), ('grade_assignment', self.url)):
            response = self.client.get(path)
            self.assertTemplateUsed(response, f'frontend_v1/teacher/{name}.html')
            self.assertIn('no-store', response['Cache-Control'])
        self.assertContains(self.client.get(self.url), '&lt;learner answer&gt;')
        self.assertFalse(SystemAuditEvent.objects.filter(action='assignment.review').exists())
        self.submission.refresh_from_db(); self.assertEqual(stamp, self.submission.updated_at)
        set_flag('frontend_v1_teacher', enabled=False, reason='Rollback')
        for name, path in (('grading', self.queue_url), ('grade_assignment', self.url)):
            self.assertTemplateUsed(self.client.get(path), f'teacher/{name}.html')

    def test_normalized_input_ack_is_one_shot_and_revision_scoped(self):
        response = self.client.post(self.url, self.payload(action='revision', awarded_xp='015'), follow=True)
        self.assertContains(response, 'data-draft-confirmed="true"')
        self.assertEqual(response.context['review_form'].fields['awarded_xp'].widget.attrs['data-draft-saved'], '015')
        self.assertEqual(response.context['submission'].awarded_xp, 0)
        self.assertNotContains(self.client.get(self.url), 'data-draft-confirmed')
        self.client.post(self.url, self.payload())
        review_assignment_submission(submission=self.submission, reviewer=self.teacher, approved=True, feedback='New decision', awarded_xp=20)
        self.assertNotContains(self.client.get(self.url), 'data-draft-confirmed')

    def test_scope_roles_foreign_submission_and_course_filter(self):
        User = get_user_model()
        self.other.is_staff = True; self.other.save()
        foreign_course = Course.objects.create(title='Hidden foreign course', instructor=self.other)
        foreign_lesson = Lesson.objects.create(module=Module.objects.create(course=foreign_course, title='M'), title='Hidden lesson')
        foreign = AssignmentSubmission.objects.create(student=self.other, assignment=Assignment.objects.create(lesson=foreign_lesson, title='Hidden work'), answer_text='private')
        self.assertNotContains(self.client.get(self.queue_url + '?status=all'), 'Hidden work')
        foreign_url = reverse('teacher_grade_assignment', args=[foreign.pk])
        self.assertEqual(self.client.get(foreign_url).status_code, 404)
        self.assertEqual(self.client.post(foreign_url, self.payload()).status_code, 404)
        for raw in (str(foreign_course.pk), '99999', '²', '9' * 4400):
            self.assertEqual(self.client.get(self.queue_url, {'course': raw}).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        owner = User.objects.create_superuser('review-owner', 'owner@example.test', 'test')
        self.client.force_login(owner)
        self.assertContains(self.client.get(self.queue_url + '?status=all'), 'Hidden work')
        self.client.force_login(self.student)
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 302)
        self.client.logout()
        self.assertEqual(self.client.get(self.queue_url).status_code, 302)

    def test_queue_filters_both_kinds_empty_and_safe_return(self):
        self.assertContains(self.client.get(self.queue_url), 'Exam waiting')
        self.client.post(self.url, self.payload())
        self.assertNotContains(self.client.get(self.queue_url), 'My day')
        reviewed = self.client.get(self.queue_url, {'status':'reviewed', 'course':self.course.pk})
        self.assertContains(reviewed, 'My day')
        self.assertNotContains(reviewed, 'Exam waiting')
        self.assertContains(self.client.get(self.queue_url, {'status':'all'}), 'My day')
        self.assertContains(self.client.get(self.url + '?return_status=reviewed&course=' + str(self.course.pk) + '&next=https://evil.example'), '?status=reviewed&amp;course=')
        self.assertNotContains(self.client.get(self.url + '?return_status=https://evil.example'), 'evil.example')
        self.assertEqual(self.client.get(self.queue_url + '?status=nonsense').context['queue_filter'], 'pending')

    def test_pagination_preserves_scope_and_does_not_truncate_queue(self):
        for i in range(26):
            assignment = Assignment.objects.create(lesson=self.lesson, title=f'Extra {i}')
            AssignmentSubmission.objects.create(student=self.student, assignment=assignment)
        response = self.client.get(self.queue_url, {'course':self.course.pk, 'status':'pending', 'assignments_page':2})
        self.assertEqual(response.context['assignment_page'].paginator.count, 27)
        self.assertEqual(len(response.context['assignment_page']), 2)
        self.assertContains(response, 'assignments_page=1')
        self.assertContains(response, f'course={self.course.pk}')

    def test_private_attachment_and_file_only_work(self):
        self.submission.attachment = pdf_upload(); self.submission.answer_text = ''; self.submission.save()
        file_url = reverse('submission_file', args=[self.submission.pk])
        response = self.client.get(self.url)
        self.assertContains(response, file_url)
        self.assertNotContains(response, self.submission.attachment.name)
        stream = self.client.get(file_url)
        self.assertEqual(b''.join(stream.streaming_content), PDF_BYTES)

    def test_invalid_input_preserves_feedback_no_state_xp_audit_notification(self):
        for extra in ({'action':'erase'}, {'action':''}, {'awarded_xp':'bad'}, {'awarded_xp':'1.5'},
                      {'awarded_xp':'51'}, {'awarded_xp':'-1'}, {'awarded_xp':'9' * 4400},
                      {'confirm_review':''}, {'revision':''}):
            response = self.client.post(self.url, self.payload(teacher_feedback='<keep my feedback>', **extra))
            self.assertContains(response, '&lt;keep my feedback&gt;', status_code=400)
            self.assertIn('no-store', response['Cache-Control'])
            self.assertNotContains(response, 'name="confirm_review" required id="id_confirm_review" checked', status_code=400)
        self.submission.refresh_from_db(); self.student.refresh_from_db()
        self.assertEqual((self.submission.status, self.student.total_xp), ('pending', 0))
        self.assertFalse(SystemAuditEvent.objects.filter(action='assignment.review').exists())
        self.assertFalse(Notification.objects.filter(recipient=self.student).exists())

    def test_csrf_and_flag_change_before_post_are_no_write(self):
        client = Client(enforce_csrf_checks=True); client.force_login(self.teacher)
        self.assertEqual(client.post(self.url, self.payload()).status_code, 403)
        set_flag('frontend_v1_teacher', enabled=False, reason='Rollback mid-form')
        self.assertEqual(self.client.post(self.url, self.payload()).status_code, 400)
        self.submission.refresh_from_db(); self.assertEqual(self.submission.status, 'pending')

    def test_real_review_then_learner_projection_queue_and_xp(self):
        url = self.url + f'?return_status=all&course={self.course.pk}'
        response = self.client.post(url, self.payload())
        self.assertRedirects(response, url)
        self.submission.refresh_from_db(); self.student.refresh_from_db()
        self.assertEqual((self.submission.status, self.submission.awarded_xp, self.student.total_xp), ('approved', 15, 15))
        self.assertTrue(SystemAuditEvent.objects.filter(action='assignment.review').exists())
        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 1)
        set_flag('frontend_v1_lesson', enabled=True, reason='Learner projection')
        self.client.force_login(self.student)
        response = self.client.get(reverse('lesson_detail', args=[self.course.pk, self.lesson.pk]) + '?tab=homework')
        self.assertContains(response, 'Yaxshi!'); self.assertContains(response, '15 XP')

    def test_revision_clears_xp_and_repeat_post_does_not_double_notify(self):
        self.client.post(self.url, self.payload())
        data = self.payload(action='revision', teacher_feedback='To‘ldiring')
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        before = Notification.objects.filter(recipient=self.student).count()
        audit_count = SystemAuditEvent.objects.filter(action='assignment.review').count()
        self.assertEqual(self.client.post(self.url, data).status_code, 409)
        self.submission.refresh_from_db(); self.student.refresh_from_db()
        self.assertEqual((self.submission.status, self.submission.awarded_xp, self.student.total_xp), ('needs_revision', 0, 0))
        self.assertEqual(before, Notification.objects.filter(recipient=self.student).count())
        self.assertEqual(audit_count, SystemAuditEvent.objects.filter(action='assignment.review').count())

    def test_stale_work_returns_fresh_work_and_bound_feedback_requires_reconfirmation(self):
        data = self.payload(teacher_feedback='Old draft')
        submit_assignment(user=self.student, assignment=self.assignment, answer_text='New learner answer')
        response = self.client.post(self.url, data)
        self.assertContains(response, 'New learner answer', status_code=409)
        self.assertContains(response, 'Old draft', status_code=409)
        self.assertEqual(response.context['review_form']['confirm_review'].value(), False)
        self.submission.refresh_from_db()
        self.assertEqual(response.context['review_form']['revision'].value(), self.submission.updated_at.isoformat())
        self.assertFalse(Notification.objects.filter(recipient=self.student).exists())
        self.assertEqual(self.submission.status, 'pending')
        response = self.client.post(self.url, self.payload(teacher_feedback='Fresh review'))
        self.assertEqual(response.status_code, 302)

    def test_other_reviewer_and_missing_revision_cannot_overwrite(self):
        data = self.payload()
        review_assignment_submission(submission=self.submission, approved=True, reviewer=self.teacher, feedback='New grade', awarded_xp=20)
        self.assertEqual(self.client.post(self.url, data).status_code, 409)
        self.submission.refresh_from_db(); self.assertEqual(self.submission.teacher_feedback, 'New grade')
        self.assertEqual(self.submission.awarded_xp, 20)

    def test_draft_scope_changes_on_new_login_and_no_confirmation_is_persistable(self):
        first = self.client.get(self.url)
        self.assertContains(first, 'data-practice-form="review-')
        self.assertNotIn('data-draft-field', str(first.context['review_form']['confirm_review']))
        self.assertNotIn('data-draft-field', str(first.context['review_form']['revision']))
        self.client.logout(); self.client.force_login(self.teacher)
        self.assertNotEqual(first.context['practice_scope'], self.client.get(self.url).context['practice_scope'])

    def test_legacy_approve_contract_and_unknown_action_no_write(self):
        set_flag('frontend_v1_teacher', enabled=False, reason='Legacy')
        self.assertEqual(self.client.post(self.url, {'action':'erase'}).status_code, 400)
        response = self.client.post(self.url, {'action':'approve', 'awarded_xp':'12', 'teacher_feedback':'Legacy'})
        self.assertRedirects(response, self.queue_url)
        self.student.refresh_from_db(); self.assertEqual(self.student.total_xp, 12)


@skipUnlessDBFeature('has_select_for_update')
class ReviewConcurrencyTests(TransactionTestCase):
    def test_only_one_reviewer_can_write_a_given_revision(self):
        fixtures(self)
        submission = AssignmentSubmission.objects.create(assignment=self.assignment, student=self.student, answer_text='Answer')
        revision = submission.updated_at.isoformat()
        barrier = Barrier(2)
        def review():
            try:
                item = AssignmentSubmission.objects.get(pk=submission.pk)
                teacher = get_user_model().objects.get(pk=self.teacher.pk)
                barrier.wait(timeout=10)
                try:
                    review_assignment_submission(submission=item, approved=True, reviewer=teacher, awarded_xp=10, expected_revision=revision)
                    return 'saved'
                except ValidationError as exc:
                    return exc.code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [pool.submit(review) for _ in range(2)]
            self.assertEqual(sorted(f.result(timeout=20) for f in results), ['saved', 'stale_review'])
        self.student.refresh_from_db(); self.assertEqual(self.student.total_xp, 10)
        self.assertEqual(SystemAuditEvent.objects.filter(action='assignment.review').count(), 1)
