"""Course-centered backoffice HTTP adapter; services own content mutations."""
from functools import wraps
import json
import re
from urllib.parse import parse_qs, urlencode, urlparse

import bleach
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Prefetch
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.http import require_http_methods

from core.access import teacher_course_queryset
from core.audit import record_audit_event
from core.flags import flag_enabled
from core.workspace_forms import (WorkspaceCourseForm, WorkspaceLessonForm,
                                  WorkspaceModuleForm, WorkspaceUploadForm)
from courses import authoring_service as authoring
from courses.models import Course, Lesson, Module
from frontend.templatetags.bleach_tags import sanitize
from library import services as materials_service
from library.models import LibraryResource, MaterialAudience

FLAG = 'backoffice_course_workspace'


def workspace_view(view):
    @login_required
    @require_http_methods(['GET', 'POST'])
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_active or not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied
        if not flag_enabled(FLAG):
            if request.method == 'POST':
                response = render(request, 'backoffice/workspace/unavailable.html', status=409)
                patch_cache_control(response, private=True, no_store=True)
                return response
            raise Http404
        if any(len(values) != 1 for _, values in request.GET.lists()) or any(
                len(values) != 1 for _, values in request.POST.lists()):
            return HttpResponseBadRequest('Takrorlangan maydon. Hech narsa saqlanmadi.')
        response = view(request, *args, **kwargs)
        patch_cache_control(response, private=True, no_store=True)
        return response
    return wrapped


def _nav(request, active):
    from core.backoffice_navigation import navigation
    return navigation(request, active)


def _render(request, page, context, status=200):
    context.update(workspace_nav=_nav(request, 'home' if page == 'home' else 'courses'),
                   workspace_support_enabled=flag_enabled('backoffice_student_support'),
                   workspace_design_enabled=flag_enabled('backoffice_design_workspace'),
                   frontend_v1_title=context.get('page_title', 'Kurs tayyorlash'))
    return render(request, f'backoffice/workspace/{page}.html', context, status=status)


def _id(value):
    if not value or not value.isascii() or not value.isdecimal() or len(value) > 18 or int(value) < 1:
        raise Http404
    return int(value)


def draft_scope(request, course_id, lesson_id=None, module_id=None, *, kind='lesson'):
    identity = [request.user.pk, request.session.session_key, kind, course_id,
                lesson_id or f'new:{module_id or ""}']
    return salted_hmac('backoffice-workspace-draft', json.dumps(identity), algorithm='sha256').hexdigest()


def _saved(request, scope):
    # Only a successful server write can issue a draft-clear acknowledgement.
    nonce = request.POST.get('draft_submission_id', '')
    request.session['workspace_saved'] = {'scope': scope, 'submission_id': nonce if re.fullmatch(r'[A-Za-z0-9-]{1,64}', nonce) else ''}


def _saved_context(request):
    receipt = request.session.pop('workspace_saved', {})
    return {'saved_scope': receipt.get('scope', ''), 'saved_submission_id': receipt.get('submission_id', '')}


def _add_errors(form, error):
    if hasattr(error, 'error_dict'):
        for key, values in error.error_dict.items():
            form.add_error(key if key in form.fields else None, values)
    else:
        form.add_error(None, error)


@workspace_view
def home(request):
    if request.method != 'GET':
        return HttpResponseBadRequest('Bu sahifa faqat ko‘rish uchun.')
    return _render(request, 'home', {'page_title': 'Ish stoli', 'recent_courses':
                   teacher_course_queryset(request.user).order_by('-created_at', '-pk')[:6]})


@workspace_view
def courses(request):
    if request.method != 'GET':
        return HttpResponseBadRequest('Bu sahifa faqat ko‘rish uchun.')
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'all')
    if status_filter not in {'all', 'active', 'draft'}:
        return HttpResponseBadRequest('Kurs holatini qayta tanlang.')
    rows = teacher_course_queryset(request.user).filter(title__icontains=query).annotate(
        module_count=Count('modules', distinct=True), lesson_count=Count('modules__lessons', distinct=True)
    ).order_by('-created_at', '-pk')
    if status_filter != 'all':
        rows = rows.filter(is_active=status_filter == 'active')
    return _render(request, 'course_list', {'page_title': 'Kurslar', 'q': query,
                                          'status_filter': status_filter,
                                          'page_obj': Paginator(rows, 12).get_page(request.GET.get('page'))})


@workspace_view
def course_editor(request, course_id=None):
    obj = get_object_or_404(teacher_course_queryset(request.user), pk=course_id) if course_id else None
    form = WorkspaceCourseForm(request.POST if request.method == 'POST' else None, instance=obj, user=request.user)
    if not obj:
        form.initial['instructor'] = request.user.pk
    scope = draft_scope(request, course_id, kind='course')
    revision = request.POST.get('course_revision', '') if request.method == 'POST' else authoring.course_revision(request.user, obj)
    status = 200
    if request.method == 'POST':
        status = 400
        if form.is_valid():
            try:
                obj, changed = authoring.save_course(actor=request.user, data=form.cleaned_data,
                    expected_revision=revision, course_id=course_id, request=request)
            except authoring.AuthoringConflict as error:
                _add_errors(form, error)
                status = 409
            except ValidationError as error:
                _add_errors(form, error)
            except Course.DoesNotExist:
                raise Http404
            else:
                _saved(request, scope)
                messages.success(request, 'Kurs saqlandi.' if changed else 'Kurs allaqachon shu holatda saqlangan.')
                return redirect('backoffice_workspace_course', course_id=obj.pk)
        if course_id:
            obj = get_object_or_404(teacher_course_queryset(request.user), pk=course_id)
    return _render(request, 'course_form', {'page_title': 'Kurs ma’lumotlari' if obj else 'Yangi kurs',
        'course': obj, 'form': form, 'revision': revision, 'course_revision': revision,
        'draft_scope': scope, **_saved_context(request),
        'conflict': status == 409}, status)


def material_revision(actor, lesson):
    state = [actor.pk, lesson.pk, lesson.module_id,
             list(lesson.materials.order_by('pk').values_list('pk', 'resource_id', 'updated_at'))]
    return salted_hmac('workspace-materials', json.dumps(state, default=str), algorithm='sha256').hexdigest()


def _write_material(request, course_id, lesson_id, form=None):
    """Keep the existing upload/attachment policy and private storage boundary."""
    stored_file = None
    uploaded_resource = None
    try:
        with transaction.atomic():
            actor = get_object_or_404(get_user_model().objects.select_for_update(), pk=request.user.pk)
            if not actor.is_active or not (actor.is_staff or actor.is_superuser):
                raise PermissionDenied
            course = get_object_or_404(teacher_course_queryset(actor).select_for_update(), pk=course_id)
            lesson = get_object_or_404(Lesson.objects.select_for_update(), pk=lesson_id, module__course=course)
            if not constant_time_compare(request.POST.get('material_revision', ''), material_revision(request.user, lesson)):
                raise authoring.AuthoringConflict()
            if form is not None:
                resource = form.save(commit=False)
                resource.course = course
                materials_service.apply_upload(resource, form.uploaded_file, actor=request.user)
                uploaded_resource = resource
                resource.save()
                stored_file = (resource.file.storage, resource.file.name)
                record_audit_event(action='library.resource.create', request=request, target=resource,
                                   after={'version': resource.version, 'file_kind': resource.file_kind, 'size': resource.file_size})
            else:
                resource = get_object_or_404(LibraryResource.objects.select_for_update(),
                                             pk=_id(request.POST.get('resource_id')), is_archived=False)
            material, changed = materials_service.attach_to_lesson(lesson, resource, actor=request.user)
            if changed:
                record_audit_event(action='library.material.attach', request=request, target=material,
                                   after={'lesson': lesson.pk, 'resource': resource.pk})
            return changed
    except Exception:
        # FileField writes bytes before its INSERT. Also clean up when that
        # INSERT itself fails, not just when a later attachment/audit fails.
        if stored_file is None and uploaded_resource is not None and uploaded_resource.file._committed:
            stored_file = (uploaded_resource.file.storage, uploaded_resource.file.name)
        if stored_file is not None:
            stored_file[0].delete(stored_file[1])
        raise


def _preview_html(value):
    # Use the learner's sanitizer, then keep embeds out of the management page.
    from frontend.templatetags.bleach_tags import ALLOWED_TAGS, ALLOWED_ATTRIBUTES, ALLOWED_STYLES
    from bleach.css_sanitizer import CSSSanitizer
    return bleach.clean(str(sanitize(value)), tags=[tag for tag in ALLOWED_TAGS if tag != 'iframe'],
                        attributes={key: val for key, val in ALLOWED_ATTRIBUTES.items() if key != 'iframe'},
                        css_sanitizer=CSSSanitizer(allowed_css_properties=ALLOWED_STYLES), strip=True)


def _preview_video(value):
    parsed = urlparse(value or '')
    if parsed.scheme not in ('http', 'https'):
        return ''
    video_id = ''
    if parsed.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'www.youtube-nocookie.com'):
        video_id = parse_qs(parsed.query).get('v', [''])[0] if parsed.path == '/watch' else parsed.path.split('/')[-1]
    elif parsed.hostname == 'youtu.be':
        video_id = parsed.path.lstrip('/')
    return f'https://www.youtube-nocookie.com/embed/{video_id}' if re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id) else ''


@workspace_view
def course(request, course_id):
    obj = get_object_or_404(teacher_course_queryset(request.user), pk=course_id)
    action = request.POST.get('action') if request.method == 'POST' else None
    lesson_actions = {'lesson_save', 'lesson_preview', 'material_upload', 'material_attach'}
    selected_id = request.POST.get('lesson_id') if action in lesson_actions else request.GET.get('lesson')
    if action in lesson_actions and request.GET.get('lesson') and request.GET['lesson'] != selected_id:
        return HttpResponseBadRequest('Dars manzili mos kelmadi. Hech narsa saqlanmadi.')
    lesson = get_object_or_404(Lesson.objects.select_related('module'), pk=_id(selected_id), module__course=obj) if selected_id else None
    module_id = request.GET.get('module')
    # Draft identity belongs to the form that was opened, even when the author
    # chooses a different destination module before previewing or saving.
    source_module = get_object_or_404(Module, pk=_id(module_id), course=obj) if module_id and not lesson else None
    if lesson:
        module_id = str(lesson.module_id)
    if action in {'lesson_save', 'lesson_preview'} and not lesson:
        module_id = request.POST.get('module')
    module = get_object_or_404(Module, pk=_id(module_id), course=obj) if module_id else None
    # Outline edits return to the validated selection, so the browser draft
    # remains attached to the lesson the author was already working on.
    selection_module = source_module or module
    selection = {'lesson': lesson.pk} if lesson else (
        {'module': selection_module.pk, 'new': '1'} if selection_module else {})
    outline_action_url = request.path + ('?' + urlencode(selection) if selection else '')
    initial = {'module': module.pk if module else None, 'order':
               (module.lessons.order_by('-order').values_list('order', flat=True).first() or 0) + 1 if module else 1}
    form = WorkspaceLessonForm(request.POST if action in {'lesson_save', 'lesson_preview'} else None,
                               instance=lesson, user=request.user, course=obj, initial=initial if not lesson else None)
    module_form = WorkspaceModuleForm(request.POST if action in {'module_create', 'module_update'} else None, auto_id='module_%s')
    upload_form = WorkspaceUploadForm(request.POST if action == 'material_upload' else None,
                                     request.FILES if action == 'material_upload' else None, auto_id='upload_%s')
    draft_module = source_module or module
    scope = draft_scope(request, obj.pk, lesson.pk if lesson else None, draft_module.pk if draft_module else None)
    outline_token = authoring.outline_revision(request.user, obj)
    lesson_token = authoring.lesson_revision(request.user, lesson) if lesson else outline_token
    material_token = material_revision(request.user, lesson) if lesson else ''
    status, action_error, preview_unsaved = 200, '', False
    preview = {'title': lesson.title if lesson else '', 'content': lesson.content if lesson else '',
               'video_url': lesson.video_url if lesson else ''}
    if request.method == 'POST':
        status = 400
        try:
            if action in {'module_create', 'module_update'}:
                outline_token = request.POST.get('outline_revision', '')
                if module_form.is_valid():
                    changed_module, _ = authoring.save_module(actor=request.user, course_id=obj.pk,
                        title=module_form.cleaned_data['title'], expected_revision=outline_token,
                        module_id=_id(request.POST.get('module_id')) if action == 'module_update' else None, request=request)
                    messages.success(request, 'Modul saqlandi.')
                    return redirect(f'{request.path}?module={changed_module.pk}&new=1'
                                    if action == 'module_create' else outline_action_url)
            elif action == 'module_move':
                outline_token = request.POST.get('outline_revision', '')
                authoring.move_module(actor=request.user, course_id=obj.pk, module_id=_id(request.POST.get('module_id')),
                    direction=request.POST.get('direction'), expected_revision=outline_token, request=request)
                messages.success(request, 'Modullar tartibi saqlandi.')
                return redirect(outline_action_url)
            elif action in {'lesson_save', 'lesson_preview'}:
                lesson_token = request.POST.get('lesson_revision', '')
                if form.is_valid():
                    if action == 'lesson_preview':
                        preview, preview_unsaved, status = form.cleaned_data, True, 200
                    else:
                        saved, changed = authoring.save_lesson(actor=request.user, course_id=obj.pk, data=form.cleaned_data,
                            expected_revision=lesson_token, lesson_id=lesson.pk if lesson else None, request=request)
                        _saved(request, scope)
                        messages.success(request, 'Dars saqlandi.' if changed else 'Dars allaqachon shu holatda saqlangan.')
                        return redirect(f'{request.path}?lesson={saved.pk}')
            elif action in {'material_upload', 'material_attach'}:
                if lesson is None:
                    raise Http404
                material_token = request.POST.get('material_revision', '')
                if action == 'material_attach' or upload_form.is_valid():
                    _write_material(request, obj.pk, lesson.pk, upload_form if action == 'material_upload' else None)
                    messages.success(request, 'Material darsga biriktirildi.')
                    return redirect(f'{request.path}?lesson={lesson.pk}#materials')
            else:
                action_error = 'Amal tanilmadi. Hech narsa saqlanmadi.'
        except authoring.AuthoringConflict as error:
            action_error, status = ' '.join(error.messages), 409
        except ValidationError as error:
            action_error = ' '.join(error.messages)
        except (Course.DoesNotExist, Module.DoesNotExist, Lesson.DoesNotExist):
            raise Http404
        # A bound ModelForm mutates its instance even on preview/invalid POST.
        if lesson:
            lesson.refresh_from_db()
    modules = obj.modules.prefetch_related(Prefetch('lessons', queryset=Lesson.objects.order_by('order', 'pk'))).order_by('order', 'pk')
    resources = LibraryResource.objects.filter(is_archived=False)
    resource_q = request.GET.get('resource_q', '').strip()
    if resource_q:
        resources = resources.filter(title__icontains=resource_q)
    if lesson:
        resources = resources.exclude(lesson_links__lesson=lesson)
    cohorts = list(obj.cohorts.filter(is_active=True).order_by('-start_date', '-pk'))
    for cohort in cohorts:
        params = {'cohort': cohort.pk}
        if lesson:
            params.update(lesson=lesson.pk, action='release')
        cohort.release_url = reverse('teacher_release') + '?' + urlencode(params)
    materials = list(materials_service.teacher_materials(lesson)) if lesson else []
    preview_materials = []
    visibility_time = timezone.now()
    for material in materials:
        # The canonical predicate decides visibility. The remaining branches
        # only explain its denial; they never grant access independently.
        if materials_service.material_visible_to_student(material, now=visibility_time):
            material.workspace_status = 'O‘quvchiga ko‘rinadi'
            preview_materials.append(material)
        elif material.resource.is_teacher_only or material.audience != MaterialAudience.STUDENT:
            material.workspace_status = 'Faqat ustozga'
        elif not material.is_visible:
            material.workspace_status = 'O‘quvchidan yashirilgan'
        elif material.available_from:
            material.workspace_status = 'Belgilangan vaqtda ochiladi'
        else:
            material.workspace_status = 'O‘quvchiga yopiq'
    return _render(request, 'course', {'page_title': obj.title, 'course': obj, 'modules': modules,
        'lesson': lesson, 'lesson_form': form, 'module_form': module_form, 'upload_form': upload_form,
        'selected_module_id': module.pk if module else None, 'creating_lesson': bool(module and not lesson),
        'materials': materials, 'preview_materials': preview_materials,
        'resources': resources.order_by('-updated_at', '-pk')[:20], 'resource_q': resource_q,
        'cohorts': cohorts, 'outline_revision': outline_token, 'lesson_revision': lesson_token,
        'outline_action_url': outline_action_url,
        'material_revision': material_token, 'draft_scope': scope,
        **_saved_context(request),
        'preview_title': preview['title'], 'preview_content': _preview_html(preview['content']),
        'preview_video_url': _preview_video(preview['video_url']), 'preview_unsaved': preview_unsaved,
        'show_preview': preview_unsaved or request.GET.get('view') == 'preview',
        'action_error': action_error, 'conflict': status == 409}, status)
