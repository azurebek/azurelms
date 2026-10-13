"""Lesson-scoped HTTP adapters for assignment and single-answer quiz authoring."""
from functools import wraps

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorDict
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.access import teacher_course_queryset
from core.backoffice_workspace import (_add_errors, _preview_html, _render, _saved,
    _saved_context, draft_scope, workspace_view)
from core.flags import flag_enabled
from core.practice_forms import (AssignmentPracticeForm, QuizPracticeForm, QuizQuestionForms,
    change_questions, posted_questions, quiz_initial, quiz_shape_reason)
from courses import authoring_service as authoring
from courses.models import Assignment, Course, Lesson, Quiz


FLAG = 'backoffice_practice_authoring'
READ_ACTIONS = {'preview', 'edit', 'restore'}


def practice_view(view):
    @workspace_view
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not flag_enabled(FLAG):
            if request.method == 'POST':
                return render(request, 'backoffice/workspace/unavailable.html', status=409)
            raise Http404
        return view(request, *args, **kwargs)
    return wrapped


def _scope(request, course_id, lesson_id):
    course = get_object_or_404(teacher_course_queryset(request.user), pk=course_id)
    return course, get_object_or_404(Lesson, pk=lesson_id, module__course=course)


def _urls(course, lesson, kind, obj=None):
    args = {'course_id': course.pk, 'lesson_id': lesson.pk}
    new = reverse(f'backoffice_workspace_{kind}_new', kwargs=args)
    if obj:
        args[f'{kind}_id'] = obj.pk
    return {'back_url': reverse('backoffice_workspace_course', kwargs={'course_id': course.pk}) +
            f'?lesson={lesson.pk}#practice', 'new_url': new,
            'editor_url': reverse(f'backoffice_workspace_{kind}_edit', kwargs=args) if obj else new}


def _form_data(request):
    if request.method != 'POST':
        return None
    data = request.POST.copy()
    if data.get('action') != 'save':
        data.pop('confirm_impact', None)
    return data


def _errors(form, error, questions=None):
    if hasattr(error, 'error_dict'):
        for key, values in error.error_dict.items():
            if questions and questions.add_error(key, values):
                continue
            form.add_error(key if key in form.fields else None, values)
    else:
        form.add_error(None, error)


def _confirm(form):
    if not form.cleaned_data.get('confirm_impact'):
        form.add_error('confirm_impact', 'Saqlashning darsga ta’sirini tasdiqlang.')
        return False
    return True


def _base_context(request, course, lesson, kind, obj, form, revision, block_reason, status):
    scope = draft_scope(request, course.pk, lesson.pk, kind=f'{kind}:{obj.pk if obj else "new"}')
    return {'course': course, 'lesson': lesson, 'practice_kind': kind, 'practice': obj,
        'form': form, 'revision': revision, 'block_reason': block_reason,
        'draft_scope': scope, 'conflict': status == 409, 'has_errors': bool(form.errors),
        **_urls(course, lesson, kind, obj),
        **_saved_context(request)}


@practice_view
def assignment_editor(request, course_id, lesson_id, assignment_id=None):
    course, lesson = _scope(request, course_id, lesson_id)
    obj = get_object_or_404(Assignment, pk=assignment_id, lesson=lesson) if assignment_id else None
    action = request.POST.get('action', '') if request.method == 'POST' else ''
    data = _form_data(request)
    form = AssignmentPracticeForm(data=data, initial={name: getattr(obj, name) for name in
        ('title', 'description', 'max_xp')} if obj else {'max_xp': 50})
    revision = request.POST.get('editor_revision', '') if data is not None else authoring.assignment_revision(request.user, lesson, obj)
    block_reason = authoring.assignment_edit_block_reason(obj) if obj else ''
    status, preview = 200, False
    preview_data = None
    if data is not None:
        if block_reason:
            _add_errors(form, ValidationError(block_reason))
            status = 409
        elif action in {'edit', 'restore'}:
            form._errors = ErrorDict()
        elif action in {'save', 'preview'}:
            status = 400
            if form.is_valid():
                try:
                    preview_data = authoring.validate_assignment_data(form.cleaned_data)
                    if action == 'preview':
                        preview, status = True, 200
                    elif _confirm(form):
                        saved, changed = authoring.save_assignment(actor=request.user, course_id=course.pk,
                            lesson_id=lesson.pk, assignment_id=assignment_id, data=form.cleaned_data,
                            expected_revision=revision, request=request)
                        _saved(request, draft_scope(request, course.pk, lesson.pk,
                            kind=f'assignment:{obj.pk if obj else "new"}'))
                        messages.success(request, 'Topshiriq saqlandi.' if changed else 'Topshiriq allaqachon shu holatda saqlangan.')
                        return redirect(_urls(course, lesson, 'assignment', saved)['editor_url'])
                except (authoring.AuthoringConflict, authoring.PracticeInUse,
                        authoring.PracticeUnsupported, authoring.PracticeUnavailable) as error:
                    _errors(form, error)
                    status = 409
                except ValidationError as error:
                    _errors(form, error)
                except (Assignment.DoesNotExist, Course.DoesNotExist, Lesson.DoesNotExist):
                    raise Http404
        else:
            _add_errors(form, ValidationError('Amalni qayta tanlang. Hech narsa saqlanmadi.'))
            status = 400
        form.preserve_invalid_numbers()
    if block_reason and obj:
        preview_data = {'title': obj.title, 'description': obj.description, 'max_xp': obj.max_xp}
    context = _base_context(request, course, lesson, 'assignment', obj, form, revision, block_reason, status)
    context.update(page_title='Topshiriqni tayyorlash' if obj else 'Yangi topshiriq', show_preview=preview,
        preview_title=(preview_data or {}).get('title', ''),
        preview_description=_preview_html((preview_data or {}).get('description', '')),
        preview_xp=(preview_data or {}).get('max_xp', 0))
    return _render(request, 'practice_form', context, status)


@practice_view
def quiz_editor(request, course_id, lesson_id, quiz_id=None):
    course, lesson = _scope(request, course_id, lesson_id)
    obj = get_object_or_404(Quiz, pk=quiz_id, lesson=lesson) if quiz_id else None
    action = request.POST.get('action', '') if request.method == 'POST' else ''
    data = _form_data(request)
    form = QuizPracticeForm(data=data, initial={'title': obj.title, 'xp_reward': obj.xp_reward} if obj else {'xp_reward': 20})
    revision = request.POST.get('editor_revision', '') if data is not None else authoring.lesson_quiz_revision(request.user, lesson, obj)
    block_reason = authoring.lesson_quiz_edit_block_reason(obj) if obj else ''
    status, preview = 200, False
    rows, parse_error, structure_error = quiz_initial(obj), None, None
    block_reason = block_reason or quiz_shape_reason(rows)
    raw_recovery = ''
    if data is not None:
        try:
            rows = posted_questions(data)
        except ValidationError as error:
            parse_error = error
            rows = posted_questions(data, recover=True)
            raw_recovery = '\n'.join(f'{key}: {value}' for key, value in data.items()
                if key.startswith('questions-'))
        if not parse_error and action.startswith(('add_', 'remove_')) and not block_reason:
            try:
                change_questions(rows, action)
            except ValidationError as error:
                structure_error = error
    quiet = data is not None and action not in {'save', 'preview'} and not parse_error
    questions = QuizQuestionForms(rows, bound=data is not None, quiet=quiet)
    preview_data, preview_questions = None, []
    if data is not None:
        if block_reason:
            _errors(form, ValidationError(block_reason))
            status = 409
        elif parse_error:
            _errors(form, parse_error)
            status = 400
        elif structure_error:
            _errors(form, structure_error)
            status = 400
        elif action in READ_ACTIONS - {'preview'} or action.startswith(('add_', 'remove_')):
            form._errors = ErrorDict()
        elif action in {'save', 'preview'}:
            status = 400
            valid = form.is_valid()
            valid_questions = questions.is_valid()
            if valid and valid_questions:
                try:
                    preview_data, preview_questions = authoring.validate_lesson_quiz_data(
                        form.cleaned_data, questions.payload(), quiz=obj)
                    if action == 'preview':
                        preview, status = True, 200
                    elif _confirm(form):
                        saved, changed = authoring.save_lesson_quiz(actor=request.user, course_id=course.pk,
                            lesson_id=lesson.pk, quiz_id=quiz_id, data=form.cleaned_data,
                            questions=questions.payload(), expected_revision=revision, request=request)
                        _saved(request, draft_scope(request, course.pk, lesson.pk,
                            kind=f'quiz:{obj.pk if obj else "new"}'))
                        messages.success(request, 'Test saqlandi.' if changed else 'Test allaqachon shu holatda saqlangan.')
                        return redirect(_urls(course, lesson, 'quiz', saved)['editor_url'])
                except (authoring.AuthoringConflict, authoring.PracticeInUse,
                        authoring.PracticeUnsupported, authoring.PracticeUnavailable) as error:
                    _errors(form, error, questions)
                    status = 409
                except ValidationError as error:
                    _errors(form, error, questions)
                except (Quiz.DoesNotExist, Course.DoesNotExist, Lesson.DoesNotExist):
                    raise Http404
        else:
            _errors(form, ValidationError('Amalni qayta tanlang. Hech narsa saqlanmadi.'))
            status = 400
        form.preserve_invalid_numbers()
    if block_reason and obj:
        preview_data = {'title': obj.title, 'xp_reward': obj.xp_reward}
        preview_questions = [{'text': row['text'], 'choices': row['choices']} for row in quiz_initial(obj)]
    preview_questions = [{**question, 'preview_text': _preview_html(question['text'])}
                         for question in preview_questions]
    context = _base_context(request, course, lesson, 'quiz', obj, form, revision, block_reason, status)
    for row in questions.rows:
        row['has_errors'] = bool(row['form'].errors or any(choice['form'].errors for choice in row['choices']))
        row['open'] = (row['has_errors'] or (data is None and row['index'] == 0)
            or (action == 'add_question' and row['index'] == len(questions.rows) - 1)
            or action in {f'add_choice:{row["index"]}', f'remove_question:{row["index"]}'}
            or action.startswith(f'remove_choice:{row["index"]}:'))
    context['has_errors'] = context['has_errors'] or any(row['has_errors'] for row in questions.rows)
    context.update(page_title='Testni tayyorlash' if obj else 'Yangi test', show_preview=preview,
        questions=questions.rows, question_media=questions.media, preview_questions=preview_questions,
        shape_error=bool(parse_error), raw_recovery=raw_recovery,
        preview_title=(preview_data or {}).get('title', ''), preview_xp=(preview_data or {}).get('xp_reward', 0))
    return _render(request, 'practice_form', context, status)
