"""Frozen library presentation and opt-in form snapshots, not access policy."""
import json

from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import patch_cache_control
from django.utils.crypto import constant_time_compare, salted_hmac

from core.flags import flag_enabled
from core.frontend_v1 import teacher_v1_navigation
from .backoffice_forms import LibraryResourceForm
from .models import FILE_KIND_LABELS, ResourceLanguage, ResourceLevel, ResourceType


def enabled(request):
    # An in-flight V1 form keeps its error/guard contract during rollback.
    return flag_enabled('frontend_v1_library') or request.POST.get('frontend_v1_library') == '1'


def revision(user, resource, action, lesson_id=None):
    state = None
    if resource is not None:
        state = [resource.pk, str(resource.updated_at), resource.is_archived,
                 resource.version, resource.checksum,
                 [str(resource._meta.get_field(name).value_from_object(resource))
                  for name in LibraryResourceForm.Meta.fields],
                 list(resource.tags.order_by('pk').values_list('pk', 'name')),
                 list(resource.lesson_links.order_by('pk').values_list('pk', 'lesson_id'))]
    return salted_hmac('frontend-v1-library', json.dumps([user.pk, action, lesson_id, state]), algorithm='sha256').hexdigest()


def write_error(request, resource, action, lesson_id=None):
    if not enabled(request):
        return None
    if not constant_time_compare(request.POST.get('library_revision', ''), revision(request.user, resource, action, lesson_id)):
        return 'Material yoki uning bog‘lanishlari o‘zgargan. Yozuv saqlanmadi. Matningizni olib, sahifani qayta oching.', 409
    if request.POST.get('confirm_scope') != 'yes':
        return 'Amal doirasini tasdiqlang. Hech narsa saqlanmadi.', 400
    return None


def style_form(form):
    for field in form.fields.values():
        if getattr(field.widget, 'input_type', None) != 'checkbox':
            field.widget.attrs['class'] = 'c-field'
    return form


def invalid_filters(request):
    """V1 never silently substitutes an unknown/repeated filter."""
    if not enabled(request):
        return False
    allowed = {'q', 'type', 'language', 'level', 'course', 'topic', 'tag', 'kind', 'archived', 'page'}
    if any(key not in allowed or len(values) != 1 for key, values in request.GET.lists()):
        return True
    for key, values in [('type', ResourceType.values), ('language', ResourceLanguage.values),
                        ('level', ResourceLevel.values), ('kind', FILE_KIND_LABELS), ('archived', ['1'])]:
        value = request.GET.get(key, '').strip()
        if value and value not in values:
            return True
    for key in ('course', 'page'):
        value = request.GET.get(key, '').strip()
        if value and (not value.isascii() or not value.isdecimal() or len(value) > 18 or int(value) < 1):
            return True
    return False


def render_library(request, page, context, *, status=200):
    if not enabled(request):
        legacy = {'list': 'list', 'form': 'form', 'picker': 'picker'}[page]
        return render(request, f'backoffice/library_{legacy}.html', context, status=status)
    context.update(teacher_v1_navigation('teacher_dashboard'))
    if not flag_enabled('frontend_v1_teacher'):
        context['frontend_v1_legacy_nav'] += [item for item in context['frontend_v1_nav'] if item['name'].startswith('teacher_')]
        context['frontend_v1_nav'] = [item for item in context['frontend_v1_nav'] if not item['name'].startswith('teacher_')]
    context.update(active_nav='library_backoffice:resources',
                   frontend_v1_title={'list': 'Material kutubxonasi', 'form': 'Material ma’lumotlari', 'picker': 'Darsga material tanlash', 'conflict': 'Amal bajarilmadi'}[page])
    context['library_invalid_filters'] = invalid_filters(request)
    context['library_clean_url'] = request.path
    if page == 'form':
        style_form(context['form'])
        resource = context['resource']
        context['library_revision'] = request.POST.get('library_revision', '') if request.method == 'POST' else revision(request.user, resource, 'save')
        context['archive_revision'] = revision(request.user, resource, 'archive')
        context['delete_revision'] = revision(request.user, resource, 'delete')
    if page == 'picker':
        context['editor_ready'] = flag_enabled('frontend_v1_editors')
        context['attached_materials'] = context['lesson'].materials.select_related('resource').order_by('order', 'pk')
        for resource in context['page_obj']:
            resource.attach_revision = revision(request.user, resource, 'attach', context['lesson'].pk)
        params = request.GET.copy()
        params['page'] = str(context['page_obj'].number)
        context['picker_return_query'] = params.urlencode()
    response = render(request, f'frontend_v1/library/{page}.html', context, status=status)
    patch_cache_control(response, private=True, no_store=True)
    return response


def action_error(request, error, resource, lesson=None):
    message, status = error
    return render_library(request, 'conflict', dict(library_error=message, resource=resource,
        reload_url=reverse('library_backoffice:lesson_picker', args=[lesson.pk]) if lesson else reverse('library_backoffice:resource_edit', args=[resource.pk])), status=status)
