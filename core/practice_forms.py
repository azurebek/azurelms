"""Bound, lossless forms for the small lesson practice authoring adapter."""
from copy import deepcopy
import re

from django import forms
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorDict

from core.workspace_forms import rich_widget


# Request parsing guards, not product limits or learning policy.
MAX_PARSED_QUESTIONS = 100
MAX_PARSED_CHOICES = 20
MAX_PARSED_FIELDS = 900


class PracticeForm(forms.Form):
    title = forms.CharField(max_length=200, label='Nomi')
    confirm_impact = forms.BooleanField(required=False,
        label='Saqlangan o‘zgarishlar shu darsda amalda bo‘lishini tushundim')

    def preserve_invalid_numbers(self):
        if self.is_bound:
            for name, field in self.fields.items():
                if isinstance(field, forms.IntegerField):
                    try:
                        field.clean(self[name].value())
                    except ValidationError:
                        field.widget = forms.TextInput(attrs={'inputmode': 'numeric'})


class AssignmentPracticeForm(PracticeForm):
    description = forms.CharField(label='Topshiriq sharti', widget=rich_widget())
    max_xp = forms.IntegerField(label='Eng ko‘p beriladigan ball', min_value=0,
        max_value=2147483647, initial=50,
        help_text='O‘quvchining ishini tekshirganda shu miqdorgacha ball beriladi.')


class QuizPracticeForm(PracticeForm):
    xp_reward = forms.IntegerField(label='Test uchun rag‘bat balli', min_value=0,
        max_value=2147483647, initial=20,
        help_text='Natijaga mos ball mavjud test qoidasi bo‘yicha hisoblanadi.')


class QuestionPracticeForm(forms.Form):
    id = forms.IntegerField(required=False, min_value=1, widget=forms.HiddenInput)
    text = forms.CharField(label='Savol matni', widget=rich_widget())
    correct = forms.ChoiceField(label='To‘g‘ri javob', widget=forms.RadioSelect,
        error_messages={'required': 'Bitta to‘g‘ri javobni belgilang.',
                        'invalid_choice': 'Mavjud variantlardan bitta to‘g‘ri javobni belgilang.'})


class ChoicePracticeForm(forms.Form):
    id = forms.IntegerField(required=False, min_value=1, widget=forms.HiddenInput)
    text = forms.CharField(label='Javob varianti', max_length=200)


def _count(data, name, minimum, maximum):
    value = data.get(name, '')
    if not re.fullmatch(r'[0-9]{1,3}', value) or not minimum <= int(value) <= maximum:
        raise ValidationError('Savollar ro‘yxati to‘liq kelmadi. Yozganlaringizni olib, sahifani qayta oching.')
    return int(value)


def quiz_initial(quiz):
    if quiz is None:
        return [{'id': '', 'text': '', 'choices': [{'id': '', 'text': ''}, {'id': '', 'text': ''}], 'correct': ''}]
    result = []
    for question in quiz.questions.prefetch_related('choices').order_by('pk'):
        choices = list(question.choices.order_by('pk'))
        correct = [str(index) for index, choice in enumerate(choices) if choice.is_correct]
        result.append({'id': question.pk, 'text': question.text,
            'choices': [{'id': choice.pk, 'text': choice.text} for choice in choices],
            'correct': correct[0] if len(correct) == 1 else ''})
    return result


def posted_questions(data, *, recover=False):
    if recover:
        indices = [int(match.group(1)) for name in data
                   if (match := re.match(r'^questions-([0-9]{1,3})-', name))
                   and int(match.group(1)) < MAX_PARSED_QUESTIONS]
        count = max(indices, default=0) + 1
    else:
        count = _count(data, 'questions-TOTAL_FORMS', 1, MAX_PARSED_QUESTIONS)
    rows = []
    for index in range(count):
        prefix = f'questions-{index}'
        if recover:
            indices = [int(match.group(1)) for name in data
                       if (match := re.match(rf'^{prefix}-choices-([0-9]{{1,3}})-', name))
                       and int(match.group(1)) < MAX_PARSED_CHOICES]
            choices_count = max(2, max(indices, default=1) + 1)
        else:
            choices_count = _count(data, f'{prefix}-choices-TOTAL_FORMS', 2, MAX_PARSED_CHOICES)
        rows.append({'id': data.get(f'{prefix}-id', ''), 'text': data.get(f'{prefix}-text', ''),
            'correct': data.get(f'{prefix}-correct', ''), 'choices': [
                {'id': data.get(f'{prefix}-choices-{ci}-id', ''),
                 'text': data.get(f'{prefix}-choices-{ci}-text', '')} for ci in range(choices_count)]})
    if recover:
        return rows
    if quiz_shape_reason(rows):
        raise ValidationError(quiz_shape_reason(rows))
    expected = {'questions-TOTAL_FORMS'}
    for index, row in enumerate(rows):
        prefix = f'questions-{index}'
        expected.update(f'{prefix}-{name}' for name in ('id', 'text', 'correct', 'choices-TOTAL_FORMS'))
        for ci in range(len(row['choices'])):
            expected.update((f'{prefix}-choices-{ci}-id', f'{prefix}-choices-{ci}-text'))
    if any(name.startswith('questions-') and name not in expected for name in data):
        raise ValidationError('Savollar ro‘yxati mos kelmadi. Hech narsa saqlanmadi.')
    return rows


def question_data(rows):
    """Reindex a structural edit without losing typed values or object identities."""
    data = {'questions-TOTAL_FORMS': str(len(rows))}
    for index, row in enumerate(rows):
        prefix = f'questions-{index}'
        data.update({f'{prefix}-id': row['id'], f'{prefix}-text': row['text'],
                     f'{prefix}-correct': row['correct'],
                     f'{prefix}-choices-TOTAL_FORMS': str(len(row['choices']))})
        for ci, choice in enumerate(row['choices']):
            data.update({f'{prefix}-choices-{ci}-id': choice['id'], f'{prefix}-choices-{ci}-text': choice['text']})
    return data


def quiz_shape_reason(rows):
    if (len(rows) > MAX_PARSED_QUESTIONS
            or any(len(row['choices']) > MAX_PARSED_CHOICES for row in rows)
            or 1 + sum(4 + 2 * len(row['choices']) for row in rows) > MAX_PARSED_FIELDS):
        return 'Bu test shakl uchun juda katta. Asl nusxa o‘zgarmaydi; yangi kichikroq test tayyorlang.'
    return ''


def change_questions(rows, action):
    edited = deepcopy(rows)
    _change_questions(edited, action)
    if quiz_shape_reason(edited):
        raise ValidationError(quiz_shape_reason(edited))
    rows[:] = edited


def _change_questions(rows, action):
    if action == 'add_question':
        if len(rows) >= MAX_PARSED_QUESTIONS:
            raise ValidationError('Bu shaklda savollar soni juda ko‘p. Avval mavjud savollarni yakunlang.')
        rows.extend(quiz_initial(None))
        return
    match = re.fullmatch(r'(add_choice|remove_question|remove_choice):([0-9]{1,3})(?::([0-9]{1,3}))?', action)
    if not match:
        raise ValidationError('Amalni qayta tanlang. Hech narsa saqlanmadi.')
    kind, qi, ci = match.groups()
    qi = int(qi)
    if qi >= len(rows) or (kind == 'remove_choice') != (ci is not None):
        raise ValidationError('Savol yoki javob varianti topilmadi.')
    if kind == 'remove_question':
        if len(rows) <= 1:
            raise ValidationError('Testda kamida bitta savol bo‘lsin.')
        rows.pop(qi)
    elif kind == 'add_choice':
        if len(rows[qi]['choices']) >= MAX_PARSED_CHOICES:
            raise ValidationError('Bu savolda variantlar juda ko‘p. Avval mavjud variantlarni yakunlang.')
        rows[qi]['choices'].append({'id': '', 'text': ''})
    else:
        ci = int(ci)
        if ci >= len(rows[qi]['choices']):
            raise ValidationError('Javob varianti topilmadi.')
        if len(rows[qi]['choices']) <= 2:
            raise ValidationError('Savolda kamida ikkita javob varianti bo‘lsin.')
        rows[qi]['choices'].pop(ci)
        selected = rows[qi]['correct']
        if selected.isascii() and selected.isdecimal():
            rows[qi]['correct'] = '' if int(selected) == ci else str(int(selected) - (int(selected) > ci))


class QuizQuestionForms:
    def __init__(self, rows, *, bound=False, quiet=False):
        self.rows = []
        data = question_data(rows) if bound else None
        for index, row in enumerate(rows):
            prefix = f'questions-{index}'
            form = QuestionPracticeForm(data=data, initial=row, prefix=prefix)
            form.fields['correct'].choices = [(str(ci), str(ci + 1)) for ci in range(len(row['choices']))]
            choices = []
            for ci, choice in enumerate(row['choices']):
                choice_form = ChoicePracticeForm(data=data, initial=choice, prefix=f'{prefix}-choices-{ci}')
                if quiet:
                    choice_form._errors = ErrorDict()
                choices.append({'form': choice_form, 'index': ci, 'number': ci + 1,
                    'selected': str(row['correct']) == str(ci), 'correct_id': f'id_{prefix}-correct-{ci}'})
            if quiet:
                form._errors = ErrorDict()
            self.rows.append({'form': form, 'choices': choices, 'index': index, 'number': index + 1,
                              'choice_count_name': f'{prefix}-choices-TOTAL_FORMS'})

    @property
    def media(self):
        result = forms.Media()
        for row in self.rows:
            result += row['form'].media
        return result

    def is_valid(self):
        return all([form.is_valid() for row in self.rows
                    for form in [row['form'], *[choice['form'] for choice in row['choices']]]])

    def payload(self):
        return [{'id': row['form'].cleaned_data['id'], 'text': row['form'].cleaned_data['text'],
                 'choices': [{'id': choice['form'].cleaned_data['id'],
                              'text': choice['form'].cleaned_data['text'],
                              'is_correct': row['form'].cleaned_data['correct'] == str(choice['index'])}
                             for choice in row['choices']]} for row in self.rows]

    def add_error(self, key, values):
        for row in self.rows:
            for form in [row['form'], *[choice['form'] for choice in row['choices']]]:
                for name in form.fields:
                    if key == form.add_prefix(name):
                        form.add_error(name, values)
                        return True
        return False
