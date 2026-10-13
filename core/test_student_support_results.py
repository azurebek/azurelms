"""Learning support scope, publication privacy, bounded reads and no writes."""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from cohorts.models import Cohort, Enrollment
from core.flags import set_flag
from core.student_support_results import PAGE_SIZE, build_student_results
from courses.exam_publication import learner_result
from courses.models import (
    Assignment, AssignmentSubmission, Course, Exam, ExamAttempt,
    ExamResultPublication, ExamSection, Lesson, Module, Quiz, QuizAttempt,
)


@override_settings(GEMINI_API_KEY='', TELEGRAM_BOT_TOKEN='')
class StudentSupportResultsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user('results-owner', 'results-owner@example.test', is_superuser=True, is_staff=True)
        cls.teacher = User.objects.create_user('results-teacher', 'results-teacher@example.test', is_staff=True)
        cls.other_teacher = User.objects.create_user('results-other-teacher', 'results-other-teacher@example.test', is_staff=True)
        cls.student = User.objects.create_user('results-student', 'results-student@example.test')
        cls.other_student = User.objects.create_user('results-other-student', 'results-other-student@example.test')
        cls.unenrolled = User.objects.create_user('results-unenrolled', 'results-unenrolled@example.test')
        cls.course = Course.objects.create(title='Turk tili', description='Darslar', instructor=cls.teacher)
        cls.foreign_course = Course.objects.create(title='Begona kurs', description='Darslar', instructor=cls.other_teacher)
        cls.module = Module.objects.create(course=cls.course, title='Asoslar', order=1)
        cls.lesson = Lesson.objects.create(module=cls.module, title='Tanishuv', order=1)
        cls.next_lesson = Lesson.objects.create(module=cls.module, title='Oilam', order=2)
        cls.foreign_lesson = Lesson.objects.create(
            module=Module.objects.create(course=cls.foreign_course, title='Begona'), title='Begona dars')
        cls.cohort = Cohort.objects.create(course=cls.course, name='Ertalab', start_date=timezone.localdate())
        cls.foreign_cohort = Cohort.objects.create(course=cls.foreign_course, name='Kechqurun', start_date=timezone.localdate())
        Enrollment.objects.create(student=cls.student, cohort=cls.cohort, status=Enrollment.STATUS_FROZEN)
        Enrollment.objects.create(student=cls.student, cohort=cls.foreign_cohort, status=Enrollment.STATUS_ACTIVE)
        Enrollment.objects.create(student=cls.other_student, cohort=cls.foreign_cohort, status=Enrollment.STATUS_ACTIVE)
        cls.assignment = Assignment.objects.create(lesson=cls.lesson, title='O‘zim haqimda', description='Private task')
        cls.quiz = Quiz.objects.create(lesson=cls.lesson, title='Salomlashish')
        cls.exam = Exam.objects.create(course=cls.course, title='Oraliq imtihon', exam_type='visa', weight_percentage=40)
        cls.foreign_exam = Exam.objects.create(course=cls.foreign_course, title='Begona imtihon', exam_type='visa', weight_percentage=40)
        set_flag('frontend_v1_exam_review', enabled=True, actor=cls.owner, reason='Synthetic results test')

    def inspect(self, **overrides):
        params = {'actor': self.teacher, 'student_id': self.student.pk,
                  'course_id': self.course.pk, 'lesson_id': self.lesson.pk}
        params.update(overrides)
        return build_student_results(**params)

    def submission(self, **overrides):
        params = {'student': self.student, 'assignment': self.assignment,
                  'answer_text': 'PRIVATE ANSWER', 'teacher_feedback': 'PRIVATE FEEDBACK'}
        params.update(overrides)
        return AssignmentSubmission.objects.create(**params)

    def quiz_attempt(self, **overrides):
        params = {'student': self.student, 'quiz': self.quiz, 'score': Decimal('75.00'),
                  'total_correct': 3, 'total_questions': 4}
        params.update(overrides)
        return QuizAttempt.objects.create(**params)

    def exam_attempt(self, **overrides):
        params = {'student': self.student, 'exam': self.exam}
        params.update(overrides)
        return ExamAttempt.objects.create(**params)

    def publication(self, attempt, **overrides):
        payload = {'version': 1, 'score': '82.50', 'passed': True, 'passing_score': 60,
                   'review_notes': 'PUBLISHED PRIVATE FEEDBACK',
                   'reviewed_at': timezone.now().isoformat(),
                   'section_reviews': [], 'feedback_answers': []}
        payload.update(overrides)
        return ExamResultPublication.objects.create(attempt=attempt, payload=payload)

    def test_pending_approved_revision_and_unsubmitted_are_distinct(self):
        empty = self.inspect()['assignment_rows'][0]
        self.assertEqual(empty['status'], 'empty')
        self.assertFalse(empty['action_url'])
        submission = self.submission()
        pending = self.inspect()['assignment_rows'][0]
        self.assertEqual(pending['status'], 'pending')
        self.assertIsNone(pending['awarded_xp'])
        self.assertEqual(pending['action_url'], reverse('teacher_grade_assignment', kwargs={'submission_id': submission.pk}))
        for stored, projected in [('approved', 'approved'), ('needs_revision', 'revision')]:
            AssignmentSubmission.objects.filter(pk=submission.pk).update(status=stored, awarded_xp=35)
            row = self.inspect()['assignment_rows'][0]
            self.assertEqual(row['status'], projected)
            self.assertEqual(row['awarded_xp'], 35 if stored == 'approved' else None)
            self.assertNotIn('PRIVATE', str(row))

    def test_submission_does_not_cross_student_or_course(self):
        self.submission(student=self.other_student, status='approved')
        hidden = Assignment.objects.create(lesson=self.foreign_lesson, title='HIDDEN TASK', description='Hidden')
        self.submission(assignment=hidden, status='approved')
        for actor in (self.teacher, self.owner):
            data = self.inspect(actor=actor)
            self.assertEqual(len(data['assignment_rows']), 1)
            self.assertEqual(data['assignment_rows'][0]['status'], 'empty')
            self.assertNotIn('HIDDEN', str(data['assignment_rows']))

    def test_selected_lesson_filters_work_but_exams_stay_course_wide(self):
        Assignment.objects.create(lesson=self.next_lesson, title='Other lesson task', description='Task')
        quiz = Quiz.objects.create(lesson=self.next_lesson, title='Other lesson quiz')
        self.quiz_attempt(quiz=quiz)
        attempt = self.exam_attempt()
        data = self.inspect()
        self.assertEqual([row['id'] for row in data['assignment_rows']], [self.assignment.pk])
        self.assertEqual(data['quiz_rows'], [])
        self.assertEqual([row['id'] for row in data['exam_rows']], [attempt.pk])
        self.assertIn(self.course.title, data['exam_scope_label'])
        self.assertEqual(len(self.inspect(lesson_id=None)['assignment_rows']), 2)

    def test_quiz_history_marks_current_result_even_when_timestamps_tie(self):
        older, newer = self.quiz_attempt(), self.quiz_attempt(score=Decimal('25.00'))
        QuizAttempt.objects.filter(pk=newer.pk).update(completed_at=older.completed_at)
        rows = self.inspect()['quiz_rows']
        self.assertEqual([row['id'] for row in rows], [newer.pk, older.pk])
        self.assertEqual([row['is_latest'] for row in rows], [True, False])
        self.assertEqual(rows[0]['score'], Decimal('25.00'))
        self.assertIn('Oldingi', rows[1]['learner_label'])
        self.assertFalse(rows[0]['action_url'])

    def test_quiz_without_answers_is_still_a_saved_attempt_not_a_missing_record(self):
        attempt = self.quiz_attempt(total_correct=0, total_questions=0, score=0)
        row = self.inspect()['quiz_rows'][0]
        self.assertEqual(row['id'], attempt.pk)
        self.assertEqual(row['score'], 0)
        self.assertEqual(row['status'], 'recorded')

    def test_quiz_scope_excludes_other_student_course_and_ambiguous_dual_parent(self):
        own = self.quiz_attempt()
        self.quiz_attempt(student=self.other_student)
        foreign_quiz = Quiz.objects.create(lesson=self.foreign_lesson, title='HIDDEN QUIZ')
        self.quiz_attempt(quiz=foreign_quiz)
        section = ExamSection.objects.create(exam=self.foreign_exam, title='Hidden section',
                                             section_type='grammar_quiz', max_score=100)
        malformed = Quiz.objects.create(lesson=self.lesson, exam_section=section, title='DUAL PARENT')
        self.quiz_attempt(quiz=malformed)
        self.assertEqual([row['id'] for row in self.inspect()['quiz_rows']], [own.pk])

    def test_exam_draft_is_not_a_learner_result_and_in_progress_has_no_review_action(self):
        attempt = self.exam_attempt(score=Decimal('99'), review_notes='SECRET DRAFT')
        row = self.inspect()['exam_rows'][0]
        self.assertEqual(row['status'], 'in_progress')
        self.assertIsNone(row['score'])
        self.assertFalse(row['action_url'])
        ExamAttempt.objects.filter(pk=attempt.pk).update(is_completed=True)
        row = self.inspect()['exam_rows'][0]
        self.assertEqual(row['status'], 'pending')
        self.assertIsNone(row['score'])
        self.assertFalse(row['result_visible'])
        self.assertNotIn('SECRET DRAFT', str(row))
        self.assertEqual(row['action_url'], reverse('teacher_grade_exam', kwargs={'attempt_id': attempt.pk}))

    def test_exam_published_result_wins_over_later_draft_values(self):
        attempt = self.exam_attempt(is_completed=True, is_reviewed=True, score=Decimal('12'),
                                    passed=False, review_notes='SECRET DRAFT')
        self.publication(attempt)
        with patch('core.student_support_results.learner_result', wraps=learner_result) as canonical:
            row = self.inspect()['exam_rows'][0]
        canonical.assert_called_once()
        self.assertEqual(row['score'], Decimal('82.50'))
        self.assertEqual(row['detail'], 'O‘tgan.')
        self.assertTrue(row['result_visible'])
        self.assertNotIn('PRIVATE', str(row))
        self.assertNotIn('DRAFT', str(row))

    def test_exam_legacy_approved_aggregate_is_labeled_without_inventing_feedback(self):
        self.exam_attempt(is_completed=True, is_reviewed=True, score=Decimal('64.25'),
                          passed=True, review_notes='PRIVATE LEGACY DRAFT')
        row = self.inspect()['exam_rows'][0]
        self.assertEqual(row['score'], Decimal('64.25'))
        self.assertTrue(row['details_unavailable'])
        self.assertIn('Eski natija', row['detail'])
        self.assertNotIn('PRIVATE', str(row))

    def test_exam_history_uses_attempt_number_for_current_not_start_time(self):
        old = self.exam_attempt(is_completed=True, is_reviewed=True, attempt_number=1)
        self.publication(old)
        current = self.exam_attempt(attempt_number=2, score=99)
        ExamAttempt.objects.filter(pk=old.pk).update(start_time=current.start_time)
        rows = {row['id']: row for row in self.inspect()['exam_rows']}
        self.assertFalse(rows[old.pk]['is_latest'])
        self.assertFalse(rows[old.pk]['result_visible'])
        self.assertEqual(rows[old.pk]['score'], Decimal('82.50'))
        self.assertTrue(rows[current.pk]['is_latest'])
        self.assertIsNone(rows[current.pk]['score'])

    def test_exam_action_is_hidden_when_safe_review_renderer_is_disabled(self):
        self.exam_attempt(is_completed=True)
        set_flag('frontend_v1_exam_review', enabled=False, actor=self.owner, reason='Synthetic fallback')
        row = self.inspect()['exam_rows'][0]
        self.assertFalse(row['action_url'])
        self.assertIn('hozir yoqilmagan', row['action_note'])

    def test_exam_scope_excludes_other_student_and_other_course(self):
        own = self.exam_attempt()
        self.exam_attempt(student=self.other_student)
        self.exam_attempt(exam=self.foreign_exam)
        for actor in (self.teacher, self.owner):
            self.assertEqual([row['id'] for row in self.inspect(actor=actor)['exam_rows']], [own.pk])

    def test_fresh_actor_permission_is_required(self):
        for actor in (self.student, AnonymousUser()):
            with self.subTest(actor=actor), self.assertRaises(PermissionDenied):
                self.inspect(actor=actor)
        for changes in ({'is_active': False}, {'is_staff': False}):
            get_user_model().objects.filter(pk=self.teacher.pk).update(is_active=True, is_staff=True)
            get_user_model().objects.filter(pk=self.teacher.pk).update(**changes)
            with self.subTest(changes=changes), self.assertRaises(PermissionDenied):
                self.inspect()

    def test_fresh_scope_target_and_parent_validation(self):
        with self.assertRaises(get_user_model().DoesNotExist):
            self.inspect(student_id=self.other_student.pk)
        with self.assertRaises(Course.DoesNotExist):
            self.inspect(course_id=self.foreign_course.pk)
        with self.assertRaises(Lesson.DoesNotExist):
            self.inspect(actor=self.owner, lesson_id=self.foreign_lesson.pk)
        for target in (self.owner, self.teacher):
            with self.assertRaises(get_user_model().DoesNotExist):
                self.inspect(actor=self.owner, student_id=target.pk)
        Course.objects.filter(pk=self.course.pk).update(instructor=self.other_teacher)
        with self.assertRaises(get_user_model().DoesNotExist):
            self.inspect()

    def test_no_selected_course_returns_empty_pages_and_rejects_orphan_lesson(self):
        data = self.inspect(actor=self.owner, student_id=self.unenrolled.pk, course_id=None, lesson_id=None)
        for kind in ('assignment', 'quiz', 'exam'):
            self.assertEqual(data[f'{kind}_rows'], [])
            self.assertEqual(data[f'{kind}_page_obj'].paginator.count, 0)
        with self.assertRaises(Lesson.DoesNotExist):
            self.inspect(course_id=None)

    def test_three_histories_have_independent_bounded_pagination(self):
        for index in range(PAGE_SIZE + 1):
            Assignment.objects.create(lesson=self.lesson, title=f'Task {index}', description='Task')
            self.quiz_attempt()
            self.exam_attempt(attempt_number=index + 1)
        first = self.inspect()
        for kind in ('assignment', 'quiz', 'exam'):
            self.assertEqual(len(first[f'{kind}_rows']), PAGE_SIZE)
            self.assertTrue(first[f'{kind}_page_obj'].has_next())
        next_data = self.inspect(assignment_page=2, quiz_page=2, exam_page=2)
        self.assertEqual(len(next_data['assignment_rows']), 2)
        self.assertEqual(len(next_data['quiz_rows']), 1)
        self.assertEqual(len(next_data['exam_rows']), 1)
        self.assertFalse(next_data['quiz_rows'][0]['is_latest'])
        for kind in ('assignment', 'quiz', 'exam'):
            self.assertFalse({row['id'] for row in first[f'{kind}_rows']} &
                             {row['id'] for row in next_data[f'{kind}_rows']})

    def test_more_rows_do_not_add_queries_and_large_answer_fields_are_not_selected(self):
        self.submission()
        self.quiz_attempt()
        self.exam_attempt(is_completed=True, is_reviewed=True)
        with CaptureQueriesContext(connection) as baseline:
            self.inspect()
        for index in range(5):
            task = Assignment.objects.create(lesson=self.lesson, title=f'Task {index}', description='PRIVATE CONTENT')
            self.submission(assignment=task)
            self.quiz_attempt()
            self.exam_attempt(is_completed=True, is_reviewed=True, attempt_number=index + 2)
        with CaptureQueriesContext(connection) as more:
            self.inspect()
        self.assertEqual(len(more), len(baseline))
        sql = '\n'.join(row['sql'] for row in more)
        for field in ('answer_text', 'teacher_feedback', 'review_notes', 'description', 'answer_versions'):
            self.assertNotIn(f'"{field}"', sql)

    def test_projection_never_writes_or_opens_learner_or_review_views(self):
        self.submission()
        self.quiz_attempt()
        attempt = self.exam_attempt(is_completed=True, is_reviewed=True)
        self.publication(attempt)
        with (patch('courses.views.LessonDetailView.dispatch', side_effect=AssertionError('Learner view')),
              patch('courses.models.ExamAttempt.ensure_section_reviews', side_effect=AssertionError('Review write')),
              CaptureQueriesContext(connection) as captured):
            data = self.inspect()
        self.assertTrue(data['exam_rows'])
        writes = [row['sql'] for row in captured if row['sql'].lstrip().upper().startswith(
            ('INSERT', 'UPDATE', 'DELETE', 'REPLACE'))]
        self.assertEqual(writes, [])
