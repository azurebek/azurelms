"""Live V1 presentation/transport; canonical services still own all effects."""
import copy
import json
import random

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import patch_cache_control
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.generic.base import ContextMixin

from core.flags import flag_enabled
from core.frontend_v1 import FrontendV1Mixin, teacher_v1_navigation
from .models import LessonPlaybook

FLAG = 'frontend_v1_classbook_live'
MARKER = 'frontend_v1_classbook_live'


def enabled(request):
    return flag_enabled(FLAG) or request.POST.get(MARKER) == '1' or request.headers.get('X-Classbook-V1') == '1'


def digest(value):
    return salted_hmac('classbook-live-v1', json.dumps(value, sort_keys=True, default=str), algorithm='sha256').hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key')
        result[key] = value
    return result


def session_revision(user, session):
    # Response counts do not invalidate a teacher's action. Lifecycle changes do.
    activities = list(session.classbook_activities.order_by('pk').values(
        'id', 'status', 'snapshot', 'opened_at', 'closed_at', 'revealed_at', 'closes_at'))
    settings = LessonPlaybook.objects.filter(cohort_id=session.cohort_id, lesson_id=session.lesson_id).values(
        'edit_revision', 'auto_release_lesson', 'announce_names', 'homework_message').first()
    return digest([user.pk, session.pk, session.status, session.started_at, session.closed_at, activities, settings])


def action_revision(user, session, action, state=None):
    return digest([state or session_revision(user, session), action])


def write_error(request, session, action):
    if not flag_enabled(FLAG):
        return 'Yangi jonli ko‘rinish o‘chirilgan. Amal bajarilmadi.', 400
    if not constant_time_compare(request.POST.get('revision', ''), action_revision(request.user, session, action)):
        return 'Dars holati o‘zgargan. Amal bajarilmadi. Joriy holatni qayta ochib tasdiqlang.', 409
    if request.POST.get('confirm_scope') != 'yes':
        return 'Amalni tasdiqlang. Hech narsa o‘zgarmadi.', 400
    return None


class LearnerContext(FrontendV1Mixin, ContextMixin):
    frontend_v1_flag = FLAG


def render_page(request, page, context, *, teacher=False, status=200):
    if not enabled(request):
        return render(request, f'classbook/{page}.html', context, status=status)
    if teacher:
        context.update(teacher_v1_navigation('teacher_dashboard'))
    else:
        context.update(LearnerContext().get_context_data())
    context.update(frontend_v1_title='Jonli dars', active_nav='classbook:teacher_home' if teacher else 'classbook:live_home', live_teacher=teacher)
    response = render(request, f'frontend_v1/classbook/{page}.html', context, status=status)
    patch_cache_control(response, private=True, no_store=True)
    return response


def conflict(request, error, session):
    return render_page(request, 'live_conflict', {'error': error[0], 'session': session}, teacher=True, status=error[1])


def no_store(data, status=200):
    response = JsonResponse(data, status=status)
    patch_cache_control(response, private=True, no_store=True)
    return response


def answer_revision(user, activity):
    return digest([user.pk, activity.pk, activity.session_id, activity.opened_at, activity.snapshot])


def alias(user, activity, group, value):
    return digest([user.pk, activity.pk, group, str(value)])[:32]


def public_payload(user, activity, payload):
    # Do not expose storage names, author IDs, answer key or sequential pair/order IDs.
    result = {key: copy.deepcopy(payload[key]) for key in ('kind', 'config', 'closes_at', 'activity_id')}
    # The legacy shuffle seed is public. V1's permutation must not let users
    # reconstruct author order (which is itself the ordering/matching answer).
    rng = random.Random(digest(['shuffle', user.pk, activity.pk]))
    for group in ('options', 'right', 'items'):
        if group in result['config']:
            rng.shuffle(result['config'][group])
    if result['kind'] in {'ordering', 'unscramble'}:
        items = result['config']['items']
        if len(items) > 1 and [item['id'] for item in items] == activity.snapshot['answer_key']['order']:
            items.append(items.pop(0))
    if result['kind'] in {'matching', 'ordering', 'unscramble', 'categorization'}:
        for group, items in result['config'].items():
            if isinstance(items, list):
                for item in items:
                    item['id'] = alias(user, activity, group, item['id'])
    result['revision'] = answer_revision(user, activity)
    return result


def decode_answer(user, activity, answer):
    kind = activity.snapshot['kind']
    config = activity.snapshot['config']
    def mappings(group):
        return {alias(user, activity, group, item['id']): item['id'] for item in config[group]}
    if kind in {'ordering', 'unscramble'}:
        table = mappings('items')
        if not isinstance(answer, list):
            raise ValueError('Expected list')
        return [table[key] for key in answer]
    if kind in {'matching', 'categorization'}:
        left, right = ('left', 'right') if kind == 'matching' else ('items', 'categories')
        a, b = mappings(left), mappings(right)
        if not isinstance(answer, dict):
            raise ValueError('Expected mapping')
        return {a[key]: b[value] for key, value in answer.items()}
    return answer


def learner_activities(session):
    # Never return queued definitions or scores from an unrevealed activity.
    return [{'id': a.pk, 'title': a.snapshot.get('title', ''), 'status': a.status,
             'url': reverse('classbook:live_activity' if a.status == 'open' else 'classbook:activity_result', args=[a.pk])}
            for a in session.classbook_activities.filter(status__in=['open', 'revealed']).order_by('order', 'id')]
