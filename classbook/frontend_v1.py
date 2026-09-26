"""Frozen preparation presentation and write guards; no grading/delivery policy."""
import json
import uuid

from django import forms
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.cache import patch_cache_control
from django.utils.crypto import constant_time_compare, salted_hmac

from core.flags import flag_enabled
from core.frontend_v1 import teacher_v1_navigation
from .models import Exercise


FLAG = 'frontend_v1_classbook_preparation'
MARKER = 'frontend_v1_classbook'


def enabled(request):
    return flag_enabled(FLAG) or request.POST.get(MARKER) == '1'


def model_state(item):
    if not item or not item.pk:
        return None
    return {field.attname: str(field.value_from_object(item)) for field in item._meta.concrete_fields}


def preparation_state(item, cohort, lesson):
    return [cohort.pk, cohort.course_id, cohort.is_active, cohort.telegram_chat_id, lesson.pk,
            list(item.exercise_steps.order_by('order', 'pk').values_list('pk', 'order', 'exercise_id', 'teacher_note')) if item.pk else [],
            [model_state(e) for e in Exercise.objects.filter(playbook_steps__playbook=item).order_by('pk')] if item.pk else []]


def revision(user, action, item=None, *, cohort=None, lesson=None, creation_key='', prepared=None):
    state = [user.pk, action, model_state(item), creation_key]
    if cohort:
        state += prepared if prepared is not None else preparation_state(item, cohort, lesson)
        if action == 'start':
            from bot.models import TelegramLessonSession
            sessions = TelegramLessonSession.objects.filter(cohort=cohort)
            state += [sessions.order_by('-pk').values_list('pk', 'status').first(),
                      list(sessions.filter(status='open').values_list('pk', 'lesson_id', 'status'))]
    return salted_hmac('frontend-v1-classbook-preparation', json.dumps(state, sort_keys=True, default=str), algorithm='sha256').hexdigest()


def write_error(request, action, item=None, **scope):
    if not enabled(request):
        return None
    if not flag_enabled(FLAG):
        return 'Yangi muharrir o‘chirilgan. Hech narsa saqlanmadi; sahifani qayta oching.', 400
    if not constant_time_compare(request.POST.get('revision', ''), revision(request.user, action, item, **scope)):
        return 'Saqlangan ma’lumot o‘zgargan yoki forma eskirgan. Hech narsa saqlanmadi. Matningizni olib, joriy holatni qayta oching.', 409
    if request.POST.get('confirm_scope') != 'yes':
        return 'Amal doirasini tasdiqlang. Hech narsa saqlanmadi.', 400
    return None


class PrivateMediaInput(forms.ClearableFileInput):
    template_name = 'frontend_v1/classbook/file.html'

    def is_initial(self, value):
        # Private storage intentionally has no public URL.
        return bool(value)

    def render(self, name, value, attrs=None, renderer=None):
        # Project templates aren't in the isolated default form renderer.
        return render_to_string(self.template_name, self.get_context(name, value, attrs))


def style_form(form):
    if 'media' in form.fields:
        form.fields['media'].widget = PrivateMediaInput()
    labels = {'course': 'Kurs', 'lesson': 'Dars (ixtiyoriy)', 'title': 'Nomi', 'kind': 'Turi',
              'prompt': 'Savol matni', 'instructions': 'Ko‘rsatma', 'explanation': 'Izoh',
              'media': 'Media fayl', 'media_kind': 'Media turi', 'time_limit_seconds': 'Vaqt (soniya)',
              'max_points': 'Maksimal ball', 'speed_bonus_percent': 'Tezlik bonusi (%)',
              'status': 'Playbook holati', 'opening_message': 'Kirish xabari',
              'materials_message': 'Material xabari', 'homework_message': 'Uyga vazifa xabari',
              'late_after_minutes': 'Kechikish chegarasi (daqiqa)',
              'auto_release_lesson': 'Dars yakunida darsni avtomatik ochish',
              'announce_names': 'Davomat ismlarini Telegram guruhda e’lon qilish'}
    for name, field in form.fields.items():
        field.label = labels.get(name, field.label)
        # Validation may have already cached BoundFields with legacy labels.
        form[name].label = field.label
        if getattr(field.widget, 'input_type', None) != 'checkbox':
            field.widget.attrs['class'] = 'c-field'
    return form


def render_page(request, page, context, status=200):
    if not enabled(request):
        return render(request, f'classbook/{page}.html', context, status=status)
    context.update(teacher_v1_navigation('teacher_dashboard'))
    context.update(active_nav='classbook:teacher_home', frontend_v1_title='Classbook')
    if 'form' in context:
        style_form(context['form'])
    response = render(request, f'frontend_v1/classbook/{page}.html', context, status=status)
    patch_cache_control(response, private=True, no_store=True)
    return response


def conflict(request, error, cohort, lesson):
    return render_page(request, 'conflict', {
        'error': error[0], 'reload_url': reverse('classbook:playbook_edit', args=[cohort.pk, lesson.pk]),
    }, status=error[1])


def exercise_context(request, exercise):
    key = request.POST.get('creation_key', '') if request.method == 'POST' else str(uuid.uuid4())
    token = request.POST.get('revision', '') if request.method == 'POST' else revision(
        request.user, 'exercise', exercise, creation_key=key if not exercise else '')
    return {'creation_key': key, 'revision': token}


def playbook_context(request, playbook, cohort, lesson, steps):
    scope = {'cohort': cohort, 'lesson': lesson, 'prepared': preparation_state(playbook, cohort, lesson)}
    for step in steps:
        for action in ('up', 'down', 'remove'):
            setattr(step, f'{action}_revision', revision(request.user, f'{action}:{step.pk}', playbook, **scope))
    from bot.models import TelegramLessonSession
    return {
        'revision': request.POST.get('revision', '') if request.method == 'POST' else revision(request.user, 'save', playbook, **scope),
        'add_revision': revision(request.user, 'add', playbook, **scope),
        'start_revision': revision(request.user, 'start', playbook, **scope),
        'existing_session': TelegramLessonSession.objects.filter(cohort=cohort, status='open').first(),
    }
