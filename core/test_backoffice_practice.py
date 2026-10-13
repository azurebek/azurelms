"""B2.2 adapter contracts: scope, form recovery, safe preview and explicit writes."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from core.flags import set_flag
from core.practice_forms import change_questions, quiz_shape_reason
from django.core.exceptions import ValidationError
from courses import authoring_service as authoring
from courses.models import (Assignment, AssignmentSubmission, Choice, CohortLessonRelease,
    Course, Lesson, LessonProgress, Module, Question, Quiz, QuizAnswer, QuizAttempt)


class BackofficePracticeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = get_user_model().objects.create_user('practice-author', email='practice-author@example.test', is_staff=True)
        cls.owner = get_user_model().objects.create_user('practice-owner', email='practice-owner@example.test', is_superuser=True)
        cls.other = get_user_model().objects.create_user('practice-other', email='practice-other@example.test', is_staff=True)
        cls.student = get_user_model().objects.create_user('practice-student', email='practice-student@example.test')
        cls.course = Course.objects.create(title='Turk tili', instructor=cls.teacher)
        cls.lesson = Lesson.objects.create(module=Module.objects.create(course=cls.course, title='Boshlash'), title='Salomlashuv')
        cls.other_course = Course.objects.create(title='Boshqa kurs', instructor=cls.other)
        cls.other_lesson = Lesson.objects.create(module=Module.objects.create(course=cls.other_course), title='Boshqa dars')
        cls.assignment = Assignment.objects.create(lesson=cls.lesson, title='Tanishing', description='<p>O‘zingizni tanishtiring.</p>', max_xp=50)
        cls.quiz = Quiz.objects.create(lesson=cls.lesson, title='Salomlashuv testi', xp_reward=20)
        cls.question = Question.objects.create(quiz=cls.quiz, text='<p><strong>Merhaba</strong> nima?</p>')
        cls.correct = Choice.objects.create(question=cls.question, text='Salom', is_correct=True)
        cls.incorrect = Choice.objects.create(question=cls.question, text='Xayr', is_correct=False)

    def setUp(self):
        set_flag('backoffice_course_workspace', enabled=True, reason='Isolated B2.2 test')
        set_flag('backoffice_practice_authoring', enabled=True, reason='Isolated B2.2 test')
        self.client.force_login(self.teacher)

    def url(self, kind='assignment', obj=None, course=None, lesson=None):
        args = {'course_id': (course or self.course).pk, 'lesson_id': (lesson or self.lesson).pk}
        if obj:
            args[f'{kind}_id'] = obj.pk
        return reverse(f'backoffice_workspace_{kind}_{"edit" if obj else "new"}', kwargs=args)

    def data(self, kind='assignment', obj=None, count=1, **overrides):
        data = {'action': 'save', 'title': 'Yangi mashq', 'confirm_impact': 'on',
            'editor_revision': (authoring.assignment_revision(self.teacher, self.lesson, obj)
                if kind == 'assignment' else authoring.lesson_quiz_revision(self.teacher, self.lesson, obj))}
        if kind == 'assignment':
            data.update(description='<p>Bir jumla yozing.</p>', max_xp='35')
        else:
            data.update(xp_reward='30')
            rows = list(obj.questions.prefetch_related('choices').order_by('pk')) if obj else [None] * count
            data['questions-TOTAL_FORMS'] = str(len(rows))
            for index, question in enumerate(rows):
                prefix = f'questions-{index}'
                choices = list(question.choices.order_by('pk')) if question else [None, None]
                data.update({f'{prefix}-id': str(question.pk) if question else '',
                    f'{prefix}-text': question.text if question else f'<p>{index + 1}-savol</p>',
                    f'{prefix}-correct': '0', f'{prefix}-choices-TOTAL_FORMS': str(len(choices))})
                for ci, choice in enumerate(choices):
                    data.update({f'{prefix}-choices-{ci}-id': str(choice.pk) if choice else '',
                        f'{prefix}-choices-{ci}-text': choice.text if choice else f'Variant {ci + 1}'})
        data.update(overrides)
        return data

    def canonical_counts(self):
        return [model.objects.count() for model in (Assignment, Quiz, Question, Choice,
            AssignmentSubmission, QuizAttempt, QuizAnswer, LessonProgress, CohortLessonRelease)]

    def test_get_has_course_context_explicit_impact_and_private_cache(self):
        response = self.client.get(self.url())
        self.assertContains(response, 'Salomlashuv')
        self.assertContains(response, 'confirm_impact')
        self.assertContains(response, 'data-practice-draft')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertIn('private', response['Cache-Control'])

    def test_course_card_links_are_lesson_scoped_and_hidden_when_flag_off(self):
        course_url = reverse('backoffice_workspace_course', args=[self.course.pk]) + f'?lesson={self.lesson.pk}'
        response = self.client.get(course_url)
        for kind, obj in [('assignment', self.assignment), ('quiz', self.quiz)]:
            self.assertContains(response, self.url(kind))
            self.assertContains(response, self.url(kind, obj))
        set_flag('backoffice_practice_authoring', enabled=False, reason='Hide B2.2 entry links')
        response = self.client.get(course_url)
        self.assertNotContains(response, self.url())
        self.assertNotContains(response, self.url('quiz'))

    def test_assignment_create_reopen_and_same_create_replay(self):
        data = self.data()
        response = self.client.post(self.url(), data)
        saved = Assignment.objects.get(title='Yangi mashq')
        self.assertRedirects(response, self.url(obj=saved))
        self.assertEqual(saved.lesson, self.lesson)
        self.assertEqual(saved.max_xp, 35)
        self.assertEqual(self.client.post(self.url(), data).status_code, 409)
        self.assertEqual(Assignment.objects.filter(title='Yangi mashq').count(), 1)

    def test_assignment_preview_has_no_canonical_write_and_can_return(self):
        before = self.canonical_counts()
        with patch('courses.authoring_service.save_assignment') as save:
            response = self.client.post(self.url(), self.data(action='preview', confirm_impact=''))
        self.assertEqual(response.status_code, 200)
        save.assert_not_called()
        self.assertContains(response, 'O‘quvchi ko‘rinishining namunasi')
        self.assertContains(response, 'Bir jumla yozing.')
        self.assertEqual(self.canonical_counts(), before)
        returned = self.client.post(self.url(), self.data(action='edit', max_xp='not-a-number'))
        self.assertEqual(returned.status_code, 200)
        self.assertEqual(returned.context['form']['max_xp'].value(), 'not-a-number')
        self.assertContains(returned, 'type="text" name="max_xp" value="not-a-number"')

    def test_assignment_invalid_numeric_and_rich_blank_remain_editable(self):
        response = self.client.post(self.url(), self.data(max_xp='bad-number'))
        self.assertContains(response, 'value="bad-number"', status_code=400)
        self.assertEqual(response.context['form'].fields['max_xp'].widget.input_type, 'text')
        response = self.client.post(self.url(), self.data(description='<p>&nbsp;</p>'))
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.context['form'].errors['description'])

    def test_assignment_confirmation_required_only_on_save(self):
        data = self.data(confirm_impact='')
        self.assertEqual(self.client.post(self.url(), data).status_code, 400)
        self.assertFalse(Assignment.objects.filter(title='Yangi mashq').exists())
        data['action'] = 'preview'
        self.assertEqual(self.client.post(self.url(), data).status_code, 200)

    def test_assignment_stale_keeps_bound_values(self):
        data = self.data(obj=self.assignment, title='Unsaved work')
        self.assignment.title = 'Another window'
        self.assignment.save()
        response = self.client.post(self.url(obj=self.assignment), data)
        self.assertContains(response, 'value="Unsaved work"', status_code=409)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.title, 'Another window')

    def test_assignment_any_submission_is_readonly(self):
        AssignmentSubmission.objects.create(assignment=self.assignment, student=self.student, status='needs_revision')
        page = self.client.get(self.url(obj=self.assignment))
        self.assertContains(page, 'javob yuborilgan')
        self.assertNotContains(page, 'value="save"')
        before = self.canonical_counts()
        response = self.client.post(self.url(obj=self.assignment), self.data(obj=self.assignment))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.canonical_counts(), before)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.title, 'Tanishing')

    def test_quiz_three_question_create_reopen_and_preview(self):
        data = self.data('quiz', count=3)
        response = self.client.post(self.url('quiz'), data)
        saved = Quiz.objects.get(title='Yangi mashq')
        self.assertRedirects(response, self.url('quiz', saved))
        self.assertEqual(saved.questions.count(), 3)
        self.assertEqual(Choice.objects.filter(question__quiz=saved, is_correct=True).count(), 3)
        before = self.canonical_counts()
        response = self.client.post(self.url('quiz', saved), self.data('quiz', saved, action='preview', confirm_impact=''))
        self.assertContains(response, '3-savol')
        self.assertTrue(response.context['show_preview'])
        self.assertEqual(self.canonical_counts(), before)
        self.assertEqual(self.client.post(self.url('quiz'), data).status_code, 409)

    def test_question_inline_error_and_rich_text_retained(self):
        data = self.data('quiz', self.quiz)
        data['questions-0-choices-1-text'] = ''
        response = self.client.post(self.url('quiz', self.quiz), data)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.context['questions'][0]['open'])
        self.assertTrue(response.context['questions'][0]['choices'][1]['form'].errors['text'])
        self.assertContains(response, '&lt;strong&gt;Merhaba&lt;/strong&gt;', status_code=400)
        self.assertEqual(Choice.objects.filter(question=self.question).count(), 2)

    def test_question_missing_correct_answer_does_not_save(self):
        data = self.data('quiz', count=3)
        data.pop('questions-1-correct')
        response = self.client.post(self.url('quiz'), data)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.context['questions'][1]['form'].errors['correct'])
        self.assertFalse(Quiz.objects.filter(title='Yangi mashq').exists())

    def test_quiz_preview_reuses_canonical_rich_validation(self):
        data = self.data('quiz', action='preview')
        data['questions-0-text'] = '<p>&nbsp;</p>'
        before = self.canonical_counts()
        response = self.client.post(self.url('quiz'), data)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.context['questions'][0]['form'].errors['text'])
        self.assertEqual(self.canonical_counts(), before)

    def test_structural_add_remove_preserves_values_without_db_write(self):
        before = self.canonical_counts()
        data = self.data('quiz', self.quiz, action='add_question', xp_reward='unfinished')
        response = self.client.post(self.url('quiz', self.quiz), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['questions']), 2)
        self.assertTrue(response.context['questions'][1]['open'])
        self.assertEqual(response.context['questions'][0]['form']['id'].value(), str(self.question.pk))
        self.assertEqual(response.context['form']['xp_reward'].value(), 'unfinished')
        self.assertEqual(response.context['form'].fields['xp_reward'].widget.input_type, 'text')
        data = self.data('quiz', self.quiz, action='add_choice:0')
        response = self.client.post(self.url('quiz', self.quiz), data)
        self.assertEqual(len(response.context['questions'][0]['choices']), 3)
        data.update({'questions-0-choices-TOTAL_FORMS': '3', 'questions-0-choices-2-id': '',
            'questions-0-choices-2-text': 'Added', 'questions-0-correct': '2', 'action': 'remove_choice:0:1'})
        response = self.client.post(self.url('quiz', self.quiz), data)
        self.assertEqual(response.context['questions'][0]['form']['correct'].value(), '1')
        self.assertEqual(response.context['questions'][0]['choices'][1]['form']['text'].value(), 'Added')
        self.assertEqual(self.canonical_counts(), before)

    def test_restore_accepts_incomplete_nested_values_but_never_writes(self):
        before = self.canonical_counts()
        data = self.data('quiz', count=3, action='restore', title='', xp_reward='unfinished')
        data['questions-1-choices-0-text'] = ''
        response = self.client.post(self.url('quiz'), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['questions']), 3)
        self.assertEqual(response.context['form']['xp_reward'].value(), 'unfinished')
        self.assertEqual(response.context['form'].fields['xp_reward'].widget.input_type, 'text')
        self.assertEqual(self.canonical_counts(), before)

    def test_structural_count_and_unlisted_fields_are_rejected(self):
        for changes in ({'questions-TOTAL_FORMS': '10000'}, {'questions-TOTAL_FORMS': '0'},
                        {'questions-0-choices-TOTAL_FORMS': '1'}, {'questions-9-text': 'Extra'}):
            with self.subTest(changes=changes):
                response = self.client.post(self.url('quiz'), self.data('quiz', **changes))
                self.assertEqual(response.status_code, 400)
        self.assertFalse(Quiz.objects.filter(title='Yangi mashq').exists())

    def test_malformed_structure_preserves_posted_question_for_copy(self):
        data = self.data('quiz', self.quiz)
        data.update({'questions-TOTAL_FORMS': 'broken', 'questions-0-text': '<p>My unsaved question</p>',
                     'questions-0-choices-0-text': 'My unsaved choice'})
        response = self.client.post(self.url('quiz', self.quiz), data)
        self.assertContains(response, 'My unsaved question', status_code=400)
        self.assertContains(response, 'My unsaved choice', status_code=400)
        self.assertNotContains(response, 'value="save"', status_code=400)
        self.assertNotContains(response, 'data-practice-draft ', status_code=400)
        self.assertEqual(response.context['questions'][0]['form']['text'].value(), '<p>My unsaved question</p>')

    def test_aggregate_shape_guard_does_not_mutate_structure(self):
        rows = [{'id': '', 'text': f'Question {index}', 'correct': '0',
                 'choices': [{'id': '', 'text': 'Choice'}] * 3} for index in range(89)]
        self.assertEqual(quiz_shape_reason(rows), '')
        change_questions(rows, 'add_question')  # 899 content fields remain below the guard.
        self.assertEqual(len(rows), 90)
        with self.assertRaises(ValidationError):
            change_questions(rows, 'add_choice:0')
        self.assertEqual(len(rows[0]['choices']), 3)

    def test_quiz_edit_preserves_ids_and_existing_rich_text(self):
        response = self.client.post(self.url('quiz', self.quiz), self.data('quiz', self.quiz))
        self.assertEqual(response.status_code, 302)
        self.question.refresh_from_db()
        self.assertIn('<strong>Merhaba</strong>', self.question.text)
        self.assertTrue(Choice.objects.filter(pk=self.correct.pk).exists())

    def test_quiz_stale_keeps_question_values(self):
        data = self.data('quiz', self.quiz)
        self.correct.text = 'Changed elsewhere'
        self.correct.save()
        response = self.client.post(self.url('quiz', self.quiz), data)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.context['questions'][0]['choices'][0]['form']['text'].value(), 'Salom')
        self.correct.refresh_from_db()
        self.assertEqual(self.correct.text, 'Changed elsewhere')

    def test_quiz_answerless_attempt_protects_content(self):
        QuizAttempt.objects.create(quiz=self.quiz, student=self.student)
        before = self.canonical_counts()
        page = self.client.get(self.url('quiz', self.quiz))
        self.assertContains(page, 'o‘quvchi urinishi')
        self.assertNotContains(page, 'value="save"')
        response = self.client.post(self.url('quiz', self.quiz), self.data('quiz', self.quiz))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.canonical_counts(), before)

    def test_used_after_open_preserves_unsaved_assignment_and_quiz_values(self):
        assignment_data = self.data(obj=self.assignment, title='My unsaved title')
        quiz_data = self.data('quiz', self.quiz)
        quiz_data['questions-0-text'] = '<p>My unsaved quiz text</p>'
        quiz_data['questions-0-choices-0-text'] = 'My unsaved answer'
        AssignmentSubmission.objects.create(assignment=self.assignment, student=self.student)
        QuizAttempt.objects.create(quiz=self.quiz, student=self.student)
        assignment_response = self.client.post(self.url(obj=self.assignment), assignment_data)
        quiz_response = self.client.post(self.url('quiz', self.quiz), quiz_data)
        self.assertContains(assignment_response, 'value="My unsaved title"', status_code=409)
        self.assertContains(quiz_response, 'My unsaved quiz text', status_code=409)
        self.assertContains(quiz_response, 'My unsaved answer', status_code=409)
        self.assertNotContains(assignment_response, 'value="save"', status_code=409)
        self.assertNotContains(quiz_response, 'value="save"', status_code=409)

    def test_unsupported_quiz_remains_readonly_without_conversion(self):
        self.question.points = 2
        self.question.save()
        page = self.client.get(self.url('quiz', self.quiz))
        self.assertContains(page, 'tuzilishi oddiy bir javobli testga mos emas')
        self.assertNotContains(page, 'data-practice-form')
        response = self.client.post(self.url('quiz', self.quiz), self.data('quiz', self.quiz))
        self.assertEqual(response.status_code, 409)
        self.question.refresh_from_db()
        self.assertEqual(self.question.points, 2)

    def test_wrong_course_lesson_and_foreign_object_fail_closed(self):
        for kind, obj in [('assignment', self.assignment), ('quiz', self.quiz)]:
            self.assertEqual(self.client.get(self.url(kind, course=self.other_course, lesson=self.other_lesson)).status_code, 404)
            self.assertEqual(self.client.post(self.url(kind, lesson=self.other_lesson), self.data(kind)).status_code, 404)
            self.assertEqual(self.client.get(self.url(kind, obj, course=self.other_course, lesson=self.other_lesson)).status_code, 404)

    def test_other_teacher_cannot_access_but_owner_can(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.assertEqual(self.client.post(self.url(), self.data()).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_anonymous_student_and_inactive_are_denied(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url()).status_code, 302)
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.teacher.is_active = False
        self.teacher.save()
        self.client.force_login(self.teacher)
        self.assertIn(self.client.post(self.url(), self.data()).status_code, (302, 403))

    def test_flag_off_hides_get_and_denies_post(self):
        for flag in ('backoffice_practice_authoring', 'backoffice_course_workspace'):
            with self.subTest(flag=flag):
                set_flag(flag, enabled=False, reason='Rollback isolated B2.2 test')
                for kind in ('assignment', 'quiz'):
                    self.assertEqual(self.client.get(self.url(kind)).status_code, 404)
                    self.assertEqual(self.client.post(self.url(kind), self.data(kind)).status_code, 409)
                set_flag(flag, enabled=True, reason='Continue isolated B2.2 test')

    def test_csrf_and_duplicate_fields_are_rejected(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.teacher)
        self.assertEqual(client.post(self.url(), self.data()).status_code, 403)
        self.assertEqual(self.client.post(self.url(), self.data(title=['First', 'Second'])).status_code, 400)
        data = self.data('quiz')
        data['questions-0-correct'] = ['0', '1']
        self.assertEqual(self.client.post(self.url('quiz'), data).status_code, 400)

    def test_preview_sanitizes_executable_html(self):
        response = self.client.post(self.url(), self.data(action='preview',
            description='<p>Matn</p><script>danger()</script><img src="x" onerror="danger()">'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('<script>', response.context['preview_description'])
        self.assertNotIn('onerror=', response.context['preview_description'])

    def test_receipt_clears_only_saved_practice_scope(self):
        original = self.client.get(self.url())
        response = self.client.post(self.url(), self.data(draft_submission_id='practice-receipt'))
        self.assertEqual(response.status_code, 302)
        receipt = self.client.session['workspace_saved']
        self.assertEqual(receipt['scope'], original.context['draft_scope'])
        self.assertEqual(receipt['submission_id'], 'practice-receipt')
