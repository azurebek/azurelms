"""Signed, session-bound return from an existing decision page to learner help.

This is navigation state only. It neither authorizes a decision nor chooses an
arbitrary destination; action views still load their own scoped target first.
"""
from copy import copy
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils.crypto import constant_time_compare, salted_hmac

from core.access import teacher_course_queryset
from core.backoffice_return import return_context
from core.flags import flag_enabled
from core.student_support_service import support_student_queryset
from courses.models import Lesson

SALT = 'student-support-return-v1'
TOPICS = {'access', 'results', 'delivery'}
PAGE_KEYS = ('page', 'assignment_page', 'quiz_page', 'exam_page', 'delivery_page')
LIST_KEYS = ('q', 'filter_course', 'result_kind', 'delivery_filter', *PAGE_KEYS)
PARAM_KEYS = {'student', 'course', 'lesson', 'topic', 'return_to', *LIST_KEYS}


def _positive(value):
    if isinstance(value, bool):
        raise ValueError
    text = str(value)
    if not text.isascii() or not text.isdecimal() or len(text) > 18 or int(text) < 1:
        raise ValueError
    return int(text)


def _binding(request):
    return salted_hmac(SALT, f'{request.user.pk}:{request.session.session_key}',
                       algorithm='sha256').hexdigest()


def _params(values):
    if not isinstance(values, dict) or set(values) - PARAM_KEYS:
        raise ValueError
    topic = values.get('topic', 'results')
    if not isinstance(topic, str) or topic not in TOPICS:
        raise ValueError
    result = {'student': _positive(values['student']), 'topic': topic}
    result_kind = values.get('result_kind', '')
    if result_kind not in ('', None):
        if not isinstance(result_kind, str) or result_kind not in {'assignments', 'quizzes', 'exams'}:
            raise ValueError
        result['result_kind'] = result_kind
    delivery_filter = values.get('delivery_filter', '')
    if delivery_filter not in ('', None):
        if not isinstance(delivery_filter, str) or delivery_filter not in {'all', 'failed'}:
            raise ValueError
        result['delivery_filter'] = delivery_filter
    for key in ('course', 'lesson', 'filter_course', *PAGE_KEYS):
        if values.get(key) not in (None, ''):
            result[key] = _positive(values[key])
            if key in PAGE_KEYS and result[key] >= 10 ** 8:
                raise ValueError
    if result.get('lesson') and not result.get('course'):
        raise ValueError
    query = values.get('q', '')
    if not isinstance(query, str) or len(query) > 200 or any(ord(c) < 32 for c in query):
        raise ValueError
    if query:
        result['q'] = query
    upstream = values.get('return_to', '')
    if not isinstance(upstream, str) or len(upstream) > 2048:
        raise ValueError
    if upstream:
        result['return_to'] = upstream
    return result


def _scope(request, params):
    """Re-read permissions; a previously signed URL is not an access grant."""
    actor = get_user_model().objects.filter(pk=request.user.pk, is_active=True).first()
    if actor is None or not (actor.is_staff or actor.is_superuser):
        return False
    if params['topic'] == 'delivery' and not actor.is_superuser:
        return False
    if not support_student_queryset(actor).filter(pk=params['student']).exists():
        return False
    courses = teacher_course_queryset(actor)
    for key in ('course', 'filter_course'):
        if params.get(key) and not courses.filter(pk=params[key]).exists():
            return False
    if params.get('lesson') and not Lesson.objects.filter(
            pk=params['lesson'], module__course_id=params['course']).exists():
        return False
    return True


def _upstream(request, token):
    if not token:
        return ''
    probe = copy(request)
    probe.GET = request.GET.copy()
    probe.GET.setlist('return_to', [token])
    probe.__dict__.pop('_workspace_return', None)
    return return_context(probe).get('workspace_return_token', '')


def make_support_return(request, *, student_id, course_id=None, lesson_id=None,
                        topic='results', **pagination):
    if not flag_enabled('backoffice_student_support') or not request.user.is_authenticated:
        return ''
    try:
        if set(pagination) - set(LIST_KEYS):
            return ''
        if any(len(request.GET.getlist(key)) > 1 for key in (*LIST_KEYS, 'return_to')):
            return ''
        values = {key: request.GET.get(key, '') for key in LIST_KEYS}
        values.update(pagination)
        values.update(student=student_id, course=course_id, lesson=lesson_id, topic=topic,
                      return_to=_upstream(request, request.GET.get('return_to', '')))
        params = _params(values)
        if not _scope(request, params):
            return ''
        return signing.dumps({'binding': _binding(request), 'params': params},
                             salt=SALT, compress=True)
    except (ValueError, TypeError, KeyError, PermissionDenied):
        return ''


def support_return_context(request, student_id, course_id=None):
    """Validate against the action's real target before building a local URL."""
    tokens = request.GET.getlist('support_from')
    if (not flag_enabled('backoffice_student_support') or not request.user.is_authenticated
            or len(tokens) != 1 or len(tokens[0]) > 4096):
        return {}
    try:
        data = signing.loads(tokens[0], salt=SALT)
        if (not isinstance(data, dict) or set(data) != {'binding', 'params'}
                or not isinstance(data['binding'], str)
                or not constant_time_compare(data['binding'], _binding(request))):
            return {}
        params = _params(data['params'])
        if params['student'] != _positive(student_id):
            return {}
        if course_id is not None and params.get('course') != _positive(course_id):
            return {}
        if not _scope(request, params):
            return {}
        target = params.pop('student')
        upstream = _upstream(request, params.pop('return_to', ''))
        if upstream:
            params['return_to'] = upstream
        return {
            'support_return_url': reverse('backoffice_workspace_student', args=[target]) + '?' + urlencode(params),
            'support_return_label': 'O‘quvchiga qaytib tekshirish',
        }
    except (signing.BadSignature, ValueError, TypeError, KeyError, AttributeError, PermissionDenied):
        return {}
