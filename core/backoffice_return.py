"""Transient, session-bound list/search return links; never persisted in recent work."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.core import signing
from django.urls import Resolver404, resolve, reverse
from django.utils.crypto import constant_time_compare, salted_hmac

from core.flags import flag_enabled

SALT = 'backoffice-return-v1'
DESTINATIONS = {
    'backoffice_workspace_course', 'backoffice_workspace_course_edit',
    'backoffice_workspace_student', 'backoffice_workspace_assignment_new',
    'backoffice_workspace_assignment_edit', 'backoffice_workspace_quiz_new',
    'backoffice_workspace_quiz_edit',
    'backoffice_exams', 'backoffice_exam_edit',
}


def _binding(request):
    return salted_hmac(SALT, f'{request.user.pk}:{request.session.session_key}',
                       algorithm='sha256').hexdigest()


def _params(source, values):
    query = values.get('q', '')
    if not isinstance(query, str) or len(query) > 200 or any(ord(c) < 32 for c in query):
        raise ValueError
    page = str(values.get('page', 1))
    if not page.isascii() or not page.isdecimal() or len(page) > 8 or int(page) < 1:
        raise ValueError
    result = {'q': query, 'page': int(page)}
    if source == 'search':
        kind = values.get('kind', 'all')
        if kind not in {'all', 'course', 'lesson', 'student', 'section'}:
            raise ValueError
        result['kind'] = kind
    elif source == 'courses':
        status = values.get('status', 'all')
        if status not in {'all', 'active', 'draft'}:
            raise ValueError
        result['status'] = status
    else:
        raise ValueError
    return result


def make_return(request, source, **params):
    if not flag_enabled('backoffice_unified_navigation'):
        return ''
    try:
        params = _params(source, params)
    except ValueError:
        return ''
    return signing.dumps({'binding': _binding(request), 'source': source, 'params': params},
                         salt=SALT, compress=True)


def _read(request):
    if hasattr(request, '_workspace_return'):
        return request._workspace_return
    result = {}
    tokens = request.GET.getlist('return_to')
    if (flag_enabled('backoffice_unified_navigation') and len(tokens) == 1
            and len(tokens[0]) <= 2048 and request.user.is_authenticated):
        try:
            data = signing.loads(tokens[0], salt=SALT)
            if (not isinstance(data, dict) or not isinstance(data.get('binding'), str)
                    or not constant_time_compare(data['binding'], _binding(request))):
                raise ValueError
            source = data['source']
            params = _params(source, data['params'])
            if source == 'courses' and not flag_enabled('backoffice_course_workspace'):
                raise ValueError
            route = 'backoffice_workspace_search' if source == 'search' else 'backoffice_workspace_courses'
            result = {'workspace_return_url': reverse(route) + '?' + urlencode(params),
                      'workspace_return_label': 'Qidiruv natijalariga qaytish' if source == 'search' else 'Kurslar ro‘yxatiga qaytish',
                      'workspace_return_token': tokens[0],
                      'workspace_return_query': '&' + urlencode({'return_to': tokens[0]})}
        except (signing.BadSignature, ValueError, TypeError, KeyError, AttributeError):
            pass
    request._workspace_return = result
    return result


def return_context(request):
    return _read(request)


def with_return(request, url):
    """Propagate only to known local detail routes, never to a caller's URL."""
    token = _read(request).get('workspace_return_token')
    if not token:
        return url
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith('/'):
        return url
    try:
        if resolve(parsed.path).view_name not in DESTINATIONS:
            return url
    except Resolver404:
        return url
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key != 'return_to']
    query.append(('return_to', token))
    return urlunsplit(('', '', parsed.path, urlencode(query), parsed.fragment))
