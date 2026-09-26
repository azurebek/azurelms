"""I8c presentation/validation; teacher_grade_exam remains the sole web writer."""
import json
from decimal import Decimal

from django import forms
from django.db.models import Q
from django.urls import reverse
from django.utils.crypto import constant_time_compare, salted_hmac

from core.frontend_v1 import render_teacher_v1
from core.frontend_v1_review import return_query
from courses.models import Choice, Question, ReadingItem, ReadingOption, ReadingTask


def review_snapshot(user, attempt):
    # Values + canonical POST counter: covers legacy draft/admin publication,
    # same-clock/no-op replay, rubric and submitted-answer changes. Direct ORM
    # writers are not promised a global monotonic review revision.
    state = {
        'user': user.pk,
        'attempt': [attempt.pk, attempt.review_revision, attempt.input_revision,
                    attempt.review_notes, attempt.is_completed, attempt.is_reviewed,
                    attempt.reviewed_at, attempt.score],
        'exam': [attempt.exam_id, attempt.exam.title, attempt.exam.passing_score],
        'sections': list(attempt.exam.sections.order_by('pk').values()),
        'questions': list(Question.objects.filter(exam_section__exam=attempt.exam).order_by('pk').values()),
        'choices': list(Choice.objects.filter(question__exam_section__exam=attempt.exam).order_by('pk').values()),
        'reading_tasks': list(ReadingTask.objects.filter(section__exam=attempt.exam).order_by('pk').values()),
        'reading_items': list(ReadingItem.objects.filter(task__section__exam=attempt.exam).order_by('pk').values()),
        'reading_options': list(ReadingOption.objects.filter(
            Q(item__task__section__exam=attempt.exam) | Q(task__section__exam=attempt.exam)
        ).order_by('pk').values()),
        'answers': list(attempt.answers.order_by('pk').values()),
        'reading': list(attempt.reading_responses.order_by('pk').values()),
        'reviews': list(attempt.section_reviews.order_by('pk').values()),
    }
    return salted_hmac('frontend-v1-exam-review', json.dumps(state, sort_keys=True, default=str)).hexdigest()


class ExamReviewForm(forms.Form):
    revision = forms.CharField(widget=forms.HiddenInput)
    action = forms.ChoiceField(choices=[('save', 'save'), ('finalize', 'finalize')], widget=forms.HiddenInput)
    confirm_scope = forms.BooleanField(label='Joriy saqlangan holatni o‘qidim va ushbu amalni tasdiqlayman.')

    def __init__(self, *args, attempt, publish=False, **kwargs):
        super().__init__(*args, **kwargs)
        if publish:
            return
        reviews = {r.section_id: r for r in attempt.section_reviews.all()}
        for section in attempt.exam.sections.order_by('order', 'pk'):
            review = reviews.get(section.pk)
            self.add_score(f'score_{section.pk}', f'{section.title}: bo‘lim bali',
                           section.max_score, review.awarded_score if review else 0)
            self.add_text(f'feedback_{section.pk}', f'{section.title}: bo‘lim izohi', review.feedback if review else '')
        for answer in attempt.answers.select_related('question__exam_section').order_by('pk'):
            if not answer.question.exam_section_id or answer.question.exam_section.section_type not in ('writing', 'speaking'):
                continue
            self.add_score(f'answer_score_{answer.pk}', 'Javob bali', answer.question.points, answer.awarded_score)
            self.add_text(f'answer_feedback_{answer.pk}', 'Javob izohi', answer.grader_feedback)
        self.add_text('review_notes', 'Yakuniy izoh', attempt.review_notes)

    def add_score(self, name, label, maximum, value):
        self.fields[name] = forms.DecimalField(
            label=f'{label} (0–{maximum})', min_value=0, max_value=maximum,
            decimal_places=2, max_digits=6, initial=value,
            widget=forms.NumberInput(attrs={'class': 'c-field', 'step': '0.01'}),
        )

    def add_text(self, name, label, value):
        self.fields[name] = forms.CharField(label=label, required=False, strip=False, initial=value,
                                          widget=forms.Textarea(attrs={'class': 'c-field', 'rows': 3}))


def prepare_review(request, context, attempt):
    """Return normalized canonical payload or a read-only/error response.

    Caller holds attempt row lock for POST and owns the complete transaction.
    GET does not create section reviews. Finalize only uses the saved values,
    never whatever happens to be typed into the independent draft form.
    """
    revision = review_snapshot(request.user, attempt)
    section_ids = set(attempt.exam.sections.values_list('pk', flat=True))
    saved_section_ids = set(attempt.section_reviews.values_list('section_id', flat=True))
    publish_ready = bool(section_ids) and section_ids.issubset(saved_section_ids)
    data = request.POST.copy() if request.method == 'POST' else None
    publishing = bool(data is not None and data.get('action') == 'finalize')
    form = ExamReviewForm(data, attempt=attempt, publish=publishing,
                          initial={'revision': revision, 'action': 'save'})
    status = 200
    if data is not None:
        status = 400
        valid = form.is_valid()
        if publishing and not publish_ready:
            form.add_error(None, 'Har bir bo‘lim bali avval qoralamada saqlanishi kerak. Hali saqlanmagan bo‘lim bor yoki imtihon bo‘sh; natija e’lon qilinmadi.')
            valid = False
        if not constant_time_compare(data.get('revision', ''), revision):
            status = 409
            form.add_error(None, 'Saqlangan holat o‘zgargan. Qoralamangiz quyida qoldi. Joriy ball va izohlarni solishtiring, so‘ng qayta tasdiqlang.')
        elif valid:
            if publishing:
                return {'action': 'finalize'}, None
            attempt.ensure_section_reviews()
            payload = dict(form.cleaned_data)
            for review in attempt.section_reviews.all():
                payload[f'section_score_{review.pk}'] = payload.pop(f'score_{review.section_id}')
                payload[f'section_feedback_{review.pk}'] = payload.pop(f'feedback_{review.section_id}')
            return payload, None
        form.data = form.data.copy()
        form.data['revision'] = revision
        form.data.pop('confirm_scope', None)

    errors = form.errors if data is not None else {}
    publish_form = form if publishing else ExamReviewForm(
        attempt=attempt, publish=True, prefix=None,
        initial={'revision': revision, 'action': 'finalize'}, auto_id='publish_%s',
    )
    if publishing:
        form = ExamReviewForm(attempt=attempt, initial={'revision': revision, 'action': 'save'})
        publish_form.auto_id = 'publish_%s'
    reviews = {r.section_id: r for r in attempt.section_reviews.all()}
    sections = []
    answers = list(attempt.answers.select_related('question__exam_section', 'selected_choice').order_by('question_id', 'pk'))
    reading = list(attempt.reading_responses.select_related('item__task', 'selected_option').order_by('item__order', 'pk'))
    for response in reading:
        # IDs may be obsolete; never resolve options outside this exam task.
        options = ReadingOption.objects.filter(pk__in=response.selected_option_ids).filter(
            Q(item__task=response.item.task) | Q(task=response.item.task)
        ) if response.selected_option_ids else []
        response.selected_text = ', '.join(o.text for o in options)
    for section in attempt.exam.sections.order_by('order', 'pk'):
        rows = []
        for answer in answers:
            if answer.question.exam_section_id != section.pk:
                continue
            manual = section.section_type in ('writing', 'speaking')
            rows.append(dict(answer=answer,
                             score=form[f'answer_score_{answer.pk}'] if manual else None,
                             feedback=form[f'answer_feedback_{answer.pk}'] if manual else None))
        sections.append(dict(section=section, review=reviews.get(section.pk), answers=rows,
                             reading=[r for r in reading if r.item.task.section_id == section.pk],
                             score=form[f'score_{section.pk}'], feedback=form[f'feedback_{section.pk}']))
    context.update(attempt=attempt, review_form=form, publish_form=publish_form,
                   publish_ready=publish_ready,
                   review_errors=errors, sections=sections,
                   saved_total=sum((r.awarded_score for r in reviews.values()), Decimal(0)),
                   exam_max=sum(s.max_score for s in attempt.exam.sections.all()),
                   queue_url=reverse('teacher_grading') + '?' + return_query(request))
    return None, render_teacher_v1(request, 'teacher/grade_exam.html', context, enabled=True, status=status)
