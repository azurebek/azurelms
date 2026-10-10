"""Thin HTTP adapter for the owner design workspace and public theme."""
from functools import wraps
import json
from uuid import UUID

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, RequestDataTooBig
from django.db import DatabaseError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.cache import patch_cache_control
from django.utils.crypto import salted_hmac
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from core import design_service as service
from core.backoffice_workspace import _nav
from core.design_schema import CATALOG, compile_css
from core.flags import flag_enabled

FLAG = 'backoffice_design_workspace'
MAX_BODY = 40000


def _private(response):
    patch_cache_control(response, private=True, no_store=True)
    return response


def _error(code, message, status=400):
    return _private(JsonResponse({'error': {'code': code, 'message': message}}, status=status))


def owner_design(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        # Fresh identity matters when a long-lived browser has lost owner access.
        if not request.user.is_authenticated or not get_user_model().objects.filter(
                pk=request.user.pk, is_active=True, is_superuser=True).exists():
            return _error('forbidden', 'Bu amal faqat platforma egasi uchun.', 403)
        if not flag_enabled(FLAG):
            return _error('unavailable', 'Dizayn ustaxonasi hozir yopiq. O‘zgarish saqlanmadi.', 404)
        try:
            return _private(view(request, *args, **kwargs))
        except service.DesignError as exc:
            return _error(exc.code, exc.message, exc.status)
    return wrapped


@login_required
@require_GET
def studio(request):
    if not get_user_model().objects.filter(pk=request.user.pk, is_active=True, is_superuser=True).exists():
        raise PermissionDenied
    if not flag_enabled(FLAG):
        raise Http404
    scope = salted_hmac('design-workspace', json.dumps([
        request.user.pk, request.session.session_key]), algorithm='sha256').hexdigest()
    return _private(render(request, 'backoffice/workspace/design.html', {
        'design_catalog': CATALOG, 'design_state': service.read_state(request.user),
        'design_scope': scope, 'workspace_nav': _nav(request, 'design'),
        'frontend_v1_title': 'Sayt va dizayn', 'page_title': 'Sayt va dizayn',
    }))


def _operation(value):
    if not isinstance(value, str):
        raise ValueError
    parsed = UUID(value)
    if str(parsed) != value:
        raise ValueError
    return value


@require_GET
@owner_design
def state(request):
    if set(request.GET) - {'operation', 'history_before'} or any(len(v) != 1 for _, v in request.GET.lists()):
        return _error('invalid_request', 'So‘rovni qayta oching.')
    operation = request.GET.get('operation')
    if operation is not None:
        try:
            operation = _operation(operation)
        except (ValueError, AttributeError):
            return _error('invalid_operation', 'Amal raqami yaroqsiz.')
    before = request.GET.get('history_before')
    if before is not None:
        if (not before.isascii() or not before.isdecimal() or len(before) > 19
                or not 1 <= int(before) <= 9223372036854775807):
            return _error('invalid_cursor', 'Tarix sahifasini qayta oching.')
        before = int(before)
    return JsonResponse(service.read_state(request.user, operation=operation, history_before=before))


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('nonfinite')


@require_POST
@csrf_protect
@owner_design
def command(request):
    if request.content_type != 'application/json':
        return _error('invalid_request', 'So‘rov JSON shaklida bo‘lishi kerak.')
    try:
        if len(request.body) > MAX_BODY:
            return _error('too_large', 'Sozlamalar hajmi juda katta.', 413)
        data = json.loads(request.body.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant)
        if not isinstance(data, dict) or set(data) != {'operation', 'command', 'payload'}:
            raise ValueError
        operation = _operation(data['operation'])
        if not isinstance(data['command'], str) or not isinstance(data['payload'], dict):
            raise ValueError
    except RequestDataTooBig:
        return _error('too_large', 'Sozlamalar hajmi juda katta.', 413)
    except (ValueError, UnicodeDecodeError, TypeError, AttributeError, RecursionError):
        return _error('invalid_request', 'So‘rov yaroqsiz. Hech narsa saqlanmadi.')
    return JsonResponse(service.execute(request.user, data['command'], operation, data['payload'], request=request))


@require_GET
def theme_css(request):
    """Public, screen-only projection; never expose private editorial metadata."""
    css = ''
    try:
        if flag_enabled(FLAG):
            css = compile_css(service.read_published()['value'])
    except (DatabaseError, ValueError, service.DesignError):
        # Static token files remain usable during an additive migration/outage.
        pass
    response = HttpResponse(css, content_type='text/css; charset=utf-8')
    response['X-Content-Type-Options'] = 'nosniff'
    patch_cache_control(response, no_store=True)
    return response
