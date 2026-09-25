"""Teacher review presentation/forms; canonical submission_service owns writes."""
from urllib.parse import urlencode

from django import forms
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.crypto import salted_hmac

from courses.models import AssignmentSubmission, ExamAttempt
from courses.submission_service import _positive_id


def queue_status(value):
    return value if value in ('pending', 'reviewed', 'all') else 'pending'


def queue_context(request, context):
    courses = context['teacher_courses']
    course = None
    if request.GET.get('course'):
        course = get_object_or_404(courses, pk=_positive_id(request.GET['course']))
        courses = courses.filter(pk=course.pk)
    assignments = AssignmentSubmission.objects.filter(
        assignment__lesson__module__course__in=courses
    ).select_related('student', 'assignment__lesson__module__course')
    exams = ExamAttempt.objects.filter(exam__course__in=courses, is_completed=True).select_related('student', 'exam__course')
    status = queue_status(request.GET.get('status'))
    filters = []
    for key, label in (('pending', 'Kutilmoqda'), ('reviewed', 'Tekshirilgan'), ('all', 'Barchasi')):
        params = {'status': key}
        if course:
            params['course'] = course.pk
        filters.append(dict(id=key, label=label, url='?' + urlencode(params)))
    if status == 'pending':
        assignments = assignments.filter(status=AssignmentSubmission.STATUS_PENDING)
        exams = exams.filter(is_reviewed=False)
    elif status == 'reviewed':
        assignments = assignments.exclude(status=AssignmentSubmission.STATUS_PENDING)
        exams = exams.filter(is_reviewed=True)
    assignment_page = Paginator(assignments.order_by('submitted_at', 'pk'), 25).get_page(request.GET.get('assignments_page'))
    exam_page = Paginator(exams.order_by('completed_time', 'pk'), 25).get_page(request.GET.get('exams_page'))
    # Build links from allowlisted state, not arbitrary next/return URLs.
    params = {'return_status': status}
    if course:
        params['course'] = course.pk
    params['assignments_page'] = assignment_page.number
    params['exams_page'] = exam_page.number
    context.update(queue_filter=status, queue_filters=filters, selected_course=course,
                   assignment_page=assignment_page, exam_page=exam_page, review_query=urlencode(params))


def return_query(request):
    params = {'status': queue_status(request.GET.get('return_status'))}
    for key in ('course', 'assignments_page', 'exams_page'):
        value = _positive_id(request.GET.get(key))
        if value:
            params[key] = value
    return urlencode(params)


class AssignmentReviewForm(forms.Form):
    action = forms.ChoiceField(label='Qaror', choices=(('', 'Qarorni tanlang'), ('approve', 'Tasdiqlash'), ('revision', 'Qayta ishlashga qaytarish')))
    teacher_feedback = forms.CharField(label='O‘quvchiga izoh', required=False, strip=False, widget=forms.Textarea(attrs={'rows': 6}))
    awarded_xp = forms.IntegerField(label='XP', min_value=0)
    revision = forms.CharField(widget=forms.HiddenInput)
    confirm_review = forms.BooleanField(label='Joriy ishni o‘qidim. Qaror, izoh va XP o‘quvchiga qo‘llanishini tasdiqlayman.')

    def __init__(self, *args, submission, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['awarded_xp'].max_value = submission.assignment.max_xp
        from django.core.validators import MaxValueValidator
        self.fields['awarded_xp'].validators.append(MaxValueValidator(submission.assignment.max_xp))
        self.fields['awarded_xp'].widget.attrs['max'] = submission.assignment.max_xp
        self.fields['awarded_xp'].label = f'XP (0–{submission.assignment.max_xp})'
        for name in ('action', 'teacher_feedback', 'awarded_xp'):
            self.fields[name].widget.attrs.update({'class': 'c-field', 'data-draft-field': '', 'aria-describedby': 'review-errors'})
        self.fields['action'].widget.attrs['data-draft-saved'] = {'approved': 'approve', 'needs_revision': 'revision'}.get(submission.status, '')
        self.fields['teacher_feedback'].widget.attrs['data-draft-saved'] = submission.teacher_feedback
        self.fields['awarded_xp'].widget.attrs['data-draft-saved'] = str(submission.awarded_xp)


def review_context(request, context, submission, form):
    # A one-shot native POST/redirect flash reconciles raw inputs that the
    # canonical service normalizes (e.g. revision always awards zero XP).
    # It never substitutes for the persisted result shown on the page.
    receipt = request.session.get('frontend_v1_review_saved')
    if request.method == 'GET' and receipt and receipt['submission_id'] == submission.pk:
        request.session.pop('frontend_v1_review_saved')
        if receipt['revision'] == submission.updated_at.isoformat():
            for name, value in receipt['values'].items():
                form.fields[name].widget.attrs['data-draft-saved'] = value
            context['review_ack'] = True
    context.update(
        submission=submission, review_form=form,
        practice_scope=salted_hmac('frontend-v1-practice', f'{request.user.pk}:{request.session.session_key}').hexdigest(),
        revision=submission.updated_at.isoformat(),
        queue_url=reverse('teacher_grading') + '?' + return_query(request),
    )
