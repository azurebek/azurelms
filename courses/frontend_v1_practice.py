"""Presentation and native-form adapters; submission_service owns all writes."""
from django.http import Http404
from django.shortcuts import render
from django.utils.cache import patch_cache_control
from django.utils.crypto import salted_hmac

from cohorts.models import Enrollment, enrollment_active_access_q
from .access_service import check_lesson_access


def practice_enrollment(request, course_id):
    qs = Enrollment.objects.filter(
        enrollment_active_access_q(), student=request.user, cohort__course_id=course_id
    ).select_related('cohort')
    if 'cohort' in request.GET:
        from .submission_service import _positive_id
        cohort_id = _positive_id(request.GET.get('cohort'))
        if cohort_id is None:
            raise Http404
        qs = qs.filter(cohort_id=cohort_id)
    enrollment = qs.order_by('-joined_at', '-pk').first()
    if enrollment is None:
        raise Http404
    return enrollment


def decorate_practice(context, request):
    # Not a session credential: HMAC separates browser drafts after a login
    # session/account change without exposing the session key to the DOM.
    context['practice_scope'] = salted_hmac(
        'frontend-v1-practice', f'{request.user.pk}:{request.session.session_key}'
    ).hexdigest()
    bound = context.get('practice_bound', {})
    for assignment in context['assignments']:
        submission = assignment.current_submission
        assignment.form_answer = submission.answer_text if submission else ''
        assignment.form_revision = submission.updated_at.isoformat() if submission else 'new'
        assignment.form_bound = bound.get('kind') == 'assignment' and bound.get('id') == assignment.pk
        if assignment.form_bound:
            assignment.form_answer = bound.get('answer_text', '')
        if submission and submission.attachment:
            assignment.file_name = submission.attachment.name.rsplit('/', 1)[-1]
    for quiz in context['quizzes']:
        quiz.latest_attempt = context['quiz_attempts'].get(quiz.pk)
        quiz.form_revision = str(quiz.latest_attempt.pk) if quiz.latest_attempt else 'new'
        quiz.form_bound = bound.get('kind') == 'quiz' and bound.get('id') == quiz.pk
        posted = bound.get('answers', {}) if quiz.form_bound else {}
        quiz.form_questions = list(quiz.questions.all())
        answers = {a.question_id: a for a in quiz.latest_attempt.answers.select_related('selected_choice')} if quiz.latest_attempt else {}
        for question in quiz.form_questions:
            question.form_choices = list(question.choices.all())
            for choice in question.form_choices:
                choice.form_selected = str(choice.pk) == str(posted.get(str(question.pk), ''))
            question.last_answer = answers.get(question.pk)
            # Correct choices are rendered only in the persisted result section.
            question.correct_choice = next((c for c in question.form_choices if c.is_correct), None)


def form_error(request, *, lesson, enrollment, kind, record_id, message, answers=None, answer_text=''):
    """Keep a bound form on validation failure, never expose locked content."""
    access = check_lesson_access(user=request.user, lesson=lesson, enrollment=enrollment)
    if not access.is_allowed:
        response = render(request, 'frontend_v1/practice_unavailable.html', {
            'frontend_v1_title': 'Darsga kirish yopilgan', 'practice_error': access.message,
            'answer_text': answer_text, 'lesson': lesson, 'cohort_id': enrollment.cohort_id,
        }, status=403)
        patch_cache_control(response, private=True, no_store=True)
        return response
    from .views import LessonDetailView
    view = LessonDetailView()
    view.setup(request, course_id=lesson.module.course_id, lesson_id=lesson.pk)
    view.object = lesson
    view._active_enrollment = enrollment
    context = view.get_context_data(
        practice_bound=dict(kind=kind, id=record_id, answers=answers or {}, answer_text=answer_text),
        practice_error=message,
    )
    context['default_study_tab'] = 'homework' if kind == 'assignment' else 'quiz'
    return view.render_to_response(context, status=400)
