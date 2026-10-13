"""Session-only opened work; live permissions and labels remain authoritative.

Only successful page GETs record an entry. Search text, contacts, URLs, form
contents and tokens never enter this state. Reading it does not write state.
"""
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.urls import reverse

from core.access import teacher_course_queryset
from core.flags import flag_enabled
from core.student_support_service import support_student_queryset
from courses.models import Lesson, Module

SESSION_KEY = 'backoffice_recent_v1'
# A bounded UI list, not a configurable business policy or retention duration.
MAX_ITEMS = 3
NAV_FLAG = 'backoffice_unified_navigation'


def _actor(request):
    actor = getattr(request, 'user', None)
    if not getattr(actor, 'is_authenticated', False) or not actor.pk:
        return None
    actor = get_user_model().objects.only('pk', 'is_active', 'is_staff', 'is_superuser').filter(pk=actor.pk, is_active=True).first()
    return actor if actor and (actor.is_staff or actor.is_superuser) else None


def _positive(value):
    if type(value) is int:
        return value if 0 < value < 10 ** 18 else None
    if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 18:
        number = int(value)
        return number if number > 0 else None
    return None


def _entry(value):
    if not isinstance(value, dict):
        return None
    kind = value.get('kind')
    if not isinstance(kind, str):
        return None
    required, optional = {
        'course': ({'course_id'}, {'lesson_id', 'module_id', 'view'}),
        'student': ({'student_id'}, {'course_id', 'lesson_id', 'filter_course_id', 'page', 'topic',
                                   'result_kind', 'delivery_filter', 'assignment_page', 'quiz_page', 'exam_page', 'delivery_page'}),
        'design': (set(), set()),
    }.get(kind, (None, None))
    if required is None or set(value) - {'kind'} - required - optional or not required <= set(value):
        return None
    result = {'kind': kind}
    for key in required | optional:
        if key not in value or value[key] in (None, ''):
            if key in required:
                return None
            continue
        if key in {'topic', 'result_kind', 'delivery_filter'}:
            allowed = {'topic': {'access', 'results', 'delivery'}, 'result_kind': {'assignments', 'quizzes', 'exams'},
                       'delivery_filter': {'all', 'failed'}}[key]
            if not isinstance(value[key], str) or value[key] not in allowed:
                return None
            result[key] = value[key]
        elif key == 'view':
            if value[key] != 'preview':
                return None
            result[key] = 'preview'
        else:
            number = _positive(value[key])
            if number is None:
                if key == 'page':
                    continue
                return None
            result[key] = number
    if result.get('lesson_id') and (not result.get('course_id') or result.get('module_id')):
        return None
    return result


def _items(request, actor):
    state = request.session.get(SESSION_KEY)
    if not isinstance(state, dict) or type(state.get('actor_id')) is not int or state['actor_id'] != actor.pk:
        return []
    values = state.get('items')
    if not isinstance(values, list) or len(values) > MAX_ITEMS:
        return []
    return [item for value in values if (item := _entry(value)) is not None]


def _identity(item):
    if item['kind'] == 'student':
        return ('student', item['student_id'])
    return (item['kind'], item.get('course_id'), item.get('lesson_id'), item.get('module_id'))


def _project(actor, item, enabled):
    kind = item['kind']
    if kind == 'design':
        if not actor.is_superuser or not enabled['backoffice_design_workspace']:
            return None
        return {'title': 'Ko‘rinishni moslash', 'subtitle': 'Sayt va dizayn',
                'label': 'Dizayn', 'url': reverse('backoffice_design')}
    if not enabled['backoffice_course_workspace' if kind == 'course' else 'backoffice_student_support']:
        return None
    course = None
    if item.get('course_id'):
        course = teacher_course_queryset(actor).only('pk', 'title').filter(pk=item['course_id']).first()
        if course is None:
            return None
    lesson = None
    if item.get('lesson_id'):
        lesson = Lesson.objects.only('pk', 'title').filter(pk=item['lesson_id'], module__course=course).first()
        if lesson is None:
            return None
    if kind == 'course':
        params = {}
        title, subtitle, label = course.title, 'Kurs tuzilmasi', 'Kurs'
        if lesson:
            params['lesson'] = lesson.pk
            title, subtitle, label = lesson.title, course.title, 'Dars'
        elif item.get('module_id'):
            module = Module.objects.only('pk', 'title').filter(pk=item['module_id'], course=course).first()
            if module is None:
                return None
            params.update(module=module.pk, new=1)
            title, subtitle, label = 'Yangi dars', f'{course.title} · {module.title}', 'Dars tayyorlash'
        if item.get('view'):
            params['view'] = item['view']
        url = reverse('backoffice_workspace_course', kwargs={'course_id': course.pk})
    else:
        if item.get('topic') == 'delivery' and not actor.is_superuser:
            return None
        student = support_student_queryset(actor).only('pk', 'first_name', 'last_name', 'username').filter(pk=item['student_id']).first()
        if student is None:
            return None
        params = {key: item[source] for source, key in (
            ('course_id', 'course'), ('lesson_id', 'lesson'),
            ('filter_course_id', 'filter_course'), ('page', 'page'),
            ('topic', 'topic'), ('result_kind', 'result_kind'),
            ('delivery_filter', 'delivery_filter'),
            ('assignment_page', 'assignment_page'), ('quiz_page', 'quiz_page'),
            ('exam_page', 'exam_page'), ('delivery_page', 'delivery_page'),
        ) if source in item}
        if item.get('filter_course_id') and not teacher_course_queryset(actor).filter(pk=item['filter_course_id']).exists():
            return None
        title = student.get_full_name().strip() or student.username
        subtitle = ' · '.join(part for part in (course.title if course else '', lesson.title if lesson else '') if part) or 'O‘quvchiga yordam'
        if item.get('topic') in {'results', 'delivery'}:
            subtitle = ('Topshiriq va natijalar' if item['topic'] == 'results' else 'Bildirishnomalar') + ' · ' + subtitle
        label = 'O‘quvchi'
        url = reverse('backoffice_workspace_student', kwargs={'student_id': student.pk})
    return {'title': title, 'subtitle': subtitle, 'label': label,
            'url': url + ('?' + urlencode(params) if params else '')}


def _flags():
    return {name: flag_enabled(name) for name in (
        'backoffice_course_workspace', 'backoffice_student_support', 'backoffice_design_workspace')}


def recent_work(request):
    """Resolve current titles and scope without rewriting the session on Home."""
    if not flag_enabled(NAV_FLAG):
        return []
    actor = _actor(request)
    if actor is None:
        return []
    items = _items(request, actor)
    if not items:
        return []
    enabled = _flags()
    return [row for item in items if (row := _project(actor, item, enabled)) is not None]


def record_opened(request, response, **descriptor):
    """Called after an authorized page rendered; POST and error responses ignore it."""
    if request.method != 'GET' or response.status_code != 200 or not flag_enabled(NAV_FLAG):
        return response
    actor, item = _actor(request), _entry(descriptor)
    if actor is None or item is None or _project(actor, item, _flags()) is None:
        return response
    items = [item] + [old for old in _items(request, actor) if _identity(old) != _identity(item)]
    state = {'actor_id': actor.pk, 'items': items[:MAX_ITEMS]}
    if request.session.get(SESSION_KEY) != state:
        request.session[SESSION_KEY] = state
    return response
